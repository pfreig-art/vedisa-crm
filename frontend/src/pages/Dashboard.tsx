import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { crmApi, DashboardStats } from '../api/crm'
import { TrendingUp, DollarSign, BarChart2, Bot, Target, Clock, Download } from 'lucide-react'
import { useAIStore } from '../store/aiStore'

function StatCard({
  title,
  value,
  icon: Icon,
  color,
}: {
  title: string
  value: string | number
  icon: React.ElementType
  color: string
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-slate-900/80 p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-xs uppercase tracking-wide text-slate-400">{title}</div>
          <div className="mt-2 text-2xl font-semibold text-white">{value}</div>
        </div>
        <div className={`rounded-xl p-2 ${color}`}>
          <Icon className="h-5 w-5 text-white" />
        </div>
      </div>
    </div>
  )
}

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export default function Dashboard() {
  const { openDrawer } = useAIStore()

  const { data: stats, isLoading, isFetching } = useQuery<DashboardStats>({
    queryKey: ['dashboard'],
    queryFn: crmApi.getDashboard,
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
    pipeline_breakdown: Array.isArray(stats?.pipeline_breakdown) ? stats.pipeline_breakdown : [],
  }

  const forecast = safeStats.forecast_mensual.map((m) => ({
    mes: String(m.mes),
    oferta: Number(m.oferta ?? 0),
    ganadas: Number(m.ganadas ?? 0),
  }))

  const pipelineBreakdown: Array<{ label: string; value: number }> =
    safeStats.pipeline_breakdown.length > 0
      ? safeStats.pipeline_breakdown.map((item) => ({
          label: String(item.label),
          value: Number(item.value ?? 0),
        }))
      : [
          { label: 'En estudio', value: safeStats.en_estudio },
          { label: 'Ofertadas', value: safeStats.ofertadas },
          { label: 'Ganadas', value: safeStats.ganadas },
        ]

  const maxForecast = Math.max(...forecast.map((m) => m.oferta), 1)

  const exportUrl = useMemo(() => `${API_URL}/crm/solicitudes/export?formato=csv`, [])

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
        <div className="mb-6 flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
            <p className="mt-1 text-sm text-slate-400">Resumen del pipeline comercial</p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => openDrawer({mode: 'dashboard',
    title: 'Análisis IA del dashboard',
    context: safeStats,})}
              className="inline-flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-violet-500"
            >
              <Bot className="h-4 w-4" />
              Analizar con IA
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

        <div className="mb-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard title="Solicitudes" value={safeStats.total_solicitudes} icon={BarChart2} color="bg-slate-700" />
          <StatCard title="En Estudio" value={safeStats.en_estudio} icon={TrendingUp} color="bg-blue-500" />
          <StatCard title="Ofertadas" value={safeStats.ofertadas} icon={Target} color="bg-amber-500" />
          <StatCard title="Ganadas" value={safeStats.ganadas} icon={TrendingUp} color="bg-emerald-500" />
        </div>

        <div className="mb-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard
            title="Tasa Conversion"
            value={`${(safeStats.tasa_conversion * 100).toFixed(1)}%`}
            icon={Target}
            color="bg-purple-500"
          />
          <StatCard
            title="Oferta Total"
            value={`${(safeStats.oferta_total / 1000).toFixed(1)}k`}
            icon={DollarSign}
            color="bg-teal-500"
          />
          <StatCard
            title="Aging Promedio"
            value={`${Math.round(safeStats.aging_promedio)}d`}
            icon={Clock}
            color="bg-orange-500"
          />
          <StatCard
            title="Tiempo Medio Cierre"
            value={`${Math.round(safeStats.tiempo_medio_cierre)}d`}
            icon={Clock}
            color="bg-rose-500"
          />
        </div>

        <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-2xl border border-white/10 bg-slate-900/80 p-5 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-white">Forecast mensual</h2>
                <p className="text-sm text-slate-400">Oferta agregada y operaciones ganadas</p>
              </div>
              {isFetching && <span className="text-xs text-slate-500">Actualizando…</span>}
            </div>

            <div className="space-y-3">
              {forecast.length === 0 && (
                <div className="rounded-xl border border-dashed border-white/10 px-4 py-8 text-center text-sm text-slate-500">
                  No hay datos de forecast.
                </div>
              )}

              {forecast.map((m) => (
                <div key={m.mes} className="space-y-1.5">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium text-slate-200">{m.mes}</span>
                    <span className="text-slate-400">
                      {m.ganadas} ops / {(m.oferta / 1000).toFixed(1)}k
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-white/10">
                    <div
                      className="h-2 rounded-full bg-cyan-500"
                      style={{ width: `${(m.oferta / maxForecast) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-slate-900/80 p-5 shadow-sm">
            <div className="mb-4">
              <h2 className="text-lg font-semibold text-white">Embudo actual</h2>
              <p className="text-sm text-slate-400">Distribución rápida del pipeline</p>
            </div>

            <div className="space-y-4">
              {pipelineBreakdown.map((item) => (
                <div key={item.label} className="space-y-1.5">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-slate-300">{item.label}</span>
                    <span className="w-8 text-right text-sm font-medium">{Number(item.value)}</span>
                  </div>
                  <div className="h-2 rounded-full bg-white/10">
                    <div
                      className="h-2 rounded-full bg-violet-500"
                      style={{
                        width: `${
                          safeStats.total_solicitudes
                            ? (Number(item.value) / Number(safeStats.total_solicitudes)) * 100
                            : 0
                        }%`,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-6 rounded-xl border border-white/10 bg-black/20 p-4 text-sm text-slate-400">
              <div className="mb-1 font-medium text-slate-200">Lectura rápida</div>
              <p>
                {safeStats.total_solicitudes} solicitudes, {safeStats.ganadas} ganadas y una conversión actual del{' '}
                {(safeStats.tasa_conversion * 100).toFixed(1)}%.
              </p>
            </div>
          </div>
        </div>

        <div className="mt-6 rounded-2xl border border-white/10 bg-slate-900/80 p-5 shadow-sm">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-white">Notas</h2>
              <p className="text-sm text-slate-400">Vista rápida operativa para dirección comercial.</p>
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            <div className="rounded-xl border border-white/10 bg-white/5 p-4">
              <div className="text-xs uppercase tracking-wide text-slate-500">Conversión</div>
              <div className="mt-2 text-lg font-semibold text-white">
                {(safeStats.tasa_conversion * 100).toFixed(1)}%
              </div>
            </div>

            <div className="rounded-xl border border-white/10 bg-white/5 p-4">
              <div className="text-xs uppercase tracking-wide text-slate-500">Aging medio</div>
              <div className="mt-2 text-lg font-semibold text-white">{Math.round(safeStats.aging_promedio)} días</div>
            </div>

            <div className="rounded-xl border border-white/10 bg-white/5 p-4">
              <div className="text-xs uppercase tracking-wide text-slate-500">Tiempo medio cierre</div>
              <div className="mt-2 text-lg font-semibold text-white">
                {Math.round(safeStats.tiempo_medio_cierre)} días
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}