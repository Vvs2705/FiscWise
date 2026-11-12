import { describe, expect, it } from 'vitest';
import { daysUntil, effectiveStatus, onlyDigits, renewalDefaults, todayISO, type PowerOfAttorney } from './api';

const base: PowerOfAttorney = {
  id: 'p1',
  tenant_id: 't1',
  client_id: 'c1',
  outorgante_cpf_cnpj: '12345678000190',
  outorgante_nome: 'ACME',
  procurador_cpf: '12345678901',
  tipo: 'e-CAC',
  data_validade: '2026-12-31',
  status: 'ativa',
  created_at: '2026-01-01T00:00:00Z',
};

describe('procurações — mapeadores', () => {
  it('onlyDigits remove máscara', () => {
    expect(onlyDigits('123.456.789-01')).toBe('12345678901');
    expect(onlyDigits('12.345.678/0001-90')).toBe('12345678000190');
    expect(onlyDigits(undefined)).toBe('');
  });

  it('todayISO usa o fuso local', () => {
    expect(todayISO(new Date(2026, 10, 12, 23, 30))).toBe('2026-11-12');
  });

  it('daysUntil conta dias corridos sem depender do fuso', () => {
    expect(daysUntil('2026-11-13', '2026-11-12')).toBe(1);
    expect(daysUntil('2026-11-12', '2026-11-12')).toBe(0);
    expect(daysUntil('2026-11-01', '2026-11-12')).toBe(-11);
    expect(daysUntil(null, '2026-11-12')).toBeNull();
  });

  it('effectiveStatus: ativa com validade passada vira vencida; revogada é terminal', () => {
    expect(effectiveStatus(base, '2026-11-12')).toBe('ativa');
    expect(effectiveStatus({ ...base, data_validade: '2026-11-11' }, '2026-11-12')).toBe('vencida');
    expect(effectiveStatus({ ...base, data_validade: undefined }, '2026-11-12')).toBe('ativa');
    expect(effectiveStatus({ ...base, status: 'revogada', data_validade: '2020-01-01' }, '2026-11-12')).toBe('revogada');
    expect(effectiveStatus({ ...base, status: 'vencida' }, '2026-11-12')).toBe('vencida');
  });

  it('renewalDefaults copia partes e reinicia as datas', () => {
    expect(renewalDefaults(base, '2026-11-12')).toEqual({
      client_id: 'c1',
      outorgante_cpf_cnpj: '12345678000190',
      outorgante_nome: 'ACME',
      procurador_cpf: '12345678901',
      tipo: 'e-CAC',
      data_inicio: '2026-11-12',
      data_validade: '',
    });
  });
});
