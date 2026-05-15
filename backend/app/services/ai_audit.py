"""Service de observabilidad IA - graba y consulta AIAuditLog."""
from datetime import datetime
from typing import Optional, List
from sqlmodel import select, func
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import AIAuditLog


async def log_ai_call(
    db: AsyncSession,
    *,
    endpoint: str,
    provider: str,
    model: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    latency_ms: int = 0,
    success: bool = True,
    error_msg: Optional[str] = None,
    solicitud_id: Optional[str] = None,
    usuario_id: Optional[str] = None,
) -> AIAuditLog:
    """Inserta un registro de auditoria en la BD."""
    entry = AIAuditLog(
        endpoint=endpoint,
        provider=provider,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        latency_ms=latency_ms,
        success=success,
        error_msg=error_msg,
        solicitud_id=solicitud_id,
        usuario_id=usuario_id,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def get_audit_log(
    db: AsyncSession,
    *,
    provider: Optional[str] = None,
    endpoint: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[AIAuditLog]:
    """Devuelve el log de auditoria con filtros opcionales."""
    q = select(AIAuditLog).order_by(AIAuditLog.created_at.desc())
    if provider:
        q = q.where(AIAuditLog.provider == provider)
    if endpoint:
        q = q.where(AIAuditLog.endpoint == endpoint)
    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


async def get_provider_metrics(db: AsyncSession) -> List[dict]:
    """Agrega metricas por proveedor: llamadas, tokens, latencia media, tasa exito."""
    q = (
        select(
            AIAuditLog.provider,
            func.count(AIAuditLog.id).label("total_calls"),
            func.sum(AIAuditLog.total_tokens).label("total_tokens"),
            func.avg(AIAuditLog.latency_ms).label("avg_latency_ms"),
            func.sum(
                            func.cast(AIAuditLog.success, sa.Integer)
            ).label("success_calls"),
        )
        .group_by(AIAuditLog.provider)
        .order_by(func.count(AIAuditLog.id).desc())
    )
    result = await db.execute(q)
    rows = result.all()
    metrics = []
    for row in rows:
        total = row.total_calls or 1
        metrics.append({
            "provider": row.provider,
            "total_calls": row.total_calls,
            "total_tokens": int(row.total_tokens or 0),
            "avg_latency_ms": round(float(row.avg_latency_ms or 0), 1),
            "success_rate": round((row.success_calls or 0) / total * 100, 1),
        })
    return metrics
