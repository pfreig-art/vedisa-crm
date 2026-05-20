import { useEffect, useMemo, useState } from 'react'
import { CheckCircle2, AlertCircle, Loader2, Bot, PlugZap, RefreshCw } from 'lucide-react'
import llmApi, { LLMProvider, LLMTestResult } from '../api/llm'
import type { AIProvider } from '../types'

type ProviderStatusMap = Record<
  string,
  {
    loading?: boolean
    result?: LLMTestResult | null
    error?: string | null
  }
>

const PROVIDER_LABELS: Record<string, string> = {
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  gemini: 'Google Gemini',
  deepseek: 'DeepSeek',
  openrouter: 'OpenRouter',
  litellm: 'LiteLLM',
}

const PROVIDER_ENV_HINTS: Record<string, string> = {
  openai: 'OPENAI_API_KEY',
  anthropic: 'ANTHROPIC_API_KEY',
  gemini: 'GEMINI_API_KEY',
  deepseek: 'DEEPSEEK_API_KEY',
  openrouter: 'OPENROUTER_API_KEY',
  litellm: 'LITELLM_BASE_URL',
}

function normalizeProvider(input: LLMProvider | AIProvider | string): string {
  if (typeof input === 'string') return input.toLowerCase()

  const candidate =
    'provider' in input
      ? input.provider ?? input.name
      : input.name

  return String(candidate ?? '').toLowerCase()
}

function prettyProviderName(name: string): string {
  return PROVIDER_LABELS[name] ?? name.charAt(0).toUpperCase() + name.slice(1)
}

function statusColor(ok?: boolean, available?: boolean) {
  if (ok === true || available === true) return 'text-emerald-400'
  if (ok === false || available === false) return 'text-red-400'
  return 'text-slate-400'
}

