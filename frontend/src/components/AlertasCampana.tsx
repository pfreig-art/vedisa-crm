/**
 * Campana de alertas en el sidebar con dropdown de hasta 5 items.
 */
import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Bell } from 'lucide-react'
import { crmApi, Alertas } from '../api/crm'

export default function AlertasCampana() {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const { data: alertas } = useQuery<Alertas>({
    queryKey: ['alertas'],
    queryFn: crmApi.getAlertas,
    refetchInterval: 60_000,
  })

  const total = (alertas?.total_vencidas ?? 0) + (alertas?.total_proximas ?? 0)
  const items = [...(alertas?.vencidas ?? []), ...(alertas?.proximas ?? [])].slice(0, 5)

  // Cerrar al hacer click fuera
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    if (open) document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="relative flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-xs text-gray-300 hover:bg-gray-700"
        title="Alertas de fechas limite"
      >
        <Bell className="h-3.5 w-3.5" />
        Alertas
        {total > 0 && (
          <span className="ml-auto rounded-full bg-orange-500 px-1.5 py-0.5 text-[9px] font-bold text-white">
            {total}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute bottom-full left-0 z-50 mb-1 w-72 rounded-xl border border-gray-700 bg-gray-900 shadow-xl">
          <div className="border-b border-gray-700 px-4 py-2.5">
            <div className="text-sm font-medium text-white">Alertas de vencimiento</div>
          </div>
          {items.length === 0 ? (
            <div className="px-4 py-6 text-center text-xs text-gray-500">
              Sin alertas pendientes
            </div>
          ) : (
            <div className="divide-y divide-gray-800">
              {items.map((item) => (
                <div
                  key={item.id}
                  className="flex items-start gap-3 px-4 py-3 hover:bg-gray-800/60 cursor-pointer"
                  onClick={() => {
                    setOpen(false)
                    navigate('/contacts')
                  }}
                >
                  <div
                    className={`mt-0.5 h-2 w-2 shrink-0 rounded-full ${
                      item.dias_a_limite < 0 ? 'bg-red-500' : 'bg-amber-400'
                    }`}
                  />
                  <div className="min-w-0">
                    <div className="truncate text-xs font-medium text-white">{item.nombre_corto}</div>
                    <div className="mt-0.5 text-[10px] text-gray-400">
                      {item.dias_a_limite < 0
                        ? `Vencida hace ${Math.abs(item.dias_a_limite)} dia${Math.abs(item.dias_a_limite) !== 1 ? 's' : ''}`
                        : `Vence en ${item.dias_a_limite} dia${item.dias_a_limite !== 1 ? 's' : ''}`}
                    </div>
                  </div>
                  <div className="ml-auto shrink-0 text-[10px] text-gray-500">{item.codigo}</div>
                </div>
              ))}
            </div>
          )}
          <div className="border-t border-gray-700 px-4 py-2">
            <button
              type="button"
              onClick={() => {
                setOpen(false)
                navigate('/contacts')
              }}
              className="text-xs text-indigo-400 hover:text-indigo-300"
            >
              Ver todas las solicitudes
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
