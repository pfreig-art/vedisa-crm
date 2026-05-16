import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const api = axios.create({ baseURL: API_BASE })

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('access_token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

export interface Solicitud {
  id: number
  nombre_corto: string
  codigo?: string | null
  poblacion?: string | null
  estado: string
  prioridad?: string | null
  comercial?: string | null
  tecnico_estudios?: string | null
  fecha_solicitud?: string | null
  fecha_limite?: string | null
  oferta?: number | null
  observaciones?: string | null
  kanban_column?: string
}

export interface SolicitudCreate {
  nombre_corto: string
  codigo?: string
  poblacion?: string
  estado?: string
  prioridad?: string
  comercial?: string
  tecnico_estudios?: string
  fecha_solicitud?: string
  fecha_limite?: string
  oferta?: number
  observaciones?: string
}

export const crmApi = {
  listSolicitudes: async (params?: Record<string, any>) => {
    const { data } = await api.get('/crm/solicitudes', { params })
    return data
  },
  getSolicitud: async (id: number) => {
    const { data } = await api.get(`/crm/solicitudes/${id}`)
    return data as Solicitud
  },
  createSolicitud: async (payload: SolicitudCreate) => {
    const { data } = await api.post('/crm/solicitudes', payload)
    return data as Solicitud
  },
  updateSolicitud: async (id: number, payload: Partial<SolicitudCreate>) => {
    const { data } = await api.put(`/crm/solicitudes/${id}`, payload)
    return data as Solicitud
  },
  deleteSolicitud: async (id: number) => {
    await api.delete(`/crm/solicitudes/${id}`)
  },
  getPipeline: async () => {
    const { data } = await api.get('/crm/pipeline')
    return data
  },
  getDashboard: async () => {
    const { data } = await api.get('/crm/dashboard')
    return data
  },
  exportSolicitudes: async (format: 'csv' | 'xlsx' = 'csv') => {
    const { data } = await api.get(`/crm/solicitudes/export`, {
      params: { format },
      responseType: 'blob',
    })
    return data as Blob
  },
}

export default crmApi
