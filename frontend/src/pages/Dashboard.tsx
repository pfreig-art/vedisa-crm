import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  FunnelChart,
  Funnel,
  LabelList,
} from 'recharts'
import { crmApi, DashboardStats, DashboardExtended, Alertas } from '../api/crm'
import { DollarSign, BarChart2, Bot, Target, Clock, Download, AlertTriangle } from 'lucide-react'
import { useAIStore } from '../store/aiStore'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const ESTADO_META: Record<string, { color: string; label: string }> = {
  'En Estudio': { color: '#6366f1', label: 'En Estudio' },
  Enviada: { color: '#f59e0b', label: 'Enviada' },
  Adjudicada: { color: '#10b981', label: 'Adjudicada' },
  Rechazada: { color: '#ef4444', label: 'Rechazada' },
  Descartada: { color: '#6b7280', label: 'Descartada' },
}

const DONUT_COLORS = ['#6366f1', '#f59e0b', '#10b981', '#ef4444', '#06b6d4', '#a855f7', '#f97316', '#84cc16']

// ---------------------------------------------------------------------------
// Counter-up animado
// ---------------------------------------------------------------------------
function useCounterUp(target: number, duration = 1200): number {
  const [value, setValue] = useState(0)
  const rafRef = useRef<number | null>(null)
  const startRef = useRef<number | null>(null)

  useEffect(() => {
    startRef.current = null
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current)
    }
    const animate = (ts: number) => {
      if (startRef.current === null) startRef.current = ts
      const elapsed = ts - startRef.current
      const progress = Math.min(elapsed / duration, 1)
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3)
      setValue(Math.round(eased * target))
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(animate)
      }
    }
    rafRef.current = requestAnimationFrame(animate)
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
    }
  }, [target, duration])

  return value
}

