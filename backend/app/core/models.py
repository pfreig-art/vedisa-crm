"""SQLModel ORM models for Vedisa CRM.

Cada Field lleva `description` (kwarg nativo de Pydantic, queda en
`FieldInfo.description`). El resto de metadata extra (business_meaning,
examples, unit, calculated, legacy) vive en `__field_meta__` por clase.

El endpoint /meta/schema y el lint de metadata leen ambos canales por
reflexion (ver app/core/metadata.py).
"""
from datetime import datetime, date
from typing import Any, Optional
import uuid

from sqlmodel import SQLModel, Field

from app.core.metadata import entity_meta, field_meta


def _uuid() -> str:
    return str(uuid.uuid4())


_ROLES = ["admin", "comercial", "tecnico"]
_EQUIPOS = ["comercial", "estudios", "direccion", "administracion"]
_ESTADOS = ["En Estudio", "Enviada", "Adjudicada", "Rechazada", "Descartada"]
_PRIORIDADES = ["alta", "media", "baja"]
_CONTACTO_TIPOS = [
    "administracion", "tecnico_obra", "ensena_obra",
    "presidente", "propiedad", "otro",
]
_AUDIT_ACCIONES = [
    "create", "update", "delete", "estado_change", "actuaciones_update",
]
_AI_ENDPOINTS = ["analyze", "chat", "test"]


# ---------------------------------------------------------------------------
# Usuario
# ---------------------------------------------------------------------------

class Usuario(SQLModel, table=True):
    """Tabla de usuarios / agentes del CRM."""

    __tablename__ = "usuarios"
    __meta__ = entity_meta(
        description="Usuario del CRM con rol, equipo y datos de presentacion.",
        business_meaning=(
            "Quien opera el CRM. Aparece como comercial o tecnico asignado a "
            "una solicitud, como autor en audit_log y como destinatario de "
            "alertas y recordatorios."
        ),
        lifecycle=(
            "Creado por un admin via /auth/register o /crm/usuarios. activo=False "
            "lo bloquea sin borrarlo; nunca se elimina para no romper FKs en "
            "audit_log y solicitudes historicas."
        ),
    )
    __field_meta__ = {
        "id": field_meta(business_meaning="Identificador estable referenciado por FK en solicitudes y audit_log."),
        "email": field_meta(business_meaning="Identificador humano que el usuario teclea al iniciar sesion."),
        "nombre": field_meta(business_meaning="Se muestra en avatares, listados y firmas de recordatorios / PDF."),
        "hashed_password": field_meta(business_meaning="Permite validar el login sin almacenar la contrasena en claro."),
        "rol": field_meta(
            business_meaning="Controla los permisos: admin ve toda la app, comercial sus solicitudes, tecnico apoya estudios.",
            examples=_ROLES,
        ),
        "activo": field_meta(business_meaning="Permite desactivar a un usuario sin borrar su historial."),
        "equipo": field_meta(
            business_meaning="Se usa en dashboards y filtros para segmentar la actividad por equipo.",
            examples=_EQUIPOS,
        ),
        "iniciales": field_meta(business_meaning="Etiqueta visual compacta en chips, tablas e historial."),
        "color": field_meta(business_meaning="Identifica visualmente al usuario en pipeline, dashboard y tablas."),
        "cargo": field_meta(business_meaning="Aparece en perfiles y firmas; informativo, no restringe permisos."),
        "created_at": field_meta(business_meaning="Auditoria basica del alta del usuario."),
        "updated_at": field_meta(business_meaning="Permite detectar cambios recientes en el perfil."),
    }

    id: str = Field(
        default_factory=_uuid, primary_key=True,
        description="UUID v4 generado server-side al crear el usuario.",
    )
    email: str = Field(
        unique=True, index=True,
        description="Email de login, unico, indexado.",
    )
    nombre: str = Field(
        description="Nombre completo del usuario.",
    )
    hashed_password: str = Field(
        description="Hash bcrypt de la contrasena. Nunca se devuelve en respuestas.",
    )
    rol: str = Field(
        default="comercial",
        description="Rol funcional del usuario (admin / comercial / tecnico).",
    )
    activo: bool = Field(
        default=True,
        description="Flag de actividad. Si False el login devuelve 403.",
    )
    equipo: Optional[str] = Field(
        default=None, index=True,
        description="Equipo al que pertenece el usuario (comercial / estudios / direccion / administracion).",
    )
    iniciales: Optional[str] = Field(
        default=None,
        description="Dos o tres letras para mostrar en avatares.",
    )
    color: Optional[str] = Field(
        default=None,
        description="Color hex para el avatar del usuario.",
    )
    cargo: Optional[str] = Field(
        default=None,
        description="Cargo / titulo profesional libre.",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp UTC de creacion del registro.",
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp UTC de la ultima modificacion.",
    )


