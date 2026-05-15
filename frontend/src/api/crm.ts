import apiClient from './client';

// ---- Types matching backend schemas ----

export interface ContactoRef {
  nombre: string;
  rol?: string;
  telefono?: string;
  email?: string;
}

export interface Solicitud {
  id: string;
  codigo: string;
  nombre_corto: string;
  poblacion?: string;
  estado: string;
  kanban_column: string;
  color_estado: string;
  prioridad: string;
  comercial?: string;
  tecnico_estudios?: string;
  fecha_solicitud?: string;
  fecha_limite?: string;
  aging_dias?: number;
  oferta?: number;
}

export interface SolicitudFront extends Solicitud {
  estudio_direccion?: string;
  fechas: Record<string, string>;
  presupuesto: Record<string, number>;
  contactos: ContactoRef[];
  actuaciones: string[];
}

export interface PipelineColumn {
  column: string;
  estado: string;
  color: string;
  count: number;
  total_oferta: number;
  items: Solicitud[];
}

export interface SolicitudFilters {
  page?: number;
  size?: number;
  search?: string;
  estado?: string;
  comercial?: string;
  prioridad?: string;
}

export interface PaginatedSolicitudes {
  items: Solicitud[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface DashboardStats {
  total_solicitudes: number;
  en_estudio: number;
  ofertadas: number;
  ganadas: number;
  perdidas: number;
  aging_promedio: number;
  tasa_conversion: number;
  oferta_total: number;
}

// ---- API client ----

export const crmApi = {
  // Listar solicitudes con paginacion y filtros
  async listSolicitudes(filters: SolicitudFilters = {}): Promise<PaginatedSolicitudes> {
    const params = new URLSearchParams();
    if (filters.page) params.set('page', String(filters.page));
    if (filters.size) params.set('size', String(filters.size));
    if (filters.search) params.set('search', filters.search);
    if (filters.estado) params.set('estado', filters.estado);
    if (filters.comercial) params.set('comercial', filters.comercial);
    if (filters.prioridad) params.set('prioridad', filters.prioridad);

    const { data } = await apiClient.get<PaginatedSolicitudes>(
      `/crm/solicitudes?${params.toString()}`
    );
    return data;
  },

  // Obtener solicitud por ID
  async getSolicitud(id: string): Promise<SolicitudFront> {
    const { data } = await apiClient.get<SolicitudFront>(`/crm/solicitudes/${id}`);
    return data;
  },

  // Obtener contexto IA de una solicitud
  async getAIContext(id: string): Promise<Record<string, unknown>> {
    const { data } = await apiClient.get(`/crm/solicitudes/${id}/context`);
    return data;
  },

  // Actualizar estado de una solicitud
  async updateEstado(id: string, estado: string, nota?: string): Promise<Solicitud> {
    const { data } = await apiClient.patch<Solicitud>(
      `/crm/solicitudes/${id}/estado`,
      { estado, nota }
    );
    return data;
  },

  // Obtener pipeline kanban
  async getPipeline(): Promise<PipelineColumn[]> {
    const { data } = await apiClient.get<PipelineColumn[]>('/crm/pipeline');
    return data;
  },

  // Obtener KPIs del dashboard
  async getDashboard(): Promise<DashboardStats> {
    const { data } = await apiClient.get<DashboardStats>('/crm/dashboard');
    return data;
  },
};
