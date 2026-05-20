import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { crmApi, PipelineColumn, Solicitud, Usuario } from '../api/crm'
import { Clock3, Euro, GripVertical, RefreshCw } from 'lucide-react'
import SolicitudSheet from '../components/SolicitudSheet'
import { useUsuariosMap } from '../hooks/useCatalogs'

const PRIORIDAD_DOT: Record<string, string> = {
  alta: 'bg-red-500',
  media: 'bg-amber-500',
  baja: 'bg-emerald-500',
}

const COL_STYLE: Record<string, string> = {
  'Pte. Aprobación': 'from-slate-700 to-slate-800 border-slate-600/60',
  Aprobado: 'from-emerald-700 to-emerald-800 border-emerald-600/50',
  Rechazado: 'from-rose-700 to-rose-800 border-rose-600/50',
  'Pte. Aviso': 'from-violet-700 to-violet-800 border-violet-600/50',
  'Pte. Visita': 'from-amber-700 to-amber-800 border-amber-600/50',
  'En Estudio': 'from-indigo-700 to-indigo-800 border-indigo-600/50',
  Enviada: 'from-cyan-700 to-cyan-800 border-cyan-600/50',
  'Pte. Cierre': 'from-sky-700 to-sky-800 border-sky-600/50',
  Adjudicada: 'from-emerald-800 to-teal-800 border-emerald-500/50',
  Descartada: 'from-red-800 to-rose-900 border-red-500/50',
  Cancelada: 'from-zinc-700 to-zinc-800 border-zinc-500/50',
}

const DEFAULT_STYLE = 'from-slate-700 to-slate-800 border-slate-600/50'

function agingColor(days?: number | null) {
  if (days == null) return 'text-slate-400'
  if (days <= 7) return 'text-emerald-400'
  if (days <= 21) return 'text-amber-400'
  return 'text-rose-400'
}

function agingBar(days?: number | null) {
  if (days == null) return 'w-0'
  if (days <= 7) return 'w-1/4'
  if (days <= 21) return 'w-2/4'
  if (days <= 45) return 'w-3/4'
  return 'w-full'
}

function formatMoney(value?: number | null) {
  const amount = value ?? 0
  return new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 0,
  }).format(amount)
}

function priorityDotClass(priority?: string | null) {
  return PRIORIDAD_DOT[priority ?? ''] ?? 'bg-gray-500'
}

function resolveComercial(
  comercialId: string | null | undefined,
  usuariosMap: Map<string, Usuario>,
): string {
  if (!comercialId) return '-'
  const u = usuariosMap.get(comercialId)
  return u?.nombre || comercialId
}

function SolicitudCard({
  s,
  usuariosMap,
  onDragStart,
  onSelect,
}: {
  s: Solicitud
  usuariosMap: Map<string, Usuario>
  onDragStart: (solicitud: Solicitud) => void
  onSelect: (solicitud: Solicitud) => void
}) {
  const bar = agingBar(s.aging_dias)

  return (
    <div
      draggable
      onDragStart={() => onDragStart(s)}
      onClick={() => onSelect(s)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onSelect(s)
        }
      }}
      className="group cursor-pointer rounded-xl border border-white/10 bg-slate-900/80 p-3 shadow-sm transition hover:border-white/20 hover:bg-slate-900"
    >
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="mb-1 flex items-center gap-2">
            <GripVertical className="h-3.5 w-3.5 flex-shrink-0 text-white/25" />
            <span className="truncate text-xs font-mono text-cyan-300">{s.codigo}</span>
            <span className={`h-1.5 w-1.5 rounded-full flex-shrink-0 ${priorityDotClass(s.prioridad)}`} />
          </div>
          <div className="line-clamp-2 text-sm font-medium text-white">{s.nombre_corto}</div>
          {s.poblacion && <div className="mt-1 text-xs text-white/45">{s.poblacion}</div>}
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="text-white/40">Oferta</span>
          <span className="font-medium text-white/85">{formatMoney(s.oferta)}</span>
        </div>

        {s.aging_dias != null && (
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="inline-flex items-center gap-1 text-white/40">
                <Clock3 className="h-3.5 w-3.5" />
                Aging
              </span>
              <span className={`font-medium ${agingColor(s.aging_dias)}`}>{s.aging_dias}d</span>
            </div>
            <div className="h-1.5 rounded-full bg-white/10">
              <div className={`h-1.5 rounded-full bg-current ${agingColor(s.aging_dias)} ${bar}`} />
            </div>
          </div>
        )}

        <div className="flex items-center justify-between text-xs">
          <span className="text-white/40">Comercial</span>
          <span className="truncate pl-3 text-white/70">
            {resolveComercial(s.comercial, usuariosMap)}
          </span>
        </div>
      </div>
    </div>
  )
}

