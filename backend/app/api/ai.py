"""Endpoints IA - Drawer contextual y gestion de proveedores LLM."""
import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from fastapi.responses import StreamingResponse

from app.services.llm_router import llm_router
from app.providers.base import LLMRequest, LLMMessage, LLMIntent
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.services.ai_audit import log_ai_call, get_audit_log, get_provider_metrics

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
    prompt_tokens: int
    completion_tokens: int


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
        llm_request = LLMRequest(messages=messages, provider=request.provider)
        response = await llm_router.chat(llm_request, provider_name=request.provider)
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
            tokens_used=response.prompt_tokens + response.completion_tokens,
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
        llm_request = LLMRequest(
            messages=messages,
            provider=request.provider,
            model=request.model,
        )
        response = await llm_router.chat(llm_request, provider_name=request.provider)
        return ChatResponse(
            content=response.content,
            model=response.model,
            provider=response.provider,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


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
