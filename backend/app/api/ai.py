"""Endpoints IA - Drawer contextual y gestion de proveedores LLM."""
import hashlib
import json
import time
from fastapi import APIRouter, HTTPException, Depends, Response
from pydantic import BaseModel
from typing import Any, Optional
from fastapi.responses import StreamingResponse

import structlog

from app.services.llm_router import llm_router
from app.providers.base import LLMRequest, LLMMessage, LLMIntent
from app.services.ai_prompts import (
    build_brief_prompt,
    fallback_response,
    parse_brief_response,
)
from app.services.schema_summary import get_schema_summary
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.core.auth import get_current_user
from app.core.models import Usuario
from app.services.ai_audit import log_ai_call, get_audit_log, get_provider_metrics


_brief_log = structlog.get_logger("vedisa.ai.brief")

router = APIRouter()

# ---- Schemas de entrada/salida ----------------------------------

class AnalyzeRequest(BaseModel):
    solicitud_id: Optional[str] = None
    context: Optional[dict] = None  # AIContextBundle pre-construido
    intent: str = "summarize"  # summarize | risk_review | next_action
    provider: Optional[str] = None  # forzar proveedor concreto


class AIAnalysis(BaseModel):
    summary: str
    risks: list[str]
    next_actions: list[str]
    confidence: float
    provider: str
    model: str
    tokens_used: int
    latency_ms: int
    sources: list[str]


class ChatRequest(BaseModel):
    messages: list[dict]  # [{role, content}]
    provider: Optional[str] = None
    model: Optional[str] = None
    context: Optional[dict] = None


class ChatResponse(BaseModel):
    content: str
    model: str
    provider: str
    tokens_used: int
    latency_ms: int


# ---- Prompts por intencion -------------------------------------

SYSTEM_PROMPT = """Eres un asistente CRM experto en analisis comercial y gestion de obras.
Tu objetivo es ayudar al equipo de ventas y estudios a tomar decisiones rapidas y precisas.
Responde SIEMPRE en JSON valido con exactamente estas claves:
{"summary": string, "risks": [string], "next_actions": [string], "confidence": float 0-1}"""

INTENT_PROMPTS = {
    "summarize": "Resume el estado actual de esta solicitud CRM en 2-3 frases.",
    "risk_review": "Identifica los principales riesgos y alertas de esta solicitud.",
    "next_action": "Propone las 2-3 acciones mas urgentes que debe hacer el comercial o tecnico.",
    "pipeline_cluster": "Analiza el conjunto de solicitudes y detecta patrones, cuellos de botella y prioridades.",
}

# ---- Endpoints -------------------------------------------------

