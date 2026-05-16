"""Gateway provider: OpenRouter y LiteLLM via interfaz OpenAI-compatible.
Permite usar cualquier modelo disponible en el gateway sin cambiar el resto del codigo.
"""
import time
from openai import AsyncOpenAI
from app.core.config import settings
from app.providers.base import LLMRequest, LLMResponse


class GatewayProvider:
    """Adaptador generico para gateways compatibles con la API de OpenAI.
    Soporta OpenRouter y LiteLLM self-hosted.
    """

    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_available(self) -> bool:
        if self._name == "openrouter":
            return bool(settings.OPENROUTER_API_KEY)
        if self._name == "litellm":
            return bool(settings.LITELLM_BASE_URL)
        return False

    def _get_client_and_model(self) -> tuple[AsyncOpenAI, str]:
        if self._name == "openrouter":
            client = AsyncOpenAI(
                api_key=settings.OPENROUTER_API_KEY,
                base_url=settings.OPENROUTER_BASE_URL,
                default_headers={
                    "HTTP-Referer": "https://vedisa.com",
                    "X-Title": "Vedisa CRM",
                },
            )
            return client, settings.OPENROUTER_DEFAULT_MODEL
        else:  # litellm
            client = AsyncOpenAI(
                api_key=settings.LITELLM_API_KEY or "no-key",
                base_url=settings.LITELLM_BASE_URL,
            )
            return client, settings.LITELLM_DEFAULT_MODEL

    async def generate(self, request: LLMRequest) -> LLMResponse:
        client, model = self._get_client_and_model()
        # Aceptar tanto LLMMessage dataclass como dicts crudos {role, content}
        def _to_dict(m):
            if isinstance(m, dict):
                return {"role": m["role"], "content": m["content"]}
            return {"role": m.role, "content": m.content}
        messages = [_to_dict(m) for m in request.messages]

        start = time.monotonic()
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )
        latency = int((time.monotonic() - start) * 1000)

        content = response.choices[0].message.content or ""
        tokens = response.usage.total_tokens if response.usage else 0

        return LLMResponse(
            content=content,
            provider=self.name,
            model=model,
            tokens_used=tokens,
            latency_ms=latency,
            raw=response.model_dump(),
        )
