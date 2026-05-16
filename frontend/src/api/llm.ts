import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  withCredentials: true,
})

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    cfg.headers = cfg.headers ?? {}
    cfg.headers.Authorization = `Bearer ${token}`
  }
  return cfg
})

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

export interface LLMProvider {
  name: string
  provider?: string
  model?: string
  base_url?: string
  enabled?: boolean
  is_default?: boolean
  status?: string
  is_available?: boolean
  error?: string | null
  latency_ms?: number | null
}

export interface LLMTestResult {
  ok: boolean
  latency_ms?: number
  error?: string
  sample?: string
  provider?: string
  model?: string
}

export interface LLMChatMessage {
  role: 'system' | 'user' | 'assistant'
  content: string
}

export interface LLMChatPayload {
  provider?: string
  model?: string
  messages: LLMChatMessage[]
  context?: Record<string, unknown>
}

export interface LLMChatResponse {
  content: string
  provider?: string
  model?: string
  latency_ms?: number
  tokens_used?: number
}

export const llmApi = {
  listProviders: async (): Promise<LLMProvider[]> => {
    const { data } = await api.get('/ai/providers')
    return data as LLMProvider[]
  },

  testProviderByName: async (provider: string): Promise<LLMTestResult> => {
    const { data } = await api.get(`/ai/test/${provider}`)
    return data as LLMTestResult
  },

  testProviderLegacy: async (provider: string): Promise<LLMTestResult> => {
    const { data } = await api.post('/ai/providers/test', { provider })
    return data as LLMTestResult
  },

  testProvider: async (provider: string): Promise<LLMTestResult> => {
    try {
      return await llmApi.testProviderByName(provider)
    } catch {
      return await llmApi.testProviderLegacy(provider)
    }
  },

  chat: async (payload: LLMChatPayload): Promise<LLMChatResponse> => {
    const { data } = await api.post('/ai/chat', payload)
    return data as LLMChatResponse
  },
}

export default llmApi