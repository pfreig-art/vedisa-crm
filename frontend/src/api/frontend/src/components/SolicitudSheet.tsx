import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { X, Trash2, Save, Plus } from 'lucide-react'
import { crmApi, Solicitud, SolicitudCreate } from '../api/crm'
import { useMutation, useQueryClient } from '@tanstack/react-query'

const ESTADOS = ['En Estudio', 'Enviada', 'Adjudicada', 'Rechazada', 'Descartada']
const PRIORIDADES = ['alta', 'media', 'baja']

const ESTADO_COLOR: Record<string, string> = {
  'En Estudio': '#6366f1', 'Enviada': '#f59e0b',
  'Adjudicada': '#10b981', 'Rechazada': '#ef4444', 'Descartada': '#6b7280',
}

interface Props {
  solicitud: Solicitud | null
  open: boolean
  onClose: () => void
  mode: 'create' | 'edit'
}

export default function SolicitudSheet({ solicitud, open, onClose, mode }: Props) {
  const qc = useQueryClient()
  const { register, handleSubmit, reset } = useForm<SolicitudCreate>()

  useEffect(() => {
    if (solicitud && mode === 'edit') {
      reset({
        nombre_corto: solicitud.nombre_corto, codigo: solicitud.codigo,
        poblacion: solicitud.poblacion ?? '', estado: solicitud.estado,
        prioridad: solicitud.prioridad, comercial: solicitud.comercial ?? '',
        tecnico_estudios: solicitud.tecnico_estudios ?? '',
        fecha_solicitud: solicitud.fecha_solicitud ?? '',
        fecha_limite: solicitud.fecha_limite ?? '',
        oferta: solicitud.oferta ?? undefined,
        observaciones: (solicitud as any).observaciones ?? '',
      })
    } else { reset({ estado: 'En Estudio', prioridad: 'media' }) }
  }, [solicitud, mode, reset, open])

  const inv = () => {
    qc.invalidateQueries({ queryKey: ['solicitudes'] })
    qc.invalidateQueries({ queryKey: ['pipeline'] })
    qc.invalidateQueries({ queryKey: ['dashboard'] })
  }

  const createMut = useMutation({ mutationFn: (d: SolicitudCreate) => crmApi.createSolicitud(d), onSuccess: () => { inv(); onClose() } })
  const updateMut = useMutation({ mutationFn: (d: SolicitudCreate) => crmApi.updateSolicitud(solicitud!.id, d), onSuccess: () => { inv(); onClose() } })
  const deleteMut = useMutation({ mutationFn: () => crmApi.deleteSolicitud(solicitud!.id), onSuccess: () => { inv(); onClose() } })

  const onSubmit = (data: SolicitudCreate) => {
    const p = { ...data, color_estado: ESTADO_COLOR[data.estado ?? 'En Estudio'] ?? '#6366f1', kanban_column: data.estado ?? 'En Estudio' }
    mode === 'create' ? createMut.mutate(p) : updateMut.mutate(p)
  }
  const isPending = createMut.isPending || updateMut.isPending
  const inp = 'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500'

  return (
    <>
      <div className={`fixed inset-0 bg-black/40 backdrop-blur-sm z-40 transition-opacity duration-300 ${open ? 'opacity-100' : 'opacity-0 pointer-events-none'}`} onClick={onClose} />
      <div className={`fixed top-0 right-0 h-full w-full max-w-xl bg-white shadow-2xl z-50 flex flex-col transition-transform duration-300 ease-out ${open ? 'translate-x-0' : 'translate-x-full'}`}>
        <div className="flex items-center justify-between px-6 py-4 border-b bg-gray-50">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">{mode === 'create' ? 'Nueva Solicitud' : 'Editar Solicitud'}</h2>
            {solicitud && <p className="text-xs text-gray-500 mt-0.5">{solicitud.codigo}</p>}
          </div>
          <div className="flex items-center gap-2">
            {mode === 'edit' && (
              <button type="button" onClick={() => { if (confirm('Eliminar esta solicitud?')) deleteMut.mutate() }} className="p-2 text-red-500 hover:bg-red-50 rounded-lg transition">
                <Trash2 className="w-4 h-4" />
              </button>
            )}
            <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg transition"><X className="w-5 h-5 text-gray-500" /></button>
          </div>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nombre / Proyecto *</label>
            <input {...register('nombre_corto', { required: true })} className={inp} placeholder="Nave industrial..." />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Código</label><input {...register('codigo')} className={inp} placeholder="SOL-2026-XXXX" /></div>
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Población</label><input {...register('poblacion')} className={inp} placeholder="Barcelona" /></div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Estado</label>
              <select {...register('estado')} className={inp}>{ESTADOS.map(e => <option key={e} value={e}>{e}</option>)}</select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Prioridad</label>
              <select {...register('prioridad')} className={inp}>{PRIORIDADES.map(p => <option key={p} value={p}>{p}</option>)}</select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Comercial</label><input {...register('comercial')} className={inp} /></div>
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Técnico estudios</label><input {...register('tecnico_estudios')} className={inp} /></div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Fecha solicitud</label><input type="date" {...register('fecha_solicitud')} className={inp} /></div>
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Fecha límite</label><input type="date" {...register('fecha_limite')} className={inp} /></div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Oferta (EUR)</label>
            <input type="number" step="0.01" {...register('oferta', { valueAsNumber: true })} className={inp} placeholder="125000" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Observaciones</label>
            <textarea {...register('observaciones')} rows={4} className={`${inp} resize-none`} placeholder="Notas internas..." />
          </div>
        </form>

        <div className="px-6 py-4 border-t bg-gray-50 flex items-center justify-between">
          <button onClick={onClose} className="text-sm text-gray-500 hover:text-gray-700">Cancelar</button>
          <button onClick={handleSubmit(onSubmit)} disabled={isPending}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition">
            {mode === 'create' ? <Plus className="w-4 h-4" /> : <Save className="w-4 h-4" />}
            {isPending ? 'Guardando...' : mode === 'create' ? 'Crear' : 'Guardar'}
          </button>
        </div>
      </div>
    </>
  )
}
