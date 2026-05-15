import { useState, useEffect } from 'react';
import { useAIStore } from '../store/aiStore';
import { llmApi } from '../api/llm';
import { Settings, CheckCircle, XCircle, RefreshCw, Zap } from 'lucide-react';

interface ProviderStatus {
  name: string;
  available: boolean;
  status?: 'ok' | 'error' | 'not_configured' | 'checking';
  error?: string;
}

export default function SettingsPage() {
  const { providers, selectedProvider, setProvider, fetchProviders } = useAIStore();
  const [statuses, setStatuses] = useState<Record<string, ProviderStatus>>({});
  const [testing, setTesting] = useState<string | null>(null);

  useEffect(() => {
    fetchProviders();
  }, [fetchProviders]);

  const testProvider = async (name: string) => {
    setTesting(name);
    setStatuses(prev => ({ ...prev, [name]: { ...prev[name], name, status: 'checking', available: false } }));
    try {
      const result = await llmApi.testProvider(name);
      setStatuses(prev => ({
        ...prev,
        [name]: {
          name,
          available: result.status === 'ok',
          status: result.status as ProviderStatus['status'],
          error: result.error,
        },
      }));
    } catch (e) {
      setStatuses(prev => ({
        ...prev,
        [name]: { name, available: false, status: 'error', error: String(e) },
      }));
    } finally {
      setTesting(null);
    }
  };

  const testAll = async () => {
    for (const p of providers) {
      await testProvider(p.name);
    }
  };

  const allProviders = [
    { name: 'openai', label: 'OpenAI', description: 'GPT-4o, GPT-4 Turbo', envKey: 'OPENAI_API_KEY' },
    { name: 'anthropic', label: 'Anthropic', description: 'Claude 3.5 Sonnet, Claude 3 Opus', envKey: 'ANTHROPIC_API_KEY' },
    { name: 'gemini', label: 'Google Gemini', description: 'Gemini 1.5 Pro, Gemini Flash', envKey: 'GEMINI_API_KEY' },
    { name: 'deepseek', label: 'DeepSeek', description: 'DeepSeek Chat, DeepSeek Coder', envKey: 'DEEPSEEK_API_KEY' },
    { name: 'openrouter', label: 'OpenRouter', description: 'Multi-model gateway', envKey: 'OPENROUTER_API_KEY' },
    { name: 'litellm', label: 'LiteLLM', description: 'LiteLLM unified gateway', envKey: 'LITELLM_BASE_URL' },
  ];

  return (
    <div className="p-6 max-w-4xl">
      <div className="flex items-center gap-3 mb-6">
        <Settings className="w-6 h-6 text-brand-500" />
        <h1 className="text-2xl font-bold text-white">Configuracion IA</h1>
      </div>

      <div className="mb-6 p-4 bg-gray-800 rounded-lg border border-gray-700">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-1">Proveedor Activo</h2>
        <p className="text-white text-lg font-medium capitalize">{selectedProvider || 'Automatico'}</p>
        <p className="text-gray-500 text-sm mt-1">El router selecciona automaticamente el proveedor disponible con fallback.</p>
      </div>

      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold text-white">Proveedores LLM</h2>
        <button
          onClick={testAll}
          disabled={testing !== null}
          className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white rounded-md text-sm font-medium transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${testing ? 'animate-spin' : ''}`} />
          Verificar todos
        </button>
      </div>

      <div className="grid gap-4">
        {allProviders.map((p) => {
          const backendProvider = providers.find(bp => bp.name === p.name);
          const status = statuses[p.name];
          const isActive = selectedProvider === p.name;
          const isAvailable = backendProvider?.available;

          return (
            <div
              key={p.name}
              className={`p-4 rounded-lg border transition-all ${
                isActive
                  ? 'border-brand-500 bg-brand-900/20'
                  : 'border-gray-700 bg-gray-800/50 hover:border-gray-600'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-white">{p.label}</h3>
                    {isActive && (
                      <span className="px-2 py-0.5 text-xs bg-brand-600 text-white rounded-full">Activo</span>
                    )}
                    {isAvailable && !isActive && (
                      <span className="px-2 py-0.5 text-xs bg-green-800 text-green-200 rounded-full">Disponible</span>
                    )}
                  </div>
                  <p className="text-sm text-gray-400 mt-0.5">{p.description}</p>
                  <p className="text-xs text-gray-600 mt-1 font-mono">{p.envKey}</p>

                  {status && (
                    <div className={`mt-2 flex items-center gap-1.5 text-sm ${
                      status.status === 'ok' ? 'text-green-400' :
                      status.status === 'checking' ? 'text-yellow-400' :
                      'text-red-400'
                    }`}>
                      {status.status === 'ok' ? <CheckCircle className="w-4 h-4" /> :
                       status.status === 'checking' ? <RefreshCw className="w-4 h-4 animate-spin" /> :
                       <XCircle className="w-4 h-4" />}
                      {status.status === 'ok' ? 'Conectado' :
                       status.status === 'checking' ? 'Verificando...' :
                       status.status === 'not_configured' ? 'Sin configurar (API key ausente)' :
                       status.error || 'Error de conexion'}
                    </div>
                  )}
                </div>

                <div className="flex gap-2 ml-4">
                  <button
                    onClick={() => testProvider(p.name)}
                    disabled={testing === p.name}
                    className="px-3 py-1.5 text-xs bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-gray-300 rounded transition-colors"
                  >
                    {testing === p.name ? 'Probando...' : 'Probar'}
                  </button>
                  <button
                    onClick={() => setProvider(p.name)}
                    className={`flex items-center gap-1 px-3 py-1.5 text-xs rounded transition-colors ${
                      isActive
                        ? 'bg-brand-600 text-white'
                        : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
                    }`}
                  >
                    <Zap className="w-3 h-3" />
                    {isActive ? 'Activo' : 'Activar'}
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-6 p-4 bg-gray-800 rounded-lg border border-gray-700">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">Configuracion del entorno</h2>
        <p className="text-sm text-gray-400">Configura las claves API en el archivo <code className="text-brand-400 font-mono bg-gray-900 px-1 rounded">backend/.env</code>:</p>
        <pre className="mt-3 p-3 bg-gray-900 rounded text-xs text-gray-300 font-mono overflow-x-auto">
{`OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIza...
DEEPSEEK_API_KEY=sk-...
OPENROUTER_API_KEY=sk-or-...
LITELLM_BASE_URL=http://localhost:4000
LLM_PRIMARY_PROVIDER=openai
LLM_FALLBACK_PROVIDER=anthropic`}
        </pre>
      </div>
    </div>
  );
}
