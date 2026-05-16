import { useState, useEffect, useCallback, useMemo } from 'react';
import CRMTable from '../components/CRMTable';
import SolicitudSheet from '../components/SolicitudSheet';
import UserAvatar from '../components/UserAvatar';
import { ColumnDef } from '@tanstack/react-table';
import { useAIStore } from '../store/aiStore';
import { crmApi, Solicitud, Usuario } from '../api/crm';
import { useUsuariosMap } from '../hooks/useCatalogs';
import { Search, RefreshCw, Download, Plus, Bot } from 'lucide-react';

const PRIORIDAD_COLORS: Record<string, string> = {
  alta: 'bg-red-100 text-red-700',
  media: 'bg-yellow-100 text-yellow-700',
  baja: 'bg-gray-100 text-gray-600',
};

const ESTADO_COLORS: Record<string, string> = {
  recibida: 'bg-blue-100 text-blue-700',
  en_estudio: 'bg-indigo-100 text-indigo-700',
  ofertada: 'bg-purple-100 text-purple-700',
  ganada: 'bg-green-100 text-green-700',
  perdida: 'bg-red-100 text-red-700',
  descartada: 'bg-gray-100 text-gray-500',
};

/** Compone una dirección legible a partir de los campos individuales. */
function composeDireccion(s: Solicitud): string {
  const linea1Parts = [s.tipo_via, s.estudio_direccion, s.numero].filter(
    (v) => v && String(v).trim() !== '',
  );
  const linea2Parts = [s.cp, s.poblacion].filter(
    (v) => v && String(v).trim() !== '',
  );
  const l1 = linea1Parts.join(' ').trim();
  const l2 = linea2Parts.join(' ').trim();
  if (l1 && l2) return `${l1}, ${l2}`;
  return l1 || l2 || '-';
}

/** Resuelve un UUID o nombre legacy a un Usuario del mapa, o devuelve null. */
function resolveUsuario(
  raw: string | null | undefined,
  map: Map<string, Usuario>,
): { usuario: Usuario | null; fallback: string | null } {
  if (!raw) return { usuario: null, fallback: null };
  const trimmed = raw.trim();
  if (!trimmed) return { usuario: null, fallback: null };
  // UUID v4: usar mapa
  if (/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(trimmed)) {
    const u = map.get(trimmed);
    return { usuario: u ?? null, fallback: u ? null : '·' };
  }
  // Valor legacy en texto plano
  return { usuario: null, fallback: trimmed };
}