# ---------------------------------------------------------------------------
# Solicitud
# ---------------------------------------------------------------------------

class Solicitud(SQLModel, table=True):
    """Solicitud / oportunidad comercial del pipeline."""

    __tablename__ = "solicitudes"
    __meta__ = entity_meta(
        description="Oportunidad comercial / proyecto en el pipeline.",
        business_meaning=(
            "Unidad central del CRM. Recorre el embudo desde En Estudio hasta "
            "Adjudicada o Rechazada; concentra la oferta economica, las "
            "actuaciones, el calendario y la asignacion comercial / tecnica."
        ),
        lifecycle=(
            "En Estudio -> Enviada (requiere fecha_enviado + oferta>0) -> "
            "Adjudicada o Rechazada (requieren fecha_cierre_cliente). "
            "Descartada para cerrar sin ganar ni perder."
        ),
    )
    __field_meta__ = {
        "id": field_meta(business_meaning="Identificador estable referenciado por FK en audit_log, contactos y actuaciones."),
        "codigo": field_meta(
            business_meaning="Lo que ve el cliente y el comercial en el dia a dia; aparece en PDF y recordatorios.",
            examples=["SOL-2026-0001"],
        ),
        "nombre_corto": field_meta(business_meaning="Etiqueta humana usada en listados, kanban y asunto de mailto."),
        "poblacion": field_meta(business_meaning="Permite agrupar geograficamente y filtrar el pipeline."),
        "estado": field_meta(
            business_meaning="Indica en que fase del pipeline esta y que validaciones rigen.",
            examples=_ESTADOS,
        ),
        "kanban_column": field_meta(business_meaning="Normalmente igual a estado; permite agrupar columnas custom en el UI."),
        "color_estado": field_meta(business_meaning="Pista visual rapida del estado en el tablero."),
        "prioridad": field_meta(
            business_meaning="Marca el orden de atencion del comercial; alta destaca con color en filtros.",
            examples=_PRIORIDADES,
        ),
        "comercial": field_meta(business_meaning="Quien lleva la relacion con el cliente; ve esta solicitud en sus alertas."),
        "tecnico_estudios": field_meta(business_meaning="Quien valora coste y prepara la oferta tecnica."),
        "tipo_via": field_meta(business_meaning="Compone la direccion mostrada en el PDF y en el detalle."),
        "numero": field_meta(business_meaning="Parte de la direccion completa de la obra."),
        "cp": field_meta(business_meaning="Facilita la agrupacion geografica y la deteccion de mercados."),
        "fecha_solicitud": field_meta(business_meaning="Punto de inicio del embudo; alimenta el heatmap del dashboard."),
        "fecha_limite": field_meta(business_meaning="Dispara alertas: <0 dias = vencida; <=7 dias = proxima."),
        "fecha_reunion": field_meta(business_meaning="Hito intermedio entre solicitud y visita; alimenta el timeline."),
        "fecha_visita": field_meta(business_meaning="Hito previo a la oferta; permite ordenar el flujo cronologico."),
        "fecha_enviado": field_meta(business_meaning="Obligatoria para pasar a estado Enviada o Adjudicada."),
        "fecha_cierre_cliente": field_meta(business_meaning="Obligatoria para cerrar como Adjudicada o Rechazada."),
        "oferta": field_meta(
            business_meaning="Cifra que se factura si se adjudica; entra en KPIs de oferta_total y forecast.",
            unit="EUR",
        ),
        "presupuesto": field_meta(
            business_meaning="Legacy: campo TEXT de Sprints anteriores, mantenido por compatibilidad. Sustituido por la combinacion oferta + solicitud_actuaciones.",
            legacy=True,
        ),
        "cobertura_pct": field_meta(
            business_meaning="Indica que parte del importe ofertado se ira al coste; el resto es margen.",
            unit="%",
            calculated=True,
        ),
        "coste": field_meta(
            business_meaning="Entrada manual del tecnico; combinada con oferta produce margen, cobertura y coeficiente.",
            unit="EUR",
        ),
        "coeficiente": field_meta(
            business_meaning="Marcador rapido de rentabilidad: 1.33 significa que la oferta es 1.33 veces el coste.",
            calculated=True,
        ),
        "margen_pct": field_meta(
            business_meaning="Indicador comercial principal de rentabilidad; entra en el donut financiero del detalle.",
            unit="%",
            calculated=True,
        ),
        "estudio_direccion": field_meta(business_meaning="Caso de uso minoritario: permite separar la direccion de obra de la del estudio."),
        "contactos": field_meta(
            business_meaning="Legacy: serializaba la lista de contactos antes de Sprint A. Sustituido por la tabla solicitud_contactos.",
            legacy=True,
        ),
        "actuaciones": field_meta(
            business_meaning="Legacy: serializaba las actuaciones antes de Sprint A. Sustituido por solicitud_actuaciones.",
            legacy=True,
        ),
        "descripcion": field_meta(business_meaning="Contexto que el comercial guarda para preparar la oferta y briefing del tecnico."),
        "observaciones": field_meta(business_meaning="Conversaciones, riesgos y recordatorios cortos que no caben en el resto de campos."),
        "aging_dias": field_meta(
            business_meaning="Mide cuanto lleva una oportunidad sin cerrarse; alerta visual de estancamiento.",
            unit="dias",
            calculated=True,
        ),
        "created_at": field_meta(business_meaning="Punto de partida para aging y heatmap mensual."),
        "updated_at": field_meta(business_meaning="Permite ordenar por actividad reciente y detectar solicitudes paradas."),
    }

    id: str = Field(default_factory=_uuid, primary_key=True,
        description="UUID v4 generado al crear la solicitud.")
    codigo: str = Field(unique=True, index=True,
        description="Codigo legible tipo SOL-2026-ABCD.")
    nombre_corto: str = Field(
        description="Nombre breve de la obra o proyecto.")
    poblacion: Optional[str] = Field(default=None,
        description="Ciudad o localidad de la obra.")
    estado: str = Field(default="En Estudio", index=True,
        description="Estado actual de la solicitud en el embudo.")
    kanban_column: str = Field(default="En Estudio",
        description="Columna del tablero kanban donde se renderiza la tarjeta.")
    color_estado: str = Field(default="#6366f1",
        description="Color hex asociado a la tarjeta en el kanban.")
    prioridad: str = Field(default="media",
        description="Prioridad asignada a la solicitud (alta / media / baja).")
    comercial: Optional[str] = Field(default=None, foreign_key="usuarios.id", index=True,
        description="FK al usuario comercial asignado.")
    tecnico_estudios: Optional[str] = Field(default=None, foreign_key="usuarios.id", index=True,
        description="FK al usuario tecnico de estudios.")
    tipo_via: Optional[str] = Field(default=None,
        description="Tipo de via (Calle, Avenida, Plaza...).")
    numero: Optional[str] = Field(default=None,
        description="Numero de portal en la direccion.")
    cp: Optional[str] = Field(default=None, index=True,
        description="Codigo postal de la obra.")
    fecha_solicitud: Optional[date] = Field(default=None,
        description="Fecha en que entra la solicitud.")
    fecha_limite: Optional[date] = Field(default=None,
        description="Fecha limite para enviar / cerrar la oferta.")
    fecha_reunion: Optional[date] = Field(default=None,
        description="Fecha de reunion con el cliente.")
    fecha_visita: Optional[date] = Field(default=None,
        description="Fecha de visita a la obra.")
    fecha_enviado: Optional[date] = Field(default=None,
        description="Fecha de envio de la oferta al cliente.")
    fecha_cierre_cliente: Optional[date] = Field(default=None,
        description="Fecha de decision del cliente.")
    oferta: Optional[float] = Field(default=None,
        description="Importe de la oferta en EUR.")
    presupuesto: Optional[str] = Field(default=None,
        description="Texto libre con notas de presupuesto (legacy).")
    cobertura_pct: Optional[float] = Field(default=None,
        description="Porcentaje del coste sobre la oferta. Calculado server-side.")
    coste: Optional[float] = Field(default=None,
        description="Coste estimado del proyecto en EUR.")
    coeficiente: Optional[float] = Field(default=None,
        description="Cociente oferta / coste. Calculado server-side.")
    margen_pct: Optional[float] = Field(default=None,
        description="Porcentaje de margen sobre la oferta. Calculado server-side.")
    estudio_direccion: Optional[str] = Field(default=None,
        description="Direccion alternativa del estudio asignado.")
    contactos: Optional[str] = Field(default=None,
        description="JSON legacy con contactos embebidos.")
    actuaciones: Optional[str] = Field(default=None,
        description="JSON legacy con actuaciones embebidas.")
    descripcion: Optional[str] = Field(default=None,
        description="Descripcion libre del proyecto.")
    observaciones: Optional[str] = Field(default=None,
        description="Notas internas sobre la solicitud.")
    aging_dias: Optional[int] = Field(default=None,
        description="Edad de la solicitud en dias desde su creacion.")
    created_at: datetime = Field(default_factory=datetime.utcnow,
        description="Timestamp UTC de creacion.")
    updated_at: Optional[datetime] = Field(default=None,
        description="Timestamp UTC de la ultima modificacion.")


