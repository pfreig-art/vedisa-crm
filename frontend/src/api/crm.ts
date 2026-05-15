import { apiClient } from './client';
import type { Contact } from '../types';

export interface PaginatedContacts {
  items: Contact[];
  total: number;
  page: number;
  size: number;
}

export interface ContactFilters {
  page?: number;
  size?: number;
  search?: string;
  stage?: string;
  owner_id?: string;
}

export const crmApi = {
  // Listar contactos con paginacion y filtros
  async listContacts(filters: ContactFilters = {}): Promise<PaginatedContacts> {
    const params = new URLSearchParams();
    if (filters.page) params.set('page', String(filters.page));
    if (filters.size) params.set('size', String(filters.size));
    if (filters.search) params.set('search', filters.search);
    if (filters.stage) params.set('stage', filters.stage);
    if (filters.owner_id) params.set('owner_id', filters.owner_id);

    const response = await apiClient.get<PaginatedContacts>(
      `/crm/contacts?${params.toString()}`
    );
    return response.data;
  },

  // Obtener contacto por ID
  async getContact(id: string): Promise<Contact> {
    const response = await apiClient.get<Contact>(`/crm/contacts/${id}`);
    return response.data;
  },

  // Crear contacto
  async createContact(data: Partial<Contact>): Promise<Contact> {
    const response = await apiClient.post<Contact>('/crm/contacts', data);
    return response.data;
  },

  // Actualizar contacto
  async updateContact(id: string, data: Partial<Contact>): Promise<Contact> {
    const response = await apiClient.patch<Contact>(`/crm/contacts/${id}`, data);
    return response.data;
  },

  // Eliminar contacto
  async deleteContact(id: string): Promise<void> {
    await apiClient.delete(`/crm/contacts/${id}`);
  },

  // Obtener etapas del pipeline
  async getPipelineStages(): Promise<{ stage: string; count: number }[]> {
    const response = await apiClient.get<{ stage: string; count: number }[]>(
      '/crm/pipeline'
    );
    return response.data;
  },

  // Obtener stats del dashboard
  async getDashboardStats(): Promise<Record<string, number>> {
    const response = await apiClient.get<Record<string, number>>('/crm/stats');
    return response.data;
  },
};
