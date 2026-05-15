/**
 * PipelineBoard.tsx - Kanban pipeline view for Vedisa CRM
 * Columns driven by /crm/pipeline endpoint (PipelineColumn[])
 * Supports drag-free estado change via dropdown on each card
 */
import { useEffect, useState, useCallback } from 'react';
import { crmApi, PipelineColumn, Solicitud } from '../api/crm';
import { ChevronDown, RefreshCw, TrendingUp, AlertCircle } from 'lucide-react';

// ---- Colores por prioridad ----
const PRIORIDAD_BADGE: Record<string, string> = {
  alta: 'bg-red-100 text-red-700',
  media: 'bg-yellow-100 text-yellow-700',
  baja: 'bg-green-100 text-green-700',
};

// ---- Componente tarjeta ----
interface KanbanCardProps {
  solicitud: Solicitud;
  onEstadoChange: (id: string, nuevoEstado: string) => void;
  allColumns: PipelineColumn[];
}

function KanbanCard({ solicitud, onEstadoChange, allColumns }: KanbanCardProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-3 mb-2 hover:shadow-md transition-shadow">
      {/* Cabecera */}
      <div className="flex items-start justify-between gap-1 mb-1">
        <span className="text-xs font-mono text-gray-400">{solicitud.codigo}</span>
        <span
          className={`text-xs font-medium px-1.5 py-0.5 rounded-full ${
            PRIORIDAD_BADGE[solicitud.prioridad] ?? 'bg-gray-100 text-gray-600'
          }`}
        >
          {solicitud.prioridad}
        </span>
      </div>

      {/* Nombre */}
      <p className="text-sm font-semibold text-gray-800 leading-tight mb-1">
        {solicitud.nombre_corto}
      </p>

      {/* Poblacion + comercial */}
      <p className="text-xs text-gray-500 mb-2">
        {[solicitud.poblacion, solicitud.comercial].filter(Boolean).join(' · ')}
      </p>

      {/* Oferta */}
      {solicitud.oferta != null && (
        <p className="text-xs text-indigo-600 font-medium mb-2">
          {solicitud.oferta.toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })}
        </p>
      )}

      {/* Aging */}
      {solicitud.aging_dias != null && (
        <p className="text-xs text-gray-400 mb-2">{solicitud.aging_dias}d en pipeline</p>
      )}

      {/* Cambiar estado */}
      <div className="relative">
        <button
          onClick={() => setOpen((v) => !v)}
          className="flex items-center gap-1 text-xs text-gray-500 hover:text-indigo-600 transition-colors"
        >
          Mover a <ChevronDown size={12} />
        </button>
        {open && (
          <div className="absolute left-0 top-5 z-20 bg-white border border-gray-200 rounded-lg shadow-lg min-w-[160px]">
            {allColumns
              .filter((c) => c.estado !== solicitud.estado)
              .map((c) => (
                <button
                  key={c.estado}
                  onClick={() => {
                    setOpen(false);
                    onEstadoChange(solicitud.id, c.estado);
                  }}
                  className="block w-full text-left px-3 py-2 text-xs hover:bg-gray-50 transition-colors"
                >
                  <span
                    className="inline-block w-2 h-2 rounded-full mr-2"
                    style={{ backgroundColor: c.color }}
                  />
                  {c.estado}
                </button>
              ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ---- Componente columna ----
interface KanbanColumnProps {
  column: PipelineColumn;
  onEstadoChange: (id: string, nuevoEstado: string) => void;
  allColumns: PipelineColumn[];
}

function KanbanColumnCard({ column, onEstadoChange, allColumns }: KanbanColumnProps) {
  return (
    <div className="flex-shrink-0 w-72">
      {/* Cabecera columna */}
      <div
        className="flex items-center justify-between px-3 py-2 rounded-t-lg text-white text-sm font-semibold"
        style={{ backgroundColor: column.color }}
      >
        <span>{column.column}</span>
        <div className="flex items-center gap-2">
          <span className="bg-white/20 px-1.5 py-0.5 rounded-full text-xs">{column.count}</span>
        </div>
      </div>

      {/* Total oferta columna */}
      {column.total_oferta > 0 && (
        <div className="flex items-center gap-1 px-3 py-1 bg-gray-50 border-x border-gray-200 text-xs text-gray-500">
          <TrendingUp size={11} />
          {column.total_oferta.toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })}
        </div>
      )}

      {/* Tarjetas */}
      <div
        className="bg-gray-50 border border-gray-200 rounded-b-lg p-2 min-h-[200px] max-h-[calc(100vh-240px)] overflow-y-auto"
      >
        {column.items.length === 0 ? (
          <p className="text-xs text-gray-400 text-center mt-8">Sin solicitudes</p>
        ) : (
          column.items.map((s) => (
            <KanbanCard
              key={s.id}
              solicitud={s}
              onEstadoChange={onEstadoChange}
              allColumns={allColumns}
            />
          ))
        )}
      </div>
    </div>
  );
}

// ---- Pagina principal ----
export default function PipelineBoard() {
  const [columns, setColumns] = useState<PipelineColumn[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      setError(null);
      const data = await crmApi.getPipeline();
      setColumns(data);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Error al cargar el pipeline');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleRefresh = () => {
    setRefreshing(true);
    load();
  };

  const handleEstadoChange = async (id: string, nuevoEstado: string) => {
    try {
      await crmApi.updateEstado(id, nuevoEstado);
      // Optimistic: mover la card localmente
      setColumns((prev) => {
        // Encontrar la solicitud
        let moved: Solicitud | undefined;
        const next = prev.map((col) => {
          const items = col.items.filter((s) => {
            if (s.id === id) { moved = { ...s, estado: nuevoEstado, kanban_column: nuevoEstado }; return false; }
            return true;
          });
          return { ...col, items, count: items.length };
        });
        if (moved) {
          return next.map((col) =>
            col.estado === nuevoEstado
              ? { ...col, items: [...col.items, moved!], count: col.items.length + 1 }
              : col
          );
        }
        return next;
      });
    } catch {
      // Si falla, recargamos del servidor
      load();
    }
  };

  // ---- Render ----
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Pipeline Kanban</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {columns.reduce((acc, c) => acc + c.count, 0)} solicitudes activas
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-indigo-600 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
        >
          <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
          Actualizar
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 p-3 mb-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          <AlertCircle size={14} />
          {error}
        </div>
      )}

      {/* Board */}
      <div className="flex gap-4 overflow-x-auto pb-4">
        {columns.map((col) => (
          <KanbanColumnCard
            key={col.estado}
            column={col}
            onEstadoChange={handleEstadoChange}
            allColumns={columns}
          />
        ))}
      </div>
    </div>
  );
}
