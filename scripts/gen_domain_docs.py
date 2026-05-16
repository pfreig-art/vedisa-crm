#!/usr/bin/env python3
"""Generador de docs/DOMAIN.md a partir de la metadata del dominio.

Lee `extract_all_entities()`, `BUSINESS_RULES` y el OpenAPI de FastAPI y
emite un Markdown con secciones: Entidades, Relaciones (mermaid), Enums,
Reglas de negocio y Endpoints.

Idempotente: regenera el archivo entero cada vez. Sin timestamps en el
contenido para que `git diff --exit-code` lo detecte solo si cambia algo
real.

Uso:
    python scripts/gen_domain_docs.py            # escribe docs/DOMAIN.md
    python scripts/gen_domain_docs.py --check    # compara con docs/DOMAIN.md
                                                  # y sale != 0 si difiere
"""
from __future__ import annotations

import argparse
import difflib
import os
import sys
from io import StringIO
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
DOCS = ROOT / "docs"
sys.path.insert(0, str(BACKEND))
os.chdir(str(BACKEND))
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./vedisa_dev.db")
os.environ.setdefault("SECRET_KEY", "gen-docs-only-not-for-production")


HEADER = "<!-- AUTO-GENERATED. Run: python scripts/gen_domain_docs.py -->\n"


# Relaciones (duplicado controlado vs api/meta.py para evitar import circular
# desde el script CLI). Si cambia, actualizar tambien meta.py RELATIONS.
RELATIONS = [
    ("solicitudes.comercial", "usuarios.id", "many_to_one"),
    ("solicitudes.tecnico_estudios", "usuarios.id", "many_to_one"),
    ("solicitud_actuaciones.solicitud_id", "solicitudes.id", "many_to_one"),
    ("solicitud_actuaciones.actuacion_id", "actuaciones.id", "many_to_one"),
    ("solicitud_contactos.solicitud_id", "solicitudes.id", "many_to_one"),
    ("audit_log.solicitud_id", "solicitudes.id", "many_to_one"),
    ("audit_log.usuario_id", "usuarios.id", "many_to_one"),
    ("ai_audit_log.solicitud_id", "solicitudes.id", "many_to_one"),
    ("ai_audit_log.usuario_id", "usuarios.id", "many_to_one"),
]


def _md_escape(s: str | None) -> str:
    if s is None:
        return "-"
    return s.replace("|", "\\|").replace("\n", " ")


