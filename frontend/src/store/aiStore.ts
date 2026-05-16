import { create } from 'zustand'

export type AIDrawerMode = 'default' | 'dashboard' | 'solicitud' | 'obra'

export interface AIDrawerPayload {
  mode?: AIDrawerMode
  title?: string
  context?: unknown
}

interface AIStoreState {
  isOpen: boolean
  mode: AIDrawerMode
  title: string
  context: unknown
  openDrawer: (payload?: AIDrawerPayload) => void
  closeDrawer: () => void
  setContext: (context: unknown) => void
}

export const useAIStore = create<AIStoreState>((set) => ({
  isOpen: false,
  mode: 'default',
  title: 'Asistente IA',
  context: null,

  openDrawer: (payload) =>
    set({
      isOpen: true,
      mode: payload?.mode ?? 'default',
      title: payload?.title ?? 'Asistente IA',
      context: payload?.context ?? null,
    }),

  closeDrawer: () =>
    set({
      isOpen: false,
    }),

  setContext: (context) =>
    set({
      context,
    }),
}))