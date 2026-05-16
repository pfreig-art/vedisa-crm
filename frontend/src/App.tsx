import { Routes, Route, NavLink } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Contacts from './pages/Contacts';
import SettingsPage from './pages/Settings';
import PipelineBoard from './pages/PipelineBoard';
import { useAIStore } from './store/aiStore';
import AIDrawer from './components/AIDrawer';
import { LayoutDashboard, Users, Settings, Bot, Zap } from 'lucide-react';

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/contacts', label: 'Contactos', icon: Users },
  { to: '/pipeline', label: 'Pipeline', icon: Zap },
  { to: '/settings', label: 'Configuracion IA', icon: Settings },
];

export default function App() {
  const { isOpen } = useAIStore();

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
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
        <div className="p-4 border-t border-gray-700 text-xs text-gray-500">
          v0.1.0 &ndash; Multi-LLM CRM
        </div>
      </aside>

      {/* Main content */}
      <main className={`flex-1 transition-all duration-300 ${isOpen ? 'mr-96' : ''}`}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/contacts" element={<Contacts />} />
          <Route path="/pipeline" element={<PipelineBoard />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>

      {/* AI Drawer */}
      <AIDrawer />
    </div>
  );
}
