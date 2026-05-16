import { useState, useMemo, useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { crmApi, Usuario, UsuarioCreate, UsuarioUpdate } from '../api/crm'
import { useUsuarios } from '../hooks/useCatalogs'
import { useAuthStore } from '../store/authStore'
import UserAvatar from '../components/UserAvatar'
import { RefreshCw, Plus, X, KeyRound, Pencil } from 'lucide-react'

const EQUIPOS = ['comercial', 'estudios', 'direccion', 'administracion'] as const
const ROLES = ['admin', 'usuario'] as const

type ModalMode =
  | { kind: 'closed' }
  | { kind: 'create' }
  | { kind: 'edit'; usuario: Usuario }
  | { kind: 'password'; usuario: Usuario }

// ---------- Helpers ----------

function deriveIniciales(nombre: string): string {
  const parts = nombre.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return ''
  return parts
    .slice(0, 3)
    .map((p) => p[0]?.toUpperCase() ?? '')
    .join('')
}

function errorMessage(err: unknown): string {
  const anyErr = err as { response?: { data?: { detail?: string } }; message?: string }
  return anyErr?.response?.data?.detail || anyErr?.message || 'Error inesperado'
}

// ---------- Modal de creación / edición ----------

function UsuarioFormModal({
  mode,
  onClose,
  onSaved,
}: {
  mode: ModalMode
  onClose: () => void
  onSaved: () => void
}) {
  const editing = mode.kind === 'edit' ? mode.usuario : null
  const [form, setForm] = useState({
    email: editing?.email ?? '',
    nombre: editing?.nombre ?? '',
    password: '',
    rol: editing?.rol ?? 'usuario',
    equipo: editing?.equipo ?? '',
    iniciales: editing?.iniciales ?? '',
    color: editing?.color ?? '',
    cargo: editing?.cargo ?? '',
    activo: editing?.activo ?? true,
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Auto-deriva iniciales si están vacías y cambia el nombre
  useEffect(() => {
    if (!form.iniciales && form.nombre) {
      setForm((f) => ({ ...f, iniciales: deriveIniciales(form.nombre) }))
    }
    // solo cuando cambia nombre
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form.nombre])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      if (mode.kind === 'create') {
        if (!form.email.trim() || !form.nombre.trim() || form.password.length < 6) {
          throw new Error('Email, nombre y password (>=6) son obligatorios')
        }
        const payload: UsuarioCreate = {
          email: form.email.trim(),
          nombre: form.nombre.trim(),
          password: form.password,
          rol: form.rol,
          equipo: form.equipo || null,
          iniciales: form.iniciales || null,
          color: form.color || null,
          cargo: form.cargo || null,
          activo: form.activo,
        }
        await crmApi.createUsuario(payload)
      } else if (mode.kind === 'edit') {
        const payload: UsuarioUpdate = {
          nombre: form.nombre.trim() || undefined,
          rol: form.rol,
          activo: form.activo,
          equipo: form.equipo || null,
          iniciales: form.iniciales || null,
          color: form.color || null,
          cargo: form.cargo || null,
        }
        await crmApi.updateUsuario(mode.usuario.id, payload)
      }
      onSaved()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  if (mode.kind !== 'create' && mode.kind !== 'edit') return null

  const title = mode.kind === 'create' ? 'Nuevo usuario' : `Editar ${mode.usuario.nombre}`

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-lg rounded-lg bg-white shadow-xl">
        <div className="flex items-center justify-between border-b px-5 py-3">
          <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1 text-gray-500 hover:bg-gray-100"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 px-5 py-4">
          <div className="grid grid-cols-2 gap-3">
            <label className="col-span-2 block text-sm">
              <span className="text-gray-700">Email</span>
              <input
                type="email"
                required
                disabled={mode.kind === 'edit'}
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm disabled:bg-gray-100"
              />
            </label>

            <label className="col-span-2 block text-sm">
              <span className="text-gray-700">Nombre completo</span>
              <input
                type="text"
                required
                value={form.nombre}
                onChange={(e) => setForm({ ...form, nombre: e.target.value })}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </label>

            {mode.kind === 'create' && (
              <label className="col-span-2 block text-sm">
                <span className="text-gray-700">Password (mín. 6 caracteres)</span>
                <input
                  type="password"
                  required
                  minLength={6}
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                />
              </label>
            )}

            <label className="block text-sm">
              <span className="text-gray-700">Rol</span>
              <select
                value={form.rol}
                onChange={(e) => setForm({ ...form, rol: e.target.value })}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              >
                {ROLES.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </label>

            <label className="block text-sm">
              <span className="text-gray-700">Equipo</span>
              <select
                value={form.equipo ?? ''}
                onChange={(e) => setForm({ ...form, equipo: e.target.value })}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              >
                <option value="">— sin equipo —</option>
                {EQUIPOS.map((eq) => (
                  <option key={eq} value={eq}>
                    {eq}
                  </option>
                ))}
              </select>
            </label>

            <label className="block text-sm">
              <span className="text-gray-700">Iniciales</span>
              <input
                type="text"
                maxLength={4}
                value={form.iniciales ?? ''}
                onChange={(e) => setForm({ ...form, iniciales: e.target.value.toUpperCase() })}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </label>

            <label className="block text-sm">
              <span className="text-gray-700">Color</span>
              <div className="mt-1 flex items-center gap-2">
                <input
                  type="color"
                  value={form.color || '#6b7280'}
                  onChange={(e) => setForm({ ...form, color: e.target.value })}
                  className="h-9 w-12 cursor-pointer rounded border border-gray-300"
                />
                <input
                  type="text"
                  value={form.color ?? ''}
                  placeholder="#6b7280"
                  onChange={(e) => setForm({ ...form, color: e.target.value })}
                  className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
            </label>

            <label className="col-span-2 block text-sm">
              <span className="text-gray-700">Cargo</span>
              <input
                type="text"
                value={form.cargo ?? ''}
                onChange={(e) => setForm({ ...form, cargo: e.target.value })}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </label>

            <label className="col-span-2 flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={form.activo}
                onChange={(e) => setForm({ ...form, activo: e.target.checked })}
                className="h-4 w-4 rounded border-gray-300"
              />
              <span className="text-gray-700">Activo</span>
            </label>
          </div>

          {/* Preview */}
          <div className="flex items-center gap-3 rounded-md bg-gray-50 p-3">
            <UserAvatar
              usuario={{
                id: editing?.id ?? 'preview',
                email: form.email || 'preview@local',
                nombre: form.nombre || 'Sin nombre',
                rol: form.rol,
                activo: form.activo,
                equipo: form.equipo || null,
                iniciales: form.iniciales || null,
                color: form.color || null,
                cargo: form.cargo || null,
              }}
              size="md"
            />
            <div className="text-sm">
              <div className="font-medium text-gray-900">{form.nombre || '—'}</div>
              <div className="text-gray-500">{form.cargo || form.equipo || form.rol}</div>
            </div>
          </div>

          {error && (
            <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
            >
              {submitting ? 'Guardando…' : 'Guardar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ---------- Modal de password ----------

function PasswordModal({
  usuario,
  onClose,
  onSaved,
}: {
  usuario: Usuario
  onClose: () => void
  onSaved: () => void
}) {
  const [password, setPassword] = useState('')
  const [email, setEmail] = useState(usuario.email)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (password.length < 6) {
      setError('La password debe tener al menos 6 caracteres')
      return
    }
    setSubmitting(true)
    try {
      const newEmail = email.trim() !== usuario.email ? email.trim() : undefined
      await crmApi.setUsuarioPassword(usuario.id, password, newEmail)
      onSaved()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-lg bg-white shadow-xl">
        <div className="flex items-center justify-between border-b px-5 py-3">
          <h2 className="text-lg font-semibold text-gray-900">
            {usuario.activo ? 'Cambiar password' : 'Activar usuario'}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1 text-gray-500 hover:bg-gray-100"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 px-5 py-4">
          <div className="flex items-center gap-3 rounded-md bg-gray-50 p-3">
            <UserAvatar usuario={usuario} size="md" />
            <div className="text-sm">
              <div className="font-medium text-gray-900">{usuario.nombre}</div>
              <div className="text-gray-500">
                {usuario.activo ? 'Usuario activo' : 'Placeholder — sin password'}
              </div>
            </div>
          </div>

          <label className="block text-sm">
            <span className="text-gray-700">Email (opcional, dejar igual si no cambia)</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </label>

          <label className="block text-sm">
            <span className="text-gray-700">Nueva password (mín. 6 caracteres)</span>
            <input
              type="password"
              required
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              autoFocus
            />
          </label>

          {error && (
            <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
            >
              {submitting ? 'Guardando…' : usuario.activo ? 'Cambiar' : 'Activar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ---------- Página principal ----------

export default function Usuarios() {
  const { user } = useAuthStore()
  const qc = useQueryClient()
  const { data: usuarios = [], isLoading, refetch, isFetching } = useUsuarios()
  const [filterActivo, setFilterActivo] = useState<'all' | 'active' | 'placeholder'>('all')
  const [search, setSearch] = useState('')
  const [modal, setModal] = useState<ModalMode>({ kind: 'closed' })

  const filtered = useMemo(() => {
    let list = usuarios
    if (filterActivo === 'active') list = list.filter((u) => u.activo)
    if (filterActivo === 'placeholder') list = list.filter((u) => !u.activo)
    const q = search.trim().toLowerCase()
    if (q) {
      list = list.filter(
        (u) =>
          u.nombre.toLowerCase().includes(q) ||
          u.email.toLowerCase().includes(q) ||
          (u.cargo ?? '').toLowerCase().includes(q) ||
          (u.equipo ?? '').toLowerCase().includes(q),
      )
    }
    return [...list].sort((a, b) => Number(b.activo) - Number(a.activo) || a.nombre.localeCompare(b.nombre))
  }, [usuarios, filterActivo, search])

  const handleSaved = () => {
    setModal({ kind: 'closed' })
    qc.invalidateQueries({ queryKey: ['usuarios'] })
  }

  // Guard: solo admin
  if (user?.rol !== 'admin') {
    return (
      <div className="p-6">
        <div className="rounded-md bg-yellow-50 px-4 py-3 text-sm text-yellow-800">
          Solo los administradores pueden gestionar usuarios.
        </div>
      </div>
    )
  }

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Usuarios</h1>
          <p className="mt-1 text-sm text-gray-400">
            {usuarios.length} usuarios en total · {usuarios.filter((u) => !u.activo).length} pendientes de activar
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setModal({ kind: 'create' })}
            className="flex items-center gap-2 rounded-md bg-brand-600 px-3 py-2 text-sm text-white hover:bg-brand-700"
          >
            <Plus className="h-4 w-4" />
            Nuevo usuario
          </button>
          <button
            type="button"
            onClick={() => refetch()}
            disabled={isFetching}
            className="flex items-center gap-2 rounded-md bg-gray-700 px-3 py-2 text-sm text-gray-300 hover:bg-gray-600"
          >
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
            Actualizar
          </button>
        </div>
      </div>

      <div className="mb-4 flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Buscar por nombre, email, cargo o equipo…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 min-w-[240px] rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-brand-500 focus:outline-none"
        />
        <select
          value={filterActivo}
          onChange={(e) => setFilterActivo(e.target.value as typeof filterActivo)}
          className="rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-white"
        >
          <option value="all">Todos</option>
          <option value="active">Activos</option>
          <option value="placeholder">Placeholders</option>
        </select>
      </div>

      <div className="overflow-hidden rounded-lg bg-white shadow">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                Usuario
              </th>
              <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                Email
              </th>
              <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                Equipo
              </th>
              <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                Cargo
              </th>
              <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                Rol
              </th>
              <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                Estado
              </th>
              <th className="px-4 py-2 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                Acciones
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {isLoading ? (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center text-gray-500">
                  <RefreshCw className="mx-auto mb-2 h-5 w-5 animate-spin" />
                  Cargando usuarios…
                </td>
              </tr>
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center text-gray-500">
                  Sin resultados
                </td>
              </tr>
            ) : (
              filtered.map((u) => (
                <tr key={u.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2">
                    <UserAvatar usuario={u} size="sm" showName />
                  </td>
                  <td className="px-4 py-2 text-sm text-gray-700">{u.email}</td>
                  <td className="px-4 py-2 text-sm text-gray-700">{u.equipo ?? '-'}</td>
                  <td className="px-4 py-2 text-sm text-gray-700">{u.cargo ?? '-'}</td>
                  <td className="px-4 py-2">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        u.rol === 'admin'
                          ? 'bg-purple-100 text-purple-700'
                          : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {u.rol}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    {u.activo ? (
                      <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                        activo
                      </span>
                    ) : (
                      <span className="rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-700">
                        placeholder
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <div className="flex justify-end gap-1">
                      <button
                        type="button"
                        onClick={() => setModal({ kind: 'password', usuario: u })}
                        title={u.activo ? 'Cambiar password' : 'Activar (asignar password)'}
                        className="rounded-md p-1.5 text-brand-600 hover:bg-brand-500/10"
                      >
                        <KeyRound className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => setModal({ kind: 'edit', usuario: u })}
                        title="Editar metadata"
                        className="rounded-md p-1.5 text-gray-600 hover:bg-gray-100"
                      >
                        <Pencil className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {(modal.kind === 'create' || modal.kind === 'edit') && (
        <UsuarioFormModal mode={modal} onClose={() => setModal({ kind: 'closed' })} onSaved={handleSaved} />
      )}
      {modal.kind === 'password' && (
        <PasswordModal
          usuario={modal.usuario}
          onClose={() => setModal({ kind: 'closed' })}
          onSaved={handleSaved}
        />
      )}
    </div>
  )
}
