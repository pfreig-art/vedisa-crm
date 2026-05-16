import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { X, Trash2, Save, Plus, Clock } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import {
  crmApi,
  Solicitud,
  SolicitudCreate,
  ContactoTipo,
  ContactoInput,
  AuditLogEntry,
} from '../api/crm'
import { useUsuarios, useActuaciones } from '../hooks/useCatalogs'
import UserAvatar from './UserAvatar'
import { useUsuariosMap } from '../hooks/useCatalogs'

const ESTADOS = ['En Estudio', 'Enviada', 'Adjudicada', 'Rechazada', 'Descartada'] as const
type EstadoType = typeof ESTADOS[number]

const PRIORIDADES = ['alta', 'media', 'baja'] as const

const ESTADO_COLOR: Record<string, string> = {
  'En Estudio': '#6366f1',
  Enviada: '#f59e0b',
  Adjudicada: '#10b981',
  Rechazada: '#ef4444',
  Descartada: '#6b7280',
}

// Orden de progresion de estados
const ESTADO_STEP: Record<string, number> = {
  'En Estudio': 0,
  Enviada: 1,
  Adjudicada: 2,
  Rechazada: 2,
  Descartada: 2,
}

const TIPOS_VIA = [
  'Calle', 'Avenida', 'Paseo', 'Plaza', 'Carretera', 'Camino', 'Ronda', 'Pasaje', 'Otro',
]

const CONTACTO_TIPOS: { value: ContactoTipo; label: string }[] = [
  { value: 'administracion', label: 'Administracion' },
  { value: 'tecnico_obra', label: 'Tecnico de obra' },
  { value: 'ensena_obra', label: 'Ensena obra' },
  { value: 'presidente', label: 'Presidente' },
  { value: 'propiedad', label: 'Propiedad' },
  { value: 'otro', label: 'Otro' },
]

interface Props {
  solicitud: Solicitud | null
  open: boolean
  onClose: () => void
  mode: 'create' | 'edit'
}

type FormData = SolicitudCreate

const inp =
  'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500'
const lbl = 'block text-xs font-medium text-gray-600 mb-1'
const section = 'border-t pt-4'
const sectionTitle = 'text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3'

type TabKey = 'form' | 'historial'

function emptyValues(): Partial<FormData> {
  return {
    estado: 'En Estudio',
    prioridad: 'media',
    nombre_corto: '',
    codigo: '',
    poblacion: '',
    tipo_via: '',
    numero: '',
    cp: '',
    comercial: '',
    tecnico_estudios: '',
    fecha_solicitud: '',
    fecha_limite: '',
    fecha_reunion: '',
    fecha_visita: '',
    fecha_enviado: '',
    fecha_cierre_cliente: '',
    descripcion: '',
    observaciones: '',
    oferta: undefined,
    cobertura_pct: undefined,
    coste: undefined,
    coeficiente: undefined,
    margen_pct: undefined,
  }
}

