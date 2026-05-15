"""LLMRouterService - Orquesta proveedores LLM con fallback y politica configurable.

Flujo:
  1. Selecciona proveedor primario segun settings.LLM_PRIMARY_PROVIDER
  2. Si falla o no disponible, intenta el fallback
  3. Registra latencia, tokens y proveedor en cada intento
  4. Devuelve LLMResponse normalizado independiente del proveedor
"""
import time
import asyncio
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings
from app.providers.base import LLMProvider, LLMRequest, LLMResponse
from app.providers.openai_provider import OpenAIProvider
from app.providers.anthropic_provider import AnthropicProvider
from app.providers.gemini_provider import GeminiProvider
from app.providers.deepseek_provider import DeepSeekProvider
from app.providers.gateway_provider import GatewayProvider

log = structlog.get_logger()


class LLMRouterService:
    """Router multi-proveedor con fallback automatico."""

    def __init__(self):
        self._providers: dict[str, LLMProvider] = {
            "openai": OpenAIProvider(),
            "anthropic": AnthropicProvider(),
            "gemini": GeminiProvider(),
            "deepseek": DeepSeekProvider(),
            "openrouter": GatewayProvider(name="openrouter"),
            "litellm": GatewayProvider(name="litellm"),
        }

    def available_providers(self) -> list[dict]:
        """Lista de proveedores con su estado de disponibilidad."""
        return [
            {"name": name, "available": p.is_available}
            for name, p in self._providers.items()
        ]

    def _get_provider(self, name: str) -> LLMProvider | None:
        p = self._providers.get(name)
        if p and p.is_available:
            return p
        return None

    async def generate(
        self,
        request: LLMRequest,
        provider_name: str | None = None,
    ) -> LLMResponse:
        """Genera respuesta usando proveedor indicado o el primario con fallback."""
        primary_name = provider_name or settings.LLM_PRIMARY_PROVIDER
        fallback_name = settings.LLM_FALLBACK_PROVIDER

        provider = self._get_provider(primary_name)
        if provider:
            try:
                return await asyncio.wait_for(
                    provider.generate(request),
                    timeout=settings.LLM_TIMEOUT_SECONDS,
                )
            except Exception as e:
                log.warning(
                    "llm_primary_failed",
                    provider=primary_name,
                    error=str(e),
                    fallback=fallback_name,
                )

        # Fallback
        fallback = self._get_provider(fallback_name)
        if fallback:
            return await asyncio.wait_for(
                fallback.generate(request),
                timeout=settings.LLM_TIMEOUT_SECONDS,
            )

        raise RuntimeError(
            f"Ningún proveedor disponible. Primary={primary_name}, Fallback={fallback_name}"
        )

    async def test_provider(self, name: str) -> dict:
        """Test de conectividad para un proveedor concreto."""
        provider = self._providers.get(name)
        if not provider:
            return {"name": name, "status": "not_found"}
        if not provider.is_available:
            return {"name": name, "status": "no_api_key"}
        try:
            from app.providers.base import LLMMessage, LLMIntent
            test_req = LLMRequest(
                messages=[LLMMessage(role="user", content="ping")],
                intent=LLMIntent.GENERAL,
                max_tokens=10,
            )
            start = time.monotonic()
            resp = await asyncio.wait_for(provider.generate(test_req), timeout=15)
            latency = int((time.monotonic() - start) * 1000)
            return {"name": name, "status": "ok", "latency_ms": latency, "model": resp.model}
        except Exception as e:
            return {"name": name, "status": "error", "error": str(e)}


# Singleton
llm_router = LLMRouterService()
