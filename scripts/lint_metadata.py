#!/usr/bin/env python3
"""Lint de metadata del dominio.

Verifica que todos los modelos `table=True` tienen `__meta__` con description,
que todos los campos tienen description no vacia y que todos los endpoints
registrados en FastAPI tienen summary o description.

Sale con codigo 0 si todo OK, 1 si falta algo (lista los faltantes).
Pensado para integrarse al job 'lint' del workflow CI.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(str(BACKEND))
# Para que app.core.config no exija un .env real con DATABASE_URL.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./vedisa_dev.db")
os.environ.setdefault("SECRET_KEY", "lint-only-not-for-production")


def main() -> int:
    from app.core.metadata import extract_all_entities
    from main import app  # importa app FastAPI para extraer endpoints

    fallos: list[str] = []
    entidades = extract_all_entities()
    for ent in entidades:
        if not ent["description"]:
            fallos.append(
                f"[entity] {ent['name']}: falta __meta__.description"
            )
        for f in ent["fields"]:
            if not f["description"]:
                fallos.append(
                    f"[field]  {ent['name']}.{f['name']}: falta description"
                )

    openapi = app.openapi()
    paths = openapi.get("paths", {}) or {}
    _SKIP = {"/openapi.json", "/docs", "/redoc", "/docs/oauth2-redirect"}
    for path, ops in paths.items():
        if path in _SKIP:
            continue
        if not isinstance(ops, dict):
            continue
        for method, op in ops.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            if not isinstance(op, dict):
                continue
            summary = op.get("summary")
            description = op.get("description")
            if not summary and not description:
                fallos.append(
                    f"[endpoint] {method.upper():6s} {path}: sin summary ni description"
                )

    if fallos:
        print(f"ERROR: lint de metadata fallo con {len(fallos)} problemas:\n")
        for f in fallos:
            print(f"  - {f}")
        return 1

    print(
        f"OK: {len(entidades)} entidades, "
        f"{sum(len(e['fields']) for e in entidades)} campos, "
        f"{sum(1 for _ in paths)} paths revisados."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