# ---------------------------------------------------------------------------
# Sprint A: Contactos por solicitud (tabla hija)
# ---------------------------------------------------------------------------

class SolicitudContacto(SQLModel, table=True):
    """Contacto asociado a una solicitud."""

    __tablename__ = "solicitud_contactos"
    __meta__ = entity_meta(
        description="Contacto humano asociado a una solicitud (admin, tecnico de obra, propiedad...).",
        business_meaning=(
            "Lista de personas con las que hablar para esa oportunidad: telefono, "
            "email y rol. Sustituye al JSON legacy 'contactos' de Solicitud."
        ),
        lifecycle="Creado, editado y borrado libremente. Se borra al borrar la solicitud padre.",
    )
    __field_meta__ = {
        "id": field_meta(business_meaning="Identificador estable para edicion / borrado individual."),
        "solicitud_id": field_meta(business_meaning="Vincula el contacto al proyecto comercial donde se usa."),
        "tipo": field_meta(
            business_meaning="Permite al comercial saber a quien dirigirse para cada gestion.",
            examples=_CONTACTO_TIPOS,
        ),
        "nombre": field_meta(business_meaning="Lo que el comercial dice al llamar."),
        "telefono": field_meta(business_meaning="Canal principal de contacto en obra y administracion."),
        "email": field_meta(business_meaning="Usado para envio de oferta y comunicaciones formales."),
        "notas": field_meta(business_meaning="Detalles utiles que no caben en los campos estandar (horario, idioma, preferencias)."),
        "created_at": field_meta(business_meaning="Permite ordenar contactos por orden de alta."),
        "updated_at": field_meta(business_meaning="Detecta cambios recientes en datos de contacto."),
    }

    id: str = Field(default_factory=_uuid, primary_key=True,
        description="UUID v4 generado server-side.")
    solicitud_id: str = Field(foreign_key="solicitudes.id", index=True,
        description="FK a la solicitud padre.")
    tipo: str = Field(index=True,
        description="Rol del contacto dentro de la obra.")
    nombre: Optional[str] = Field(default=None,
        description="Nombre del contacto.")
    telefono: Optional[str] = Field(default=None,
        description="Telefono libre (sin validacion de formato).")
    email: Optional[str] = Field(default=None,
        description="Email del contacto.")
    notas: Optional[str] = Field(default=None,
        description="Notas libres sobre el contacto.")
    created_at: datetime = Field(default_factory=datetime.utcnow,
        description="Timestamp UTC de creacion.")
    updated_at: Optional[datetime] = Field(default=None,
        description="Timestamp UTC de la ultima modificacion.")