function Column({
  col,
  usuariosMap,
  onDropSolicitud,
  onDragStart,
  onSelect,
}: {
  col: PipelineColumn
  usuariosMap: Map<string, Usuario>
  onDropSolicitud: (estado: string) => void
  onDragStart: (solicitud: Solicitud) => void
  onSelect: (solicitud: Solicitud) => void
}) {
  const [over, setOver] = useState(false)
  const style = COL_STYLE[col.estado] ?? DEFAULT_STYLE

  return (
    <div
      className={`min-w-[280px] max-w-[280px] rounded-2xl border bg-gradient-to-b ${style} ${over ? 'ring-2 ring-cyan-400/70' : ''}`}
      onDragOver={(e) => {
        e.preventDefault()
        setOver(true)
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault()
        setOver(false)
        onDropSolicitud(col.estado)
      }}
    >
      <div className="sticky top-0 z-10 rounded-t-2xl bg-black/10 px-4 py-3 backdrop-blur">
        <div className="flex items-center justify-between gap-2">
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold tracking-wide text-white/90">{col.label}</div>
            <div className="mt-1 flex items-center gap-2 text-xs text-white/55">
              <span>{col.count} ops</span>
              {col.total_oferta > 0 && (
                <>
                  <span>•</span>
                  <span className="inline-flex items-center gap-1">
                    <Euro className="h-3 w-3" />
                    {(col.total_oferta / 1000).toFixed(0)}k
                  </span>
                </>
              )}
            </div>
          </div>
          <div className="rounded-full bg-white/10 px-2 py-1 text-xs font-semibold text-white/85">
            {col.count}
          </div>
        </div>
      </div>

      <div className="flex max-h-[calc(100vh-240px)] flex-col gap-3 overflow-y-auto p-3">
        {col.items.map((s) => (
          <SolicitudCard
            key={s.id}
            s={s}
            usuariosMap={usuariosMap}
            onDragStart={onDragStart}
            onSelect={onSelect}
          />
        ))}

        {col.items.length === 0 && (
          <div className="rounded-xl border border-dashed border-white/15 bg-black/10 px-3 py-6 text-center text-xs text-white/40">
            Suelta aquí una solicitud
          </div>
        )}
      </div>
    </div>
  )
}

export default function PipelineBoard() {
  const queryClient = useQueryClient()
  const [dragging, setDragging] = useState<Solicitud | null>(null)
  const [selected, setSelected] = useState<Solicitud | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)
  const { map: usuariosMap } = useUsuariosMap()

  const handleSelect = (s: Solicitud) => {
    setSelected(s)
    setSheetOpen(true)
  }

  const handleSheetClose = () => {
    setSheetOpen(false)
    void queryClient.invalidateQueries({ queryKey: ['pipeline'] })
    void queryClient.invalidateQueries({ queryKey: ['solicitudes'] })
  }

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['pipeline'],
    queryFn: crmApi.getPipeline,
  })

  const columns = useMemo<PipelineColumn[]>(() => {
    return (data ?? []).map((col) => {
      const items = col.items ?? []
      const total_oferta =
        col.total_oferta ??
        items.reduce((acc, item) => acc + (item.oferta ?? 0), 0)

      return {
        ...col,
        label: col.label ?? col.estado,
        count: col.count ?? items.length,
        total_oferta,
        items,
      }
    })
  }, [data])

  const moveMutation = useMutation({
    mutationFn: async ({ id, nuevoEstado }: { id: string; nuevoEstado: string }) => {
      await crmApi.updateEstado(id, nuevoEstado)
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['pipeline'] })
      await queryClient.invalidateQueries({ queryKey: ['solicitudes'] })
      setDragging(null)
    },
  })

  function handleDrop(nuevoEstado: string) {
    if (!dragging) return
    if (dragging.estado === nuevoEstado || dragging.kanban_column === nuevoEstado) {
      setDragging(null)
      return
    }
    moveMutation.mutate({ id: dragging.id, nuevoEstado })
  }

  const totalOps = columns.reduce((a, c) => a + c.count, 0)
  const totalValor = columns.reduce((a, c) => a + (c.total_oferta ?? 0), 0)

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6 text-sm text-slate-400">
          Cargando pipeline…
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col bg-slate-950 text-slate-100">
      <div className="border-b border-white/10 px-6 py-4">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Pipeline</h1>
            <p className="mt-1 text-sm text-slate-400">Vista kanban del flujo comercial.</p>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-sm">
            <div className="rounded-xl border border-white/10 bg-white/5 px-3 py-2">
              <span className="text-slate-400">Operaciones:</span>{' '}
              <span className="font-semibold text-white">{totalOps}</span>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/5 px-3 py-2">
              <span className="text-slate-400">Valor total:</span>{' '}
              <span className="font-semibold text-white">{formatMoney(totalValor)}</span>
            </div>
            <button
              type="button"
              onClick={() => void refetch()}
              className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-white transition hover:bg-white/10"
            >
              <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
              Actualizar
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-x-auto">
        <div className="flex min-h-full gap-4 p-6">
          {columns.map((col) => (
            <Column
              key={col.estado}
              col={col}
              onDropSolicitud={handleDrop}
              onDragStart={(s) => setDragging(s)}
              onSelect={handleSelect}
              usuariosMap={usuariosMap}
            />
          ))}
        </div>
      </div>

      <SolicitudSheet
        solicitud={selected}
        open={sheetOpen}
        onClose={handleSheetClose}
        mode="edit"
      />
    </div>
  )
}