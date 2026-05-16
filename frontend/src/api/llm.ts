import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  withCredentials: true,
})

export interface LLMProvider {
  id: number
  name: string
  provider: string
  model: string
  base_url?: string
  enabled: boolean
  is_default?: boolean
}

export interface LLMProviderCreate {
  name: string
  provider: string
  model: string
  base_url?: string
  api_key?: string
  enabled?: boolean
  is_default?: boolean
}

export interface LLMTestResult {
  ok: boolean
  latency_ms?: number
  error?: string
  sample?: string
}

export interface LLMChatMessage {
  role: 'system' | 'user' | 'assistant'
  content: string
}

export const llmApi = {
  listProviders: async (): Promise<LLMProvider[]> => {
    const { data } = await api.get('/llm/providers')
    return data as LLMProvider[]
  },
  getProvider: async (id: number): Promise<LLMProvider> => {
    const { data } = await api.get(`/llm/providers/${id}`)
    return data as LLMProvider
  },
  createProvider: async (payload: LLMProviderCreate): Promise<LLMProvider> => {
    const { data } = await api.post('/llm/providers', payload)
    return data as LLMProvider
  },
  updateProvider: async (id: number, payload: Partial<LLMProviderCreate>): Promise<LLMProvider> => {
    const { data } = await api.put(`/llm/providers/${id}`, payload)
    return data as LLMProvider
  },
  deleteProvider: async (id: number): Promise<void> => {
    await api.delete(`/llm/providers/${id}`)
  },
  setDefault: async (id: number): Promise<LLMProvider> => {
    const { data } = await api.post(`/llm/providers/${id}/default`)
    return data as LLMProvider
  },
  testProvider: async (id: number): Promise<LLMTestResult> => {
    const { data } = await api.post(`/llm/providers/${id}/test`)
    return data as LLMTestResult
  },
  chat: async (payload: { provider_id?: number; messages: LLMChatMessage[]; temperature?: number; max_tokens?: number }) => {
    const { data } = await api.post('/llm/chat', payload)
    return data as { content: string; provider: string; model: string; latency_ms?: number }
  },
}

export default llmApi