@router.post("/analyze/solicitud")
async def analyze_solicitud(request: AnalyzeRequest):
    """Analiza una solicitud CRM con el LLM seleccionado."""
    intent_prompt = INTENT_PROMPTS.get(request.intent, INTENT_PROMPTS["summarize"])
    context_str = json.dumps(request.context or {}, ensure_ascii=False, indent=2)

    messages = [
        LLMMessage(role="system", content=SYSTEM_PROMPT),
        LLMMessage(
            role="user",
            content=f"{intent_prompt}\n\nContexto de la solicitud:\n{context_str}",
        ),
    ]

    import time
    start = time.perf_counter()
    try:
        llm_request = LLMRequest(messages=messages)
        response = await llm_router.generate(llm_request, provider_name=request.provider)
        latency_ms = int((time.perf_counter() - start) * 1000)

        try:
            data = json.loads(response.content)
        except json.JSONDecodeError:
            data = {
                "summary": response.content,
                "risks": [],
                "next_actions": [],
                "confidence": 0.7,
            }

        return AIAnalysis(
            summary=data.get("summary", ""),
            risks=data.get("risks", []),
            next_actions=data.get("next_actions", []),
            confidence=data.get("confidence", 0.7),
            provider=response.provider,
            model=response.model,
            tokens_used=response.tokens_used,
            latency_ms=latency_ms,
            sources=[f"solicitud:{request.solicitud_id}"] if request.solicitud_id else [],
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/chat")
async def chat(request: ChatRequest):
    """Endpoint de chat directo con el router LLM."""
    messages = [
        LLMMessage(role=m["role"], content=m["content"])
        for m in request.messages
    ]
    try:
        llm_request = LLMRequest(messages=messages)
        response = await llm_router.generate(llm_request, provider_name=request.provider)
        return ChatResponse(
            content=response.content,
            model=response.model,
            provider=response.provider,
            tokens_used=response.tokens_used,
            latency_ms=response.latency_ms,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


# ---------------------------------------------------------------------------
# Sprint E2: brief contextual con cache 60s
# ---------------------------------------------------------------------------

class BriefRequest(BaseModel):
    mode: str = "default"  # default | dashboard | solicitud | obra
    context: Optional[dict] = None
    force_refresh: bool = False


class BriefResponse(BaseModel):
    summary: str
    bullets: list[str]
    suggested_questions: list[str]
    chart_specs: list[dict]
    model: str
    provider: str
    tokens_used: int
    latency_ms: int


_BRIEF_CACHE_TTL = 60.0  # segundos
_brief_cache: dict[str, tuple[float, dict]] = {}


def _stable_json(value: Any) -> str:
    """Serializa un valor de forma estable (sort_keys) para hashing."""
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(value)


def _make_cache_key(user_id: str, mode: str, context: Any) -> str:
    payload = f"{user_id}::{mode}::{_stable_json(context)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@router.post("/brief", response_model=BriefResponse)
async def ai_brief(
    request: BriefRequest,
    response: Response,
    db: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """Genera un brief contextual al abrir el drawer IA (Sprint E2).

    Fuerza provider='openai' (gpt-4o) por decision de diseno: el brief
    queremos uniforme entre tenants aunque el primary del router sea otro.
    Cachea 60s por (user.id, mode, context). Si el provider falla o el JSON
    no parsea, devuelve un fallback graceful con status 200.
    """
    mode = (request.mode or "default").strip().lower()
    cache_key = _make_cache_key(current_user.id, mode, request.context)

    # --- Cache hit ----------------------------------------------------
    if not request.force_refresh:
        cached = _brief_cache.get(cache_key)
        if cached is not None:
            expires_at, payload = cached
            if expires_at > time.monotonic():
                response.headers["X-Brief-Cached"] = "true"
                return payload
            _brief_cache.pop(cache_key, None)

    response.headers["X-Brief-Cached"] = "false"

    # --- Construir prompts -------------------------------------------
    try:
        schema = get_schema_summary()
    except Exception as exc:  # pragma: no cover - defensivo
        _brief_log.warning("schema_summary_error", error=str(exc))
        schema = ""

    msgs = build_brief_prompt(mode, request.context, schema)
    llm_messages = [LLMMessage(role=m["role"], content=m["content"]) for m in msgs]
    llm_request = LLMRequest(messages=llm_messages, response_format="json")

    start = time.perf_counter()
    parsed: dict | None = None
    provider_used = "openai"
    model_used = ""
    tokens_used = 0
    success = True
    error_msg: Optional[str] = None

    try:
        # Forzamos provider='openai' (gpt-4o) por decision de diseno del brief.
        llm_response = await llm_router.generate(llm_request, provider_name="openai")
        provider_used = llm_response.provider
        model_used = llm_response.model
        tokens_used = llm_response.tokens_used
        parsed = parse_brief_response(llm_response.content)
        if not parsed.get("summary"):
            # JSON parseable pero sin summary util -> fallback.
            parsed = fallback_response("respuesta sin summary util")
            success = False
            error_msg = "respuesta sin summary util"
    except Exception as exc:
        success = False
        error_msg = str(exc)
        parsed = fallback_response(error_msg)
        _brief_log.warning(
            "brief_provider_error", error=error_msg, mode=mode
        )

    latency_ms = int((time.perf_counter() - start) * 1000)

    # --- Auditar la llamada ------------------------------------------
    try:
        await log_ai_call(
            db,
            endpoint="brief",
            provider=provider_used or "openai",
            model=model_used or "unknown",
            prompt_tokens=0,
            completion_tokens=tokens_used,
            latency_ms=latency_ms,
            success=success,
            error_msg=error_msg,
            solicitud_id=None,
            usuario_id=current_user.id,
        )
    except Exception as exc:  # pragma: no cover
        _brief_log.warning("audit_log_error", error=str(exc))

    payload = {
        "summary": parsed.get("summary", ""),
        "bullets": parsed.get("bullets", []),
        "suggested_questions": parsed.get("suggested_questions", []),
        "chart_specs": parsed.get("chart_specs", []),
        "model": model_used or "fallback",
        "provider": provider_used or "openai",
        "tokens_used": tokens_used,
        "latency_ms": latency_ms,
    }

    # --- Guardar en cache solo si fue exito ---------------------------
    if success:
        _brief_cache[cache_key] = (
            time.monotonic() + _BRIEF_CACHE_TTL,
            payload,
        )

    return payload


def _reset_brief_cache() -> None:
    """Util para tests."""
    _brief_cache.clear()


@router.get("/providers")
async def list_providers():
    """Lista los proveedores disponibles y su estado."""
    return llm_router.available_providers()


@router.get("/test/{provider_name}")
async def test_provider(provider_name: str):
    """Prueba un proveedor especifico con un health check."""
    return await llm_router.test_provider(provider_name)


@router.post("/providers/test")
async def test_provider_post(body: dict):
    """(Legacy) Prueba un proveedor especifico."""
    name = body.get("name")
    if not name:
        raise HTTPException(status_code=422, detail="name is required")
    return await llm_router.test_provider(name)


@router.get("/health")
async def health_check(provider: Optional[str] = None):
    """Health check general o de un proveedor especifico."""
    if provider:
        result = await llm_router.test_provider(provider)
        return {"status": result["status"], "providers": [result]}
    providers = llm_router.available_providers()
    return {
        "status": "ok" if any(p["available"] for p in providers) else "degraded",
        "providers": providers,
    }


# ---- Observabilidad IA -----------------------------------------------

@router.get("/audit", tags=["IA"])
async def get_ai_audit(
    provider: Optional[str] = None,
    endpoint: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_session),
):
    """Devuelve el log de auditoria de llamadas al LLM."""
    logs = await get_audit_log(
        db,
        provider=provider,
        endpoint=endpoint,
        limit=limit,
        offset=offset,
    )
    return {"items": [log.dict() for log in logs], "count": len(logs)}


@router.get("/metrics", tags=["IA"])
async def get_ai_metrics(db: AsyncSession = Depends(get_session)):
    """Agrega metricas por proveedor: llamadas, tokens, latencia, tasa de exito."""
    return await get_provider_metrics(db)
