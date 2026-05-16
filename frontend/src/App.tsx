import { useEffect } from 'react'
import { Routes, Route, NavLink, Navigate, useLocation } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Contacts from './pages/Contacts'
import SettingsPage from './pages/Settings'
import PipelineBoard from './pages/PipelineBoard'
import Login from './pages/Login'
import { useAIStore } from './store/aiStore'
import { useAuthStore } from './store/authStore'
import AIDrawer from './components/AIDrawer'
import { LayoutDashboard, Users, Settings, Bot, Zap, LogOut, Loader2 } from 'lucide-react'

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/contacts', label: 'Contactos', icon: Users },
  { to: '/pipeline', label: 'Pipeline', icon: Zap },
  { to: '/settings', label: 'Configuracion IA', icon: Settings },
]

function ProtectedShell({ children }: { children: React.ReactNode }) {
  const { isOpen } = useAIStore()
  const { user, logout } = useAuthStore()

  return (
    <div className="min-h-screen flex">
      <aside className="w-56 bg-gray-900 text-white flex flex-col">
        <div className="p-4 border-b border-gray-700">
          <div className="flex items-center gap-2">
            <Bot className="w-6 h-6 text-brand-400" />
            <h1 className="text-xl font-bold text-brand-500">Vedisa CRM</h1>
          </div>
        </div>

        <nav className="flex-1 p-4 space-y-1">
          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive ? 'bg-brand-600 text-white' : 'text-gray-300 hover:bg-gray-700'
                }`
              }
            >
              <Icon className="w-4 h-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        {user && (
          <div className="p-4 border-t border-gray-700">
            <div className="mb-2">
              <div className="truncate text-sm font-medium text-white" title={user.nombre}>
                {user.nombre}
              </div>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="truncate text-xs text-gray-400" title={user.email}>
                  {user.email}
                </span>
              </div>
              <div className="mt-1.5">
                <span className="inline-block rounded-full bg-brand-500/15 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-brand-300">
                  {user.rol}
                </span>
              </div>
            </div>
            <button
              type="button"
              onClick={logout}
              className="mt-2 flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-xs text-gray-300 hover:bg-gray-700"
            >
              <LogOut className="h-3.5 w-3.5" />
              Cerrar sesión
            </button>
          </div>
        )}

        <div className="p-4 border-t border-gray-700 text-xs text-gray-500">
          v0.1.0 &ndash; Multi-LLM CRM
        </div>
      </aside>

      <main className={`flex-1 transition-all duration-300 ${isOpen ? 'mr-96' : ''}`}>
        {children}
      </main>

      <AIDrawer />
    </div>
  )
}

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { status } = useAuthStore()
  const location = useLocation()

  if (status === 'idle' || status === 'loading') {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-950 text-slate-400">
        <Loader2 className="h-5 w-5 animate-spin" />
        <span className="ml-2 text-sm">Verificando sesión…</span>
      </div>
    )
  }

  if (status !== 'authenticated') {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  return <ProtectedShell>{children}</ProtectedShell>
}

export default function App() {
  const hydrate = useAuthStore((s) => s.hydrate)
  const status = useAuthStore((s) => s.status)

  useEffect(() => {
    void hydrate()
  }, [hydrate])

  return (
    <Routes>
      <Route
        path="/login"
        element={status === 'authenticated' ? <Navigate to="/" replace /> : <Login />}
      />
      <Route
        path="/"
        element={
          <RequireAuth>
            <Dashboard />
          </RequireAuth>
        }
      />
      <Route
        path="/contacts"
        element={
          <RequireAuth>
            <Contacts />
          </RequireAuth>
        }
      />
      <Route
        path="/pipeline"
        element={
          <RequireAuth>
            <PipelineBoard />
          </RequireAuth>
        }
      />
      <Route
        path="/settings"
        element={
          <RequireAuth>
            <SettingsPage />
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
