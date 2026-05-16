import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { FechaLimiteBadge } from '../../pages/Contacts'
import type { Solicitud } from '../../api/crm'

function makeSolicitud(overrides: Partial<Solicitud>): Solicitud {
  return {
    id: 's-1',
    codigo: 'SOL-2026-TEST',
    nombre_corto: 'Test',
    estado: 'En Estudio',
    kanban_column: 'En Estudio',
    color_estado: '#6366f1',
    prioridad: 'media',
    ...overrides,
  } as Solicitud
}

describe('FechaLimiteBadge', () => {
  it('vencida hace 5 dias: clase rojo y formato (-5d)', () => {
    const sol = makeSolicitud({
      fecha_limite: '2026-05-11',
      dias_a_limite: -5,
    })
    const { container } = render(<FechaLimiteBadge solicitud={sol} />)
    const span = container.querySelector('span')
    expect(span?.className).toMatch(/text-red-400/)
    expect(span?.className).toMatch(/bg-red-500/)
    expect(screen.getByText(/\(-5d\)/)).toBeInTheDocument()
  })

  it('en 3 dias: clase amarillo (amber)', () => {
    const sol = makeSolicitud({
      fecha_limite: '2026-05-19',
      dias_a_limite: 3,
    })
    const { container } = render(<FechaLimiteBadge solicitud={sol} />)
    const span = container.querySelector('span')
    expect(span?.className).toMatch(/text-amber-400/)
    expect(span?.className).toMatch(/bg-amber-500/)
    expect(screen.getByText(/\(3d\)/)).toBeInTheDocument()
  })

  it('en 30 dias: sin color especial', () => {
    const sol = makeSolicitud({
      fecha_limite: '2026-06-15',
      dias_a_limite: 30,
    })
    const { container } = render(<FechaLimiteBadge solicitud={sol} />)
    const span = container.querySelector('span')
    expect(span?.className).not.toMatch(/text-red-400/)
    expect(span?.className).not.toMatch(/text-amber-400/)
  })

  it('sin fecha_limite: renderiza guion en gris', () => {
    const sol = makeSolicitud({ fecha_limite: null, dias_a_limite: null })
    render(<FechaLimiteBadge solicitud={sol} />)
    // Sin badge real: muestra '-' con clase gris.
    expect(screen.getByText('-')).toHaveClass('text-gray-400')
  })
})
