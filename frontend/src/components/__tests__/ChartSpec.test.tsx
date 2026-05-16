import { describe, it, expect, beforeAll } from 'vitest'
import { render } from '@testing-library/react'
import ChartSpec from '../ChartSpec'
import type { ChartSpec as ChartSpecType } from '../../api/ai'


// Recharts ResponsiveContainer requiere dimensiones; jsdom las da en 0.
// Mockeamos lo minimo para que los charts pinten en los tests.
beforeAll(() => {
  class ResizeObserverMock {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  ;(globalThis as any).ResizeObserver = ResizeObserverMock
  Object.defineProperty(HTMLElement.prototype, 'offsetHeight', {
    configurable: true,
    value: 200,
  })
  Object.defineProperty(HTMLElement.prototype, 'offsetWidth', {
    configurable: true,
    value: 320,
  })
})


describe('ChartSpec', () => {
  it('renderiza el contenedor de un bar chart con datos', () => {
    const spec: ChartSpecType = {
      type: 'bar',
      title: 'Estados',
      data: [
        { name: 'En Estudio', value: 5 },
        { name: 'Enviada', value: 3 },
      ],
      x: 'name',
      y: 'value',
    }
    const { getByText, getByTestId } = render(<ChartSpec spec={spec} />)
    // El titulo y el wrapper se renderizan; la pintura del SVG depende
    // de que ResponsiveContainer reciba dimensiones reales (no garantizado
    // en jsdom), pero esto confirma que el chart NO cayo al fallback de
    // datos insuficientes.
    expect(getByText('Estados')).toBeInTheDocument()
    expect(getByTestId('chart-spec-bar')).toBeInTheDocument()
  })

  it('renderiza una KPI card con valor 42', () => {
    const spec: ChartSpecType = {
      type: 'kpi',
      title: 'Margen medio',
      data: [{ name: '%', value: 42 }],
      x: 'name',
      y: 'value',
    }
    const { getByText, getByTestId } = render(<ChartSpec spec={spec} />)
    expect(getByText('Margen medio')).toBeInTheDocument()
    expect(getByText('42')).toBeInTheDocument()
    expect(getByTestId('chart-spec-kpi')).toBeInTheDocument()
  })

  it('renderiza fallback con data vacia', () => {
    const spec: ChartSpecType = {
      type: 'donut',
      title: 'Mix actuaciones',
      data: [],
      x: 'name',
      y: 'value',
    }
    const { getByText } = render(<ChartSpec spec={spec} />)
    expect(getByText(/Datos insuficientes/i)).toBeInTheDocument()
  })

  it('renderiza fallback cuando los valores son null', () => {
    const spec: ChartSpecType = {
      type: 'line',
      title: 'Tendencia',
      data: [{ name: 'a', value: null as unknown as number }],
      x: 'name',
      y: 'value',
    }
    const { getByText } = render(<ChartSpec spec={spec} />)
    expect(getByText(/Datos insuficientes/i)).toBeInTheDocument()
  })
})
