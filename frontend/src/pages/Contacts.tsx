import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { Contact } from '../types'
import CRMTable from '../components/CRMTable'
import { ColumnDef } from '@tanstack/react-table'
import { useAIStore } from '../store/aiStore'

async function fetchContacts(): Promise<Contact[]> {
  const { data } = await axios.get<Contact[]>('/api/crm/contacts')
  return data
}

const STATUS_COLORS: Record<string, string> = {
  lead: 'bg-blue-100 text-blue-700',
  prospect: 'bg-yellow-100 text-yellow-700',
  client: 'bg-green-100 text-green-700',
  inactive: 'bg-gray-100 text-gray-600',
}

const columns: ColumnDef<Contact>[] = [
  {
    accessorKey: 'name',
    header: 'Nombre',
    cell: ({ getValue }) => (
      <span className="font-medium text-gray-900">{getValue<string>()}</span>
    ),
  },
  {
    accessorKey: 'email',
    header: 'Email',
  },
  {
    accessorKey: 'company',
    header: 'Empresa',
    cell: ({ getValue }) => getValue<string>() || '-',
  },
  {
    accessorKey: 'phone',
    header: 'Telefono',
    cell: ({ getValue }) => getValue<string>() || '-',
  },
  {
    accessorKey: 'status',
    header: 'Estado',
    cell: ({ getValue }) => {
      const status = getValue<string>()
      return (
        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[status] || 'bg-gray-100'}`}>
          {status}
        </span>
      )
    },
  },
  {
    accessorKey: 'value',
    header: 'Valor',
    cell: ({ getValue }) => {
      const val = getValue<number>()
      return val ? `$${val.toLocaleString('es-ES')}` : '-'
    },
  },
]

export default function Contacts() {
  const { data = [], isLoading, error } = useQuery({
    queryKey: ['contacts'],
    queryFn: fetchContacts,
  })
  const { setContext, openDrawer } = useAIStore()

  const handleRowClick = (contact: Contact) => {
    setContext({ contact, page: 'contact_detail' })
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
          Error al cargar contactos. Verifica que el backend este corriendo.
        </div>
      </div>
    )
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Contactos</h1>
        <p className="text-gray-500 text-sm mt-1">
          {data.length} contactos en total
        </p>
      </div>
      <CRMTable
        data={data}
        columns={columns}
        onRowClick={handleRowClick}
        aiContextKey="contacts"
      />
    </div>
  )
}