def render(entities: list[dict[str, Any]],
           rules: list[dict[str, Any]],
           enums: dict[str, list[str]],
           endpoints: list[dict[str, Any]]) -> str:
    buf = StringIO()
    w = buf.write

    w(HEADER)
    w("\n# Vedisa CRM - Dominio\n\n")
    w(
        "Documento generado automaticamente desde las anotaciones de los "
        "modelos SQLModel (`__meta__` + `description` por Field + "
        "`__field_meta__`) y el catalogo de reglas de negocio "
        "(`app/services/business_rules.py`). No editar a mano: regenerar con "
        "`python scripts/gen_domain_docs.py`.\n\n"
    )

    # --- Indice ----------------------------------------------------------
    w("## Indice\n\n")
    w("- [Entidades](#entidades)\n")
    for ent in entities:
        w(f"  - [{ent['name']}](#{ent['name']})\n")
    w("- [Relaciones](#relaciones)\n")
    w("- [Enums](#enums)\n")
    w("- [Reglas de negocio](#reglas-de-negocio)\n")
    w("- [Endpoints](#endpoints)\n\n")

    # --- Entidades --------------------------------------------------------
    w("## Entidades\n\n")
    for ent in entities:
        w(f"### {ent['name']}\n\n")
        w(f"**Clase Python**: `{ent['class_name']}`\n\n")
        if ent["description"]:
            w(f"{ent['description']}\n\n")
        if ent["business_meaning"]:
            w(f"**Significado de negocio**: {ent['business_meaning']}\n\n")
        if ent["lifecycle"]:
            w(f"**Ciclo de vida**: {ent['lifecycle']}\n\n")
        # Tabla de campos.
        w("| Campo | Tipo | Req | Calc | Descripcion | Negocio |\n")
        w("|---|---|---|---|---|---|\n")
        for f in ent["fields"]:
            req = "PK" if f["primary_key"] else ("si" if f["required"] else "no")
            calc = "si" if f["calculated"] else ""
            extra_bits = []
            if f["unit"]:
                extra_bits.append(f"_{f['unit']}_")
            if f["legacy"]:
                extra_bits.append("**LEGACY**")
            if f["examples"]:
                ex = ", ".join(str(x) for x in f["examples"][:5])
                extra_bits.append(f"ej. {ex}")
            extra = " " + " ".join(extra_bits) if extra_bits else ""
            w(
                f"| `{f['name']}` | `{f['type']}` | {req} | {calc} | "
                f"{_md_escape(f['description'])}{extra} | "
                f"{_md_escape(f['business_meaning'])} |\n"
            )
        w("\n")

    # --- Relaciones (Mermaid + tabla) -------------------------------------
    w("## Relaciones\n\n")
    w("```mermaid\nerDiagram\n")
    tablas = sorted({r["name"] for r in []} | {ent["name"] for ent in entities})
    for t in tablas:
        w(f"  {t} {{ }}\n")
    for f, to, kind in RELATIONS:
        from_table = f.split(".")[0]
        to_table = to.split(".")[0]
        sym = "}o--||" if kind == "many_to_one" else "||--||"
        w(f"  {from_table} {sym} {to_table} : \"{f.split('.')[1]}\"\n")
    w("```\n\n")
    w("| Origen | Destino | Tipo |\n|---|---|---|\n")
    for f, to, kind in RELATIONS:
        w(f"| `{f}` | `{to}` | {kind} |\n")
    w("\n")

    # --- Enums ------------------------------------------------------------
    w("## Enums\n\n")
    for nombre, valores in enums.items():
        w(f"- **{nombre}**: " + ", ".join(f"`{v}`" for v in valores) + "\n")
    w("\n")

    # --- Reglas de negocio ------------------------------------------------
    w("## Reglas de negocio\n\n")
    w("| ID | Aplica a | Descripcion | Severidad |\n|---|---|---|---|\n")
    for r in rules:
        w(
            f"| `{r['id']}` | `{r['applies_to']}` | "
            f"{_md_escape(r['description'])} | {r['severity']} |\n"
        )
    w("\n")

    # --- Endpoints --------------------------------------------------------
    w("## Endpoints\n\n")
    w("| Metodo | Path | Proposito |\n|---|---|---|\n")
    for e in endpoints:
        purpose = e.get("purpose") or "_(sin description)_"
        w(
            f"| `{e['method']}` | `{e['path']}` | "
            f"{_md_escape(purpose)} |\n"
        )
    w("\n")

    return buf.getvalue()


def _gather() -> tuple[list, list, dict, list]:
    from app.core.metadata import extract_all_entities
    from app.services.business_rules import serialize_rules
    from app.api.meta import ENUMS, _extract_endpoints
    from main import app

    return (
        extract_all_entities(),
        serialize_rules(),
        ENUMS,
        _extract_endpoints(app.openapi()),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="No escribe; compara con docs/DOMAIN.md y sale != 0 si difiere.",
    )
    args = parser.parse_args()

    entities, rules, enums, endpoints = _gather()
    nuevo = render(entities, rules, enums, endpoints)
    out_file = DOCS / "DOMAIN.md"

    if args.check:
        if not out_file.exists():
            print(f"ERROR: {out_file} no existe. Ejecuta sin --check primero.")
            return 1
        actual = out_file.read_text(encoding="utf-8")
        if actual != nuevo:
            diff = difflib.unified_diff(
                actual.splitlines(keepends=True),
                nuevo.splitlines(keepends=True),
                fromfile="docs/DOMAIN.md (en repo)",
                tofile="docs/DOMAIN.md (regenerado)",
                n=2,
            )
            print(
                "ERROR: docs/DOMAIN.md esta desincronizado. "
                "Ejecuta `python scripts/gen_domain_docs.py` y commitea.\n"
            )
            sys.stdout.writelines(list(diff)[:120])
            return 1
        print("OK: docs/DOMAIN.md esta al dia.")
        return 0

    DOCS.mkdir(exist_ok=True)
    out_file.write_text(nuevo, encoding="utf-8")
    print(f"OK: regenerado {out_file} ({len(nuevo)} bytes).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
