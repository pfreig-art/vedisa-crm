"""Protocol base para todos los proveedores LLM.
Cualquier proveedor nuevo debe implementar esta interfaz.
"""
from typing import Protocol, runtime_checkable
from dataclasses import dataclass, field
from enum import Enum


class LLMIntent(str, Enum):
    """Intenciones de uso del LLM para routing por tarea."""
    SUMMARIZE = "summarize"
    RISK_REVIEW = "risk_review"
    NEXT_ACTION = "next_action"
    PIPELINE_CLUSTER = "pipeline_cluster"
    GENERAL = "general"


@dataclass
class LLMMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMRequest:
    messages: list[LLMMessage]
    intent: LLMIntent = LLMIntent.GENERAL
    max_tokens: int = 1024
    temperature: float = 0.3
    response_format: str = "json"  # "json" | "text"
    metadata: dict = field(default_factory=dict)


@dataclass
class LLMResponse:
    content: str
    provider: str
    model: str
    tokens_used: int
    latency_ms: int
    raw: dict = field(default_factory=dict)


@runtime_checkable
class LLMProvider(Protocol):
    """Interfaz que deben implementar todos los adaptadores de proveedor."""

    @property
    def name(self) -> str:
        """Nombre del proveedor: openai, anthropic, gemini, deepseek, openrouter, litellm"""
        ...

    @property
    def is_available(self) -> bool:
        """True si el proveedor tiene API key configurada y es utilizable."""
        ...

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Invoca el LLM y devuelve LLMResponse normalizado."""
        ...
