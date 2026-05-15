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

export interface DashboardStats {
  total_contacts: number
  total_deals: number
  pipeline_value: number
  conversion_rate: number
  contacts_by_status: Record<string, number>
  deals_by_stage: Record<string, number>
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
  tokens_used?: number
}
