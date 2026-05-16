import { create } from 'zustand'
import { authApi, CurrentUser } from '../api/auth'

interface AuthState {
  user: CurrentUser | null
  token: string | null
  status: 'idle' | 'loading' | 'authenticated' | 'unauthenticated'
  error: string | null

  hydrate: () => Promise<void>
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: typeof window !== 'undefined' ? localStorage.getItem('access_token') : null,
  status: 'idle',
  error: null,

  hydrate: async () => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
    if (!token) {
      set({ status: 'unauthenticated', user: null, token: null })
      return
    }
    set({ status: 'loading', token })
    try {
      const user = await authApi.me()
      set({ user, status: 'authenticated', error: null })
    } catch {
      localStorage.removeItem('access_token')
      set({ user: null, token: null, status: 'unauthenticated' })
    }
  },

  login: async (email, password) => {
    set({ status: 'loading', error: null })
    try {
      const resp = await authApi.login(email, password)
      localStorage.setItem('access_token', resp.access_token)
      set({ token: resp.access_token })
      // Cargar /me para tener el objeto completo y validar el token
      const user = await authApi.me()
      set({ user, status: 'authenticated', error: null })
    } catch (err: unknown) {
      let message = 'No se pudo iniciar sesión.'
      // axios error shape sin tiparlo duro
      const anyErr = err as { response?: { data?: { detail?: string } }; message?: string }
      if (anyErr?.response?.data?.detail) message = anyErr.response.data.detail
      else if (anyErr?.message) message = anyErr.message
      set({ status: 'unauthenticated', error: message, user: null, token: null })
      localStorage.removeItem('access_token')
      throw err
    }
  },

  logout: () => {
    localStorage.removeItem('access_token')
    set({ user: null, token: null, status: 'unauthenticated', error: null })
  },
}))

// hydrate compat para consumidores no-hook si hace falta
export const ensureAuthHydrated = () => useAuthStore.getState().hydrate()
