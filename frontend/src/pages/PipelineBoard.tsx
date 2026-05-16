import { useState, useEffect, useCallback } from 'react'
import { crmApi, PipelineColumn, Solicitud } from '../api/crm'
import SolicitudSheet from '../components/SolicitudSheet'
import { Plus, RefreshCw, Zap } from 'lucide-react'

const PRIORIDAD_DOT: Record<string, string> = {
  alta: 'bg-red-500', media: 'bg-amber-400', baja: 'bg-green-500',
}

function agingColor(dias: number | null | undefined): string {
  if (!dias) return 'text-gray-400'
  if (dias < 30) return 'text-emerald-500'
  if (dias < 60) return 'text-amber-500'
  if (dias < 90) return 'text-orange-500'
  return 'text-red-500'
}

function agingBar(dias: number | null | undefined): number {
  if (!dias) return 0
  return Math.min((dias / 120) * 100, 100)
}

const COL_STYLE: Record<string, { bg: string; border: string; accent: string; glow: string }> = {
  'En Estudio': { bg: 'from-indigo-950/80 to-indigo-900/60', border: 'border-indigo-500/30', accent: 'bg-indigo-500', glow: 'shadow-indigo-500/20' },
  'Enviada':    { bg: 'from-amber-950/80 to-amber-900/60',   border: 'border-amber-500/30',  accent: 'bg-amber-400',  glow: 'shadow-amber-500/20' },
  'Adjudicada': { bg: 'from-emerald-950/80 to-emerald-900/60', border: 'border-emerald-500/30', accent: 'bg-emerald-400', glow: 'shadow-emerald-500/20' },
  'Rechazada':  { bg: 'from-red-950/80 to-red-900/60',       border: 'border-red-500/30',    accent: 'bg-red-500',    glow: 'shadow-red-500/20' },
  'Descartada': { bg: 'from-gray-900/80 to-gray-800/60',     border: 'border-gray-600/30',   accent: 'bg-gray-500',   glow: 'shadow-gray-500/10' },
}

const DEFAULT_STYLE = { bg: 'from-gray-900/80 to-gray-800/60', border: 'border-gray-600/30', accent: 'bg-gray-500', glow: 'shadow-gray-500/10' }

interface CardProps {
  s: Solicitud
  onClick: (s: Solicitud) => void
  onDragStart: (e: React.DragEvent, s: Solicitud) => void
}

