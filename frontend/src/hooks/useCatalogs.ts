import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import { crmApi, Usuario, Actuacion } from '../api/crm'

/** Lista de usuarios (todos por defecto). Cacheada 30s. */
export function useUsuarios(opts: { activo?: boolean } = {}) {
  return useQuery({
    queryKey: ['usuarios', opts],
    queryFn: () => crmApi.listUsuarios(opts),
    staleTime: 30_000,
  })
}

/** Mapa id -> Usuario para resolver UUIDs rapidamente en tablas. */
export function useUsuariosMap() {
  const q = useUsuarios()
  const map = useMemo(() => {
    const m = new Map<string, Usuario>()
    for (const u of q.data ?? []) m.set(u.id, u)
    return m
  }, [q.data])
  return { ...q, map }
}

/** Catalogo de actuaciones. Cacheado 5min (no cambia). */
export function useActuaciones() {
  return useQuery<Actuacion[]>({
    queryKey: ['actuaciones'],
    queryFn: () => crmApi.listActuaciones(),
    staleTime: 5 * 60_000,
  })
}
