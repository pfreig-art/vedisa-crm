import time
from openai import AsyncOpenAI
from app.core.config import settings
from app.providers.base import LLMRequest, LLMResponse


class OpenAIProvider:
    """Adaptador para OpenAI GPT."""

    @property
    def name(self) -> str:
        return "openai"

    @property
    def is_available(self) -> bool:
        return bool(settings.OPENAI_API_KEY)

    async def generate(self, request: LLMRequest) -> LLMResponse:
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        kwargs = dict(
            model=settings.OPENAI_DEFAULT_MODEL,
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )
        if request.response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        start = time.monotonic()
        response = await client.chat.completions.create(**kwargs)
        latency = int((time.monotonic() - start) * 1000)

        content = response.choices[0].message.content or ""
        tokens = response.usage.total_tokens if response.usage else 0

        return LLMResponse(
            content=content,
            provider=self.name,
            model=response.model,
            tokens_used=tokens,
            latency_ms=latency,
            raw=response.model_dump(),
        )
