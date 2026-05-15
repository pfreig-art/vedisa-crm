"""Endpoints IA - Drawer contextual y gestion de proveedores LLM."""
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.llm_router import llm_router
from app.providers.base import LLMRequest, LLMMessage, LLMIntent

router = APIRouter()


# ---- Schemas de entrada/salida -----------------------------------

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


# ---- Prompts por intencion ---------------------------------------

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


# ---- Endpoints ---------------------------------------------------

@router.post("/analyze/solicitud", response_model=AIAnalysis)
async def analyze_solicitud(req: AnalyzeRequest):
    """Analiza una solicitud CRM y devuelve resumen, riesgos y acciones sugeridas."""
    if not req.context and not req.solicitud_id:
        raise HTTPException(400, "Se requiere solicitud_id o context")

    context_str = json.dumps(req.context or {"solicitud_id": req.solicitud_id}, ensure_ascii=False)
    intent_prompt = INTENT_PROMPTS.get(req.intent, INTENT_PROMPTS["summarize"])

    llm_request = LLMRequest(
        messages=[
            LLMMessage(role="system", content=SYSTEM_PROMPT),
            LLMMessage(
                role="user",
                content=f"{intent_prompt}\n\nContexto CRM:\n{context_str}",
            ),
        ],
        intent=LLMIntent(req.intent) if req.intent in LLMIntent.__members__.values() else LLMIntent.GENERAL,
        max_tokens=1024,
        temperature=0.2,
        response_format="json",
    )

    response = await llm_router.generate(llm_request, provider_name=req.provider)

    try:
        parsed = json.loads(response.content)
    except json.JSONDecodeError:
        parsed = {"summary": response.content, "risks": [], "next_actions": [], "confidence": 0.5}

    return AIAnalysis(
        summary=parsed.get("summary", ""),
        risks=parsed.get("risks", []),
        next_actions=parsed.get("next_actions", []),
        confidence=parsed.get("confidence", 0.7),
        provider=response.provider,
        model=response.model,
        tokens_used=response.tokens_used,
        latency_ms=response.latency_ms,
        sources=["crm_context"],
    )


@router.get("/providers")
async def list_providers():
    """Lista proveedores disponibles y su estado."""
    return {"providers": llm_router.available_providers()}


@router.post("/providers/test")
async def test_provider(name: str):
    """Test de conectividad para un proveedor concreto."""
    result = await llm_router.test_provider(name)
    return result
