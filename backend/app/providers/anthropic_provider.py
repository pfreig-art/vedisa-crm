import time
import anthropic
from app.core.config import settings
from app.providers.base import LLMRequest, LLMResponse


class AnthropicProvider:
    """Adaptador para Anthropic Claude."""

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def is_available(self) -> bool:
        return bool(settings.ANTHROPIC_API_KEY)

    async def generate(self, request: LLMRequest) -> LLMResponse:
        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

        # Separar system de user messages
        system_content = ""
        messages = []
        for m in request.messages:
            if m.role == "system":
                system_content = m.content
            else:
                messages.append({"role": m.role, "content": m.content})

        start = time.monotonic()
        response = await client.messages.create(
            model=settings.ANTHROPIC_DEFAULT_MODEL,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            system=system_content or anthropic.NOT_GIVEN,
            messages=messages,
        )
        latency = int((time.monotonic() - start) * 1000)

        content = response.content[0].text if response.content else ""
        tokens = (response.usage.input_tokens or 0) + (response.usage.output_tokens or 0)

        return LLMResponse(
            content=content,
            provider=self.name,
            model=response.model,
            tokens_used=tokens,
            latency_ms=latency,
            raw=response.model_dump(),
        )
