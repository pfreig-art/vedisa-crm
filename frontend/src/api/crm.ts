import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({ baseURL: API_BASE })

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    cfg.headers = cfg.headers ?? {}
    cfg.headers.Authorization = `Bearer ${token}`
  }
  return cfg
})

export interface Solicitud {
  id: string
  codigo: string
  nombre_corto: string
  poblacion?: string | null
  estado: string
  kanban_column: string
  color_estado: string
  prioridad?: string | null
  comercial?: string | null
  tecnico_estudios?: string | null
  fecha_solicitud?: string | null
  fecha_limite?: string | null
  aging_dias?: number | null
  oferta?: number | null
  estudio_direccion?: string | null
  presupuesto?: string | null
  contactos?: string | null
  actuaciones?: string | null
  observaciones?: string | null
}

export interface SolicitudCreate {
  nombre_corto: string
  codigo?: string | null
  poblacion?: string | null
  estado?: string
  kanban_column?: string
  color_estado?: string
  prioridad?: string | null
  comercial?: string | null
  tecnico_estudios?: string | null
  fecha_solicitud?: string | null
  fecha_limite?: string | null
  oferta?: number | null
  presupuesto?: string | null
  estudio_direccion?: string | null
  observaciones?: string | null
  contactos?: string | null
  actuaciones?: string | null
}

export interface DashboardMonth {
  mes: string
  oferta: number
  ganadas: number
  count?: number
}

export interface DashboardBreakdownItem {
  label: string
  value: number
}

export interface DashboardStats {
  total_solicitudes: number
  en_estudio: number
  ofertadas: number
  ganadas: number
  tasa_conversion: number
  oferta_total: number
  aging_promedio: number
  tiempo_medio_cierre: number
  forecast_mensual: DashboardMonth[]
  pipeline_breakdown?: DashboardBreakdownItem[]
  [key: string]: unknown
}

export interface PipelineColumn {
  id: string
  estado: string
  label: string
  color?: string
  count: number
  total_oferta: number
  items: Solicitud[]
}

export interface PaginatedSolicitudes {
  items: Solicitud[]
  total: number
  page: number
  page_size: number
  total_pages: number
  pages: number
}

export interface EstadoUpdatePayload {
  estado: string
  kanban_column?: string | null
  color_estado?: string | null
}

export const crmApi = {
  listSolicitudes: async (params?: Record<string, unknown>): Promise<PaginatedSolicitudes> => {
    const { data } = await api.get('/crm/solicitudes', { params })
    return {
      ...data,
      pages: data.total_pages,
    } as PaginatedSolicitudes
  },

  getSolicitud: async (id: string): Promise<Solicitud> => {
    const { data } = await api.get(`/crm/solicitudes/${id}`)
    return data as Solicitud
  },

  createSolicitud: async (payload: SolicitudCreate): Promise<Solicitud> => {
    const { data } = await api.post('/crm/solicitudes', payload)
    return data as Solicitud
  },

  updateSolicitud: async (id: string, payload: Partial<SolicitudCreate>): Promise<Solicitud> => {
    const { data } = await api.put(`/crm/solicitudes/${id}`, payload)
    return data as Solicitud
  },

  deleteSolicitud: async (id: string): Promise<void> => {
    await api.delete(`/crm/solicitudes/${id}`)
  },

  getSolicitudContext: async (id: string): Promise<Record<string, unknown>> => {
    const { data } = await api.get(`/crm/solicitudes/${id}/context`)
    return data as Record<string, unknown>
  },

  getAIContext: async (id: string): Promise<Record<string, unknown>> => {
    const { data } = await api.get(`/crm/solicitudes/${id}/context`)
    return data as Record<string, unknown>
  },

  updateEstado: async (id: string, estado: string, extras?: Omit<EstadoUpdatePayload, 'estado'>): Promise<void> => {
    await api.patch(`/crm/solicitudes/${id}/estado`, {
      estado,
      ...extras,
    })
  },

  getPipeline: async (): Promise<PipelineColumn[]> => {
    const { data } = await api.get('/crm/pipeline')
    return data as PipelineColumn[]
  },

  getDashboard: async (): Promise<DashboardStats> => {
    const { data } = await api.get('/crm/dashboard')
    return data as DashboardStats
  },

  exportSolicitudes: async (format: 'csv' | 'xlsx' = 'csv'): Promise<Blob> => {
    const { data } = await api.get('/crm/solicitudes/export', {
      params: { formato: format },
      responseType: 'blob',
    })
    return data as Blob
  },
}

export default crmApi