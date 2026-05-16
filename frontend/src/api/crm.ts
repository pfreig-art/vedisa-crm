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

// Si una llamada autenticada devuelve 401, la sesión murió: limpiar y mandar a /login.
api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err?.response?.status === 401) {
      localStorage.removeItem('access_token')
      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
        window.location.assign('/login')
      }
    }
    return Promise.reject(err)
  },
)

// ============================================================
// Tipos
// ============================================================

export interface Solicitud {
  id: string
  codigo: string
  nombre_corto: string
  poblacion?: string | null
  estado: string
  kanban_column: string
  color_estado: string
  prioridad?: string | null
  comercial?: string | null            // UUID -> usuarios.id
  tecnico_estudios?: string | null     // UUID -> usuarios.id
  fecha_solicitud?: string | null
  fecha_limite?: string | null
  aging_dias?: number | null
  oferta?: number | null
  // Sprint C
  dias_a_limite?: number | null
  // Legacy
  estudio_direccion?: string | null
  presupuesto?: string | null
  contactos?: string | null
  actuaciones?: string | null
  observaciones?: string | null
  // Sprint A
  tipo_via?: string | null
  numero?: string | null
  cp?: string | null
  fecha_reunion?: string | null
  fecha_visita?: string | null
  fecha_enviado?: string | null
  fecha_cierre_cliente?: string | null
  descripcion?: string | null
  cobertura_pct?: number | null
  coste?: number | null
  coeficiente?: number | null
  margen_pct?: number | null
}

// Sprint C: Historial de auditoria
export interface AuditLogEntry {
  id: string
  solicitud_id: string
  usuario_id?: string | null
  usuario_nombre?: string | null
  usuario_iniciales?: string | null
  usuario_color?: string | null
  accion: string
  campo?: string | null
  valor_anterior?: string | null
  valor_nuevo?: string | null
  created_at: string
}

// Sprint C: Alertas
export interface AlertaItem {
  id: string
  codigo: string
  nombre_corto: string
  fecha_limite: string
  dias_a_limite: number
  comercial?: string | null
}

export interface Alertas {
  vencidas: AlertaItem[]
  proximas: AlertaItem[]
  total_vencidas: number
  total_proximas: number
}

// Sprint C: Dashboard extended
export interface TopComercial {
  id: string
  nombre: string
  iniciales?: string | null
  color?: string | null
  oferta_total: number
}

export interface MixActuacion {
  id: string
  nombre: string
  count: number
}

export interface HeatmapItem {
  mes: string
  mes_key: string
  count: number
}

export interface DashboardExtended {
  heatmap: HeatmapItem[]
  top_comerciales: TopComercial[]
  mix_actuaciones: MixActuacion[]
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
  // Sprint A
  tipo_via?: string | null
  numero?: string | null
  cp?: string | null
  fecha_reunion?: string | null
  fecha_visita?: string | null
  fecha_enviado?: string | null
  fecha_cierre_cliente?: string | null
  descripcion?: string | null
  cobertura_pct?: number | null
  coste?: number | null
  coeficiente?: number | null
  margen_pct?: number | null
}

export interface Usuario {
  id: string
  email: string
  nombre: string
  rol: string
  activo: boolean
  equipo?: string | null
  iniciales?: string | null
  color?: string | null
  cargo?: string | null
}

export interface UsuarioUpdate {
  nombre?: string
  rol?: string
  activo?: boolean
  equipo?: string | null
  iniciales?: string | null
  color?: string | null
  cargo?: string | null
}

export interface UsuarioCreate {
  email: string
  nombre: string
  password: string
  rol?: string
  equipo?: string | null
  iniciales?: string | null
  color?: string | null
  cargo?: string | null
  activo?: boolean
}

export type ContactoTipo =
  | 'administracion'
  | 'tecnico_obra'
  | 'ensena_obra'
  | 'presidente'
  | 'propiedad'
  | 'otro'

export interface Contacto {
  id: string
  solicitud_id: string
  tipo: ContactoTipo
  nombre?: string | null
  telefono?: string | null
  email?: string | null
  notas?: string | null
}

