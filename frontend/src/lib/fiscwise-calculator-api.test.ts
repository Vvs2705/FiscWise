import { describe, expect, it, vi } from 'vitest';

vi.mock('./api', () => ({ api: { post: vi.fn(), get: vi.fn() } }));

import {
  buildRegimePayload,
  canExportPdf,
  isValidCnae,
  mapRegimeResponse,
  mapSimulationItem,
  normalizeCalculatorPlan,
  type ApiSimulationItem,
} from './fiscwise-calculator-api';

const scenarios = [
  { regime: 'simples_nacional', total_tax: 7200, effective_rate: 0.06, tax_breakdown: {}, is_recommended: true },
  { regime: 'lucro_presumido', total_tax: 13596, effective_rate: 0.1133, tax_breakdown: {} },
  { regime: 'lucro_real', total_tax: 18000, effective_rate: 0.15, tax_breakdown: {} },
];

describe('buildRegimePayload', () => {
  it('sends the CNAE typed by the user (digits only) instead of a fixed value', () => {
    const p = buildRegimePayload({ monthly_revenue: 10000, annual_cogs: 5000, activity_code: '4711-3/02' });
    expect(p).toMatchObject({ annual_revenue: 120000, annual_costs: 5000, activity_code: '4711302' });
  });

  it('omits activity_code when empty and never sends fields the backend does not accept', () => {
    const p = buildRegimePayload({ monthly_revenue: 1000, annual_cogs: 0, activity_code: '' });
    expect(p).not.toHaveProperty('activity_code');
    expect(p).not.toHaveProperty('state');
    expect(p).not.toHaveProperty('has_pis_cofins_credit');
  });
});

describe('isValidCnae', () => {
  it('accepts 7 digits with or without mask', () => {
    expect(isValidCnae('6201500')).toBe(true);
    expect(isValidCnae('6201-5/00')).toBe(true);
    expect(isValidCnae('620150')).toBe(false);
    expect(isValidCnae('62a1500')).toBe(false);
  });
});

describe('mapRegimeResponse', () => {
  it('keeps ai_recommendation from the backend', () => {
    const r = mapRegimeResponse(
      { monthly_revenue: 10000, annual_cogs: 0 },
      { scenarios, ai_recommendation: 'Fique no Simples.' },
    );
    expect(r.ai_recommendation).toBe('Fique no Simples.');
    expect(r.recommended_regime).toBe('Simples Nacional');
    expect(r.annual_savings).toBe(18000 - 7200);
  });

  it('maps missing ai_recommendation to null', () => {
    const r = mapRegimeResponse({ monthly_revenue: 1, annual_cogs: 0 }, { scenarios });
    expect(r.ai_recommendation).toBeNull();
  });
});

describe('mapSimulationItem', () => {
  it('maps fator_r history from the saved payload (not N/A / 0)', () => {
    const item: ApiSimulationItem = {
      id: 's1',
      created_at: '2026-11-12T10:00:00Z',
      simulation_type: 'fator_r',
      input_data: { months: [{ revenue: 30000 }, { revenue: 30000 }] },
      result_data: {
        rbt12: 360000,
        anexo: 'III',
        total_das_anual: 21600,
        monthly_details: [{ aliquota_efetiva: 0.06 }],
        comparison: { anexo: 'V', aliquota_efetiva: 0.155, total_das_anual: 55800, diferenca_anual: -34200 },
      },
    };
    const sim = mapSimulationItem(item);
    expect(sim.revenue).toBe(360000);
    expect(sim.regime).toBe('Simples Nacional - Anexo III');
    expect(sim.annual_savings).toBe(34200);
    expect(sim.result.scenarios.map((s) => s.regime)).toEqual([
      'Simples Nacional - Anexo III',
      'Simples Nacional - Anexo V',
    ]);
    expect(sim.result.scenarios[0].annual_tax).toBe(21600);
  });

  it('falls back to the sum of month revenues when rbt12 is absent', () => {
    const sim = mapSimulationItem({
      id: 's2',
      created_at: '2026-11-12T10:00:00Z',
      simulation_type: 'fator_r',
      input_data: { months: [{ revenue: '1000' }, { revenue: 2000 }] },
      result_data: { anexo: 'V' },
    });
    expect(sim.revenue).toBe(3000);
    expect(sim.annual_savings).toBe(0);
  });

  it('still maps regime simulations', () => {
    const sim = mapSimulationItem({
      id: 's3',
      created_at: '2026-11-12T10:00:00Z',
      simulation_type: 'regime',
      input_data: { annual_revenue: 120000, annual_costs: 1000 },
      result_data: { scenarios },
    });
    expect(sim.regime).toBe('Simples Nacional');
    expect(sim.revenue).toBe(120000);
    expect(sim.result.cogs).toBe(1000);
  });
});

describe('plan helpers', () => {
  it('normalizes effective plan slugs and gates PDF to Premium', () => {
    expect(normalizeCalculatorPlan('premium')).toBe('PREMIUM');
    expect(normalizeCalculatorPlan('intermediario')).toBe('INTERMEDIARIO');
    expect(normalizeCalculatorPlan('basico')).toBe('FREE');
    expect(normalizeCalculatorPlan(undefined)).toBe('FREE');
    expect(canExportPdf('PREMIUM')).toBe(true);
    expect(canExportPdf('INTERMEDIARIO')).toBe(false);
  });
});
