import { describe, expect, it } from 'vitest';
import { resolveTitle } from './RouteTitle';

describe('resolveTitle', () => {
  it('maps static routes to friendly titles with the brand suffix', () => {
    expect(resolveTitle('/painel')).toBe('Painel · FiscWise');
    expect(resolveTitle('/clientes')).toBe('Clientes · FiscWise');
    expect(resolveTitle('/certificados')).toBe('Certificados · FiscWise');
    expect(resolveTitle('/configuracoes')).toBe('Configurações · FiscWise');
  });

  it('matches dynamic-segment routes', () => {
    expect(resolveTitle('/clientes/abc-123')).toBe('Cliente · FiscWise');
    expect(resolveTitle('/guias/42')).toBe('Guia · FiscWise');
    expect(resolveTitle('/fechamento/xyz')).toBe('Fechamento · FiscWise');
  });

  it('prefers the most specific route over its dynamic counterpart', () => {
    // /notas-fiscais/nova must NOT be swallowed by /notas-fiscais/:id
    expect(resolveTitle('/notas-fiscais/nova')).toBe('Nova Nota Fiscal · FiscWise');
    expect(resolveTitle('/notas-fiscais/99/emitir')).toBe('Emitir Nota Fiscal · FiscWise');
    expect(resolveTitle('/notas-fiscais/99')).toBe('Nota Fiscal · FiscWise');
    expect(resolveTitle('/notas-fiscais')).toBe('Notas Fiscais · FiscWise');
  });

  it('falls back to the brand title for unmapped routes', () => {
    expect(resolveTitle('/rota-inexistente')).toBe('FiscWise — Gestão Contábil Inteligente');
  });
});
