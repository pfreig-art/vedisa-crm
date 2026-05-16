# -*- coding: utf-8 -*-
import asyncio
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.models import Solicitud
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

SOLICITUDES = [
    {'codigo': 'SOL-2026-001', 'nombre_corto': 'Nave industrial Poligono Sur', 'poblacion': 'Sevilla', 'estado': 'En Estudio', 'kanban_column': 'En Estudio', 'color_estado': '#6366f1', 'prioridad': 'Alta', 'comercial': 'Carlos Ruiz', 'tecnico_estudios': 'Ana Lopez', 'fecha_solicitud': date(2026, 1, 10), 'fecha_limite': date(2026, 3, 31), 'aging_dias': 125, 'oferta': 85000.0},
    {'codigo': 'SOL-2026-002', 'nombre_corto': 'Centro logistico norte', 'poblacion': 'Zaragoza', 'estado': 'Enviada', 'kanban_column': 'Pte. Cierre', 'color_estado': '#f59e0b', 'prioridad': 'Media', 'comercial': 'Maria Garcia', 'tecnico_estudios': 'Pedro Sanz', 'fecha_solicitud': date(2026, 1, 15), 'fecha_limite': date(2026, 4, 15), 'aging_dias': 120, 'oferta': 142000.0},
    {'codigo': 'SOL-2026-003', 'nombre_corto': 'Almacen frigorifico Mercabarna', 'poblacion': 'Barcelona', 'estado': 'Adjudicada', 'kanban_column': 'Adjudicada', 'color_estado': '#10b981', 'prioridad': 'Alta', 'comercial': 'Carlos Ruiz', 'tecnico_estudios': 'Ana Lopez', 'fecha_solicitud': date(2026, 1, 20), 'fecha_limite': date(2026, 3, 20), 'aging_dias': 115, 'oferta': 310000.0},
    {'codigo': 'SOL-2026-004', 'nombre_corto': 'Oficinas corporativas Madrid', 'poblacion': 'Madrid', 'estado': 'Rechazada', 'kanban_column': 'Rechazada', 'color_estado': '#ef4444', 'prioridad': 'Baja', 'comercial': 'Luis Martin', 'tecnico_estudios': 'Pedro Sanz', 'fecha_solicitud': date(2026, 2, 1), 'fecha_limite': date(2026, 4, 1), 'aging_dias': 103, 'oferta': 67000.0},
    {'codigo': 'SOL-2026-005', 'nombre_corto': 'Planta fotovoltaica Extremadura', 'poblacion': 'Badajoz', 'estado': 'En Estudio', 'kanban_column': 'En Estudio', 'color_estado': '#6366f1', 'prioridad': 'Alta', 'comercial': 'Maria Garcia', 'tecnico_estudios': 'Ana Lopez', 'fecha_solicitud': date(2026, 2, 5), 'fecha_limite': date(2026, 5, 5), 'aging_dias': 99, 'oferta': 520000.0},
    {'codigo': 'SOL-2026-006', 'nombre_corto': 'Hotel boutique Costa Brava', 'poblacion': 'Girona', 'estado': 'Enviada', 'kanban_column': 'Pte. Cierre', 'color_estado': '#f59e0b', 'prioridad': 'Media', 'comercial': 'Luis Martin', 'tecnico_estudios': 'Pedro Sanz', 'fecha_solicitud': date(2026, 2, 10), 'fecha_limite': date(2026, 4, 30), 'aging_dias': 94, 'oferta': 195000.0},
    {'codigo': 'SOL-2026-007', 'nombre_corto': 'Residencia universitaria Valencia', 'poblacion': 'Valencia', 'estado': 'Adjudicada', 'kanban_column': 'Adjudicada', 'color_estado': '#10b981', 'prioridad': 'Alta', 'comercial': 'Carlos Ruiz', 'tecnico_estudios': 'Ana Lopez', 'fecha_solicitud': date(2026, 2, 15), 'fecha_limite': date(2026, 5, 15), 'aging_dias': 89, 'oferta': 430000.0},
    {'codigo': 'SOL-2026-008', 'nombre_corto': 'Supermercado franquicia Bilbao', 'poblacion': 'Bilbao', 'estado': 'Descartada', 'kanban_column': 'Rechazada', 'color_estado': '#6b7280', 'prioridad': 'Baja', 'comercial': 'Maria Garcia', 'tecnico_estudios': 'Pedro Sanz', 'fecha_solicitud': date(2026, 2, 20), 'fecha_limite': date(2026, 4, 20), 'aging_dias': 84, 'oferta': 48000.0},
    {'codigo': 'SOL-2026-009', 'nombre_corto': 'Parking automatizado Malaga', 'poblacion': 'Malaga', 'estado': 'En Estudio', 'kanban_column': 'En Estudio', 'color_estado': '#6366f1', 'prioridad': 'Media', 'comercial': 'Luis Martin', 'tecnico_estudios': 'Ana Lopez', 'fecha_solicitud': date(2026, 3, 1), 'fecha_limite': date(2026, 6, 1), 'aging_dias': 75, 'oferta': 280000.0},
    {'codigo': 'SOL-2026-010', 'nombre_corto': 'Centro deportivo municipal', 'poblacion': 'Valladolid', 'estado': 'Enviada', 'kanban_column': 'Pte. Cierre', 'color_estado': '#f59e0b', 'prioridad': 'Media', 'comercial': 'Carlos Ruiz', 'tecnico_estudios': 'Pedro Sanz', 'fecha_solicitud': date(2026, 3, 5), 'fecha_limite': date(2026, 5, 30), 'aging_dias': 71, 'oferta': 175000.0},
    {'codigo': 'SOL-2026-011', 'nombre_corto': 'Industria carnica Salamanca', 'poblacion': 'Salamanca', 'estado': 'Adjudicada', 'kanban_column': 'Adjudicada', 'color_estado': '#10b981', 'prioridad': 'Alta', 'comercial': 'Maria Garcia', 'tecnico_estudios': 'Ana Lopez', 'fecha_solicitud': date(2026, 3, 10), 'fecha_limite': date(2026, 6, 10), 'aging_dias': 66, 'oferta': 390000.0},
    {'codigo': 'SOL-2026-012', 'nombre_corto': 'Torre oficinas Alicante', 'poblacion': 'Alicante', 'estado': 'En Estudio', 'kanban_column': 'En Estudio', 'color_estado': '#6366f1', 'prioridad': 'Alta', 'comercial': 'Luis Martin', 'tecnico_estudios': 'Pedro Sanz', 'fecha_solicitud': date(2026, 3, 15), 'fecha_limite': date(2026, 6, 30), 'aging_dias': 61, 'oferta': 720000.0},
]

async def seed():
    async with AsyncSessionLocal() as session:
        for data in SOLICITUDES:
            sol = Solicitud(**data)
            session.add(sol)
        await session.commit()
        print(f'OK {len(SOLICITUDES)} solicitudes insertadas en PostgreSQL')

if __name__ == '__main__':
    asyncio.run(seed())