// ---------------------------------------------------------------------------
// KPI Card con counter-up
// ---------------------------------------------------------------------------
function KpiCard({
  title,
  target,
  format,
  icon: Icon,
  color,
}: {
  title: string
  target: number
  format: (v: number) => string
  icon: React.ElementType
  color: string
}) {
  const value = useCounterUp(target)
  return (
    <div className="rounded-2xl border border-white/10 bg-slate-900/80 p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-xs uppercase tracking-wide text-slate-400">{title}</div>
          <div className="mt-2 text-2xl font-semibold text-white">{format(value)}</div>
        </div>
        <div className={`rounded-xl p-2 ${color}`}>
          <Icon className="h-5 w-5 text-white" />
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Heatmap mensual
// ---------------------------------------------------------------------------
function HeatmapMensual({ data }: { data: { mes: string; count: number }[] }) {
  const max = Math.max(...data.map((d) => d.count), 1)
  return (
    <div className="rounded-2xl border border-white/10 bg-slate-900/80 p-5 shadow-sm">
      <h2 className="mb-1 text-lg font-semibold text-white">Actividad mensual</h2>
      <p className="mb-4 text-sm text-slate-400">Solicitudes recibidas por mes (ultimos 12 meses)</p>
      <div className="grid grid-cols-12 gap-1.5">
        {data.map((item) => {
          const intensity = item.count === 0 ? 0 : Math.ceil((item.count / max) * 4)
          const bgClass = [
            'bg-slate-800',
            'bg-indigo-900',
            'bg-indigo-700',
            'bg-indigo-500',
            'bg-indigo-400',
          ][intensity] ?? 'bg-indigo-400'
          return (
            <div key={item.mes} className="flex flex-col items-center gap-1" title={`${item.mes}: ${item.count}`}>
              <div className={`h-8 w-full rounded-md ${bgClass} transition-colors`} />
              <span className="truncate text-[9px] text-slate-500">{item.mes.split(' ')[0]}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Dashboard principal
// ---------------------------------------------------------------------------
export default function Dashboard() {
  const navigate = useNavigate()
  const { openDrawer } = useAIStore()

  const { data: stats, isLoading } = useQuery<DashboardStats>({
    queryKey: ['dashboard'],
    queryFn: crmApi.getDashboard,
  })

  const { data: extended } = useQuery<DashboardExtended>({
    queryKey: ['dashboard-extended'],
    queryFn: crmApi.getDashboardExtended,
  })

  const { data: alertas } = useQuery<Alertas>({
    queryKey: ['alertas'],
    queryFn: crmApi.getAlertas,
  })

  const safeStats = {
    total_solicitudes: Number(stats?.total_solicitudes ?? 0),
    en_estudio: Number(stats?.en_estudio ?? 0),
    ofertadas: Number(stats?.ofertadas ?? 0),
    ganadas: Number(stats?.ganadas ?? 0),
    tasa_conversion: Number(stats?.tasa_conversion ?? 0),
    oferta_total: Number(stats?.oferta_total ?? 0),
    aging_promedio: Number(stats?.aging_promedio ?? 0),
    tiempo_medio_cierre: Number(stats?.tiempo_medio_cierre ?? 0),
    forecast_mensual: Array.isArray(stats?.forecast_mensual) ? stats.forecast_mensual : [],
  }

  const exportUrl = `${API_URL}/crm/solicitudes/export?formato=csv`

  // Contexto enriquecido para el drawer IA: incluye KPIs, embudo,
  // forecast, alertas y mix de actuaciones / top comerciales / heatmap
  // (todo lo que la pagina ya tiene cargado en memoria).
  const aiContext = {
    kpis: safeStats,
    funnel: [
      { estado: 'En Estudio', count: safeStats.en_estudio },
      { estado: 'Enviada', count: safeStats.ofertadas },
      { estado: 'Adjudicada', count: safeStats.ganadas },
    ],
    forecast_mensual: safeStats.forecast_mensual,
    alertas: alertas
      ? {
          total_vencidas: alertas.total_vencidas,
          total_proximas: alertas.total_proximas,
          vencidas: alertas.vencidas?.slice(0, 10) ?? [],
          proximas: alertas.proximas?.slice(0, 10) ?? [],
        }
      : null,
    mix_actuaciones: extended?.mix_actuaciones ?? [],
    top_comerciales: extended?.top_comerciales ?? [],
    heatmap_estados_dias: extended?.heatmap ?? [],
  }
  const aiReady = !isLoading && !!stats

  // Datos del embudo para recharts FunnelChart
  const funnelData = [
    { name: 'En Estudio', value: safeStats.en_estudio, fill: ESTADO_META['En Estudio'].color },
    { name: 'Enviada', value: safeStats.ofertadas, fill: ESTADO_META['Enviada'].color },
    { name: 'Adjudicada', value: safeStats.ganadas, fill: ESTADO_META['Adjudicada'].color },
  ]

  const donutActuaciones = (extended?.mix_actuaciones ?? []).map((a, i) => ({
    name: a.nombre,
    value: a.count,
    fill: DONUT_COLORS[i % DONUT_COLORS.length],
  }))

  const heatmap = extended?.heatmap ?? []
  const topComerciales = extended?.top_comerciales ?? []

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6 text-sm text-slate-400">
          Cargando dashboard…
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-full bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-7xl px-6 py-6">

        {/* Cabecera */}
        <div className="mb-6 flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
            <p className="mt-1 text-sm text-slate-400">Resumen del pipeline comercial</p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              disabled={!aiReady}
              aria-busy={!aiReady}
              onClick={() =>
                openDrawer({
                  mode: 'dashboard',
                  title: 'Analisis IA del dashboard',
                  context: aiContext,
                })
              }
              className="inline-flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Bot className="h-4 w-4" />
              {aiReady ? 'Analizar con IA' : 'Cargando datos…'}
            </button>
            <a
              href={exportUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-white transition hover:bg-white/10"
            >
              <Download className="h-4 w-4" />
              Exportar CSV
            </a>
          </div>
        </div>

        {/* Banner alertas */}
        {alertas && (alertas.total_vencidas > 0 || alertas.total_proximas > 0) && (
          <div className="mb-6 flex items-center justify-between rounded-xl border border-orange-500/30 bg-orange-500/10 px-4 py-3">
            <div className="flex items-center gap-2 text-sm text-orange-300">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>
                Tienes{' '}
                {alertas.total_vencidas > 0 && (
                  <strong className="text-orange-200">{alertas.total_vencidas} solicitud{alertas.total_vencidas !== 1 ? 'es' : ''} vencida{alertas.total_vencidas !== 1 ? 's' : ''}</strong>
                )}
                {alertas.total_vencidas > 0 && alertas.total_proximas > 0 && ' y '}
                {alertas.total_proximas > 0 && (
                  <strong className="text-orange-200">{alertas.total_proximas} proxima{alertas.total_proximas !== 1 ? 's' : ''} a vencer</strong>
                )}
              </span>
            </div>
            <button
              type="button"
              onClick={() => navigate('/contacts')}
              className="text-xs text-orange-400 underline hover:text-orange-300"
            >
              Ver solicitudes
            </button>
          </div>
        )}

        {/* Fila de KPIs animados */}
        <div className="mb-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <KpiCard
            title="Cartera total (EUR)"
            target={Math.round(safeStats.oferta_total)}
            format={(v) => `${(v / 1000).toFixed(1)}k`}
            icon={DollarSign}
            color="bg-teal-500"
          />
          <KpiCard
            title="Conversion"
            target={Math.round(safeStats.tasa_conversion * 1000)}
            format={(v) => `${(v / 10).toFixed(1)}%`}
            icon={Target}
            color="bg-purple-500"
          />
          <KpiCard
            title="Ticket medio (EUR)"
            target={safeStats.total_solicitudes > 0 ? Math.round(safeStats.oferta_total / safeStats.total_solicitudes) : 0}
            format={(v) => `${(v / 1000).toFixed(1)}k`}
            icon={BarChart2}
            color="bg-blue-500"
          />
          <KpiCard
            title="Aging promedio"
            target={Math.round(safeStats.aging_promedio)}
            format={(v) => `${v}d`}
            icon={Clock}
            color="bg-orange-500"
          />
        </div>

        {/* Fila 2: embudo + donut actuaciones */}
        <div className="mb-6 grid gap-6 xl:grid-cols-2">

          {/* Embudo de pipeline */}
          <div className="rounded-2xl border border-white/10 bg-slate-900/80 p-5 shadow-sm">
            <h2 className="mb-1 text-lg font-semibold text-white">Embudo de pipeline</h2>
            <p className="mb-4 text-sm text-slate-400">Solicitudes por estado (activos)</p>
            <ResponsiveContainer width="100%" height={200}>
              <FunnelChart>
                <Tooltip
                  contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                  labelStyle={{ color: '#94a3b8' }}
                  itemStyle={{ color: '#e2e8f0' }}
                />
                <Funnel dataKey="value" data={funnelData} isAnimationActive>
                  <LabelList position="right" fill="#94a3b8" stroke="none" dataKey="name" style={{ fontSize: 12 }} />
                  <LabelList position="center" fill="#ffffff" stroke="none" dataKey="value" style={{ fontSize: 13, fontWeight: 600 }} />
                </Funnel>
              </FunnelChart>
            </ResponsiveContainer>
          </div>

          {/* Donut mix actuaciones */}
          <div className="rounded-2xl border border-white/10 bg-slate-900/80 p-5 shadow-sm">
            <h2 className="mb-1 text-lg font-semibold text-white">Mix de actuaciones</h2>
            <p className="mb-4 text-sm text-slate-400">Tipos mas frecuentes en el portfolio</p>
            {donutActuaciones.length === 0 ? (
              <div className="flex h-[200px] items-center justify-center text-center text-sm text-slate-500 px-4">
                Aun no hay actuaciones asignadas a solicitudes
              </div>
            ) : (
              <div className="flex items-center gap-4">
                <ResponsiveContainer width={160} height={160}>
                  <PieChart>
                    <Pie
                      data={donutActuaciones}
                      cx="50%"
                      cy="50%"
                      innerRadius={45}
                      outerRadius={70}
                      dataKey="value"
                      strokeWidth={0}
                    >
                      {donutActuaciones.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.fill} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                      itemStyle={{ color: '#e2e8f0' }}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="flex flex-col gap-1.5 overflow-hidden">
                  {donutActuaciones.slice(0, 6).map((item) => (
                    <div key={item.name} className="flex items-center gap-2 text-xs">
                      <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: item.fill }} />
                      <span className="truncate text-slate-300">{item.name}</span>
                      <span className="ml-auto font-medium text-slate-400">{item.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Fila 3: Top comerciales */}
        <div className="mb-6 rounded-2xl border border-white/10 bg-slate-900/80 p-5 shadow-sm">
          <h2 className="mb-1 text-lg font-semibold text-white">Top comerciales</h2>
          <p className="mb-4 text-sm text-slate-400">Por oferta adjudicada</p>
          {topComerciales.length === 0 ? (
            <div className="text-sm text-slate-500">Sin datos adjudicados aun</div>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={topComerciales} layout="vertical" margin={{ left: 0, right: 20 }}>
                <XAxis type="number" tick={{ fill: '#64748b', fontSize: 11 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                <YAxis
                  type="category"
                  dataKey="nombre"
                  tick={{ fill: '#94a3b8', fontSize: 12 }}
                  width={110}
                />
                <Tooltip
                  contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                  itemStyle={{ color: '#e2e8f0' }}
                  formatter={(v) => [`${Number(v ?? 0).toLocaleString('es-ES')} EUR`, 'Oferta']}
                />
                <Bar dataKey="oferta_total" fill="#6366f1" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Heatmap mensual */}
        {heatmap.length > 0 && <HeatmapMensual data={heatmap} />}

        {/* Forecast mensual */}
        {safeStats.forecast_mensual.length > 0 && (
          <div className="mt-6 rounded-2xl border border-white/10 bg-slate-900/80 p-5 shadow-sm">
            <h2 className="mb-1 text-lg font-semibold text-white">Forecast mensual</h2>
            <p className="mb-4 text-sm text-slate-400">Oferta agregada y operaciones adjudicadas</p>
            <div className="space-y-3">
              {safeStats.forecast_mensual.map((m) => {
                const maxOferta = Math.max(...safeStats.forecast_mensual.map((x) => x.oferta ?? 0), 1)
                return (
                  <div key={m.mes} className="space-y-1.5">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium text-slate-200">{m.mes}</span>
                      <span className="text-slate-400">
                        {m.ganadas} ops / {((m.oferta ?? 0) / 1000).toFixed(1)}k
                      </span>
                    </div>
                    <div className="h-2 rounded-full bg-white/10">
                      <div
                        className="h-2 rounded-full bg-cyan-500"
                        style={{ width: `${((m.oferta ?? 0) / maxOferta) * 100}%` }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Lectura rapida */}
        <div className="mt-6 rounded-2xl border border-white/10 bg-slate-900/80 p-5 shadow-sm">
          <div className="mb-3">
            <h2 className="text-lg font-semibold text-white">Lectura rapida</h2>
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            <div className="rounded-xl border border-white/10 bg-white/5 p-4">
              <div className="text-xs uppercase tracking-wide text-slate-500">Conversion</div>
              <div className="mt-2 text-lg font-semibold text-white">
                {(safeStats.tasa_conversion * 100).toFixed(1)}%
              </div>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/5 p-4">
              <div className="text-xs uppercase tracking-wide text-slate-500">Aging medio</div>
              <div className="mt-2 text-lg font-semibold text-white">{Math.round(safeStats.aging_promedio)} dias</div>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/5 p-4">
              <div className="text-xs uppercase tracking-wide text-slate-500">Tiempo medio cierre</div>
              <div className="mt-2 text-lg font-semibold text-white">
                {Math.round(safeStats.tiempo_medio_cierre)} dias
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}