export interface ContactoInput {
  tipo: ContactoTipo
  nombre?: string | null
  telefono?: string | null
  email?: string | null
  notas?: string | null
}

export interface Actuacion {
  id: string
  nombre: string
  orden: number
  activo: boolean
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

// ============================================================
// API
// ============================================================

export const crmApi = {
  // -- Solicitudes --
  listSolicitudes: async (params?: Record<string, unknown>): Promise<PaginatedSolicitudes> => {
    const { data } = await api.get('/crm/solicitudes', {
      params,
      paramsSerializer: (p) => {
        const parts: string[] = []
        for (const [k, v] of Object.entries(p)) {
          if (Array.isArray(v)) {
            v.forEach((item) => parts.push(`${encodeURIComponent(k)}=${encodeURIComponent(String(item))}`))
          } else if (v !== undefined && v !== null) {
            parts.push(`${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
          }
        }
        return parts.join('&')
      },
    })
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

  // -- Usuarios --
  listUsuarios: async (params?: { activo?: boolean; equipo?: string }): Promise<Usuario[]> => {
    const { data } = await api.get('/crm/usuarios', { params })
    return data as Usuario[]
  },

  getUsuario: async (id: string): Promise<Usuario> => {
    const { data } = await api.get(`/crm/usuarios/${id}`)
    return data as Usuario
  },

  updateUsuario: async (id: string, payload: UsuarioUpdate): Promise<Usuario> => {
    const { data } = await api.patch(`/crm/usuarios/${id}`, payload)
    return data as Usuario
  },

  createUsuario: async (payload: UsuarioCreate): Promise<Usuario> => {
    const { data } = await api.post('/crm/usuarios', payload)
    return data as Usuario
  },

  setUsuarioPassword: async (id: string, password: string, email?: string): Promise<Usuario> => {
    const { data } = await api.post(`/crm/usuarios/${id}/password`, { password, email })
    return data as Usuario
  },

  // -- Contactos --
  listContactos: async (solicitudId: string): Promise<Contacto[]> => {
    const { data } = await api.get(`/crm/solicitudes/${solicitudId}/contactos`)
    return data as Contacto[]
  },

  createContacto: async (solicitudId: string, payload: ContactoInput): Promise<Contacto> => {
    const { data } = await api.post(`/crm/solicitudes/${solicitudId}/contactos`, payload)
    return data as Contacto
  },

  updateContacto: async (id: string, payload: Partial<ContactoInput>): Promise<Contacto> => {
    const { data } = await api.put(`/crm/contactos/${id}`, payload)
    return data as Contacto
  },

  deleteContacto: async (id: string): Promise<void> => {
    await api.delete(`/crm/contactos/${id}`)
  },

  // -- Actuaciones --
  listActuaciones: async (): Promise<Actuacion[]> => {
    const { data } = await api.get('/crm/actuaciones')
    return data as Actuacion[]
  },

  listSolicitudActuaciones: async (solicitudId: string): Promise<Actuacion[]> => {
    const { data } = await api.get(`/crm/solicitudes/${solicitudId}/actuaciones`)
    return data as Actuacion[]
  },

  setSolicitudActuaciones: async (solicitudId: string, actuacionIds: string[]): Promise<void> => {
    await api.put(`/crm/solicitudes/${solicitudId}/actuaciones`, { actuacion_ids: actuacionIds })
  },

  // -- Sprint C: Historial de auditoria --
  getHistorial: async (solicitudId: string): Promise<AuditLogEntry[]> => {
    const { data } = await api.get(`/crm/solicitudes/${solicitudId}/historial`)
    return data as AuditLogEntry[]
  },

  // -- Sprint C: Alertas --
  getAlertas: async (): Promise<Alertas> => {
    const { data } = await api.get('/crm/alertas')
    return data as Alertas
  },

  // -- Sprint C: Dashboard extended --
  getDashboardExtended: async (): Promise<DashboardExtended> => {
    const { data } = await api.get('/crm/dashboard/extended')
    return data as DashboardExtended
  },
}

export default crmApi
