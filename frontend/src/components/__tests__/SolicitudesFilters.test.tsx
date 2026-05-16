/**
 * Tests de SolicitudesFilters.
 *
 * NOTA: el componente NO recibe onChange. Persiste el estado en la URL via
 * useSearchParams. Los tests verifican render y que clickar un boton de estado
 * llama setSearchParams con el valor seleccionado.
 */
import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import SolicitudesFilters from '../SolicitudesFilters'
import type { Usuario, Actuacion } from '../../api/crm'

const usuarios: Usuario[] = [
  { id: 'u1', email: 'a@x.com', nombre: 'Alice', rol: 'comercial', activo: true, iniciales: 'AL', color: '#ff0000' } as Usuario,
]
const actuaciones: Actuacion[] = [
  { id: 'fachada', nombre: 'Fachada', orden: 10, activo: true } as Actuacion,
]

function renderWithRouter(initialUrl = '/') {
  return render(
    <MemoryRouter initialEntries={[initialUrl]}>
      <SolicitudesFilters usuarios={usuarios} actuaciones={actuaciones} />
    </MemoryRouter>,
  )
}

describe('SolicitudesFilters', () => {
  it('renderiza los 5 botones de estado', () => {
    renderWithRouter()
    for (const estado of [
      'En Estudio',
      'Enviada',
      'Adjudicada',
      'Rechazada',
      'Descartada',
    ]) {
      expect(screen.getByRole('button', { name: estado })).toBeInTheDocument()
    }
  })

  it('renderiza la cabecera "Filtros" y la seccion Prioridad', () => {
    renderWithRouter()
    expect(screen.getByText('Filtros')).toBeInTheDocument()
    expect(screen.getByText('Prioridad')).toBeInTheDocument()
  })

  it('seleccionar dos estados refleja "2 activos" y muestra chips de filtro', () => {
    renderWithRouter('/?estado=Enviada&estado=Adjudicada')
    // Aparece el contador de filtros activos.
    expect(screen.getByText(/2 activos/i)).toBeInTheDocument()
    // Aparece el boton "Limpiar filtros".
    expect(screen.getByRole('button', { name: /limpiar/i })).toBeInTheDocument()
    // Chips activos visibles.
    expect(screen.getByText('Estado: Enviada')).toBeInTheDocument()
    expect(screen.getByText('Estado: Adjudicada')).toBeInTheDocument()
  })

  it('click en un estado dispara cambio en la URL', () => {
    renderWithRouter()
    const btn = screen.getByRole('button', { name: 'Enviada' })
    fireEvent.click(btn)
    // Tras el click, el componente vuelve a renderizar con el estado activo;
    // como el estado vive en useSearchParams, la chip "Estado: Enviada" debe
    // aparecer en el bloque de chips activos.
    expect(screen.getByText('Estado: Enviada')).toBeInTheDocument()
  })

  it('boton limpiar quita todos los chips activos', () => {
    renderWithRouter('/?estado=Enviada&prioridad=alta')
    expect(screen.getByText('Estado: Enviada')).toBeInTheDocument()
    const limpiar = screen.getByRole('button', { name: /limpiar/i })
    fireEvent.click(limpiar)
    expect(screen.queryByText('Estado: Enviada')).not.toBeInTheDocument()
    expect(screen.queryByText('Prioridad: alta')).not.toBeInTheDocument()
  })
})
