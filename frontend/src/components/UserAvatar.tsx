import { Usuario } from '../api/crm'

interface Props {
  usuario?: Usuario | null
  size?: 'xs' | 'sm' | 'md'
  showName?: boolean
  fallback?: string
}

const SIZE_CLASS = {
  xs: 'w-6 h-6 text-[10px]',
  sm: 'w-7 h-7 text-xs',
  md: 'w-9 h-9 text-sm',
} as const

function deriveIniciales(nombre?: string | null): string {
  if (!nombre) return '·'
  const parts = nombre.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return '·'
  return parts
    .slice(0, 3)
    .map((p) => p[0]?.toUpperCase() ?? '')
    .join('')
}

function defaultColor(seed?: string | null): string {
  // Color determinista a partir del seed (id o nombre)
  if (!seed) return '#6b7280'
  let h = 0
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) >>> 0
  const hue = h % 360
  return `hsl(${hue} 55% 45%)`
}

export default function UserAvatar({ usuario, size = 'sm', showName = false, fallback = '·' }: Props) {
  if (!usuario) {
    return (
      <span className="inline-flex items-center gap-2">
        <span
          className={`inline-flex items-center justify-center rounded-full bg-gray-200 text-gray-500 font-semibold ${SIZE_CLASS[size]}`}
          title="Sin asignar"
        >
          {fallback}
        </span>
        {showName && <span className="text-xs text-gray-400">Sin asignar</span>}
      </span>
    )
  }
  const iniciales = (usuario.iniciales && usuario.iniciales.trim()) || deriveIniciales(usuario.nombre)
  const bg = usuario.color || defaultColor(usuario.id || usuario.nombre)
  return (
    <span className="inline-flex items-center gap-2">
      <span
        className={`inline-flex items-center justify-center rounded-full text-white font-semibold select-none ${SIZE_CLASS[size]}`}
        style={{ backgroundColor: bg }}
        title={`${usuario.nombre}${usuario.cargo ? ` · ${usuario.cargo}` : ''}`}
      >
        {iniciales}
      </span>
      {showName && (
        <span className="text-sm text-gray-700 truncate" title={usuario.nombre}>
          {usuario.nombre}
        </span>
      )}
    </span>
  )
}
