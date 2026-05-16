"""Tests unitarios puros (sin DB) de app.services.business_logic."""
from datetime import date

from freezegun import freeze_time

from app.services.business_logic import (
    calcular_dias_a_limite,
    calcular_financiero,
    validar_fechas,
    validar_solicitud_para_estado,
)


# ---------------------------------------------------------------------------
# calcular_financiero
# ---------------------------------------------------------------------------

class TestCalcularFinanciero:
    def test_caso_basico_oferta_12000_coste_9000(self):
        r = calcular_financiero(12000, 9000)
        assert r["cobertura_pct"] == 75.0
        assert r["coeficiente"] == 1.33
        assert r["margen_pct"] == 25.0

    def test_oferta_cero_devuelve_todo_none(self):
        r = calcular_financiero(0, 9000)
        assert r["cobertura_pct"] is None
        assert r["coeficiente"] is None
        assert r["margen_pct"] is None

    def test_coste_cero_calcula_margen_pero_no_coeficiente(self):
        r = calcular_financiero(12000, 0)
        # margen y cobertura se calculan; coeficiente requiere coste>0.
        assert r["margen_pct"] == 100.0
        assert r["cobertura_pct"] == 0.0
        assert r["coeficiente"] is None

    def test_ambos_none_no_falla(self):
        r = calcular_financiero(None, None)
        assert r == {"margen_pct": None, "cobertura_pct": None, "coeficiente": None}

    def test_solo_oferta_sin_coste(self):
        r = calcular_financiero(12000, None)
        assert r["margen_pct"] is None

    def test_redondeo_a_dos_decimales(self):
        # 100/333 = 0.3003003... -> 30.03
        r = calcular_financiero(333, 100)
        assert r["cobertura_pct"] == 30.03


# ---------------------------------------------------------------------------
# validar_solicitud_para_estado
# ---------------------------------------------------------------------------

class TestValidarSolicitudParaEstado:
    def test_enviada_sin_fecha_enviado_error(self):
        errs = validar_solicitud_para_estado({"oferta": 1000}, "Enviada")
        assert errs
        assert any("fecha_enviado" in e for e in errs)

    def test_enviada_sin_oferta_error(self):
        errs = validar_solicitud_para_estado(
            {"fecha_enviado": "2026-01-01"}, "Enviada"
        )
        assert errs
        assert any("oferta" in e for e in errs)

    def test_enviada_oferta_cero_error(self):
        errs = validar_solicitud_para_estado(
            {"fecha_enviado": "2026-01-01", "oferta": 0}, "Enviada"
        )
        assert any("oferta" in e for e in errs)

    def test_enviada_completa_sin_errores(self):
        errs = validar_solicitud_para_estado(
            {"fecha_enviado": "2026-01-01", "oferta": 1000}, "Enviada"
        )
        assert errs == []

    def test_adjudicada_sin_cierre_error(self):
        errs = validar_solicitud_para_estado({"oferta": 1000}, "Adjudicada")
        assert any("fecha_cierre_cliente" in e for e in errs)

    def test_adjudicada_sin_oferta_error(self):
        errs = validar_solicitud_para_estado(
            {"fecha_cierre_cliente": "2026-01-01"}, "Adjudicada"
        )
        assert any("oferta" in e for e in errs)

    def test_rechazada_sin_cierre_error(self):
        errs = validar_solicitud_para_estado({}, "Rechazada")
        assert any("fecha_cierre_cliente" in e for e in errs)

    def test_rechazada_con_cierre_ok(self):
        errs = validar_solicitud_para_estado(
            {"fecha_cierre_cliente": "2026-01-01"}, "Rechazada"
        )
        assert errs == []

    def test_en_estudio_sin_requisitos(self):
        assert validar_solicitud_para_estado({}, "En Estudio") == []

    def test_descartada_sin_requisitos(self):
        assert validar_solicitud_para_estado({}, "Descartada") == []


# ---------------------------------------------------------------------------
# validar_fechas
# ---------------------------------------------------------------------------

class TestValidarFechas:
    def test_orden_correcto_sin_errores(self):
        errs = validar_fechas(
            {
                "fecha_solicitud": "2026-01-01",
                "fecha_reunion": "2026-01-10",
                "fecha_visita": "2026-01-15",
                "fecha_enviado": "2026-02-01",
                "fecha_cierre_cliente": "2026-03-01",
            }
        )
        assert errs == []

    def test_reunion_anterior_a_solicitud_error(self):
        errs = validar_fechas(
            {"fecha_solicitud": "2026-02-01", "fecha_reunion": "2026-01-01"}
        )
        assert errs

    def test_solo_una_fecha_no_falla(self):
        assert validar_fechas({"fecha_solicitud": "2026-01-01"}) == []

    def test_fechas_none_ignoradas(self):
        # fecha_limite no participa en el orden; solo informativa.
        errs = validar_fechas(
            {"fecha_solicitud": "2026-01-01", "fecha_visita": None}
        )
        assert errs == []


# ---------------------------------------------------------------------------
# calcular_dias_a_limite
# ---------------------------------------------------------------------------

class TestCalcularDiasALimite:
    @freeze_time("2026-05-16")
    def test_dias_positivos_futuro(self):
        d = date(2026, 5, 26)  # +10 dias
        assert calcular_dias_a_limite(d) == 10

    @freeze_time("2026-05-16")
    def test_dias_negativos_pasado(self):
        d = date(2026, 5, 11)  # -5 dias
        assert calcular_dias_a_limite(d) == -5

    @freeze_time("2026-05-16")
    def test_hoy_es_cero(self):
        assert calcular_dias_a_limite(date(2026, 5, 16)) == 0

    def test_sin_fecha_devuelve_none(self):
        assert calcular_dias_a_limite(None) is None
