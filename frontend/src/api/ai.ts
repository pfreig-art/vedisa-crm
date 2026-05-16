/**
 * Cliente HTTP para los endpoints IA del Sprint E2.
 *
 * Reutiliza la instancia axios autenticada de api/llm.ts (el interceptor
 * inyecta el Bearer token del access_token guardado en localStorage). Las
 * llamadas devuelven los tipos exactos del backend.
 */
import axios, { AxiosResponse } from 'axios'

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


export type BriefMode = 'default' | 'dashboard' | 'solicitud' | 'obra'

export type ChartType = 'donut' | 'pie' | 'bar' | 'line' | 'kpi'

export interface ChartSpec {
  type: ChartType
  title: string
  data: Array<{ name: string; value: number }>
  x?: string
  y?: string
}

export interface BriefRequest {
  mode: BriefMode
  context?: unknown
  force_refresh?: boolean
}

export interface BriefResponse {
  summary: string
  bullets: string[]
  suggested_questions: string[]
  chart_specs: ChartSpec[]
  model: string
  provider: string
  tokens_used: number
  latency_ms: number
}

export interface BriefResult {
  response: BriefResponse
  cached: boolean
}


export async function postBrief(
  req: BriefRequest,
  opts: { forceRefresh?: boolean } = {},
): Promise<BriefResult> {
  const body: BriefRequest = {
    mode: req.mode,
    context: req.context,
    force_refresh: opts.forceRefresh ?? req.force_refresh ?? false,
  }
  const resp: AxiosResponse<BriefResponse> = await api.post('/ai/brief', body)
  const cachedHeader = resp.headers['x-brief-cached']
  return {
    response: resp.data,
    cached: cachedHeader === 'true',
  }
}
