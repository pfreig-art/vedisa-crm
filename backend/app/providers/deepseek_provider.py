from __future__ import annotations

from typing import AsyncIterator, List, Optional

import httpx

from app.core.config import settings
from app.providers.base import LLMMessage, LLMProvider, LLMResponse


class DeepSeekProvider(LLMProvider):
    """DeepSeek provider via OpenAI-compatible REST API."""

    BASE_URL = "https://api.deepseek.com"

    def __init__(self) -> None:
        if not settings.DEEPSEEK_API_KEY:
            raise ValueError("DEEPSEEK_API_KEY is not configured")
        self._api_key = settings.DEEPSEEK_API_KEY
        self._base_url = (settings.DEEPSEEK_BASE_URL or self.BASE_URL).rstrip("/")
        self._default_model = settings.DEEPSEEK_DEFAULT_MODEL or "deepseek-chat"
        self._fallback_model = "deepseek-chat"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _messages_payload(self, messages: List[LLMMessage]) -> list:
        return [{"role": m.role, "content": m.content} for m in messages]

    async def _chat(
        self, messages: List[LLMMessage], model: str, **kwargs
    ) -> LLMResponse:
        payload = {
            "model": model,
            "messages": self._messages_payload(messages),
            "stream": False,
            **kwargs,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self._base_url}/v1/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        choice = data["choices"][0]
        usage = data.get("usage", {})
        return LLMResponse(
            content=choice["message"]["content"],
            model=data.get("model", model),
            provider="deepseek",
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
        )

    # ------------------------------------------------------------------
    # LLMProvider protocol
    # ------------------------------------------------------------------

    async def chat(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        target = model or self._default_model
        try:
            return await self._chat(messages, target, **kwargs)
        except Exception:
            if target != self._fallback_model:
                return await self._chat(messages, self._fallback_model, **kwargs)
            raise

    async def stream(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        target = model or self._default_model
        payload = {
            "model": target,
            "messages": self._messages_payload(messages),
            "stream": True,
            **kwargs,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/v1/chat/completions",
                headers=self._headers(),
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        chunk = line[6:]
                        if chunk.strip() == "[DONE]":
                            break
                        import json
                        try:
                            data = json.loads(chunk)
                            delta = data["choices"][0]["delta"].get("content", "")
                            if delta:
                                yield delta
                        except Exception:
                            continue

    async def health_check(self) -> bool:
        try:
            await self.chat([LLMMessage(role="user", content="ping")])
            return True
        except Exception:
            return False

    @property
    def provider_name(self) -> str:
        return "deepseek"

    @property
    def default_model(self) -> str:
        return self._default_model
