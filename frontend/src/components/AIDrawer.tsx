import { useMemo, useState } from 'react'
import { X, Bot, Send, Loader2 } from 'lucide-react'
import { useAIStore } from '../store/aiStore'
import llmApi from '../api/llm'

type ChatMessage = {
  role: 'user' | 'assistant'
  content: string
}

export default function AIDrawer() {
  const { isOpen, title, context, closeDrawer } = useAIStore()
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)

  const contextText = useMemo(() => {
    if (!context) return ''
    try {
      return JSON.stringify(context, null, 2)
    } catch {
      return String(context)
    }
  }, [context])

  async function handleSend() {
    const trimmed = input.trim()
    if (!trimmed || isLoading) return

    const nextMessages: ChatMessage[] = [...messages, { role: 'user', content: trimmed }]
    setMessages(nextMessages)
    setInput('')
    setIsLoading(true)

    try {
      const response = await llmApi.chat({
        messages: [
          ...(contextText
            ? [
                {
                  role: 'system' as const,
                  content: `Contexto actual:\n${contextText}`,
                },
              ]
            : []),
          ...nextMessages.map((m) => ({
            role: m.role,
            content: m.content,
          })),
        ],
      })

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: response.content || 'Sin respuesta del modelo.',
        },
      ])
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Error enviando mensaje al modelo'
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Error: ${message}`,
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  function handleClose() {
    closeDrawer()
    setInput('')
    setMessages([])
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/40 backdrop-blur-sm">
      <div className="flex h-full w-full max-w-xl flex-col border-l border-white/10 bg-slate-950 text-slate-100 shadow-2xl">
        <div className="flex items-center justify-between border-b border-white/10 px-4 py-4">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-violet-600/20 p-2 text-violet-300">
              <Bot className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold">{title || 'Asistente IA'}</h2>
              <p className="text-xs text-slate-400">Contexto asistido del CRM</p>
            </div>
          </div>

          <button
            type="button"
            onClick={handleClose}
            className="rounded-lg p-2 text-slate-400 transition hover:bg-white/5 hover:text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {contextText && (
          <div className="border-b border-white/10 bg-black/20 p-4">
            <div className="mb-2 text-xs uppercase tracking-wide text-slate-500">Contexto</div>
            <pre className="max-h-48 overflow-auto whitespace-pre-wrap rounded-xl border border-white/10 bg-slate-900/70 p-3 text-xs text-slate-300">
              {contextText}
            </pre>
          </div>
        )}

        <div className="flex-1 space-y-3 overflow-y-auto p-4">
          {messages.length === 0 && (
            <div className="rounded-2xl border border-dashed border-white/10 bg-white/5 p-4 text-sm text-slate-400">
              Escribe una pregunta sobre el contexto actual del CRM.
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={`${msg.role}-${i}`}
              className={`max-w-[90%] rounded-2xl px-4 py-3 text-sm ${
                msg.role === 'user'
                  ? 'ml-auto bg-cyan-600 text-white'
                  : 'bg-slate-900 border border-white/10 text-slate-200'
              }`}
            >
              {msg.content}
            </div>
          ))}

          {isLoading && (
            <div className="inline-flex items-center gap-2 rounded-2xl border border-white/10 bg-slate-900 px-4 py-3 text-sm text-slate-300">
              <Loader2 className="h-4 w-4 animate-spin" />
              Pensando…
            </div>
          )}
        </div>

        <div className="border-t border-white/10 p-4">
          <div className="flex items-end gap-3">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Pregunta algo sobre dashboard, solicitudes, pipeline o contexto actual…"
              className="min-h-[88px] flex-1 resize-none rounded-2xl border border-white/10 bg-slate-900 px-4 py-3 text-sm text-white outline-none placeholder:text-slate-500"
            />
            <button
              type="button"
              onClick={() => void handleSend()}
              disabled={isLoading || !input.trim()}
              className="inline-flex h-11 items-center gap-2 rounded-xl bg-violet-600 px-4 text-sm font-medium text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Send className="h-4 w-4" />
              Enviar
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}