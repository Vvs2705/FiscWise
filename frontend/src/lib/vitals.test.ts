import { describe, expect, it } from 'vitest'
import { scrubPath } from './vitals'

describe('scrubPath (RUM não envia CPF/CNPJ/ids da URL)', () => {
  it('mantém rotas sem números longos', () => {
    expect(scrubPath('/login')).toBe('/login')
    expect(scrubPath('/clientes/42')).toBe('/clientes/42')
  })

  it('mascara CPF, CNPJ (inclusive com "/") e ids longos', () => {
    expect(scrubPath('/clientes/12.345.678/0001-95')).toBe('/clientes/:id')
    expect(scrubPath('/clientes/12345678000195/docs')).toBe('/clientes/:id/docs')
    expect(scrubPath('/x/123.456.789-09')).toBe('/x/:id')
    expect(scrubPath('/fechamento/2026-11')).toBe('/fechamento/2026-11')
  })
})
