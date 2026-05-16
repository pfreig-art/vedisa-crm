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

export interface LoginResponse {
  access_token: string
  token_type: string
  rol: string
  nombre: string
  email: string
}

export interface CurrentUser {
  id: string
  email: string
  nombre: string
  rol: string
  activo: boolean
}

export const authApi = {
  login: async (email: string, password: string): Promise<LoginResponse> => {
    // /auth/login espera OAuth2PasswordRequestForm (form-urlencoded, campos username/password)
    const form = new URLSearchParams()
    form.append('username', email)
    form.append('password', password)
    const { data } = await api.post('/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    return data as LoginResponse
  },

  me: async (): Promise<CurrentUser> => {
    const { data } = await api.get('/auth/me')
    return data as CurrentUser
  },

  changePassword: async (passwordActual: string, passwordNueva: string): Promise<{ ok: boolean }> => {
    const { data } = await api.post('/auth/change-password', {
      password_actual: passwordActual,
      password_nueva: passwordNueva,
    })
    return data as { ok: boolean }
  },
}

export default authApi