function KanbanCard({ s, onClick, onDragStart }: CardProps) {
  const bar = agingBar(s.aging_dias)
  return (
    <div
      draggable
      onDragStart={e => onDragStart(e, s)}
      onClick={() => onClick(s)}
      className="group relative bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/25 rounded-xl p-3.5 cursor-pointer transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
    >
      {/* Cabecera */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <span className="text-[10px] font-mono text-white/40 tracking-wide">{s.codigo}</span>
        <div className="flex items-center gap-1.5">
          <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${PRIORIDAD_DOT[s.prioridad] ?? 'bg-gray-500'}`} />
          <span className="text-[10px] text-white/40 capitalize">{s.prioridad}</span>
        </div>
      </div>

      {/* Nombre */}
      <p className="text-sm font-medium text-white/90 leading-snug mb-2.5 line-clamp-2">{s.nombre_corto}</p>

      {/* Meta */}
      <div className="flex items-center justify-between text-[11px] text-white/40 mb-3">
        <span>{[s.poblacion, s.comercial].filter(Boolean).join(' · ')}</span>
        {s.oferta != null && (
          <span className="text-indigo-300 font-semibold">
            {(s.oferta / 1000).toFixed(0)}k
          </span>
        )}
      </div>

      {/* Aging bar */}
      {s.aging_dias != null && (
        <div className="space-y-1">
          <div className="flex justify-between text-[10px]">
            <span className="text-white/30">Aging</span>
            <span className={`font-medium ${agingColor(s.aging_dias)}`}>{s.aging_dias}d</span>
          </div>
          <div className="w-full h-0.5 rounded-full bg-white/10">
            <div
              className={`h-full rounded-full transition-all duration-700 ${
                bar < 25 ? 'bg-emerald-400' : bar < 50 ? 'bg-amber-400' : bar < 75 ? 'bg-orange-500' : 'bg-red-500'
              }`}
              style={{ width: `${bar}%` }}
            />
          </div>
        </div>
      )}
    </div>
  )
}

interface ColProps {
  col: PipelineColumn
  onCardClick: (s: Solicitud) => void
  onDragStart: (e: React.DragEvent, s: Solicitud) => void
  onDrop: (e: React.DragEvent, estado: string) => void
}

function KanbanColumn({ col, onCardClick, onDragStart, onDrop }: ColProps) {
  const [over, setOver] = useState(false)
  const style = COL_STYLE[col.estado] ?? DEFAULT_STYLE

  return (
    <div
      onDragOver={e => { e.preventDefault(); setOver(true) }}
      onDragLeave={() => setOver(false)}
      onDrop={e => { setOver(false); onDrop(e, col.estado) }}
      className={`flex flex-col min-w-[280px] max-w-[320px] w-full rounded-2xl border ${
        style.border
      } bg-gradient-to-b ${style.bg} backdrop-blur-sm shadow-xl ${style.glow} transition-all duration-200 ${
        over ? 'ring-2 ring-white/30 scale-[1.01]' : ''
      }`}
    >
      {/* Column header */}
      <div className="px-4 pt-4 pb-3 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className={`w-2.5 h-2.5 rounded-full ${style.accent} shadow-lg`} />
          <span className="text-sm font-semibold text-white/90 tracking-wide">{col.label}</span>
        </div>
        <div className="flex items-center gap-2">
          {col.total_oferta > 0 && (
            <span className="text-xs text-white/40 font-mono">{(col.total_oferta / 1000).toFixed(0)}k</span>
          )}
          <span className={`text-xs font-bold px-2 py-0.5 rounded-full bg-white/10 text-white/70`}>{col.count}</span>
        </div>
      </div>

      {/* Cards */}
      <div className="flex-1 overflow-y-auto px-3 pb-3 space-y-2 scrollbar-thin scrollbar-track-transparent scrollbar-thumb-white/10">
        {col.items.length === 0 && (
          <div className={`border-2 border-dashed border-white/10 rounded-xl h-20 flex items-center justify-center text-white/20 text-xs transition-all ${
            over ? 'border-white/30 bg-white/5' : ''
          }`}>
            Arrastra aquí
          </div>
        )}
        {col.items.map(s => (
          <KanbanCard key={s.id} s={s} onClick={onCardClick} onDragStart={onDragStart} />
        ))}
      </div>
    </div>
  )
}

export default function PipelineBoard() {
  const [columns, setColumns] = useState<PipelineColumn[]>([])
  const [loading, setLoading] = useState(true)
  const [dragging, setDragging] = useState<Solicitud | null>(null)
  const [sheet, setSheet] = useState<{ open: boolean; mode: 'create' | 'edit'; solicitud: Solicitud | null }>({
    open: false, mode: 'create', solicitud: null,
  })

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await crmApi.getPipeline()
      setColumns(data)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleDragStart = (e: React.DragEvent, s: Solicitud) => {
    setDragging(s)
    e.dataTransfer.effectAllowed = 'move'
  }

  const handleDrop = async (e: React.DragEvent, nuevoEstado: string) => {
    e.preventDefault()
    if (!dragging || dragging.estado === nuevoEstado) { setDragging(null); return }
    // Optimistic update
    setColumns(prev => {
      let moved: Solicitud | undefined
      const next = prev.map(col => {
        const items = col.items.filter(s => {
          if (s.id === dragging.id) { moved = { ...s, estado: nuevoEstado, kanban_column: nuevoEstado }; return false }
          return true
        })
        return { ...col, items, count: items.length, total_oferta: items.reduce((a, s) => a + (s.oferta ?? 0), 0) }
      })
      return next.map(col => col.estado === nuevoEstado && moved
        ? { ...col, items: [moved, ...col.items], count: col.count + 1, total_oferta: col.total_oferta + (moved.oferta ?? 0) }
        : col
      )
    })
    setDragging(null)
    try {
      await crmApi.updateEstado(dragging.id, nuevoEstado)
    } catch { load() }
  }

  const totalOps = columns.reduce((a, c) => a + c.count, 0)
  const totalValor = columns.reduce((a, c) => a + c.total_oferta, 0)

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Top bar */}
      <div className="px-6 py-4 border-b border-white/5 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Zap className="w-5 h-5 text-indigo-400" /> Pipeline
          </h1>
          <p className="text-xs text-white/40 mt-0.5">{totalOps} solicitudes · {(totalValor / 1000).toFixed(0)}k EUR en cartera</p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={load} className="p-2 hover:bg-white/5 rounded-lg transition" title="Refrescar">
            <RefreshCw className={`w-4 h-4 text-white/50 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={() => setSheet({ open: true, mode: 'create', solicitud: null })}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-xl transition shadow-lg shadow-indigo-500/25"
          >
            <Plus className="w-4 h-4" /> Nueva solicitud
          </button>
        </div>
      </div>

      {/* Board */}
      <div className="p-6 flex gap-4 overflow-x-auto pb-10">
        {loading && columns.length === 0 ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="min-w-[280px] h-64 rounded-2xl bg-white/5 animate-pulse" />
          ))
        ) : (
          columns.map(col => (
            <KanbanColumn
              key={col.estado}
              col={col}
              onCardClick={s => setSheet({ open: true, mode: 'edit', solicitud: s })}
              onDragStart={handleDragStart}
              onDrop={handleDrop}
            />
          ))
        )}
      </div>

      {/* Sheet CRUD */}
      <SolicitudSheet
        open={sheet.open}
        mode={sheet.mode}
        solicitud={sheet.solicitud}
        onClose={() => { setSheet(p => ({ ...p, open: false })); load() }}
      />
    </div>
  )
}