export default function Settings() {
  const [providers, setProviders] = useState<LLMProvider[]>([])
  const [statusMap, setStatusMap] = useState<ProviderStatusMap>({})
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [activeProvider, setActiveProvider] = useState<string>('')

  const providerRows = useMemo(() => {
    const seen = new Set<string>()
    const rows = providers
      .map((p) => {
        const name = normalizeProvider(p)
        if (!name || seen.has(name)) return null
        seen.add(name)
        return {
          raw: p,
          name,
          label: prettyProviderName(name),
          envHint: PROVIDER_ENV_HINTS[name] ?? '',
          isAvailable: p.is_available ?? false,
          model: p.model ?? '',
          baseUrl: p.base_url ?? '',
          enabled: p.enabled ?? true,
          isDefault: p.is_default ?? false,
          error: p.error ?? null,
          latencyMs: p.latency_ms ?? null,
          status: p.status ?? '',
        }
      })
      .filter(Boolean) as Array<{
      raw: LLMProvider
      name: string
      label: string
      envHint: string
      isAvailable: boolean
      model: string
      baseUrl: string
      enabled: boolean
      isDefault: boolean
      error: string | null
      latencyMs: number | null
      status: string
    }>

    return rows
  }, [providers])

  useEffect(() => {
    void loadProviders()
  }, [])

  useEffect(() => {
    const defaultProvider = providerRows.find((p) => p.isDefault) ?? providerRows[0]
    if (defaultProvider) setActiveProvider(defaultProvider.name)
  }, [providerRows])

  async function loadProviders() {
    setLoading(true)
    try {
      const data = await llmApi.listProviders()
      setProviders(Array.isArray(data) ? data : [])
    } catch (err) {
      console.error('Error cargando proveedores IA', err)
      setProviders([])
    } finally {
      setLoading(false)
    }
  }

  async function verifyProvider(name: string) {
    setStatusMap((prev) => ({
      ...prev,
      [name]: { ...(prev[name] ?? {}), loading: true, error: null },
    }))

    try {
      const result = await llmApi.testProvider(name)
      setStatusMap((prev) => ({
        ...prev,
        [name]: { loading: false, result, error: null },
      }))
    } catch (err) {
      const message = err instanceof Error ? err.message : 'No se pudo verificar el proveedor'
      setStatusMap((prev) => ({
        ...prev,
        [name]: { loading: false, result: null, error: message },
      }))
    }
  }

  async function verifyAll() {
    setRefreshing(true)
    try {
      for (const provider of providerRows) {
        // secuencial a propósito para evitar ráfagas innecesarias al backend
        // y para que el usuario vea el progreso proveedor a proveedor
        await verifyProvider(provider.name)
      }
    } finally {
      setRefreshing(false)
    }
  }

  const activeProviderData = providerRows.find((p) => p.name === activeProvider) ?? providerRows[0]

  return (
    <div className="min-h-full bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <div className="mx-auto max-w-6xl px-6 py-8">
        <div className="mb-6 flex items-center gap-3">
          <div className="rounded-xl bg-cyan-500/10 p-2 text-cyan-500">
            <Bot className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Configuración IA</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Verifica conectividad y disponibilidad de proveedores LLM.
            </p>
          </div>
        </div>

        <div className="mb-6 grid gap-4 md:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-2xl border border-slate-200 bg-slate-900 p-5 text-white shadow-sm dark:border-slate-800">
            <div className="mb-2 text-xs uppercase tracking-[0.14em] text-slate-400">Proveedor activo</div>
            <div className="text-xl font-semibold">
              {activeProviderData ? activeProviderData.label : 'Sin proveedor'}
            </div>
            <div className="mt-1 text-sm text-slate-400">
              {activeProviderData?.model || 'El router selecciona automáticamente el proveedor disponible o fallback.'}
            </div>
          </div>

          <div className="flex items-end justify-start md:justify-end">
            <button
              type="button"
              onClick={verifyAll}
              disabled={refreshing || loading || providerRows.length === 0}
              className="inline-flex items-center gap-2 rounded-lg bg-cyan-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-cyan-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {refreshing ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
              Verificar todos
            </button>
          </div>
        </div>

        <div className="space-y-3">
          {loading && (
            <div className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-500 shadow-sm dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400">
              Cargando proveedores…
            </div>
          )}

          {!loading && providerRows.length === 0 && (
            <div className="rounded-2xl border border-amber-300 bg-amber-50 p-6 text-sm text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-300">
              El backend no devolvió proveedores IA disponibles.
            </div>
          )}

          {providerRows.map((provider) => {
            const check = statusMap[provider.name]
            const testResult = check?.result
            const isLoading = check?.loading
            const explicitError = check?.error
            const backendError = provider.error
            const effectiveError = explicitError || testResult?.error || backendError || null
            const effectiveOk = testResult?.ok ?? provider.isAvailable
            const isActive = provider.name === activeProvider

            return (
              <div
                key={provider.name}
                className={`rounded-2xl border p-4 shadow-sm transition ${
                  isActive
                    ? 'border-cyan-300 bg-cyan-50 dark:border-cyan-900/50 dark:bg-cyan-950/20'
                    : 'border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900'
                }`}
              >
                <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                  <div className="min-w-0">
                    <div className="mb-1 flex items-center gap-2">
                      <span className="text-base font-semibold">{provider.label}</span>
                      {provider.isDefault && (
                        <span className="rounded-full bg-cyan-600 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white">
                          Activo
                        </span>
                      )}
                    </div>

                    <div className="space-y-1 text-sm text-slate-500 dark:text-slate-400">
                      {provider.model && <div>{provider.model}</div>}
                      {provider.envHint && <div>{provider.envHint}</div>}
                      {provider.baseUrl && <div>{provider.baseUrl}</div>}
                      {provider.status && <div>Estado backend: {provider.status}</div>}
                    </div>

                    {(effectiveError || testResult?.sample || provider.latencyMs != null || testResult?.latency_ms != null) && (
                      <div className="mt-3 space-y-1 text-sm">
                        {effectiveError && (
                          <div className="flex items-center gap-2 text-red-500">
                            <AlertCircle className="h-4 w-4 flex-shrink-0" />
                            <span>{effectiveError}</span>
                          </div>
                        )}
                        {testResult?.sample && (
                          <div className="text-slate-500 dark:text-slate-400">
                            Muestra: <span className="font-mono text-xs">{testResult.sample}</span>
                          </div>
                        )}
                        {(testResult?.latency_ms != null || provider.latencyMs != null) && (
                          <div className="text-slate-500 dark:text-slate-400">
                            Latencia: {testResult?.latency_ms ?? provider.latencyMs} ms
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    <div className={`inline-flex items-center gap-2 text-sm ${statusColor(effectiveOk, provider.isAvailable)}`}>
                      {isLoading ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : effectiveOk ? (
                        <CheckCircle2 className="h-4 w-4" />
                      ) : (
                        <PlugZap className="h-4 w-4" />
                      )}
                    </div>

                    <button
                      type="button"
                      onClick={() => void verifyProvider(provider.name)}
                      disabled={!!isLoading}
                      className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                    >
                      {isLoading ? 'Probando…' : 'Probar'}
                    </button>

                    <button
                      type="button"
                      onClick={() => setActiveProvider(provider.name)}
                      className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                        isActive
                          ? 'bg-cyan-600 text-white'
                          : 'bg-slate-800 text-white hover:bg-slate-700 dark:bg-slate-700 dark:hover:bg-slate-600'
                      }`}
                    >
                      {isActive ? 'Activo' : 'Activar'}
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-900 p-5 text-slate-100 shadow-sm dark:border-slate-800">
          <div className="mb-3 text-xs uppercase tracking-[0.14em] text-slate-400">Configuración del entorno</div>
          <div className="overflow-x-auto rounded-xl bg-slate-950/60 p-4 font-mono text-xs leading-6 text-slate-300">
            {providerRows.length === 0 && (
              <div className="text-slate-500">Sin datos de proveedores.</div>
            )}
            {providerRows.map((p) => (
              <div key={`env-${p.name}`}>
                {p.envHint || `${p.name.toUpperCase()}_API_KEY`}=
                {p.isAvailable ? '••• (configurado)' : '(no configurado)'}
              </div>
            ))}
            <div>
              LLM_PRIMARY_PROVIDER=
              {providerRows.find((p) => p.isDefault)?.name || '(no definido)'}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}