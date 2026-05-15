import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  ColumnDef,
  SortingState,
  PaginationState,
} from '@tanstack/react-table';
import { ChevronUp, ChevronDown, ChevronLeft, ChevronRight, Bot, Filter } from 'lucide-react';
import { crmApi, Solicitud } from '../api/crm';
import { useAIStore } from '../store/aiStore';

const ESTADOS = ['En Estudio', 'Enviada', 'Adjudicada', 'Rechazada', 'Descartada'];
const PRIORIDADES = ['alta', 'media', 'baja'];

const ESTADO_COLOR: Record<string, string> = {
  'En Estudio': 'bg-indigo-100 text-indigo-800',
  'Enviada': 'bg-amber-100 text-amber-800',
  'Adjudicada': 'bg-emerald-100 text-emerald-800',
  'Rechazada': 'bg-red-100 text-red-800',
  'Descartada': 'bg-gray-100 text-gray-600',
};

const PRIORIDAD_COLOR: Record<string, string> = {
  alta: 'bg-red-100 text-red-700',
  media: 'bg-yellow-100 text-yellow-700',
  baja: 'bg-green-100 text-green-700',
};

export default function SolicitudesPage() {
  const queryClient = useQueryClient();
  const { setContext, openDrawer } = useAIStore();

  // --- Filtros ---
  const [estado, setEstado] = useState('');
  const [prioridad, setPrioridad] = useState('');
  const [comercial, setComercial] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  // --- Paginacion y sorting server-side ---
  const [sorting, setSorting] = useState<SortingState>([]);
  const [{ pageIndex, pageSize }, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 20,
  });

  const { data, isLoading, isError } = useQuery({
    queryKey: ['solicitudes', pageIndex, pageSize, estado, prioridad, comercial],
    queryFn: () =>
      crmApi.listSolicitudes({
        page: pageIndex + 1,
        size: pageSize,
        estado: estado || undefined,
        prioridad: prioridad || undefined,
        comercial: comercial || undefined,
      }),
    placeholderData: (prev) => prev,
  });

  const updateEstado = useMutation({
    mutationFn: ({ id, estado }: { id: string; estado: string }) =>
      crmApi.updateEstado(id, estado),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['solicitudes'] }),
  });

  const handleAnalyzeAI = useCallback(
    async (sol: Solicitud) => {
      const ctx = await crmApi.getSolicitudContext(sol.id);
      setContext({ data: ctx, total: 1 });
      openDrawer();
    },
    [setContext, openDrawer]
  );

  const columns: ColumnDef<Solicitud>[] = [
    {
      accessorKey: 'codigo',
      header: 'Codigo',
      size: 100,
    },
    {
      accessorKey: 'nombre_corto',
      header: 'Nombre',
      cell: ({ row }) => (
        <span className="font-medium text-gray-900">{row.original.nombre_corto}</span>
      ),
    },
    {
      accessorKey: 'poblacion',
      header: 'Poblacion',
    },
    {
      accessorKey: 'estado',
      header: 'Estado',
      cell: ({ row }) => (
        <span
          className={`px-2 py-0.5 rounded-full text-xs font-medium ${
            ESTADO_COLOR[row.original.estado] ?? 'bg-gray-100 text-gray-700'
          }`}
        >
          {row.original.estado}
        </span>
      ),
    },
    {
      accessorKey: 'prioridad',
      header: 'Prioridad',
      cell: ({ row }) => (
        <span
          className={`px-2 py-0.5 rounded-full text-xs font-medium ${
            PRIORIDAD_COLOR[row.original.prioridad ?? 'media']
          }`}
        >
          {row.original.prioridad ?? 'media'}
        </span>
      ),
    },
    {
      accessorKey: 'comercial',
      header: 'Comercial',
    },
    {
      accessorKey: 'oferta',
      header: 'Oferta',
      cell: ({ row }) =>
        row.original.oferta != null
          ? new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(
              row.original.oferta
            )
          : '-',
    },
    {
      accessorKey: 'aging_dias',
      header: 'Aging',
      cell: ({ row }) =>
        row.original.aging_dias != null ? `${row.original.aging_dias}d` : '-',
    },
    {
      id: 'actions',
      header: '',
      size: 60,
      cell: ({ row }) => (
        <button
          onClick={() => handleAnalyzeAI(row.original)}
          title="Analizar con IA"
          className="p-1.5 rounded-md text-brand-600 hover:bg-brand-50 transition-colors"
        >
          <Bot size={16} />
        </button>
      ),
    },
  ];

  const table = useReactTable({
    data: data?.items ?? [],
    columns,
    pageCount: data?.pages ?? -1,
    state: { sorting, pagination: { pageIndex, pageSize } },
    onSortingChange: setSorting,
    onPaginationChange: setPagination,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
    manualSorting: true,
  });

  return (
    <div className="p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Solicitudes</h1>
          <p className="text-sm text-gray-500">
            {data?.total ?? 0} solicitudes
          </p>
        </div>
        <button
          onClick={() => setShowFilters((v) => !v)}
          className="flex items-center gap-2 px-3 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50 transition-colors"
        >
          <Filter size={16} />
          Filtros
        </button>
      </div>

      {/* Filtros */}
      {showFilters && (
        <div className="bg-white border border-gray-200 rounded-xl p-4 grid grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Estado</label>
            <select
              value={estado}
              onChange={(e) => { setEstado(e.target.value); setPagination((p) => ({ ...p, pageIndex: 0 })); }}
              className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="">Todos</option>
              {ESTADOS.map((e) => <option key={e} value={e}>{e}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Prioridad</label>
            <select
              value={prioridad}
              onChange={(e) => { setPrioridad(e.target.value); setPagination((p) => ({ ...p, pageIndex: 0 })); }}
              className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="">Todas</option>
              {PRIORIDADES.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Comercial</label>
            <input
              type="text"
              value={comercial}
              onChange={(e) => { setComercial(e.target.value); setPagination((p) => ({ ...p, pageIndex: 0 })); }}
              placeholder="Filtrar por comercial..."
              className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>
        </div>
      )}

      {/* Tabla */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        {isLoading && (
          <div className="flex items-center justify-center h-32 text-gray-400">Cargando...</div>
        )}
        {isError && (
          <div className="flex items-center justify-center h-32 text-red-500">Error al cargar solicitudes</div>
        )}
        {!isLoading && !isError && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                {table.getHeaderGroups().map((hg) => (
                  <tr key={hg.id}>
                    {hg.headers.map((header) => (
                      <th
                        key={header.id}
                        onClick={header.column.getToggleSortingHandler()}
                        className="px-4 py-3 text-left font-medium text-gray-600 cursor-pointer select-none hover:bg-gray-100"
                        style={{ width: header.getSize() }}
                      >
                        <div className="flex items-center gap-1">
                          {flexRender(header.column.columnDef.header, header.getContext())}
                          {header.column.getIsSorted() === 'asc' ? (
                            <ChevronUp size={14} />
                          ) : header.column.getIsSorted() === 'desc' ? (
                            <ChevronDown size={14} />
                          ) : null}
                        </div>
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody className="divide-y divide-gray-100">
                {table.getRowModel().rows.map((row) => (
                  <tr key={row.id} className="hover:bg-gray-50 transition-colors">
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-4 py-3">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Paginacion */}
        {data && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 bg-gray-50">
            <span className="text-sm text-gray-500">
              Pagina {pageIndex + 1} de {data.pages} &bull; {data.total} registros
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPagination((p) => ({ ...p, pageIndex: 0 }))}
                disabled={pageIndex === 0}
                className="p-1 rounded disabled:opacity-40 hover:bg-gray-200 transition-colors"
              >
                &laquo;
              </button>
              <button
                onClick={() => setPagination((p) => ({ ...p, pageIndex: p.pageIndex - 1 }))}
                disabled={pageIndex === 0}
                className="p-1 rounded disabled:opacity-40 hover:bg-gray-200 transition-colors"
              >
                <ChevronLeft size={16} />
              </button>
              <button
                onClick={() => setPagination((p) => ({ ...p, pageIndex: p.pageIndex + 1 }))}
                disabled={pageIndex >= data.pages - 1}
                className="p-1 rounded disabled:opacity-40 hover:bg-gray-200 transition-colors"
              >
                <ChevronRight size={16} />
              </button>
              <button
                onClick={() => setPagination((p) => ({ ...p, pageIndex: data.pages - 1 }))}
                disabled={pageIndex >= data.pages - 1}
                className="p-1 rounded disabled:opacity-40 hover:bg-gray-200 transition-colors"
              >
                &raquo;
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
