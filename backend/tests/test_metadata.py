"""Tests de la capa de metadata del dominio (Sprint E1)."""
import pytest

from app.core.metadata import extract_all_entities, extract_entity_metadata
from app.core.models import Solicitud, Usuario
from app.services.business_rules import BUSINESS_RULES


# ---------------------------------------------------------------------------
# extract_*
# ---------------------------------------------------------------------------

class TestExtractMetadata:
    def test_solicitud_tiene_mas_de_20_campos_todos_documentados(self):
        meta = extract_entity_metadata(Solicitud)
        assert meta["class_name"] == "Solicitud"
        assert meta["description"]
        assert meta["business_meaning"]
        assert meta["lifecycle"]
        assert len(meta["fields"]) > 20
        for f in meta["fields"]:
            assert f["description"], f"campo {f['name']} sin description"
            assert f["business_meaning"], f"campo {f['name']} sin business_meaning"

    def test_usuario_rol_tiene_examples(self):
        meta = extract_entity_metadata(Usuario)
        rol = next(f for f in meta["fields"] if f["name"] == "rol")
        assert rol["examples"] == ["admin", "comercial", "tecnico"]

    def test_solicitud_marca_campos_calculados(self):
        meta = extract_entity_metadata(Solicitud)
        calculados = {f["name"] for f in meta["fields"] if f["calculated"]}
        assert "margen_pct" in calculados
        assert "cobertura_pct" in calculados
        assert "coeficiente" in calculados
        assert "aging_dias" in calculados

    def test_solicitud_marca_legacy(self):
        meta = extract_entity_metadata(Solicitud)
        legacy = {f["name"] for f in meta["fields"] if f["legacy"]}
        assert "presupuesto" in legacy
        assert "contactos" in legacy
        assert "actuaciones" in legacy

    def test_extract_all_entities_descubre_al_menos_5_tables(self):
        ents = extract_all_entities()
        nombres = {e["name"] for e in ents}
        assert {
            "usuarios", "solicitudes", "actuaciones",
            "solicitud_actuaciones", "audit_log",
        }.issubset(nombres)


# ---------------------------------------------------------------------------
# Endpoints /meta/*
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestMetaEndpoints:
    async def test_meta_schema_responde_200_y_estructura(self, client):
        r = await client.get("/meta/schema")
        assert r.status_code == 200
        body = r.json()
        for k in (
            "app", "schema_version", "generated_at", "entities",
            "relations", "enums", "business_rules", "endpoints",
        ):
            assert k in body, f"missing key {k}"
        assert body["app"]["name"] == "Vedisa CRM"
        assert len(body["entities"]) >= 5
        assert len(body["business_rules"]) >= 5
        assert len(body["enums"]) >= 3
        # estado_solicitud trae los 5 valores reales.
        assert body["enums"]["estado_solicitud"] == [
            "En Estudio", "Enviada", "Adjudicada", "Rechazada", "Descartada",
        ]

    async def test_meta_schema_no_filtra_secrets(self, client):
        import json as _json
        r = await client.get("/meta/schema")
        text = _json.dumps(r.json())
        for needle in ("DATABASE_URL", "SECRET_KEY", "JWT_SECRET", "PGPASSWORD"):
            assert needle not in text, f"posible leak de {needle}"

    async def test_meta_glossary_responde_12_o_mas_terminos(self, client):
        r = await client.get("/meta/glossary")
        assert r.status_code == 200
        body = r.json()
        assert len(body) >= 12
        # Algunos terminos esperados.
        for t in ("oferta", "coste", "margen", "cobertura",
                  "actuacion", "alerta", "recordatorio", "auditoria"):
            assert t in body, f"falta el termino '{t}'"
        # Cada entrada tiene definition y appears_in.
        for term, data in body.items():
            assert "definition" in data
            assert "appears_in" in data
            assert data["definition"]


# ---------------------------------------------------------------------------
# Catalogo de reglas de negocio
# ---------------------------------------------------------------------------

class TestBusinessRules:
    def test_al_menos_10_reglas_catalogadas(self):
        assert len(BUSINESS_RULES) >= 10

    def test_ids_unicos_y_con_prefijo(self):
        ids = [r.id for r in BUSINESS_RULES]
        assert len(set(ids)) == len(ids), "hay ids de reglas duplicados"
        # Prefijos esperados.
        for rid in ids:
            assert rid.startswith("BR-"), f"id {rid} no empieza por BR-"

    def test_cubre_estados_y_calculos(self):
        applies = " ".join(r.applies_to for r in BUSINESS_RULES)
        assert "solicitudes" in applies
        # Reglas para los tres KPI financieros.
        descs = " ".join(r.description for r in BUSINESS_RULES)
        assert "margen_pct" in descs
        assert "cobertura_pct" in descs
        assert "coeficiente" in descs


# ---------------------------------------------------------------------------
# Regresion: si un campo nuevo no tiene description, el lint detecta
# ---------------------------------------------------------------------------

class TestRegresionLint:
    def test_todos_los_campos_tienen_description(self):
        ents = extract_all_entities()
        faltantes = []
        for e in ents:
            for f in e["fields"]:
                if not f["description"]:
                    faltantes.append(f"{e['name']}.{f['name']}")
        assert not faltantes, f"sin description: {faltantes}"

    def test_todas_las_entidades_tienen_meta(self):
        ents = extract_all_entities()
        sin_meta = [e["name"] for e in ents if not e["description"]]
        assert not sin_meta, f"sin __meta__: {sin_meta}"