# ---------------------------------------------------------------------------
# Sprint A: Catalogo de actuaciones + tabla N-N
# ---------------------------------------------------------------------------

class Actuacion(SQLModel, table=True):
    """Catalogo maestro de tipos de actuacion."""

    __tablename__ = "actuaciones"
    __meta__ = entity_meta(
        description="Catalogo cerrado de tipos de actuacion que ofrece Vedisa.",
        business_meaning=(
            "Inventario fijo (fachada, cubierta, estructura...) que el comercial "
            "asigna a una solicitud. Alimenta el donut 'Mix de actuaciones' del "
            "dashboard y las lineas del PDF de oferta."
        ),
        lifecycle="Catalogo semilla seteado por migracion Alembic; rara vez crece.",
    )
    __field_meta__ = {
        "id": field_meta(
            business_meaning="Identificador legible que aparece en URLs y filtros.",
            examples=["fachada", "cubierta", "estructura", "sate", "zbcc"],
        ),
        "nombre": field_meta(business_meaning="Lo que se muestra en checkboxes del panel y en el PDF."),
        "orden": field_meta(business_meaning="Controla la posicion del checkbox en la lista del panel."),
        "activo": field_meta(business_meaning="Permite retirar una actuacion sin borrarla y perder historial."),
    }

    id: str = Field(primary_key=True,
        description="Slug estable, ej. 'fachada'.")
    nombre: str = Field(
        description="Etiqueta humana del tipo de actuacion.")
    orden: int = Field(default=0,
        description="Orden de presentacion en el UI.")
    activo: bool = Field(default=True,
        description="Si False, el catalogo deja de ofrecerlo.")


