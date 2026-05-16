import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { X, Trash2, Save, Plus } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  crmApi,
  Solicitud,
  SolicitudCreate,
  ContactoTipo,
  ContactoInput,
} from '../api/crm'
import { useUsuarios, useActuaciones } from '../hooks/useCatalogs'

const ESTADOS = ['En Estudio', 'Enviada', 'Adjudicada', 'Rechazada', 'Descartada'] as const
const PRIORIDADES = ['alta', 'media', 'baja'] as const

const ESTADO_COLOR: Record<string, string> = {
  'En Estudio': '#6366f1',
  Enviada: '#f59e0b',
  Adjudicada: '#10b981',
  Rechazada: '#ef4444',
  Descartada: '#6b7280',
}

const TIPOS_VIA = [
  'Calle', 'Avenida', 'Paseo', 'Plaza', 'Carretera', 'Camino', 'Ronda', 'Pasaje', 'Otro',
]

const CONTACTO_TIPOS: { value: ContactoTipo; label: string }[] = [
  { value: 'administracion', label: 'Administración' },
  { value: 'tecnico_obra', label: 'Técnico de obra' },
  { value: 'ensena_obra', label: 'Enseña obra' },
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

export default function SolicitudSheet({ solicitud, open, onClose, mode }: Props) {
  const qc = useQueryClient()
  const { register, handleSubmit, reset } = useForm<FormData>({ defaultValues: emptyValues() })

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
  }

  // Helper: convierte cadenas vacias a null y normaliza tipos
  function toPayload(data: FormData): SolicitudCreate {
    const out: Record<string, unknown> = {}
    for (const [k, v] of Object.entries(data)) {
      if (v === '' || v === undefined) out[k] = null
      else out[k] = v
    }
    return out as unknown as SolicitudCreate
  }

  async function persistChildren(solicitudId: string) {
    // 1) actuaciones (set completo)
    await crmApi.setSolicitudActuaciones(solicitudId, selectedActuaciones)
    // 2) contactos: borrar los existentes y reinsertar (set completo simple)
    const existentes = await crmApi.listContactos(solicitudId)
    await Promise.all(existentes.map((c) => crmApi.deleteContacto(c.id)))
    for (const c of contactos) {
      // Solo insertar si tiene al menos nombre o telefono o email
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
        <div className="flex items-center justify-between px-6 py-4 border-b bg-gray-50">
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
                <label className={lbl}>Código</label>
                <input {...register('codigo')} className={inp} placeholder="auto si vacío" />
              </div>
              <div>
                <label className={lbl}>Población</label>
                <input {...register('poblacion')} className={inp} placeholder="Maó" />
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

          {/* Dirección */}
          <div className={section}>
            <div className={sectionTitle}>Dirección</div>
            <div className="grid grid-cols-6 gap-3">
              <div className="col-span-2">
                <label className={lbl}>Tipo vía</label>
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
                <label className={lbl}>Nombre vía</label>
                <input
                  {...register('estudio_direccion')}
                  className={inp}
                  placeholder="Ej. Mossèn Antoni Maria Alcover"
                />
              </div>
              <div className="col-span-1">
                <label className={lbl}>Número</label>
                <input {...register('numero')} className={inp} />
              </div>
              <div className="col-span-1">
                <label className={lbl}>CP</label>
                <input {...register('cp')} className={inp} placeholder="07700" />
              </div>
            </div>
          </div>

          {/* Asignación */}
          <div className={section}>
            <div className={sectionTitle}>Asignación</div>
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
                <label className={lbl}>Técnico de estudios</label>
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
                <label className={lbl}>Reunión</label>
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
                <label className={lbl}>Límite</label>
                <input type="date" {...register('fecha_limite')} className={inp} />
              </div>
              <div>
                <label className={lbl}>Cierre cliente</label>
                <input type="date" {...register('fecha_cierre_cliente')} className={inp} />
              </div>
            </div>
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
                <label className={lbl}>Cobertura (%)</label>
                <input
                  type="number"
                  step="0.01"
                  {...register('cobertura_pct', { valueAsNumber: true })}
                  className={inp}
                />
              </div>
              <div>
                <label className={lbl}>Coeficiente</label>
                <input
                  type="number"
                  step="0.001"
                  {...register('coeficiente', { valueAsNumber: true })}
                  className={inp}
                />
              </div>
              <div>
                <label className={lbl}>Margen (%)</label>
                <input
                  type="number"
                  step="0.01"
                  {...register('margen_pct', { valueAsNumber: true })}
                  className={inp}
                />
              </div>
            </div>
          </div>

          {/* Actuaciones */}
          <div className={section}>
            <div className={sectionTitle}>Actuaciones</div>
            {actuaciones.length === 0 && (
              <p className="text-xs text-gray-400">Cargando catálogo…</p>
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
                  + añadir contacto
                </option>
                {CONTACTO_TIPOS.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
            {contactos.length === 0 && (
              <p className="text-xs text-gray-400">Sin contactos. Añade uno con el desplegable.</p>
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
                      placeholder="Teléfono"
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

          {/* Descripción y observaciones */}
          <div className={section}>
            <div className={sectionTitle}>Notas</div>
            <div className="space-y-3">
              <div>
                <label className={lbl}>Descripción del proyecto</label>
                <textarea
                  {...register('descripcion')}
                  rows={3}
                  className={`${inp} resize-none`}
                  placeholder="Rehabilitación integral de fachada y cubierta..."
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
      </div>
    </>
  )
}
