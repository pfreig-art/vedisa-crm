import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { crmApi, Solicitud } from '../api/crm'
import { Search, RefreshCw } from 'lucide-react'

export default function SolicitudesPage() {
  const [search, setSearch] = useState('')
  const [estado, setEstado] = useState('')
  const [prioridad, setPrioridad] = useState('')
  const [comercial, setComercial] = useState('')

  const { data, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['solicitudes'],
    queryFn: () => crmApi.listSolicitudes(),
  })

  const rows = Array.isArray(data?.items) ? data.items : []

  const solicitudes = useMemo<Solicitud[]>(() => {
    return rows.filter((item) => {
      const matchesSearch =
        !search ||
        item.codigo?.toLowerCase().includes(search.toLowerCase()) ||
        item.nombre_corto?.toLowerCase().includes(search.toLowerCase()) ||
        item.poblacion?.toLowerCase().includes(search.toLowerCase())

      const matchesEstado = !estado || item.estado === estado
      const matchesPrioridad = !prioridad || item.prioridad === prioridad
      const matchesComercial = !comercial || item.comercial === comercial

      return matchesSearch && matchesEstado && matchesPrioridad && matchesComercial
    })
  }, [rows, search, estado, prioridad, comercial])

  const estados = useMemo(() => {
    return Array.from(new Set(rows.map((s) => s.estado).filter(Boolean)))
  }, [rows])

  const prioridades = useMemo(() => {
    return Array.from(new Set(rows.map((s) => s.prioridad).filter(Boolean)))
  }, [rows])

  const comerciales = useMemo(() => {
    return Array.from(new Set(rows.map((s) => s.comercial).filter(Boolean)))
  }, [rows])

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6 text-sm text-slate-400">
          Cargando solicitudes…
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-full bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-7xl px-6 py-6">
        <div className="mb-6 flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Solicitudes</h1>
            <p className="mt-1 text-sm text-slate-400">Listado filtrable de oportunidades y solicitudes.</p>
          </div>

          <button
            type="button"
            onClick={() => void refetch()}
            className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-white transition hover:bg-white/10"
          >
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
            Actualizar
          </button>
        </div>

        <div className="mb-6 grid gap-3 rounded-2xl border border-white/10 bg-slate-900/80 p-4 md:grid-cols-2 xl:grid-cols-5">
          <div className="xl:col-span-2">
            <label className="mb-2 block text-xs uppercase tracking-wide text-slate-400">Buscar</label>
            <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-black/20 px-3 py-2">
              <Search className="h-4 w-4 text-slate-500" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Código, nombre, población..."
                className="w-full bg-transparent text-sm text-white outline-none placeholder:text-slate-500"
              />
            </div>
          </div>

          <div>
            <label className="mb-2 block text-xs uppercase tracking-wide text-slate-400">Estado</label>
            <select
              value={estado}
              onChange={(e) => setEstado(e.target.value)}
              className="w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white outline-none"
            >
              <option value="">Todos</option>
              {estados.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-2 block text-xs uppercase tracking-wide text-slate-400">Prioridad</label>
            <select
              value={prioridad}
              onChange={(e) => setPrioridad(e.target.value)}
              className="w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white outline-none"
            >
              <option value="">Todas</option>
              {prioridades.map((item) => (
                <option key={item} value={item ?? ''}>
                  {item}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-2 block text-xs uppercase tracking-wide text-slate-400">Comercial</label>
            <select
              value={comercial}
              onChange={(e) => setComercial(e.target.value)}
              className="w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white outline-none"
            >
              <option value="">Todos</option>
              {comerciales.map((item) => (
                <option key={item} value={item ?? ''}>
                  {item}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="overflow-hidden rounded-2xl border border-white/10 bg-slate-900/80 shadow-sm">
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-white/5 text-left text-xs uppercase tracking-wide text-slate-400">
                <tr>
                  <th className="px-4 py-3">Código</th>
                  <th className="px-4 py-3">Nombre</th>
                  <th className="px-4 py-3">Población</th>
                  <th className="px-4 py-3">Estado</th>
                  <th className="px-4 py-3">Prioridad</th>
                  <th className="px-4 py-3">Comercial</th>
                  <th className="px-4 py-3 text-right">Oferta</th>
                </tr>
              </thead>
              <tbody>
                {solicitudes.map((item) => (
                  <tr key={item.id} className="border-t border-white/5">
                    <td className="px-4 py-3 font-mono text-cyan-300">{item.codigo}</td>
                    <td className="px-4 py-3 text-white">{item.nombre_corto}</td>
                    <td className="px-4 py-3 text-slate-300">{item.poblacion || '-'}</td>
                    <td className="px-4 py-3 text-slate-300">{item.estado}</td>
                    <td className="px-4 py-3 text-slate-300">{item.prioridad || '-'}</td>
                    <td className="px-4 py-3 text-slate-300">{item.comercial || '-'}</td>
                    <td className="px-4 py-3 text-right text-slate-200">
                      {new Intl.NumberFormat('es-ES', {
                        style: 'currency',
                        currency: 'EUR',
                        maximumFractionDigits: 0,
                      }).format(item.oferta ?? 0)}
                    </td>
                  </tr>
                ))}

                {solicitudes.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-10 text-center text-slate-500">
                      No hay solicitudes que coincidan con los filtros.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}