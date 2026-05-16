"""Generador de PDF de oferta para una solicitud del CRM Vedisa.

Usa ReportLab (Python puro, sin dependencias del sistema). Devuelve los bytes
del PDF para que el endpoint los sirva como `application/pdf`.
"""
from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.models import Solicitud, SolicitudActuacion, Usuario


def _euro(value: Optional[float]) -> str:
    """Formato '1.234,56 EUR' con separadores espanoles."""
    if value is None:
        return "-"
    # Separador miles con punto, decimal con coma.
    s = f"{value:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".") + " EUR"


def _m2(value: Optional[float]) -> str:
    if value is None:
        return "-"
    s = f"{value:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".") + " m2"


def _pct(value: Optional[float]) -> str:
    if value is None:
        return "-"
    return f"{value:.2f}".replace(".", ",") + " %"


def _direccion(s: Solicitud) -> str:
    partes = [
        s.tipo_via,
        s.numero,
        s.cp,
        s.poblacion,
    ]
    return ", ".join(p for p in partes if p)


def generar_pdf_oferta(
    solicitud: Solicitud,
    actuaciones: list[tuple[SolicitudActuacion, str]],
    usuario: Optional[Usuario] = None,
) -> bytes:
    """Devuelve los bytes del PDF de oferta.

    `actuaciones` es una lista de tuplas (SolicitudActuacion, nombre_catalogo)
    para evitar otra carga lazy desde la sesion.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Oferta {solicitud.codigo}",
        author="Vedisa CRM",
    )

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle(
        "Vedisa-H1",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=16,
        textColor=colors.HexColor("#1f2937"),
        spaceAfter=4,
    )
    h2 = ParagraphStyle(
        "Vedisa-H2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=colors.HexColor("#4338ca"),
        spaceBefore=10,
        spaceAfter=4,
    )
    body = ParagraphStyle(
        "Vedisa-Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=12,
    )
    right_small = ParagraphStyle(
        "Vedisa-Right",
        parent=body,
        alignment=TA_RIGHT,
        fontSize=8.5,
        textColor=colors.HexColor("#6b7280"),
    )

    now = datetime.utcnow()

    elementos = []

    # Encabezado.
    elementos.append(
        Paragraph(f"Vedisa CRM &mdash; Oferta {solicitud.codigo}", h1)
    )
    elementos.append(
        Paragraph(
            f"Fecha emision: {now.strftime('%d/%m/%Y')} &nbsp;|&nbsp; "
            f"Estado: <b>{solicitud.estado}</b>",
            right_small,
        )
    )
    elementos.append(Spacer(1, 6 * mm))

    # Datos cliente / direccion.
    elementos.append(Paragraph("Datos del proyecto", h2))
    direccion = _direccion(solicitud) or "-"
    cliente_tbl = Table(
        [
            ["Cliente / obra", solicitud.nombre_corto or "-"],
            ["Direccion", direccion],
            ["Codigo solicitud", solicitud.codigo],
            [
                "Fecha solicitud",
                solicitud.fecha_solicitud.strftime("%d/%m/%Y")
                if solicitud.fecha_solicitud
                else "-",
            ],
            [
                "Fecha enviada",
                solicitud.fecha_enviado.strftime("%d/%m/%Y")
                if solicitud.fecha_enviado
                else "-",
            ],
            [
                "Fecha cierre",
                solicitud.fecha_cierre_cliente.strftime("%d/%m/%Y")
                if solicitud.fecha_cierre_cliente
                else "-",
            ],
        ],
        colWidths=[42 * mm, 130 * mm],
        hAlign="LEFT",
    )
    cliente_tbl.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#374151")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                (
                    "LINEBELOW",
                    (0, 0),
                    (-1, -1),
                    0.25,
                    colors.HexColor("#e5e7eb"),
                ),
            ]
        )
    )
    elementos.append(cliente_tbl)

    # Tabla actuaciones.
    elementos.append(Paragraph("Actuaciones", h2))
    if actuaciones:
        rows = [["Actuacion", "Superficie", "Importe"]]
        total_m2 = 0.0
        total_importe = 0.0
        for sa, nombre in actuaciones:
            rows.append([nombre, _m2(sa.m2), _euro(sa.importe)])
            if sa.m2 is not None:
                total_m2 += sa.m2
            if sa.importe is not None:
                total_importe += sa.importe
        rows.append(["TOTAL", _m2(total_m2 or None), _euro(total_importe or None)])

        act_tbl = Table(rows, colWidths=[100 * mm, 36 * mm, 36 * mm], hAlign="LEFT")
        act_tbl.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#eef2ff"),
                    ),
                    (
                        "BACKGROUND",
                        (0, -1),
                        (-1, -1),
                        colors.HexColor("#f9fafb"),
                    ),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("ALIGN", (0, 0), (0, -1), "LEFT"),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#9ca3af")),
                    (
                        "INNERGRID",
                        (0, 0),
                        (-1, -1),
                        0.25,
                        colors.HexColor("#d1d5db"),
                    ),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        elementos.append(act_tbl)
    else:
        elementos.append(
            Paragraph(
                "Sin actuaciones asignadas a esta solicitud.", body
            )
        )

    # Bloque financiero.
    elementos.append(Paragraph("Resumen financiero", h2))
    fin_tbl = Table(
        [
            ["Oferta", _euro(solicitud.oferta)],
            ["Coste", _euro(solicitud.coste)],
            ["Margen", _pct(solicitud.margen_pct)],
            ["Cobertura", _pct(solicitud.cobertura_pct)],
            [
                "Coeficiente",
                f"{solicitud.coeficiente:.2f}".replace(".", ",")
                if solicitud.coeficiente is not None
                else "-",
            ],
        ],
        colWidths=[60 * mm, 60 * mm],
        hAlign="LEFT",
    )
    fin_tbl.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                (
                    "LINEBELOW",
                    (0, 0),
                    (-1, -1),
                    0.25,
                    colors.HexColor("#e5e7eb"),
                ),
            ]
        )
    )
    elementos.append(fin_tbl)

    # Pie con firma del usuario.
    elementos.append(Spacer(1, 10 * mm))
    quien = (
        f"{usuario.nombre} ({usuario.email})" if usuario else "Sistema"
    )
    elementos.append(
        Paragraph(
            f"Generado por <b>{quien}</b> el "
            f"{now.strftime('%d/%m/%Y %H:%M UTC')} &mdash; "
            f"Solicitud {solicitud.codigo}",
            right_small,
        )
    )

    doc.build(elementos)
    return buffer.getvalue()
