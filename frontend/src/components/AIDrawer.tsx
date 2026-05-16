import { useEffect, useMemo, useState } from 'react'
import {
  X, Bot, Send, Loader2, Sparkles, RefreshCw, AlertCircle,
} from 'lucide-react'
import { useAIStore } from '../store/aiStore'
import llmApi from '../api/llm'
import { postBrief, BriefResponse, BriefMode } from '../api/ai'
import { getSchemaSummary } from '../api/meta'
import ChartSpec from './ChartSpec'


type ChatMessage = {
  role: 'user' | 'assistant'
  content: string
}


function BriefSkeleton() {
  return (
    <div className="space-y-3" data-testid="brief-skeleton">
      <div className="h-4 w-3/4 animate-pulse rounded bg-slate-700/60" />
      <div className="h-3 w-full animate-pulse rounded bg-slate-700/40" />
      <div className="h-3 w-5/6 animate-pulse rounded bg-slate-700/40" />
    </div>
  )
}


export default function AIDrawer() {
  const { isOpen, mode, title, context, closeDrawer } = useAIStore()
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)

  // --- Estado del brief contextual (Sprint E2) -----------------------
  const [brief, setBrief] = useState<BriefResponse | null>(null)
  const [briefLoading, setBriefLoading] = useState(false)
  const [briefError, setBriefError] = useState<string | null>(null)
  const [briefCached, setBriefCached] = useState(false)
  const [schemaSummary, setSchemaSummary] = useState<string>('')

  // Serialización del contexto: se envía al modelo en el system prompt pero
  // NO se muestra al usuario en pantalla.
  const contextPayload = useMemo(() => {
    if (!context) return ''
    try {
      return JSON.stringify(context, null, 2)
    } catch {
      return String(context)
    }
  }, [context])

  const systemPrompt = useMemo(() => {
    const base =
      'Eres el asistente de Vedisa CRM. Responde única y exclusivamente sobre ' +
      'los datos del CRM Vedisa: solicitudes, pipeline comercial, ofertas, estados, ' +
      'clientes, tiempos de cierre, técnicos y comerciales. ' +
      'Si el usuario pregunta algo que no se refiere a estos datos (cultura general, ' +
      'geografía, noticias, productos de terceros, opiniones, etc.) responde exactamente: ' +
      '"Esta consulta queda fuera del alcance del CRM Vedisa." y no añadas nada más. ' +
      'Usa los números del contexto cuando estén disponibles. ' +
      'Responde en español, en tono profesional y conciso. ' +
      'No expongas el JSON del contexto al usuario.'
    const blocks = [base]
    if (schemaSummary) {
      blocks.push(
        `\nResumen del dominio del CRM (para fundamentar tus respuestas):\n${schemaSummary}`,
      )
    }
    if (contextPayload) {
      blocks.push(`\nContexto actual (datos vivos del CRM):\n${contextPayload}`)
    }
    return blocks.join('')
  }, [contextPayload, schemaSummary])

  // --- Cargar schema summary 1 vez ---------------------------------
  useEffect(() => {
    if (!isOpen) return
    if (schemaSummary) return
    getSchemaSummary().then(setSchemaSummary)
  }, [isOpen, schemaSummary])

  // --- Disparar brief al abrir / cambiar contexto -------------------
  async function fetchBrief(forceRefresh = false) {
    if (!isOpen) return
    setBriefLoading(true)
    setBriefError(null)
    try {
      const { response, cached } = await postBrief(
        { mode: (mode as BriefMode) ?? 'default', context },
        { forceRefresh },
      )
      setBrief(response)
      setBriefCached(cached)
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Error generando brief'
      setBriefError(msg)
      setBrief(null)
    } finally {
      setBriefLoading(false)
    }
  }

  useEffect(() => {
    if (!isOpen) return
    // Solo intentar brief si hay un mode util (siempre lo hay) y context.
    // No bloquea la UI: el chat libre queda interactivo en paralelo.
    void fetchBrief(false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, mode, contextPayload])

  async function handleSend(presetText?: string) {
    const candidate = (presetText ?? input).trim()
    if (!candidate || isLoading) return

    const nextMessages: ChatMessage[] = [
      ...messages,
      { role: 'user', content: candidate },
    ]
    setMessages(nextMessages)
    setInput('')
    setIsLoading(true)

    try {
      const response = await llmApi.chat({
        messages: [
          { role: 'system' as const, content: systemPrompt },
          ...nextMessages.map((m) => ({ role: m.role, content: m.content })),
        ],
      })
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: response.content || 'Sin respuesta del modelo.' },
      ])
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Error enviando mensaje al modelo'
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Error: ${message}` },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  function handleClose() {
    closeDrawer()
    setInput('')
    setMessages([])
    setBrief(null)
    setBriefError(null)
    setBriefCached(false)
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

        <div className="flex-1 space-y-4 overflow-y-auto p-4">
          {/* ----- Brief contextual (Sprint E2) ----- */}
          <section
            className="rounded-2xl border border-violet-500/30 bg-violet-600/10 p-4"
            data-testid="brief-panel"
          >
            <div className="mb-2 flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-violet-200">
                <Sparkles className="h-3.5 w-3.5" />
                Brief automatico
              </div>
              <button
                type="button"
                onClick={() => void fetchBrief(true)}
                disabled={briefLoading}
                className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-violet-200 transition hover:bg-violet-500/20 disabled:opacity-50"
                title="Regenerar brief"
              >
                <RefreshCw
                  className={`h-3.5 w-3.5 ${briefLoading ? 'animate-spin' : ''}`}
                />
                Regenerar
              </button>
            </div>

            {briefLoading && !brief && <BriefSkeleton />}

            {briefError && (
              <div className="flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <div>
                  <p>{briefError}</p>
                  <button
                    type="button"
                    onClick={() => void fetchBrief(true)}
                    className="mt-1 text-xs underline hover:text-white"
                  >
                    Reintentar
                  </button>
                </div>
              </div>
            )}

            {brief && !briefError && (
              <div className="space-y-3">
                {brief.summary && (
                  <p className="text-base font-medium text-white">
                    {brief.summary}
                  </p>
                )}
                {brief.bullets.length > 0 && (
                  <ul className="ml-4 list-disc space-y-1 text-sm text-slate-200">
                    {brief.bullets.map((b, i) => (
                      <li key={`b-${i}`}>{b}</li>
                    ))}
                  </ul>
                )}
                {brief.suggested_questions.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {brief.suggested_questions.map((q, i) => (
                      <button
                        key={`q-${i}`}
                        type="button"
                        onClick={() => void handleSend(q)}
                        className="rounded-full border border-violet-400/40 bg-violet-500/20 px-2.5 py-1 text-xs text-violet-100 transition hover:bg-violet-500/40"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                )}
                {brief.chart_specs.length > 0 && (
                  <div className="space-y-2">
                    {brief.chart_specs.map((spec, i) => (
                      <ChartSpec key={`c-${i}`} spec={spec} />
                    ))}
                  </div>
                )}
                {briefCached && (
                  <div className="flex justify-end">
                    <span className="rounded-full bg-slate-800/60 px-2 py-0.5 text-[10px] text-slate-400">
                      Brief en cache
                    </span>
                  </div>
                )}
              </div>
            )}
          </section>

          {/* ----- Chat libre (siempre disponible) ----- */}
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
