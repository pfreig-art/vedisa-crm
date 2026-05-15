from __future__ import annotations

import asyncio
from typing import AsyncIterator, List, Optional

import google.generativeai as genai

from app.core.config import settings
from app.providers.base import LLMMessage, LLMProvider, LLMResponse


class GeminiProvider(LLMProvider):
    """Google Gemini provider via google-generativeai SDK."""

    def __init__(self) -> None:
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self._default_model = settings.GEMINI_DEFAULT_MODEL or "gemini-1.5-pro"
        self._fallback_model = settings.GEMINI_FALLBACK_MODEL or "gemini-1.5-flash"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_contents(self, messages: List[LLMMessage]) -> list:
        """Convert LLMMessage list to Gemini content format."""
        contents = []
        for msg in messages:
            role = "user" if msg.role == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg.content}]})
        return contents

    def _system_instruction(self, messages: List[LLMMessage]) -> Optional[str]:
        """Extract system message if present (Gemini handles it separately)."""
        for msg in messages:
            if msg.role == "system":
                return msg.content
        return None

    def _non_system_messages(self, messages: List[LLMMessage]) -> List[LLMMessage]:
        return [m for m in messages if m.role != "system"]

    async def _chat(
        self, messages: List[LLMMessage], model: str, **kwargs
    ) -> LLMResponse:
        system = self._system_instruction(messages)
        non_sys = self._non_system_messages(messages)
        contents = self._build_contents(non_sys)

        model_obj = genai.GenerativeModel(
            model_name=model,
            system_instruction=system,
        )

        # Run blocking SDK call in thread pool
        response = await asyncio.to_thread(
            model_obj.generate_content,
            contents,
        )

        text = response.text or ""
        usage = response.usage_metadata
        return LLMResponse(
            content=text,
            model=model,
            provider="gemini",
            prompt_tokens=getattr(usage, "prompt_token_count", 0),
            completion_tokens=getattr(usage, "candidates_token_count", 0),
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
        system = self._system_instruction(messages)
        non_sys = self._non_system_messages(messages)
        contents = self._build_contents(non_sys)

        model_obj = genai.GenerativeModel(
            model_name=target,
            system_instruction=system,
        )

        def _generate():
            return model_obj.generate_content(contents, stream=True)

        stream_response = await asyncio.to_thread(_generate)
        for chunk in stream_response:
            if chunk.text:
                yield chunk.text

    async def health_check(self) -> bool:
        try:
            await self.chat(
                [LLMMessage(role="user", content="ping")],
                model=self._fallback_model,
            )
            return True
        except Exception:
            return False

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def default_model(self) -> str:
        return self._default_model
