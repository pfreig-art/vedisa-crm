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
    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500">{title}</p>
          <p className="text-2xl font-bold mt-1">{value}</p>
        </div>
        <div className={`w-12 h-12 rounded-full flex items-center justify-center ${color}`}>
          <Icon size={22} className="text-white" />
        </div>
      </div>
    </div>
  )
}

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export default function Dashboard() {
  const { data: stats, isLoading, error } = useQuery<DashboardStats>({
    queryKey: ['dashboard'],
    queryFn: () => crmApi.getDashboard(),
  })

  const { openDrawer, setContext } = useAIStore()

  const handleAIAnalysis = () => {
    setContext({ stats, page: 'dashboard' })
    openDrawer()
  }

  const handleExport = async (formato: 'csv' | 'xlsx') => {
    const token = localStorage.getItem('token')
    const res = await fetch(`${API_URL}/crm/solicitudes/export?formato=${formato}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `solicitudes.${formato}`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (isLoading) {
    return (
      <div className="p-6 flex items-center justify-center h-64">
        <div className="animate-spin w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-600">
          Error al cargar el dashboard. Verifica que el backend este corriendo.
        </div>
      </div>
    )
  }

  const maxForecast = Math.max(...(stats?.forecast_mensual?.map((m) => m.oferta) ?? [1]), 1)

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">Resumen del pipeline comercial</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => handleExport('csv')}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <Download size={14} /> CSV
          </button>
          <button
            onClick={() => handleExport('xlsx')}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700"
          >
            <Download size={14} /> Excel
          </button>
          <button
            onClick={handleAIAnalysis}
            className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 text-sm font-medium"
          >
            <Bot size={16} /> Analizar con IA
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Total Solicitudes" value={stats?.total_solicitudes ?? 0} icon={BarChart2} color="bg-indigo-500" />
        <StatCard title="En Estudio" value={stats?.en_estudio ?? 0} icon={TrendingUp} color="bg-blue-500" />
        <StatCard title="Ofertadas" value={stats?.ofertadas ?? 0} icon={Target} color="bg-amber-500" />
        <StatCard title="Ganadas" value={stats?.ganadas ?? 0} icon={TrendingUp} color="bg-emerald-500" />
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Tasa Conversion" value={`${((stats?.tasa_conversion ?? 0) * 100).toFixed(1)}%`} icon={Target} color="bg-purple-500" />
        <StatCard title="Oferta Total" value={`${((stats?.oferta_total ?? 0) / 1000).toFixed(1)}k`} icon={DollarSign} color="bg-teal-500" />
        <StatCard title="Aging Promedio" value={`${Math.round(stats?.aging_promedio ?? 0)}d`} icon={Clock} color="bg-orange-500" />
        <StatCard title="Tiempo Medio Cierre" value={`${Math.round(stats?.tiempo_medio_cierre ?? 0)}d`} icon={Clock} color="bg-rose-500" />
      </div>

      {/* Forecast Mensual */}
      {stats?.forecast_mensual && stats.forecast_mensual.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <h2 className="text-base font-semibold text-gray-800 mb-4">Forecast mensual — Ganadas (ultimos 6 meses)</h2>
          <div className="space-y-3">
            {stats.forecast_mensual.map((m) => (
              <div key={m.mes} className="flex items-center gap-3">
                <span className="w-20 text-xs text-gray-500 shrink-0">{m.mes}</span>
                <div className="flex-1 bg-gray-100 rounded-full h-4 overflow-hidden">
                  <div
                    className="bg-indigo-500 h-4 rounded-full transition-all"
                    style={{ width: `${(m.oferta / maxForecast) * 100}%` }}
                  />
                </div>
                <span className="text-xs font-medium text-gray-700 w-20 text-right">
                  {m.ganadas} ops / {(m.oferta / 1000).toFixed(1)}k
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Pipeline Estado */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
        <h2 className="text-base font-semibold text-gray-800 mb-4">Estado del Pipeline</h2>
        <div className="space-y-3">
          {[
          
            { label: 'En Estudio', value: stats?.en_estudio ?? 0, color: 'bg-indigo-400' },
            { label: 'Ofertadas', value: stats?.ofertadas ?? 0, color: 'bg-amber-400' },
            { label: 'Ganadas', value: stats?.ganadas ?? 0, color: 'bg-emerald-400' },
            { label: 'Perdidas', value: stats?.perdidas ?? 0, color: 'bg-red-400' },
          ].map((item) => (
            <div key={item.label} className="flex items-center gap-3">
              <span className="w-24 text-sm text-gray-600">{item.label}</span>
              <div className="flex-1 bg-gray-100 rounded-full h-3">
                <div
                  className={`${item.color} h-3 rounded-full`}
                  style={{
                    width: `${stats?.total_solicitudes ? (item.value / stats.total_solicitudes) * 100 : 0}%`,
                  }}
                />
              </div>
              <span className="text-sm font-medium w-8 text-right">{item.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
