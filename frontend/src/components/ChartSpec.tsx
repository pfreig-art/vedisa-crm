/**
 * Renderiza un chart_spec sugerido por el modelo en el brief del drawer IA.
 *
 * Tipos soportados: donut, pie, bar, line, kpi. Si los datos vienen vacios
 * o el tipo no es valido, muestra un fallback "Datos insuficientes".
 *
 * Tema oscuro consistente con el drawer (fondo slate). Las dimensiones se
 * adaptan al contenedor via ResponsiveContainer; altura fija ~200px.
 */
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { ChartSpec } from '../api/ai'


const PALETTE = [
  '#6366f1', // indigo
  '#f59e0b', // amber
  '#10b981', // emerald
  '#ef4444', // red
  '#06b6d4', // cyan
  '#a855f7', // purple
  '#f97316', // orange
  '#84cc16', // lime
]

const AXIS_COLOR = '#94a3b8'
const GRID_COLOR = 'rgba(148, 163, 184, 0.15)'
const TOOLTIP_STYLE: React.CSSProperties = {
  background: '#1e293b',
  border: '1px solid rgba(148, 163, 184, 0.25)',
  borderRadius: 6,
  color: '#e2e8f0',
  fontSize: 12,
}


function Fallback({ title }: { title?: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-slate-900/60 p-4 text-sm text-slate-400">
      {title && (
        <div className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-300">
          {title}
        </div>
      )}
      Datos insuficientes
    </div>
  )
}


export default function ChartSpec({ spec }: { spec: ChartSpec }) {
  if (!spec) return null

  const xKey = (spec.x as string) || 'name'
  const yKey = (spec.y as string) || 'value'
  const data = Array.isArray(spec.data) ? spec.data : []
  const hasData = data.length > 0 && data.some((d) => d && d[yKey as keyof typeof d] != null)

  if (spec.type === 'kpi') {
    // KPI: leemos el primer dato; data.value = numero; data.name = label.
    const entry = data[0]
    if (!entry || entry[yKey as keyof typeof entry] == null) {
      return <Fallback title={spec.title} />
    }
    const value = entry[yKey as keyof typeof entry] as number | string
    const label = (entry[xKey as keyof typeof entry] as string) || spec.title || ''
    return (
      <div
        className="rounded-xl border border-white/10 bg-slate-900/80 p-4"
        data-testid="chart-spec-kpi"
      >
        {spec.title && (
          <div className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-300">
            {spec.title}
          </div>
        )}
        <div className="text-3xl font-semibold text-violet-300">{String(value)}</div>
        {label && label !== spec.title && (
          <div className="mt-1 text-xs text-slate-400">{label}</div>
        )}
      </div>
    )
  }

  if (!hasData) {
    return <Fallback title={spec.title} />
  }

  return (
    <div
      className="rounded-xl border border-white/10 bg-slate-900/80 p-3"
      data-testid={`chart-spec-${spec.type}`}
    >
      {spec.title && (
        <div className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-300">
          {spec.title}
        </div>
      )}
      <div style={{ width: '100%', height: 200 }}>
        <ResponsiveContainer>
          {spec.type === 'donut' || spec.type === 'pie' ? (
            <PieChart>
              <Pie
                data={data}
                dataKey={yKey}
                nameKey={xKey}
                innerRadius={spec.type === 'donut' ? 40 : 0}
                outerRadius={70}
                stroke="rgba(15, 23, 42, 0.6)"
                strokeWidth={2}
              >
                {data.map((_, idx) => (
                  <Cell key={`cell-${idx}`} fill={PALETTE[idx % PALETTE.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Legend wrapperStyle={{ fontSize: 11, color: '#cbd5e1' }} />
            </PieChart>
          ) : spec.type === 'line' ? (
            <LineChart data={data}>
              <CartesianGrid stroke={GRID_COLOR} strokeDasharray="3 3" />
              <XAxis dataKey={xKey} stroke={AXIS_COLOR} fontSize={11} />
              <YAxis stroke={AXIS_COLOR} fontSize={11} />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Line
                type="monotone"
                dataKey={yKey}
                stroke={PALETTE[0]}
                strokeWidth={2}
                dot={{ r: 3, fill: PALETTE[0] }}
              />
            </LineChart>
          ) : (
            // bar (por defecto y type=='bar')
            <BarChart data={data}>
              <CartesianGrid stroke={GRID_COLOR} strokeDasharray="3 3" />
              <XAxis dataKey={xKey} stroke={AXIS_COLOR} fontSize={11} />
              <YAxis stroke={AXIS_COLOR} fontSize={11} />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Bar dataKey={yKey} radius={[4, 4, 0, 0]}>
                {data.map((_, idx) => (
                  <Cell key={`bar-${idx}`} fill={PALETTE[idx % PALETTE.length]} />
                ))}
              </Bar>
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  )
}
