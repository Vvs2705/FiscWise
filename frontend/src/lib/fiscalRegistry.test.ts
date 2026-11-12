import { describe, expect, it } from 'vitest';
import { formatOption, formatRegistryDate, registryBadge } from './fiscalRegistry';

describe('registryBadge', () => {
  it('mapeia as situações cadastrais da Receita', () => {
    expect(registryBadge('ATIVA')).toEqual({ label: 'Ativa', tone: 'success' });
    expect(registryBadge('baixada').tone).toBe('error');
    expect(registryBadge('SUSPENSA').tone).toBe('warning');
    expect(registryBadge('INAPTA').label).toBe('Inapta');
  });

  it('trata ausência e valores desconhecidos sem inventar regularidade', () => {
    expect(registryBadge(null).label).toBe('Não consultada');
    expect(registryBadge('DESCONHECIDA')).toEqual({ label: 'Desconhecida', tone: 'default' });
  });
});

describe('formatRegistryDate', () => {
  it('formata AAAA-MM-DD sem deslocar o dia por fuso', () => {
    expect(formatRegistryDate('2019-05-01')).toBe('01/05/2019');
    expect(formatRegistryDate(null)).toBeNull();
  });
});

describe('formatOption', () => {
  it('distingue sim, não e não informado', () => {
    expect(formatOption(true)).toBe('Sim');
    expect(formatOption(false)).toBe('Não');
    expect(formatOption(null)).toBe('Não informado');
  });
});
