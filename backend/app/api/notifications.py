"""SSE - Server-Sent Events para notificaciones en tiempo real."""
import asyncio
import json
from datetime import datetime
from typing import List

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/notifications", tags=["notifications"])

_subscribers: List[asyncio.Queue] = []


async def broadcast(event: dict):
    """Envia un evento a todos los suscriptores SSE activos."""
    for q in list(_subscribers):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass


async def _sse_gen(queue: asyncio.Queue):
    try:
        yield f"data: {json.dumps({'type': 'connected', 'ts': datetime.utcnow().isoformat()})}\n\n"
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=25.0)
                yield f"data: {json.dumps(event)}\n\n"
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
    except GeneratorExit:
        pass
    finally:
        if queue in _subscribers:
            _subscribers.remove(queue)


@router.get("/stream")
async def sse_stream():
    """Endpoint SSE - conectar para recibir eventos en tiempo real."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=50)
    _subscribers.append(queue)
    return StreamingResponse(
        _sse_gen(queue),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
