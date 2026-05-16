import { FormEvent, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Bot, LogIn, AlertCircle, Loader2 } from 'lucide-react'
import { useAuthStore } from '../store/authStore'

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation() as { state?: { from?: { pathname?: string } } }
  const { login, status, error } = useAuthStore()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (submitting) return
    setSubmitting(true)
    try {
      await login(email.trim(), password)
      const to = location.state?.from?.pathname ?? '/'
      navigate(to, { replace: true })
    } catch {
      // El store ya guarda el error
    } finally {
      setSubmitting(false)
    }
  }

  const loading = submitting || status === 'loading'

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 px-4">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm rounded-2xl border border-white/10 bg-slate-900/80 p-6 shadow-xl"
      >
        <div className="mb-6 flex items-center gap-3">
          <div className="rounded-xl bg-brand-500/15 p-2 text-brand-400">
            <Bot className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-white">Vedisa CRM</h1>
            <p className="text-xs text-slate-400">Iniciar sesión</p>
          </div>
        </div>

        <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-400">
          Email
        </label>
        <input
          type="email"
          required
          autoFocus
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="mb-4 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none focus:border-brand-500"
          placeholder="tu@empresa.com"
          disabled={loading}
        />

        <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-400">
          Contraseña
        </label>
        <input
          type="password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mb-4 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none focus:border-brand-500"
          placeholder="••••••••"
          disabled={loading}
        />

        {error && (
          <div className="mb-4 flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-300">
            <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white transition hover:bg-brand-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <LogIn className="h-4 w-4" />}
          {loading ? 'Entrando…' : 'Entrar'}
        </button>

        <p className="mt-4 text-center text-xs text-slate-500">
          ¿Sin usuario? Pídelo a tu administrador.
        </p>
      </form>
    </div>
  )
}