class SolicitudActuacion(SQLModel, table=True):
    """Relacion N-N entre solicitudes y actuaciones con m2 e importe por linea."""

    __tablename__ = "solicitud_actuaciones"
    __meta__ = entity_meta(
        description="Linea de actuacion asignada a una solicitud, con superficie e importe.",
        business_meaning=(
            "Detalle constructivo de la oferta: para cada actuacion del catalogo "
            "que aplica al proyecto, guarda m2 estimados e importe asociado. Se "
            "usa para construir la tabla de actuaciones del PDF de oferta."
        ),
        lifecycle=(
            "Creada al activar el checkbox en el panel; borrada al desactivarlo. "
            "PK compuesto (solicitud_id, actuacion_id) garantiza unicidad."
        ),
    )
    __field_meta__ = {
        "solicitud_id": field_meta(business_meaning="Vincula esta linea de actuacion al proyecto comercial."),
        "actuacion_id": field_meta(business_meaning="Indica que tipo de obra concreto se incluye en esta linea."),
        "m2": field_meta(
            business_meaning="Magnitud principal para dimensionar la oferta de esta actuacion.",
            unit="m2",
        ),
        "importe": field_meta(
            business_meaning="Suma de todas las lineas debe cuadrar con la oferta total de la solicitud.",
            unit="EUR",
        ),
        "created_at": field_meta(business_meaning="Auditoria basica de cuando se anadio la actuacion al proyecto."),
    }

    solicitud_id: str = Field(foreign_key="solicitudes.id", primary_key=True,
        description="FK a la solicitud padre.")
    actuacion_id: str = Field(foreign_key="actuaciones.id", primary_key=True,
        description="FK a la actuacion del catalogo.")
    m2: Optional[float] = Field(default=None,
        description="Superficie estimada en metros cuadrados.")
    importe: Optional[float] = Field(default=None,
        description="Importe asignado a esta linea, en EUR.")
    created_at: datetime = Field(default_factory=datetime.utcnow,
        description="Timestamp UTC de creacion de la linea.")


# ---------------------------------------------------------------------------
# Sprint C: AuditLog de cambios en solicitudes
# ---------------------------------------------------------------------------

class AuditLog(SQLModel, table=True):
    """Registro de auditoria de cambios en solicitudes."""

    __tablename__ = "audit_log"
    __meta__ = entity_meta(
        description="Bitacora append-only de cambios sobre solicitudes.",
        business_meaning=(
            "Trazabilidad completa: cada update genera una fila por campo "
            "cambiado, los cambios de estado quedan con accion 'estado_change', "
            "y el reemplazo de actuaciones con 'actuaciones_update'. Se lee desde "
            "/historial en el panel del CRM."
        ),
        lifecycle="Insercion automatica al modificar una solicitud; nunca se borra ni se actualiza.",
    )
    __field_meta__ = {
        "id": field_meta(business_meaning="Identificador estable para una operacion concreta del historial."),
        "solicitud_id": field_meta(business_meaning="Permite reconstruir la historia completa de cambios de una solicitud."),
        "usuario_id": field_meta(business_meaning="Atribuye el cambio a la persona para auditoria y responsabilidad."),
        "accion": field_meta(
            business_meaning="Distingue create / update / estado_change / actuaciones_update / delete para filtros del historial.",
            examples=_AUDIT_ACCIONES,
        ),
        "campo": field_meta(business_meaning="Permite saber exactamente que dato se modifico en cada fila de la bitacora."),
        "valor_anterior": field_meta(business_meaning="Diff lateral del campo, util para deshacer o investigar."),
        "valor_nuevo": field_meta(business_meaning="Estado actual del campo justo despues de la operacion."),
        "created_at": field_meta(business_meaning="Ordena la bitacora; el historial del UI muestra entradas en DESC por este campo."),
    }

    id: str = Field(default_factory=_uuid, primary_key=True,
        description="UUID v4 de la entrada de auditoria.")
    solicitud_id: str = Field(foreign_key="solicitudes.id", index=True,
        description="FK a la solicitud auditada.")
    usuario_id: Optional[str] = Field(default=None, foreign_key="usuarios.id",
        description="FK al usuario que realizo el cambio (None si fue sistema).")
    accion: str = Field(
        description="Tipo de operacion auditada (create / update / delete / estado_change / actuaciones_update).")
    campo: Optional[str] = Field(default=None,
        description="Nombre del campo cambiado (None en create / delete).")
    valor_anterior: Optional[str] = Field(default=None,
        description="Valor del campo antes del cambio, serializado a string.")
    valor_nuevo: Optional[str] = Field(default=None,
        description="Valor del campo despues del cambio, serializado a string.")
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True,
        description="Timestamp UTC del cambio.")

    class Config:
        arbitrary_types_allowed = True


