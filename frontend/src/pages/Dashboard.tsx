import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { DashboardStats } from '../types'
import { Users, TrendingUp, DollarSign, BarChart2, Bot } from 'lucide-react'
import { useAIStore } from '../store/aiStore'

async function fetchStats(): Promise<DashboardStats> {
  const { data } = await axios.get<DashboardStats>('/api/crm/dashboard')
  return data
}

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
  const { data: stats, isLoading, error } = useQuery({
    queryKey: ['dashboard'],
    queryFn: fetchStats,
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
          <p className="text-gray-500 text-sm mt-1">Vision general del CRM</p>
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
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          title="Total Contactos"
          value={stats?.total_contacts ?? 0}
          icon={Users}
          color="bg-blue-500"
        />
        <StatCard
          title="Deals Activos"
          value={stats?.total_deals ?? 0}
          icon={TrendingUp}
          color="bg-green-500"
        />
        <StatCard
          title="Valor Pipeline"
          value={`$${((stats?.pipeline_value ?? 0) / 1000).toFixed(0)}k`}
          icon={DollarSign}
          color="bg-purple-500"
        />
        <StatCard
          title="Tasa Conversion"
          value={`${((stats?.conversion_rate ?? 0) * 100).toFixed(1)}%`}
          icon={BarChart2}
          color="bg-orange-500"
        />
      </div>

      {/* Stage breakdown */}
      {stats?.deals_by_stage && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <h2 className="font-semibold text-gray-800 mb-4">Pipeline por Etapa</h2>
          <div className="space-y-3">
            {Object.entries(stats.deals_by_stage).map(([stage, count]) => (
              <div key={stage} className="flex items-center gap-3">
                <span className="text-sm text-gray-600 w-28 capitalize">{stage}</span>
                <div className="flex-1 bg-gray-100 rounded-full h-2">
                  <div
                    className="bg-brand-500 h-2 rounded-full"
                    style={{
                      width: `${(count / (stats.total_deals || 1)) * 100}%`,
                    }}
                  />
                </div>
                <span className="text-sm font-medium text-gray-700 w-8 text-right">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
