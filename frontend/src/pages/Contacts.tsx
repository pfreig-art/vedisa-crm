import { useState, useEffect, useCallback } from 'react';
import CRMTable from '../components/CRMTable';
import { ColumnDef } from '@tanstack/react-table';
import { useAIStore } from '../store/aiStore';
import { crmApi, Solicitud } from '../api/crm';
import { Search, RefreshCw } from 'lucide-react';

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

const columns: ColumnDef<Solicitud>[] = [
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
    accessorKey: 'poblacion',
    header: 'Poblacion',
    cell: ({ getValue }) => getValue<string>() || '-',
  },
  {
    accessorKey: 'estado',
    header: 'Estado',
    cell: ({ getValue }) => {
      const estado = getValue<string>();
      return (
        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${ESTADO_COLORS[estado] || 'bg-gray-100 text-gray-600'}`}>
          {estado.replace('_', ' ')}
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
        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${PRIORIDAD_COLORS[p] || 'bg-gray-100 text-gray-600'}`}>
          {p}
        </span>
      );
    },
  },
  {
    accessorKey: 'comercial',
    header: 'Comercial',
    cell: ({ getValue }) => getValue<string>() || '-',
  },
  {
    accessorKey: 'aging_dias',
    header: 'Aging',
    cell: ({ getValue }) => {
      const dias = getValue<number>();
      if (!dias) return '-';
      const color = dias > 30 ? 'text-red-500' : dias > 14 ? 'text-yellow-500' : 'text-green-500';
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
];

export default function Contacts() {
  const [data, setData] = useState<Solicitud[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [total, setTotal] = useState(0);
  const { setContext, openDrawer } = useAIStore();

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const result = await crmApi.listSolicitudes({ search, size: 50 });
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

  const handleRowClick = async (row: Solicitud) => {
    try {
      const ctx = await crmApi.getAIContext(row.id);
      setContext(ctx as Record<string, unknown>);
      openDrawer();
    } catch (err) {
      console.error('Failed to load AI context', err);
    }
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Solicitudes CRM</h1>
          <p className="text-gray-400 text-sm mt-1">{total} solicitudes en total</p>
        </div>
        <button
          onClick={fetchData}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-md text-sm"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Actualizar
        </button>
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
        <CRMTable
          data={data}
          columns={columns}
          onRowClick={handleRowClick}
        />
      )}
    </div>
  );
}
