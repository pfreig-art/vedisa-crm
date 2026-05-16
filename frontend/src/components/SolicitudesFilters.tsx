/**
 * Barra de filtros avanzados para la tabla de solicitudes.
 * Persiste el estado en la URL con useSearchParams.
 */
import { useSearchParams } from 'react-router-dom'
import { X, Filter } from 'lucide-react'
import { Usuario, Actuacion } from '../api/crm'

const ESTADOS = ['En Estudio', 'Enviada', 'Adjudicada', 'Rechazada', 'Descartada']
const PRIORIDADES = ['alta', 'media', 'baja']

interface Props {
  usuarios: Usuario[]
  actuaciones: Actuacion[]
}

// Helpers para leer/escribir arrays en URLSearchParams
function getMulti(params: URLSearchParams, key: string): string[] {
  return params.getAll(key)
}

function setMulti(params: URLSearchParams, key: string, values: string[]): URLSearchParams {
  const next = new URLSearchParams(params)
  next.delete(key)
  values.forEach((v) => next.append(key, v))
  return next
}

function toggleValue(arr: string[], val: string): string[] {
  return arr.includes(val) ? arr.filter((x) => x !== val) : [...arr, val]
}

// Badge de filtro seleccionado
function FilterChip({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-indigo-500/20 px-2.5 py-1 text-xs text-indigo-300">
      {label}
      <button type="button" onClick={onRemove} className="hover:text-white">
        <X className="h-3 w-3" />
      </button>
    </span>
  )
}

