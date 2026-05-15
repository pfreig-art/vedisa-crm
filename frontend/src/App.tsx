import { Routes, Route, NavLink } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Contacts from './pages/Contacts'
import { useAIStore } from './store/aiStore'
import AIDrawer from './components/AIDrawer'

export default function App() {
  const { isOpen } = useAIStore()

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-56 bg-gray-900 text-white flex flex-col">
        <div className="p-4 border-b border-gray-700">
          <h1 className="text-xl font-bold text-brand-500">Vedisa CRM</h1>
        </div>
        <nav className="flex-1 p-4 space-y-1">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `block px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive ? 'bg-brand-600 text-white' : 'text-gray-300 hover:bg-gray-700'
              }`
            }
          >
            Dashboard
          </NavLink>
          <NavLink
            to="/contacts"
            className={({ isActive }) =>
              `block px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive ? 'bg-brand-600 text-white' : 'text-gray-300 hover:bg-gray-700'
              }`
            }
          >
            Contactos
          </NavLink>
        </nav>
      </aside>

      {/* Main content */}
      <main className={`flex-1 transition-all duration-300 ${isOpen ? 'mr-96' : ''}`}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/contacts" element={<Contacts />} />
        </Routes>
      </main>

      {/* AI Drawer */}
      <AIDrawer />
    </div>
  )
}
