import { describe, expect, it } from 'vitest';
import { getProfileMissingFields } from './profile';

describe('getProfileMissingFields', () => {
  it('completo com nome, escritório e CNPJ', () => {
    expect(getProfileMissingFields({ full_name: 'Ana Lima' }, { name: 'Lima Contábil', document: '11.222.333/0001-81' })).toEqual([]);
  });
  it('lista o que falta', () => {
    expect(getProfileMissingFields({ full_name: '' }, { name: 'X', document: '' })).toEqual([
      'seu nome',
      'nome do escritório',
      'CNPJ do escritório',
    ]);
    expect(getProfileMissingFields(null, null)).toHaveLength(3);
  });
});
