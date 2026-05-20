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
    set((state) => ({
      isOpen: true,
      mode: payload?.mode ?? 'default',
      title: payload?.title ?? 'Asistente IA',
      // Si el caller no aporta context en el payload, preservamos el que ya
      // hubiera en el store (puede haberse seteado via setContext justo antes).
      // Solo se resetea a null cuando explicitamente se pasa context=null.
      context:
        payload && 'context' in payload ? payload.context ?? null : state.context,
    })),

  closeDrawer: () =>
    set({
      isOpen: false,
    }),

  setContext: (context) =>
    set({
      context,
    }),
}))