import { describe, it, expect, beforeAll } from 'vitest'
import { render } from '@testing-library/react'
import { FinancieroDonut } from '../SolicitudSheet'

// Recharts usa ResponsiveContainer que requiere dimensiones; jsdom las da en 0.
// Mockeamos ResizeObserver y dimensiones del elemento para que el chart pinte.
beforeAll(() => {
  class ResizeObserverMock {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  ;(globalThis as any).ResizeObserver = ResizeObserverMock
  Object.defineProperty(HTMLElement.prototype, 'offsetHeight', {
    configurable: true,
    value: 80,
  })
  Object.defineProperty(HTMLElement.prototype, 'offsetWidth', {
    configurable: true,
    value: 80,
  })
})

describe('FinancieroDonut', () => {
  it('oferta y coste validos renderiza el bloque con "25.0% margen"', () => {
    const { container, getByText } = render(
      <FinancieroDonut oferta={12000} coste={9000} />,
    )
    // Texto de porcentaje de margen.
    expect(getByText(/25\.0% margen/)).toBeInTheDocument()
    // Etiquetas de coste y margen aparecen.
    expect(getByText(/Coste:/)).toBeInTheDocument()
    expect(getByText(/Margen:/)).toBeInTheDocument()
    // Contenedor con el wrapper visual.
    expect(container.firstChild).not.toBeNull()
  })

  it('oferta=0 no renderiza nada', () => {
    const { container } = render(
      <FinancieroDonut oferta={0} coste={1000} />,
    )
    expect(container.firstChild).toBeNull()
  })

  it('coste=undefined no renderiza nada', () => {
    const { container } = render(
      <FinancieroDonut oferta={10000} coste={undefined as any} />,
    )
    expect(container.firstChild).toBeNull()
  })

  it('coste=null no renderiza nada', () => {
    const { container } = render(
      <FinancieroDonut oferta={10000} coste={null} />,
    )
    expect(container.firstChild).toBeNull()
  })
})
