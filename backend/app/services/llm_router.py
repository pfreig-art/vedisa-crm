"""LLMRouterService - Orquesta proveedores LLM con fallback y politica configurable.

Flujo:
  1. Selecciona proveedor primario segun settings.LLM_PRIMARY_PROVIDER
  2. Si falla o no disponible, intenta el fallback
  3. Registra latencia, tokens y proveedor en cada intento
  4. Devuelve LLMResponse normalizado independiente del proveedor
"""
import os
import time
import asyncio
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings
from app.providers.base import LLMProvider, LLMRequest, LLMResponse, LLMMessage

log = structlog.get_logger()


def _try_load_provider(name: str, factory):
    """Intenta instanciar un provider; si falla (key ausente u otro error) lo omite."""
    try:
        p = factory()
        log.info("llm_provider_loaded", provider=name)
        return p
    except Exception as e:
        log.warning("llm_provider_skipped", provider=name, reason=str(e))
        return None


class LLMRouterService:
    """Router multi-proveedor con fallback automatico."""

    def __init__(self):
        # Importaciones locales para evitar errores de importacion al nivel de modulo
        from app.providers.openai_provider import OpenAIProvider
        from app.providers.anthropic_provider import AnthropicProvider
        from app.providers.gemini_provider import GeminiProvider
        from app.providers.deepseek_provider import DeepSeekProvider
        from app.providers.gateway_provider import GatewayProvider

        candidates = {
            "openai":     lambda: OpenAIProvider(),
            "anthropic":  lambda: AnthropicProvider(),
            "gemini":     lambda: GeminiProvider(),
            "deepseek":   lambda: DeepSeekProvider(),
            "openrouter": lambda: GatewayProvider(name="openrouter"),
            "litellm":    lambda: GatewayProvider(name="litellm"),
        }

        # Solo registra los proveedores que arrancan sin error
        self._providers: dict[str, LLMProvider] = {}
        for name, factory in candidates.items():
            provider = _try_load_provider(name, factory)
            if provider is not None:
                self._providers[name] = provider

        if not self._providers:
            log.warning("llm_no_providers_available", msg="Ninguna API key configurada. El chat IA no estara disponible.")

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

        # Si el primario pedido no esta disponible, buscar cualquiera disponible
        provider = self._get_provider(primary_name)
        if not provider and self._providers:
            primary_name = next(iter(self._providers))
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
            "No hay proveedores LLM disponibles. Configura al menos una API key en el .env."
        )

    async def test_provider(self, name: str) -> dict:
        """Prueba un proveedor especifico con un prompt minimo."""
        provider = self._providers.get(name)
        if not provider:
            return {"provider": name, "status": "not_configured", "error": "Provider no cargado"}
        try:
            req = LLMRequest(messages=[LLMMessage(role="user", content="di: ok")])
            resp = await asyncio.wait_for(provider.generate(req), timeout=15)
            return {"provider": name, "status": "ok", "model": resp.model, "latency_ms": resp.latency_ms}
        except Exception as e:
            return {"provider": name, "status": "error", "error": str(e)}


# Singleton global
llm_router = LLMRouterService()
