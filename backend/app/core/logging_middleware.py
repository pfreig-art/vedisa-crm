"""Middleware de logging estructurado para Vedisa CRM.

Emite un evento structlog por request con metodo, ruta, status y latencia_ms.
Si el request lleva Authorization Bearer valido, anade user_id y user_email
sin fallar si el token es invalido o no existe.
"""
import time
from typing import Awaitable, Callable

import structlog
from fastapi import Request, Response
from jose import JWTError, jwt

from app.core.config import settings

log = structlog.get_logger("vedisa.request")

_EXCLUDED_PATHS = {"/healthz"}


def _extract_user_from_token(authorization: str | None) -> tuple[str | None, str | None]:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None, None
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError:
        return None, None
    return payload.get("user_id") or payload.get("uid"), payload.get("sub")


async def request_logging_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    path = request.url.path
    if path in _EXCLUDED_PATHS:
        return await call_next(request)

    start = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        latency_ms = int((time.perf_counter() - start) * 1000)
        user_id, user_email = _extract_user_from_token(
            request.headers.get("authorization")
        )
        log.info(
            "http_request",
            method=request.method,
            path=path,
            status=status_code,
            latency_ms=latency_ms,
            user_id=user_id,
            user_email=user_email,
        )