export default function SolicitudesFilters({ usuarios, actuaciones }: Props) {
  const [params, setParams] = useSearchParams()

  const estados = getMulti(params, 'estado')
  const prioridades = getMulti(params, 'prioridad')
  const comerciales = getMulti(params, 'comercial')
  const tecnicos = getMulti(params, 'tecnico')
  const actuacionFiltros = getMulti(params, 'actuacion')
  const fechaDesde = params.get('fecha_desde') ?? ''
  const fechaHasta = params.get('fecha_hasta') ?? ''

  const totalFiltros =
    estados.length +
    prioridades.length +
    comerciales.length +
    tecnicos.length +
    actuacionFiltros.length +
    (fechaDesde ? 1 : 0) +
    (fechaHasta ? 1 : 0)

  function toggleEstado(e: string) {
    setParams(setMulti(params, 'estado', toggleValue(estados, e)))
  }
  function togglePrioridad(p: string) {
    setParams(setMulti(params, 'prioridad', toggleValue(prioridades, p)))
  }
  function toggleComercial(id: string) {
    setParams(setMulti(params, 'comercial', toggleValue(comerciales, id)))
  }
  function toggleTecnico(id: string) {
    setParams(setMulti(params, 'tecnico', toggleValue(tecnicos, id)))
  }
  function toggleActuacion(id: string) {
    setParams(setMulti(params, 'actuacion', toggleValue(actuacionFiltros, id)))
  }
  function setFechaDesde(v: string) {
    const next = new URLSearchParams(params)
    if (v) next.set('fecha_desde', v)
    else next.delete('fecha_desde')
    setParams(next)
  }
  function setFechaHasta(v: string) {
    const next = new URLSearchParams(params)
    if (v) next.set('fecha_hasta', v)
    else next.delete('fecha_hasta')
    setParams(next)
  }
  function limpiar() {
    setParams(new URLSearchParams())
  }

  const inp = 'border border-gray-700 rounded-md bg-gray-800 text-white text-xs px-2 py-1.5 focus:outline-none focus:border-indigo-500'

  return (
    <div className="rounded-xl border border-gray-700 bg-gray-800/60 p-4 space-y-4">
      {/* Cabecera */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium text-gray-300">
          <Filter className="h-4 w-4" />
          Filtros
          {totalFiltros > 0 && (
            <span className="rounded-full bg-indigo-600 px-2 py-0.5 text-[10px] font-semibold text-white">
              {totalFiltros} activo{totalFiltros !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        {totalFiltros > 0 && (
          <button
            type="button"
            onClick={limpiar}
            className="text-xs text-gray-400 hover:text-white"
          >
            Limpiar filtros
          </button>
        )}
      </div>

      {/* Estado */}
      <div>
        <div className="mb-1.5 text-xs font-medium text-gray-400">Estado</div>
        <div className="flex flex-wrap gap-1.5">
          {ESTADOS.map((e) => (
            <button
              key={e}
              type="button"
              onClick={() => toggleEstado(e)}
              className={`rounded-full px-2.5 py-1 text-xs transition ${
                estados.includes(e)
                  ? 'bg-indigo-600 text-white'
                  : 'border border-gray-600 text-gray-300 hover:bg-gray-700'
              }`}
            >
              {e}
            </button>
          ))}
        </div>
      </div>

      {/* Prioridad */}
      <div>
        <div className="mb-1.5 text-xs font-medium text-gray-400">Prioridad</div>
        <div className="flex flex-wrap gap-1.5">
          {PRIORIDADES.map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => togglePrioridad(p)}
              className={`rounded-full px-2.5 py-1 text-xs capitalize transition ${
                prioridades.includes(p)
                  ? 'bg-amber-600 text-white'
                  : 'border border-gray-600 text-gray-300 hover:bg-gray-700'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Comercial y Tecnico */}
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <div className="mb-1.5 text-xs font-medium text-gray-400">Comercial</div>
          <div className="flex flex-wrap gap-1.5">
            {usuarios.map((u) => (
              <button
                key={u.id}
                type="button"
                onClick={() => toggleComercial(u.id)}
                className={`flex items-center gap-1 rounded-full px-2.5 py-1 text-xs transition ${
                  comerciales.includes(u.id)
                    ? 'bg-teal-600 text-white'
                    : 'border border-gray-600 text-gray-300 hover:bg-gray-700'
                }`}
              >
                {u.iniciales ? (
                  <span
                    className="inline-flex h-4 w-4 items-center justify-center rounded-full text-[9px] font-bold text-white"
                    style={{ backgroundColor: u.color ?? '#6b7280' }}
                  >
                    {u.iniciales}
                  </span>
                ) : null}
                {u.nombre}
              </button>
            ))}
          </div>
        </div>
        <div>
          <div className="mb-1.5 text-xs font-medium text-gray-400">Tecnico</div>
          <div className="flex flex-wrap gap-1.5">
            {usuarios.map((u) => (
              <button
                key={u.id}
                type="button"
                onClick={() => toggleTecnico(u.id)}
                className={`flex items-center gap-1 rounded-full px-2.5 py-1 text-xs transition ${
                  tecnicos.includes(u.id)
                    ? 'bg-purple-600 text-white'
                    : 'border border-gray-600 text-gray-300 hover:bg-gray-700'
                }`}
              >
                {u.nombre}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Actuaciones */}
      <div>
        <div className="mb-1.5 text-xs font-medium text-gray-400">Actuaciones</div>
        <div className="flex flex-wrap gap-1.5">
          {actuaciones.map((a) => (
            <button
              key={a.id}
              type="button"
              onClick={() => toggleActuacion(a.id)}
              className={`rounded-full px-2.5 py-1 text-xs transition ${
                actuacionFiltros.includes(a.id)
                  ? 'bg-rose-600 text-white'
                  : 'border border-gray-600 text-gray-300 hover:bg-gray-700'
              }`}
            >
              {a.nombre}
            </button>
          ))}
        </div>
      </div>

      {/* Date range */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-400">Desde</label>
          <input
            type="date"
            value={fechaDesde}
            onChange={(e) => setFechaDesde(e.target.value)}
            className={inp}
          />
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-400">Hasta</label>
          <input
            type="date"
            value={fechaHasta}
            onChange={(e) => setFechaHasta(e.target.value)}
            className={inp}
          />
        </div>
      </div>

      {/* Chips activos */}
      {totalFiltros > 0 && (
        <div className="flex flex-wrap gap-1.5 border-t border-gray-700 pt-3">
          {estados.map((e) => (
            <FilterChip key={`e-${e}`} label={`Estado: ${e}`} onRemove={() => toggleEstado(e)} />
          ))}
          {prioridades.map((p) => (
            <FilterChip key={`p-${p}`} label={`Prioridad: ${p}`} onRemove={() => togglePrioridad(p)} />
          ))}
          {comerciales.map((id) => {
            const u = usuarios.find((x) => x.id === id)
            return <FilterChip key={`c-${id}`} label={`Comercial: ${u?.nombre ?? id}`} onRemove={() => toggleComercial(id)} />
          })}
          {tecnicos.map((id) => {
            const u = usuarios.find((x) => x.id === id)
            return <FilterChip key={`t-${id}`} label={`Tecnico: ${u?.nombre ?? id}`} onRemove={() => toggleTecnico(id)} />
          })}
          {actuacionFiltros.map((id) => {
            const a = actuaciones.find((x) => x.id === id)
            return <FilterChip key={`a-${id}`} label={`Actuacion: ${a?.nombre ?? id}`} onRemove={() => toggleActuacion(id)} />
          })}
          {fechaDesde && (
            <FilterChip label={`Desde: ${fechaDesde}`} onRemove={() => setFechaDesde('')} />
          )}
          {fechaHasta && (
            <FilterChip label={`Hasta: ${fechaHasta}`} onRemove={() => setFechaHasta('')} />
          )}
        </div>
      )}
    </div>
  )
}