// ---------------------------------------------------------------------------
// Progress bar de estados
// ---------------------------------------------------------------------------
function EstadoProgressBar({ estado }: { estado: string }) {
  const steps: { key: EstadoType; label: string }[] = [
    { key: 'En Estudio', label: 'En Estudio' },
    { key: 'Enviada', label: 'Enviada' },
    { key: 'Adjudicada', label: 'Adjudicada / Rechazada / Descartada' },
  ]
  const currentStep = ESTADO_STEP[estado] ?? 0

  return (
    <div className="mt-2 flex items-center gap-0">
      {steps.map((step, idx) => {
        const isActive = idx === currentStep
        const isDone = idx < currentStep
        const color = isActive
          ? ESTADO_COLOR[estado] ?? '#6366f1'
          : isDone
          ? '#475569'
          : '#1e293b'
        return (
          <div key={step.key} className="flex flex-1 flex-col items-center">
            <div
              className="h-1.5 w-full rounded-full transition-colors"
              style={{ backgroundColor: color }}
            />
            <span
              className="mt-1 text-center text-[9px] leading-tight"
              style={{
                color: isActive ? ESTADO_COLOR[estado] ?? '#6366f1' : isDone ? '#64748b' : '#334155',
                fontWeight: isActive ? 600 : 400,
              }}
            >
              {step.label}
            </span>
          </div>
        )
      })}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Mini donut financiero
// ---------------------------------------------------------------------------
export function FinancieroDonut({ oferta, coste }: { oferta?: number | null; coste?: number | null }) {
  if (!oferta || !coste || oferta <= 0 || coste <= 0) return null
  const margen = oferta - coste
  const data = [
    { name: 'Coste', value: coste, fill: '#ef4444' },
    { name: 'Margen', value: Math.max(margen, 0), fill: '#10b981' },
  ]
  return (
    <div className="flex items-center gap-3 mt-3">
      <ResponsiveContainer width={80} height={80}>
        <PieChart>
          <Pie data={data} cx="50%" cy="50%" innerRadius={22} outerRadius={36} dataKey="value" strokeWidth={0}>
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.fill} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 6, fontSize: 11 }}
            formatter={(v) => [`${Number(v ?? 0).toLocaleString('es-ES')} EUR`]}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="space-y-1 text-xs">
        <div className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-red-400" />
          <span className="text-gray-600">Coste: {coste.toLocaleString('es-ES')} EUR</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-emerald-500" />
          <span className="text-gray-600">Margen: {margen.toLocaleString('es-ES')} EUR</span>
        </div>
        {oferta > 0 && (
          <div className="text-gray-500">
            {((margen / oferta) * 100).toFixed(1)}% margen
          </div>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Timeline visual de fechas
// ---------------------------------------------------------------------------
function FechasTimeline({ solicitud }: { solicitud: Solicitud | null }) {
  if (!solicitud) return null

  const hitos: { key: string; label: string; fecha?: string | null }[] = [
    { key: 'solicitud', label: 'Solicitud', fecha: solicitud.fecha_solicitud },
    { key: 'reunion', label: 'Reunion', fecha: solicitud.fecha_reunion },
    { key: 'visita', label: 'Visita', fecha: solicitud.fecha_visita },
    { key: 'enviado', label: 'Enviada', fecha: solicitud.fecha_enviado },
    { key: 'limite', label: 'Limite', fecha: solicitud.fecha_limite },
    { key: 'cierre', label: 'Cierre', fecha: solicitud.fecha_cierre_cliente },
  ]

  const presentes = hitos.filter((h) => h.fecha)
  if (presentes.length === 0) return <p className="text-xs text-gray-400">Sin fechas registradas.</p>

  return (
    <div className="mt-3 overflow-x-auto">
      <div className="flex min-w-max items-start gap-0">
        {presentes.map((h, idx) => (
          <div key={h.key} className="flex items-start">
            <div className="flex flex-col items-center">
              <div className="flex items-center">
                <div className="h-2.5 w-2.5 rounded-full bg-indigo-500 ring-2 ring-indigo-100" />
                {idx < presentes.length - 1 && <div className="h-px w-16 bg-gray-200" />}
              </div>
              <div className="mt-1.5 flex flex-col items-center text-center">
                <span className="text-[9px] font-semibold uppercase tracking-wide text-gray-400">{h.label}</span>
                <span className="text-[10px] text-gray-600">{h.fecha}</span>
              </div>
            </div>
            {idx < presentes.length - 1 && <div className="invisible h-px w-0" />}
          </div>
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Tab Historial
// ---------------------------------------------------------------------------
function HistorialTab({ solicitudId }: { solicitudId: string }) {
  const { data: historial = [], isLoading } = useQuery<AuditLogEntry[]>({
    queryKey: ['historial', solicitudId],
    queryFn: () => crmApi.getHistorial(solicitudId),
  })
  const { map: usuariosMap } = useUsuariosMap()

  if (isLoading) {
    return <div className="py-8 text-center text-sm text-gray-400">Cargando historial…</div>
  }
  if (historial.length === 0) {
    return <div className="py-8 text-center text-sm text-gray-400">Sin registros de auditoria.</div>
  }

  const ACCION_LABEL: Record<string, string> = {
    create: 'Creado',
    update: 'Actualizado',
    delete: 'Eliminado',
    estado_change: 'Cambio de estado',
  }

  return (
    <div className="space-y-3 py-4">
      {historial.map((log) => {
        const u = log.usuario_id ? usuariosMap.get(log.usuario_id) : null
        const hasUser = u || log.usuario_nombre
        return (
          <div key={log.id} className="flex gap-3">
            <div className="flex flex-col items-center">
              <div className="h-7 w-7 shrink-0">
                {hasUser ? (
                  <UserAvatar
                    usuario={
                      u ?? {
                        id: log.usuario_id ?? '',
                        nombre: log.usuario_nombre ?? '',
                        email: '',
                        rol: '',
                        activo: true,
                        iniciales: log.usuario_iniciales ?? undefined,
                        color: log.usuario_color ?? undefined,
                      }
                    }
                    size="sm"
                  />
                ) : (
                  <div className="flex h-7 w-7 items-center justify-center rounded-full bg-gray-200">
                    <Clock className="h-3.5 w-3.5 text-gray-400" />
                  </div>
                )}
              </div>
              <div className="mt-1 w-px flex-1 bg-gray-100" />
            </div>
            <div className="pb-4 min-w-0">
              <div className="flex items-baseline gap-2">
                <span className="text-xs font-semibold text-gray-700">
                  {log.usuario_nombre ?? 'Sistema'}
                </span>
                <span className="rounded-full bg-indigo-50 px-1.5 py-0.5 text-[10px] text-indigo-600">
                  {ACCION_LABEL[log.accion] ?? log.accion}
                </span>
                <span className="text-[10px] text-gray-400">
                  {new Date(log.created_at).toLocaleString('es-ES', {
                    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
                  })}
                </span>
              </div>
              {log.campo && (
                <div className="mt-0.5 text-xs text-gray-500">
                  <span className="font-medium text-gray-600">{log.campo}</span>
                  {log.valor_anterior !== null && log.valor_anterior !== '' && (
                    <span> de <span className="line-through text-red-400">{log.valor_anterior}</span></span>
                  )}
                  {log.valor_nuevo !== null && log.valor_nuevo !== '' && (
                    <span> a <span className="text-green-600">{log.valor_nuevo}</span></span>
                  )}
                </div>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ---------------------------------------------------------------------------
// SolicitudSheet principal
// ---------------------------------------------------------------------------
export default function SolicitudSheet({ solicitud, open, onClose, mode }: Props) {
  const qc = useQueryClient()
  const { register, handleSubmit, reset } = useForm<FormData>({ defaultValues: emptyValues() })
  const [activeTab, setActiveTab] = useState<TabKey>('form')

  const { data: usuarios = [] } = useUsuarios({ activo: true })
  const { data: actuaciones = [] } = useActuaciones()

  const [selectedActuaciones, setSelectedActuaciones] = useState<string[]>([])
  const [contactos, setContactos] = useState<ContactoInput[]>([])

  // Carga de actuaciones y contactos al abrir en modo edit
  const { data: solActuaciones } = useQuery({
    queryKey: ['solicitud-actuaciones', solicitud?.id],
    queryFn: () => crmApi.listSolicitudActuaciones(solicitud!.id),
    enabled: !!solicitud?.id && mode === 'edit' && open,
  })
  const { data: solContactos } = useQuery({
    queryKey: ['solicitud-contactos', solicitud?.id],
    queryFn: () => crmApi.listContactos(solicitud!.id),
    enabled: !!solicitud?.id && mode === 'edit' && open,
  })

  useEffect(() => {
    if (!open) return
    setActiveTab('form')
    if (solicitud && mode === 'edit') {
      reset({
        nombre_corto: solicitud.nombre_corto,
        codigo: solicitud.codigo,
        poblacion: solicitud.poblacion ?? '',
        estado: solicitud.estado,
        prioridad: solicitud.prioridad ?? 'media',
        comercial: solicitud.comercial ?? '',
        tecnico_estudios: solicitud.tecnico_estudios ?? '',
        tipo_via: solicitud.tipo_via ?? '',
        numero: solicitud.numero ?? '',
        cp: solicitud.cp ?? '',
        fecha_solicitud: solicitud.fecha_solicitud ?? '',
        fecha_limite: solicitud.fecha_limite ?? '',
        fecha_reunion: solicitud.fecha_reunion ?? '',
        fecha_visita: solicitud.fecha_visita ?? '',
        fecha_enviado: solicitud.fecha_enviado ?? '',
        fecha_cierre_cliente: solicitud.fecha_cierre_cliente ?? '',
        oferta: solicitud.oferta ?? undefined,
        cobertura_pct: solicitud.cobertura_pct ?? undefined,
        coste: solicitud.coste ?? undefined,
        coeficiente: solicitud.coeficiente ?? undefined,
        margen_pct: solicitud.margen_pct ?? undefined,
        descripcion: solicitud.descripcion ?? '',
        observaciones: solicitud.observaciones ?? '',
      })
    } else {
      reset(emptyValues())
      setSelectedActuaciones([])
      setContactos([])
    }
  }, [solicitud, mode, reset, open])

  useEffect(() => {
    if (solActuaciones) setSelectedActuaciones(solActuaciones.map((a) => a.id))
  }, [solActuaciones])

  useEffect(() => {
    if (solContactos) {
      setContactos(
        solContactos.map((c) => ({
          tipo: c.tipo,
          nombre: c.nombre ?? '',
          telefono: c.telefono ?? '',
          email: c.email ?? '',
          notas: c.notas ?? '',
        })),
      )
    }
  }, [solContactos])

  const inv = () => {
    qc.invalidateQueries({ queryKey: ['solicitudes'] })
    qc.invalidateQueries({ queryKey: ['pipeline'] })
    qc.invalidateQueries({ queryKey: ['dashboard'] })
    qc.invalidateQueries({ queryKey: ['alertas'] })
  }

  function toPayload(data: FormData): SolicitudCreate {
    const out: Record<string, unknown> = {}
    for (const [k, v] of Object.entries(data)) {
      if (v === '' || v === undefined) out[k] = null
      else out[k] = v
    }
    return out as unknown as SolicitudCreate
  }

  async function persistChildren(solicitudId: string) {
    await crmApi.setSolicitudActuaciones(solicitudId, selectedActuaciones)
    const existentes = await crmApi.listContactos(solicitudId)
    await Promise.all(existentes.map((c) => crmApi.deleteContacto(c.id)))
    for (const c of contactos) {
      if (!c.nombre && !c.telefono && !c.email) continue
      await crmApi.createContacto(solicitudId, {
        tipo: c.tipo,
        nombre: c.nombre || null,
        telefono: c.telefono || null,
        email: c.email || null,
        notas: c.notas || null,
      })
    }
  }

  const createMut = useMutation({
    mutationFn: async (d: SolicitudCreate) => {
      const created = await crmApi.createSolicitud(d)
      await persistChildren(created.id)
      return created
    },
    onSuccess: () => {
      inv()
      onClose()
    },
  })

  const updateMut = useMutation({
    mutationFn: async (d: SolicitudCreate) => {
      const updated = await crmApi.updateSolicitud(solicitud!.id, d)
      await persistChildren(updated.id)
      return updated
    },
    onSuccess: () => {
      inv()
      qc.invalidateQueries({ queryKey: ['solicitud-actuaciones', solicitud?.id] })
      qc.invalidateQueries({ queryKey: ['solicitud-contactos', solicitud?.id] })
      qc.invalidateQueries({ queryKey: ['historial', solicitud?.id] })
      onClose()
    },
  })

  const deleteMut = useMutation({
    mutationFn: () => crmApi.deleteSolicitud(solicitud!.id),
    onSuccess: () => {
      inv()
      onClose()
    },
  })

  const onSubmit = (data: FormData) => {
    const payload = toPayload(data)
    payload.color_estado = ESTADO_COLOR[data.estado ?? 'En Estudio'] ?? '#6366f1'
    payload.kanban_column = data.estado ?? 'En Estudio'
    mode === 'create' ? createMut.mutate(payload) : updateMut.mutate(payload)
  }

  const isPending = createMut.isPending || updateMut.isPending

  const toggleActuacion = (id: string) => {
    setSelectedActuaciones((curr) =>
      curr.includes(id) ? curr.filter((x) => x !== id) : [...curr, id],
    )
  }

  const addContacto = (tipo: ContactoTipo) => {
    setContactos((curr) => [...curr, { tipo, nombre: '', telefono: '', email: '', notas: '' }])
  }
  const updateContactoField = (idx: number, field: keyof ContactoInput, value: string) => {
    setContactos((curr) => curr.map((c, i) => (i === idx ? { ...c, [field]: value } : c)))
  }
  const removeContacto = (idx: number) => {
    setContactos((curr) => curr.filter((_, i) => i !== idx))
  }

  return (
    <>
      <div
        className={`fixed inset-0 bg-black/40 backdrop-blur-sm z-40 transition-opacity duration-300 ${
          open ? 'opacity-100' : 'opacity-0 pointer-events-none'
        }`}
        onClick={onClose}
      />
      <div
        className={`fixed top-0 right-0 h-full w-full max-w-2xl bg-white shadow-2xl z-50 flex flex-col transition-transform duration-300 ease-out ${
          open ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        {/* Cabecera */}
        <div className="flex flex-col px-6 py-4 border-b bg-gray-50">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                {mode === 'create' ? 'Nueva Solicitud' : 'Editar Solicitud'}
              </h2>
              {solicitud && <p className="text-xs text-gray-500 mt-0.5">{solicitud.codigo}</p>}
            </div>
            <div className="flex items-center gap-2">
              {mode === 'edit' && (
                <button
                  type="button"
                  onClick={() => {
                    if (confirm('Eliminar esta solicitud?')) deleteMut.mutate()
                  }}
                  className="p-2 text-red-500 hover:bg-red-50 rounded-lg transition"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
              <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg transition">
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
          </div>

          {/* Progress bar de estado */}
          {solicitud && mode === 'edit' && (
            <EstadoProgressBar estado={solicitud.estado} />
          )}
        </div>

        {/* Tabs */}
        {mode === 'edit' && solicitud && (
          <div className="flex border-b border-gray-200 px-6">
            {(['form', 'historial'] as TabKey[]).map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={`py-2.5 px-4 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab
                    ? 'border-indigo-600 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab === 'form' ? 'Datos' : 'Historial'}
              </button>
            ))}
          </div>
        )}

        {/* Tab Historial */}
        {activeTab === 'historial' && solicitud?.id ? (
          <div className="flex-1 overflow-y-auto px-6">
            <HistorialTab solicitudId={solicitud.id} />
          </div>
        ) : (
          <form onSubmit={handleSubmit(onSubmit)} className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
            {/* Cabecera */}
            <div className="space-y-4">
              <div>
                <label className={lbl}>Nombre / Proyecto *</label>
                <input
                  {...register('nombre_corto', { required: true })}
                  className={inp}
                  placeholder="Edificio Mar y Sol..."
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={lbl}>Codigo</label>
                  <input {...register('codigo')} className={inp} placeholder="auto si vacio" />
                </div>
                <div>
                  <label className={lbl}>Poblacion</label>
                  <input {...register('poblacion')} className={inp} placeholder="Mao" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={lbl}>Estado</label>
                  <select {...register('estado')} className={inp}>
                    {ESTADOS.map((e) => (
                      <option key={e} value={e}>
                        {e}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className={lbl}>Prioridad</label>
                  <select {...register('prioridad')} className={inp}>
                    {PRIORIDADES.map((p) => (
                      <option key={p} value={p}>
                        {p}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            {/* Direccion */}
            <div className={section}>
              <div className={sectionTitle}>Direccion</div>
              <div className="grid grid-cols-6 gap-3">
                <div className="col-span-2">
                  <label className={lbl}>Tipo via</label>
                  <select {...register('tipo_via')} className={inp}>
                    <option value="">—</option>
                    {TIPOS_VIA.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="col-span-3">
                  <label className={lbl}>Nombre via</label>
                  <input
                    {...register('estudio_direccion')}
                    className={inp}
                    placeholder="Ej. Mossen Antoni Maria Alcover"
                  />
                </div>
                <div className="col-span-1">
                  <label className={lbl}>Numero</label>
                  <input {...register('numero')} className={inp} />
                </div>
                <div className="col-span-1">
                  <label className={lbl}>CP</label>
                  <input {...register('cp')} className={inp} placeholder="07700" />
                </div>
              </div>
            </div>

            {/* Asignacion */}
            <div className={section}>
              <div className={sectionTitle}>Asignacion</div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={lbl}>Comercial</label>
                  <select {...register('comercial')} className={inp}>
                    <option value="">— sin asignar —</option>
                    {usuarios.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.nombre}
                        {u.cargo ? ` · ${u.cargo}` : ''}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className={lbl}>Tecnico de estudios</label>
                  <select {...register('tecnico_estudios')} className={inp}>
                    <option value="">— sin asignar —</option>
                    {usuarios.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.nombre}
                        {u.cargo ? ` · ${u.cargo}` : ''}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            {/* Fechas */}
            <div className={section}>
              <div className={sectionTitle}>Fechas</div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className={lbl}>Solicitud</label>
                  <input type="date" {...register('fecha_solicitud')} className={inp} />
                </div>
                <div>
                  <label className={lbl}>Reunion</label>
                  <input type="date" {...register('fecha_reunion')} className={inp} />
                </div>
                <div>
                  <label className={lbl}>Visita</label>
                  <input type="date" {...register('fecha_visita')} className={inp} />
                </div>
                <div>
                  <label className={lbl}>Enviado</label>
                  <input type="date" {...register('fecha_enviado')} className={inp} />
                </div>
                <div>
                  <label className={lbl}>Limite</label>
                  <input type="date" {...register('fecha_limite')} className={inp} />
                </div>
                <div>
                  <label className={lbl}>Cierre cliente</label>
                  <input type="date" {...register('fecha_cierre_cliente')} className={inp} />
                </div>
              </div>

              {/* Timeline visual de fechas (solo modo edit) */}
              {mode === 'edit' && solicitud && (
                <div className="mt-4">
                  <div className="text-xs font-medium text-gray-500 mb-1">Timeline de hitos</div>
                  <FechasTimeline solicitud={solicitud} />
                </div>
              )}
            </div>

            {/* Financiero */}
            <div className={section}>
              <div className={sectionTitle}>Financiero</div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={lbl}>Oferta (EUR)</label>
                  <input
                    type="number"
                    step="0.01"
                    {...register('oferta', { valueAsNumber: true })}
                    className={inp}
                  />
                </div>
                <div>
                  <label className={lbl}>Coste (EUR)</label>
                  <input
                    type="number"
                    step="0.01"
                    {...register('coste', { valueAsNumber: true })}
                    className={inp}
                  />
                </div>
                <div>
                  <label className={lbl}>Cobertura (%) — calculado</label>
                  <input
                    type="number"
                    step="0.01"
                    {...register('cobertura_pct', { valueAsNumber: true })}
                    className={inp + ' bg-gray-50'}
                    readOnly
                  />
                </div>
                <div>
                  <label className={lbl}>Coeficiente — calculado</label>
                  <input
                    type="number"
                    step="0.001"
                    {...register('coeficiente', { valueAsNumber: true })}
                    className={inp + ' bg-gray-50'}
                    readOnly
                  />
                </div>
                <div>
                  <label className={lbl}>Margen (%) — calculado</label>
                  <input
                    type="number"
                    step="0.01"
                    {...register('margen_pct', { valueAsNumber: true })}
                    className={inp + ' bg-gray-50'}
                    readOnly
                  />
                </div>
              </div>

              {/* Mini donut financiero */}
              {mode === 'edit' && solicitud && (
                <FinancieroDonut oferta={solicitud.oferta} coste={solicitud.coste} />
              )}
            </div>

            {/* Actuaciones */}
            <div className={section}>
              <div className={sectionTitle}>Actuaciones</div>
              {actuaciones.length === 0 && (
                <p className="text-xs text-gray-400">Cargando catalogo…</p>
              )}
              <div className="grid grid-cols-3 gap-2">
                {actuaciones.map((a) => {
                  const checked = selectedActuaciones.includes(a.id)
                  return (
                    <label
                      key={a.id}
                      className={`flex items-center gap-2 rounded-md border px-2.5 py-1.5 text-xs cursor-pointer transition ${
                        checked
                          ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                          : 'border-gray-200 hover:bg-gray-50 text-gray-700'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggleActuacion(a.id)}
                        className="accent-indigo-600"
                      />
                      {a.nombre}
                    </label>
                  )
                })}
              </div>
            </div>

            {/* Contactos */}
            <div className={section}>
              <div className="flex items-center justify-between mb-3">
                <div className={sectionTitle + ' mb-0'}>Contactos</div>
                <select
                  onChange={(e) => {
                    if (e.target.value) {
                      addContacto(e.target.value as ContactoTipo)
                      e.target.value = ''
                    }
                  }}
                  className="text-xs border border-gray-200 rounded-md px-2 py-1"
                  defaultValue=""
                >
                  <option value="" disabled>
                    + anadir contacto
                  </option>
                  {CONTACTO_TIPOS.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </div>
              {contactos.length === 0 && (
                <p className="text-xs text-gray-400">Sin contactos. Anade uno con el desplegable.</p>
              )}
              <div className="space-y-2">
                {contactos.map((c, i) => (
                  <div key={i} className="border border-gray-200 rounded-md p-3 bg-gray-50">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-medium text-gray-600">
                        {CONTACTO_TIPOS.find((t) => t.value === c.tipo)?.label ?? c.tipo}
                      </span>
                      <button
                        type="button"
                        onClick={() => removeContacto(i)}
                        className="text-xs text-red-500 hover:underline"
                      >
                        eliminar
                      </button>
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      <input
                        placeholder="Nombre"
                        value={c.nombre ?? ''}
                        onChange={(e) => updateContactoField(i, 'nombre', e.target.value)}
                        className={inp + ' text-xs py-1.5'}
                      />
                      <input
                        placeholder="Telefono"
                        value={c.telefono ?? ''}
                        onChange={(e) => updateContactoField(i, 'telefono', e.target.value)}
                        className={inp + ' text-xs py-1.5'}
                      />
                      <input
                        placeholder="Email"
                        value={c.email ?? ''}
                        onChange={(e) => updateContactoField(i, 'email', e.target.value)}
                        className={inp + ' text-xs py-1.5'}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Descripcion y observaciones */}
            <div className={section}>
              <div className={sectionTitle}>Notas</div>
              <div className="space-y-3">
                <div>
                  <label className={lbl}>Descripcion del proyecto</label>
                  <textarea
                    {...register('descripcion')}
                    rows={3}
                    className={`${inp} resize-none`}
                    placeholder="Rehabilitacion integral de fachada y cubierta..."
                  />
                </div>
                <div>
                  <label className={lbl}>Observaciones internas</label>
                  <textarea
                    {...register('observaciones')}
                    rows={3}
                    className={`${inp} resize-none`}
                    placeholder="Notas internas, contexto, pendientes..."
                  />
                </div>
              </div>
            </div>
          </form>
        )}

        {/* Footer (solo en tab form) */}
        {activeTab === 'form' && (
          <div className="px-6 py-4 border-t bg-gray-50 flex items-center justify-between">
            <button onClick={onClose} className="text-sm text-gray-500 hover:text-gray-700">
              Cancelar
            </button>
            <button
              onClick={handleSubmit(onSubmit)}
              disabled={isPending}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition"
            >
              {mode === 'create' ? <Plus className="w-4 h-4" /> : <Save className="w-4 h-4" />}
              {isPending ? 'Guardando...' : mode === 'create' ? 'Crear' : 'Guardar'}
            </button>
          </div>
        )}
      </div>
    </>
  )
}
