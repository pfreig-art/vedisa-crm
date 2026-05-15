import { create } from 'zustand'
import { AIMessage, AIProvider } from '../types'
import axios from 'axios'

interface AIStore {
  isOpen: boolean
  messages: AIMessage[]
  providers: AIProvider[]
  selectedProvider: string
  isLoading: boolean
  context: Record<string, unknown>

  openDrawer: () => void
  closeDrawer: () => void
  toggleDrawer: () => void
  setContext: (ctx: Record<string, unknown>) => void
  setProvider: (provider: string) => void
  sendMessage: (prompt: string) => Promise<void>
  clearMessages: () => void
  fetchProviders: () => Promise<void>
}

export const useAIStore = create<AIStore>((set, get) => ({
  isOpen: false,
  messages: [],
  providers: [],
  selectedProvider: '',
  isLoading: false,
  context: {},

  openDrawer: () => set({ isOpen: true }),
  closeDrawer: () => set({ isOpen: false }),
  toggleDrawer: () => set((state) => ({ isOpen: !state.isOpen })),
  setContext: (ctx) => set({ context: ctx }),
  setProvider: (provider) => set({ selectedProvider: provider }),
  clearMessages: () => set({ messages: [] }),

  fetchProviders: async () => {
    try {
      const { data } = await axios.get<AIProvider[]>('/api/ai/providers')
      set({ providers: data, selectedProvider: data[0]?.id || '' })
    } catch (err) {
      console.error('Failed to fetch providers', err)
    }
  },

  sendMessage: async (prompt: string) => {
    const { messages, selectedProvider, context } = get()
    const userMsg: AIMessage = {
      role: 'user',
      content: prompt,
      timestamp: new Date().toISOString(),
    }
    set({ messages: [...messages, userMsg], isLoading: true })

    try {
      const { data } = await axios.post('/api/ai/analyze', {
        prompt,
        provider: selectedProvider || undefined,
        context,
      })
      const assistantMsg: AIMessage = {
        role: 'assistant',
        content: data.content,
        timestamp: new Date().toISOString(),
      }
      set((state) => ({
        messages: [...state.messages, assistantMsg],
        isLoading: false,
      }))
    } catch (err) {
      const errMsg: AIMessage = {
        role: 'assistant',
        content: 'Error al contactar con el proveedor AI. Intenta de nuevo.',
        timestamp: new Date().toISOString(),
      }
      set((state) => ({
        messages: [...state.messages, errMsg],
        isLoading: false,
      }))
    }
  },
}))
