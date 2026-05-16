/**
 * Vista expandida de alertas para admin (Sprint D bloque C).
 *
 * Listado de solicitudes con `dias_a_limite <= 7` (vencidas + proximas)
 * ordenado por dias asc. Cada fila tiene un boton "Enviar recordatorio"
 * que abre el cliente de correo del admin con asunto y cuerpo prerellenado.
 */
import { useQuery } from '@tanstack/react-query'
import { Navigate } from 'react-router-dom'
import { Mail, AlertCircle } from 'lucide-react'
import { crmApi } from '../api/crm'
import { useAuthStore } from '../store/authStore'

interface AlertaItem {
  id: string
  codigo: string
  nombre_corto: string
  fecha_limite: string
  dias_a_limite: number
  comercial: string | null
}

function badgeForDias(dias: number): string {
  if (dias < 0) return 'bg-red-500/20 text-red-300 border-red-500/40'
  if (dias <= 3) return 'bg-amber-500/20 text-amber-300 border-amber-500/40'
  return 'bg-yellow-500/20 text-yellow-200 border-yellow-500/40'
}

function diasLabel(dias: number): string {
  if (dias < 0) return `Vencida hace ${Math.abs(dias)} dias`
  if (dias === 0) return 'Vence hoy'
  return `Vence en ${dias} dias`
}

export default function Alertas() {
  const user = useAuthStore((s) => s.user)
  if (!user || user.rol !== 'admin') {
    return <Navigate to="/" replace />
  }

  const { data, isLoading, isError } = useQuery({
    queryKey: ['alertas'],
    queryFn: () => crmApi.getAlertas(),
    refetchInterval: 60_000,
  })

  const items: AlertaItem[] = [
    ...((data?.vencidas as AlertaItem[]) ?? []),
    ...((data?.proximas as AlertaItem[]) ?? []),
  ].sort((a, b) => a.dias_a_limite - b.dias_a_limite)

  async function enviarRecordatorio(id: string) {
    try {
      const r = await crmApi.recordatorioMailto(id)
      window.location.href = r.mailto_url
    } catch {
      alert('No se pudo obtener el recordatorio')
    }
  }

  return (
    <div className="px-8 py-8 max-w-6xl mx-auto">
      <div className="mb-6 flex items-center gap-3">
        <AlertCircle className="h-6 w-6 text-amber-400" />
        <div>
          <h1 className="text-2xl font-semibold text-white">Alertas y recordatorios</h1>
          <p className="text-sm text-gray-400">
            Solicitudes vencidas o que vencen en los proximos 7 dias.
          </p>
        </div>
      </div>

      {isLoading && (
        <div className="rounded-xl border border-gray-700 bg-gray-800/60 p-6 text-sm text-gray-300">
          Cargando alertas...
        </div>
      )}

      {isError && (
        <div className="rounded-xl border border-red-500/40 bg-red-900/20 p-6 text-sm text-red-300">
          Error cargando alertas.
        </div>
      )}

      {!isLoading && !isError && items.length === 0 && (
        <div className="rounded-xl border border-gray-700 bg-gray-800/60 p-6 text-sm text-gray-300">
          No hay solicitudes vencidas ni proximas a vencer en los proximos 7 dias.
        </div>
      )}

      {!isLoading && items.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-gray-700 bg-gray-800/60">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700 text-left text-xs uppercase text-gray-400">
                <th className="px-4 py-3">Codigo</th>
                <th className="px-4 py-3">Solicitud</th>
                <th className="px-4 py-3">Comercial</th>
                <th className="px-4 py-3">Fecha limite</th>
                <th className="px-4 py-3">Dias</th>
                <th className="px-4 py-3 text-right">Recordatorio</th>
              </tr>
            </thead>
            <tbody>
              {items.map((it) => (
                <tr
                  key={it.id}
                  className="border-b border-gray-700/50 text-gray-200 hover:bg-gray-700/30"
                >
                  <td className="px-4 py-3 font-mono text-xs">{it.codigo}</td>
                  <td className="px-4 py-3">{it.nombre_corto}</td>
                  <td className="px-4 py-3 text-gray-300">{it.comercial ?? '-'}</td>
                  <td className="px-4 py-3 text-gray-300">{it.fecha_limite}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${badgeForDias(
                        it.dias_a_limite,
                      )}`}
                    >
                      {diasLabel(it.dias_a_limite)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      type="button"
                      onClick={() => enviarRecordatorio(it.id)}
                      className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-indigo-700"
                    >
                      <Mail className="h-3.5 w-3.5" />
                      Enviar recordatorio
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