export default function Contacts() {
  const [data, setData] = useState<Solicitud[]>([]);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [search, setSearch] = useState('');
  const [total, setTotal] = useState(0);
  const { setContext, openDrawer } = useAIStore();
  const { map: usuariosMap } = useUsuariosMap();

  // Estado del sheet de detalle / creación
  const [sheetOpen, setSheetOpen] = useState(false);
  const [sheetMode, setSheetMode] = useState<'create' | 'edit'>('edit');
  const [selected, setSelected] = useState<Solicitud | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const result = await crmApi.listSolicitudes({ search, page_size: 50 });
      setData(result.items);
      setTotal(result.total);
    } catch (err) {
      console.error('Failed to load solicitudes', err);
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Click fila -> abrir detalle/edición
  const handleRowClick = (row: Solicitud) => {
    setSelected(row);
    setSheetMode('edit');
    setSheetOpen(true);
  };

  // Botón "Analizar con IA" en una fila concreta
  const handleAnalyzeRow = async (row: Solicitud) => {
    try {
      const ctx = await crmApi.getAIContext(row.id);
      setContext(ctx as Record<string, unknown>);
      openDrawer();
    } catch (err) {
      console.error('Failed to load AI context', err);
    }
  };

  const handleCreate = () => {
    setSelected(null);
    setSheetMode('create');
    setSheetOpen(true);
  };

  const handleSheetClose = () => {
    setSheetOpen(false);
    fetchData();
  };

  const handleExportXlsx = async () => {
    setExporting(true);
    try {
      const blob = await crmApi.exportSolicitudes('xlsx');
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const ts = new Date().toISOString().slice(0, 10);
      a.download = `solicitudes-${ts}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to export solicitudes', err);
      alert('No se pudo exportar. Revisa la consola.');
    } finally {
      setExporting(false);
    }
  };

  // Columnas — dependen de usuariosMap, así que se construyen con useMemo
  const columns = useMemo<ColumnDef<Solicitud>[]>(
    () => [
      {
        accessorKey: 'codigo',
        header: 'Codigo',
        cell: ({ getValue }) => (
          <span className="font-mono text-xs text-gray-400">{getValue<string>()}</span>
        ),
      },
      {
        accessorKey: 'nombre_corto',
        header: 'Solicitud',
        cell: ({ getValue }) => (
          <span className="font-medium text-gray-900">{getValue<string>()}</span>
        ),
      },
      {
        id: 'direccion',
        header: 'Direccion',
        cell: ({ row }) => (
          <span className="text-sm text-gray-700" title={composeDireccion(row.original)}>
            {composeDireccion(row.original)}
          </span>
        ),
      },
      {
        accessorKey: 'estado',
        header: 'Estado',
        cell: ({ getValue }) => {
          const estado = getValue<string>();
          return (
            <span
              className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                ESTADO_COLORS[estado] || 'bg-gray-100 text-gray-600'
              }`}
            >
              {estado?.replace('_', ' ')}
            </span>
          );
        },
      },
      {
        accessorKey: 'prioridad',
        header: 'Prioridad',
        cell: ({ getValue }) => {
          const p = getValue<string>();
          return (
            <span
              className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                PRIORIDAD_COLORS[p] || 'bg-gray-100 text-gray-600'
              }`}
            >
              {p}
            </span>
          );
        },
      },
      {
        accessorKey: 'comercial',
        header: 'Comercial',
        cell: ({ getValue }) => {
          const { usuario, fallback } = resolveUsuario(getValue<string>(), usuariosMap);
          if (usuario) return <UserAvatar usuario={usuario} size="sm" showName />;
          if (fallback) return <span className="text-sm text-gray-600">{fallback}</span>;
          return <span className="text-xs text-gray-400">-</span>;
        },
      },
      {
        accessorKey: 'tecnico_estudios',
        header: 'Tecnico',
        cell: ({ getValue }) => {
          const { usuario, fallback } = resolveUsuario(getValue<string>(), usuariosMap);
          if (usuario) return <UserAvatar usuario={usuario} size="sm" showName />;
          if (fallback) return <span className="text-sm text-gray-600">{fallback}</span>;
          return <span className="text-xs text-gray-400">-</span>;
        },
      },
      {
        accessorKey: 'aging_dias',
        header: 'Aging',
        cell: ({ getValue }) => {
          const dias = getValue<number>();
          if (!dias) return '-';
          const color =
            dias > 30 ? 'text-red-500' : dias > 14 ? 'text-yellow-500' : 'text-green-500';
          return <span className={`font-medium ${color}`}>{dias}d</span>;
        },
      },
      {
        accessorKey: 'oferta',
        header: 'Oferta',
        cell: ({ getValue }) => {
          const v = getValue<number>();
          return v ? `${v.toLocaleString('es-ES')} EUR` : '-';
        },
      },
      {
        id: 'acciones',
        header: '',
        cell: ({ row }) => (
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleAnalyzeRow(row.original);
            }}
            title="Analizar con IA"
            className="p-1.5 rounded-md text-brand-500 hover:bg-brand-500/10"
          >
            <Bot className="w-4 h-4" />
          </button>
        ),
      },
    ],
    [usuariosMap],
  );

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Solicitudes CRM</h1>
          <p className="text-gray-400 text-sm mt-1">{total} solicitudes en total</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleExportXlsx}
            disabled={exporting || loading}
            title="Exportar a Excel"
            className="flex items-center gap-2 px-3 py-2 bg-emerald-700 hover:bg-emerald-600 text-white rounded-md text-sm disabled:opacity-50"
          >
            <Download className={`w-4 h-4 ${exporting ? 'animate-pulse' : ''}`} />
            {exporting ? 'Exportando…' : 'Excel'}
          </button>
          <button
            onClick={handleCreate}
            className="flex items-center gap-2 px-3 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded-md text-sm"
          >
            <Plus className="w-4 h-4" />
            Nueva
          </button>
          <button
            onClick={fetchData}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-md text-sm"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Actualizar
          </button>
        </div>
      </div>

      <div className="flex gap-3 mb-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            placeholder="Buscar solicitudes..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-md text-sm text-white placeholder-gray-500 focus:outline-none focus:border-brand-500"
          />
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <RefreshCw className="w-6 h-6 text-brand-500 animate-spin" />
          <span className="ml-2 text-gray-400">Cargando...</span>
        </div>
      ) : (
        <CRMTable data={data} columns={columns} onRowClick={handleRowClick} />
      )}

      <SolicitudSheet
        solicitud={selected}
        open={sheetOpen}
        onClose={handleSheetClose}
        mode={sheetMode}
      />
    </div>
  );
}
