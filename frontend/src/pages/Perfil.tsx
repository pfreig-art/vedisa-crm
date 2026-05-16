import { useState } from 'react'
import { useAuthStore } from '../store/authStore'
import { authApi } from '../api/auth'
import { KeyRound, CheckCircle, User } from 'lucide-react'

const inp = 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500'
const lbl = 'block text-xs font-medium text-gray-600 mb-1'

function deriveIniciales(nombre?: string | null): string {
  if (!nombre) return '?'
  const parts = nombre.trim().split(/\s+/).filter(Boolean)
  return parts.slice(0, 2).map((p) => p[0]?.toUpperCase() ?? '').join('')
}

function defaultColor(seed?: string | null): string {
  if (!seed) return '#6b7280'
  let h = 0
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) >>> 0
  return `hsl(${h % 360} 55% 45%)`
}

export default function Perfil() {
  const { user } = useAuthStore()

  const [passwordActual, setPasswordActual] = useState('')
  const [passwordNueva, setPasswordNueva] = useState('')
  const [confirmar, setConfirmar] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [toast, setToast] = useState<{ type: 'ok' | 'error'; msg: string } | null>(null)

  if (!user) return null

  const iniciales = deriveIniciales(user.nombre)
  const bg = defaultColor(user.id)

  async function handleChangePassword(e: React.FormEvent) {
    e.preventDefault()
    setToast(null)

    // Validaciones cliente
    if (passwordNueva !== confirmar) {
      setToast({ type: 'error', msg: 'Las contrasenas nuevas no coinciden' })
      return
    }
    if (passwordNueva.length < 6) {
      setToast({ type: 'error', msg: 'La contrasena debe tener al menos 6 caracteres' })
      return
    }

    setSubmitting(true)
    try {
      await authApi.changePassword(passwordActual, passwordNueva)
      setToast({ type: 'ok', msg: 'Contrasena actualizada correctamente' })
      setPasswordActual('')
      setPasswordNueva('')
      setConfirmar('')
    } catch (err: unknown) {
      const anyErr = err as { response?: { data?: { detail?: string } }; message?: string }
      const msg =
        anyErr?.response?.data?.detail ?? anyErr?.message ?? 'Error al cambiar la contrasena'
      setToast({ type: 'error', msg: String(msg) })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-full bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-2xl px-6 py-10">
        <h1 className="mb-8 text-2xl font-semibold tracking-tight">Mi perfil</h1>

        {/* Card datos del usuario */}
        <div className="mb-6 rounded-2xl border border-white/10 bg-slate-900/80 p-6 shadow-sm">
          <div className="flex items-center gap-5">
            <div
              className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full text-xl font-bold text-white"
              style={{ backgroundColor: bg }}
            >
              {iniciales}
            </div>
            <div>
              <div className="text-lg font-semibold text-white">{user.nombre}</div>
              <div className="text-sm text-slate-400">{user.email}</div>
              <div className="mt-1 flex items-center gap-2">
                <span className="inline-block rounded-full bg-indigo-500/15 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-indigo-300">
                  {user.rol}
                </span>
                {user.activo && (
                  <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400">
                    <CheckCircle className="h-3 w-3" />
                    Activo
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="mt-5 grid gap-3 border-t border-white/10 pt-5 sm:grid-cols-2">
            <div>
              <div className="text-xs text-slate-500">ID de usuario</div>
              <div className="mt-0.5 font-mono text-xs text-slate-400">{user.id}</div>
            </div>
            <div>
              <div className="text-xs text-slate-500">Rol</div>
              <div className="mt-0.5 text-sm text-slate-300 capitalize">{user.rol}</div>
            </div>
          </div>
        </div>

        {/* Card cambiar contrasena */}
        <div className="rounded-2xl border border-white/10 bg-slate-900/80 p-6 shadow-sm">
          <div className="mb-5 flex items-center gap-2">
            <KeyRound className="h-5 w-5 text-indigo-400" />
            <h2 className="text-base font-semibold text-white">Cambiar contrasena</h2>
          </div>

          {toast && (
            <div
              className={`mb-4 rounded-lg px-4 py-3 text-sm ${
                toast.type === 'ok'
                  ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                  : 'bg-red-500/15 text-red-300 border border-red-500/30'
              }`}
            >
              {toast.msg}
            </div>
          )}

          <form onSubmit={handleChangePassword} className="space-y-4">
            <div>
              <label className={lbl + ' text-slate-400'}>Contrasena actual</label>
              <input
                type="password"
                value={passwordActual}
                onChange={(e) => setPasswordActual(e.target.value)}
                required
                className={inp + ' bg-slate-800 border-slate-700 text-white placeholder-slate-500'}
                placeholder="Tu contrasena actual"
              />
            </div>
            <div>
              <label className={lbl + ' text-slate-400'}>Nueva contrasena</label>
              <input
                type="password"
                value={passwordNueva}
                onChange={(e) => setPasswordNueva(e.target.value)}
                required
                minLength={6}
                className={inp + ' bg-slate-800 border-slate-700 text-white placeholder-slate-500'}
                placeholder="Minimo 6 caracteres"
              />
            </div>
            <div>
              <label className={lbl + ' text-slate-400'}>Confirmar nueva contrasena</label>
              <input
                type="password"
                value={confirmar}
                onChange={(e) => setConfirmar(e.target.value)}
                required
                className={inp + ' bg-slate-800 border-slate-700 text-white placeholder-slate-500'}
                placeholder="Repite la nueva contrasena"
              />
            </div>
            <button
              type="submit"
              disabled={submitting}
              className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50 transition"
            >
              <User className="h-4 w-4" />
              {submitting ? 'Guardando…' : 'Actualizar contrasena'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
