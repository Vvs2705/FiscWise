import { describe, expect, it } from 'vitest';
import { areaRedirect } from './access';

describe('areaRedirect', () => {
  it('manda quem não está logado para o login da área', () => {
    expect(areaRedirect('office', false, null)).toBe('/login');
    expect(areaRedirect('portal', false, null)).toBe('/portal/login');
  });

  it('cliente do portal não entra na área do escritório', () => {
    expect(areaRedirect('office', true, 'client')).toBe('/portal/dashboard');
    expect(areaRedirect('portal', true, 'client')).toBeNull();
  });

  it('equipe do escritório não cai no portal do cliente', () => {
    for (const role of ['member', 'admin', 'owner']) {
      expect(areaRedirect('office', true, role)).toBeNull();
      expect(areaRedirect('portal', true, role)).toBe('/painel');
    }
  });
});
