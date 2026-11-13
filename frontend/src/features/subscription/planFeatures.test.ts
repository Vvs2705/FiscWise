import { describe, expect, it } from 'vitest';
import {
  PLAN_ROUTE_FEATURES,
  featureLabel,
  formatPlanPrice,
  planFeatureList,
  planLacksFeature,
} from './planFeatures';

describe('planFeatureList', () => {
  it('monta a lista a partir dos limites e flags do backend', () => {
    const list = planFeatureList({
      max_clients: 80,
      max_users: 5,
      max_ai_calls_month: 20,
      features: { calculator: true, ai_chat: true, pdf_export: false, portal_cliente: true },
    });
    expect(list).toEqual([
      'Até 80 clientes',
      'Até 5 usuários',
      'IA Fiscal (20 mensagens/mês)',
      'Calculadora fiscal',
      'Portal do cliente',
    ]);
  });

  it('ilimitado quando o limite é nulo e sem IA quando é zero', () => {
    expect(planFeatureList({ max_clients: null, max_users: null, max_ai_calls_month: null, features: null })).toEqual([
      'Clientes ilimitados',
      'Usuários ilimitados',
      'IA Fiscal sem limite mensal',
    ]);
    expect(planFeatureList({ max_clients: 10, max_users: 2, max_ai_calls_month: 0, features: {} })).toHaveLength(2);
  });

  it('humaniza chave desconhecida', () => {
    expect(featureLabel('feature_nova_coisa')).toBe('Nova coisa');
  });
});

describe('formatPlanPrice', () => {
  it('usa o número do backend', () => {
    expect(formatPlanPrice(0)).toBe('Grátis');
    expect(formatPlanPrice(null)).toBe('Sob consulta');
    expect(formatPlanPrice(123.5)).toMatch(/123,50\/mês$/);
  });
});

describe('planLacksFeature', () => {
  it('só marca fora do plano quando o backend diz false', () => {
    expect(planLacksFeature({ portal_cliente: false }, 'portal_cliente')).toBe(true);
    expect(planLacksFeature({ portal_cliente: true }, 'portal_cliente')).toBe(false);
    // Sem a chave ou sem dados: liberado (mesma regra do backend).
    expect(planLacksFeature({ calculator: true }, 'obrigacoes')).toBe(false);
    expect(planLacksFeature(undefined, 'obrigacoes')).toBe(false);
  });

  it('liga as telas de Obrigações e Portal aos recursos do plano', () => {
    expect(PLAN_ROUTE_FEATURES['/obrigacoes']).toBe('obrigacoes');
    expect(PLAN_ROUTE_FEATURES['/portal']).toBe('portal_cliente');
  });
});

describe('planFeatureList com limite de documentos', () => {
  it('mostra o limite de documentos por cliente quando o plano tem', () => {
    const list = planFeatureList({
      max_clients: 80,
      max_users: 5,
      max_ai_calls_month: 20,
      max_documents_per_client: 100,
      features: {},
    });
    expect(list).toContain('Até 100 documentos por cliente');
    expect(planFeatureList({ max_clients: null, max_users: null, max_ai_calls_month: null, max_documents_per_client: null, features: {} }))
      .not.toContain(expect.stringContaining('documentos'));
  });
});
