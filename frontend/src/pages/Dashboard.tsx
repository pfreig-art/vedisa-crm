import { useQuery } from '@tanstack/react-query'
import { crmApi, DashboardStats } from '../api/crm'
import { Users, TrendingUp, DollarSign, BarChart2, Bot, Target } from 'lucide-react'
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

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 text-sm mt-1">Vision general del CRM de solicitudes</p>
        </div>
        <button
          onClick={handleAIAnalysis}
          className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors"
        >
          <Bot size={18} />
          Analisis IA
        </button>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
        <StatCard
          title="Total Solicitudes"
          value={stats?.total_solicitudes ?? 0}
          icon={Users}
          color="bg-blue-500"
        />
        <StatCard
          title="En Estudio"
          value={stats?.en_estudio ?? 0}
          icon={BarChart2}
          color="bg-indigo-500"
        />
        <StatCard
          title="Ofertadas"
          value={stats?.ofertadas ?? 0}
          icon={TrendingUp}
          color="bg-purple-500"
        />
        <StatCard
          title="Ganadas"
          value={stats?.ganadas ?? 0}
          icon={Target}
          color="bg-green-500"
        />
        <StatCard
          title="Perdidas"
          value={stats?.perdidas ?? 0}
          icon={BarChart2}
          color="bg-red-400"
        />
        <StatCard
          title="Tasa Conversion"
          value={`${((stats?.tasa_conversion ?? 0) * 100).toFixed(1)}%`}
          icon={DollarSign}
          color="bg-orange-500"
        />
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <h2 className="font-semibold text-gray-800 mb-3">Resumen Financiero</h2>
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Valor total ofertado</span>
              <span className="font-semibold text-gray-900">
                ${((stats?.oferta_total ?? 0) / 1000).toFixed(1)}k
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Aging promedio</span>
              <span className="font-semibold text-gray-900">
                {Math.round(stats?.aging_promedio ?? 0)} dias
              </span>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <h2 className="font-semibold text-gray-800 mb-3">Estado del Pipeline</h2>
          <div className="space-y-3">
            {[
              { label: 'Recibidas', value: (stats?.total_solicitudes ?? 0) - (stats?.en_estudio ?? 0) - (stats?.ofertadas ?? 0) - (stats?.ganadas ?? 0) - (stats?.perdidas ?? 0), color: 'bg-blue-400' },
              { label: 'En Estudio', value: stats?.en_estudio ?? 0, color: 'bg-indigo-400' },
              { label: 'Ofertadas', value: stats?.ofertadas ?? 0, color: 'bg-purple-400' },
              { label: 'Ganadas', value: stats?.ganadas ?? 0, color: 'bg-green-400' },
              { label: 'Perdidas', value: stats?.perdidas ?? 0, color: 'bg-red-400' },
            ].map(({ label, value, color }) => (
              <div key={label} className="flex items-center gap-3">
                <span className="text-sm text-gray-600 w-28">{label}</span>
                <div className="flex-1 bg-gray-100 rounded-full h-2">
                  <div
                    className={`${color} h-2 rounded-full`}
                    style={{
                      width: `${((value ?? 0) / Math.max(stats?.total_solicitudes ?? 1, 1)) * 100}%`,
                    }}
                  />
                </div>
                <span className="text-sm font-medium text-gray-700 w-8 text-right">{value ?? 0}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
