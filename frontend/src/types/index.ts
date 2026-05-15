// CRM Types
export interface Contact {
  id: string
  name: string
  email: string
  phone?: string
  company?: string
  status: 'lead' | 'prospect' | 'client' | 'inactive'
  stage?: string
  value?: number
  created_at: string
  updated_at: string
}

export interface Deal {
  id: string
  title: string
  contact_id: string
  value: number
  stage: 'new' | 'qualified' | 'proposal' | 'negotiation' | 'won' | 'lost'
  probability: number
  expected_close: string
  created_at: string
}

// DashboardStats - aligned with backend /crm/dashboard schema
export interface DashboardStats {
  total_solicitudes: number
  en_estudio: number
  ofertadas: number
  ganadas: number
  perdidas: number
  aging_promedio: number
  tasa_conversion: number
  oferta_total: number
}

// AI Types
export interface AIMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

export interface AIProvider {
  id: string
  name: string
  model: string
  is_available: boolean
}

export interface AIRequest {
  prompt: string
  provider?: string
  context?: Record<string, unknown>
}

export interface AIResponse {
  content: string
  provider: string
  model: string
  tokens_used: number
}