_AnyType = Any


# ---------------------------------------------------------------------------
# AIAuditLog
# ---------------------------------------------------------------------------

class AIAuditLog(SQLModel, table=True):
    """Registro de auditoria de llamadas al LLM."""

    __tablename__ = "ai_audit_log"
    __meta__ = entity_meta(
        description="Bitacora de llamadas a proveedores LLM (analyze / chat / test).",
        business_meaning=(
            "Permite analizar coste y latencia por proveedor / modelo, y detectar "
            "errores recurrentes en la integracion con OpenAI / Anthropic / etc."
        ),
        lifecycle="Insercion automatica al llamar al router LLM; nunca se borra desde el codigo.",
    )
    __field_meta__ = {
        "id": field_meta(business_meaning="Identificador estable de la operacion en metricas y debugging."),
        "endpoint": field_meta(
            business_meaning="Distingue si la llamada vino del drawer (analyze), chat o test de salud.",
            examples=_AI_ENDPOINTS,
        ),
        "solicitud_id": field_meta(business_meaning="Permite cruzar consumo IA con oportunidades comerciales."),
        "usuario_id": field_meta(business_meaning="Atribuye el consumo a una persona para reporting."),
        "provider": field_meta(business_meaning="Permite comparar coste y latencia entre proveedores."),
        "model": field_meta(business_meaning="Granularidad fina del proveedor para metricas y A/B de calidad."),
        "prompt_tokens": field_meta(business_meaning="Mitad input del coste por llamada.", unit="tokens"),
        "completion_tokens": field_meta(business_meaning="Mitad output del coste; suele ser mas cara por token.", unit="tokens"),
        "total_tokens": field_meta(business_meaning="Magnitud total de la llamada para reporting agregado.", unit="tokens", calculated=True),
        "latency_ms": field_meta(business_meaning="Mide el coste de tiempo real para el usuario que dispara la IA.", unit="ms"),
        "success": field_meta(business_meaning="Permite calcular tasa de fallos por proveedor / modelo."),
        "error_msg": field_meta(business_meaning="Pista para diagnosticar fallos recurrentes del proveedor o del prompt."),
        "created_at": field_meta(business_meaning="Permite ventanas temporales para reporting de consumo IA."),
    }

    id: str = Field(default_factory=_uuid, primary_key=True,
        description="UUID v4 de la llamada.")
    endpoint: str = Field(index=True,
        description="Endpoint logico que origino la llamada.")
    solicitud_id: Optional[str] = Field(default=None, index=True,
        description="FK opcional a la solicitud en cuyo contexto se llamo al LLM.")
    usuario_id: Optional[str] = Field(default=None, index=True,
        description="FK opcional al usuario que disparo la llamada.")
    provider: str = Field(index=True,
        description="Proveedor LLM efectivo (openai, anthropic...).")
    model: str = Field(
        description="Modelo concreto utilizado (gpt-4o, claude-3.5-sonnet, etc.).")
    prompt_tokens: int = Field(default=0,
        description="Tokens consumidos en el prompt.")
    completion_tokens: int = Field(default=0,
        description="Tokens generados en la respuesta.")
    total_tokens: int = Field(default=0,
        description="Suma prompt + completion (calculado).")
    latency_ms: int = Field(default=0,
        description="Latencia total de la llamada en milisegundos.")
    success: bool = Field(default=True,
        description="True si la llamada se completo sin error.")
    error_msg: Optional[str] = Field(default=None,
        description="Mensaje de error si success=False.")
    created_at: datetime = Field(default_factory=datetime.utcnow,
        description="Timestamp UTC de la llamada.")
