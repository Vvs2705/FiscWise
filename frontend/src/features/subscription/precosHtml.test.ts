import { describe, expect, it } from 'vitest';
import type { Plan } from '@/lib/hooks/useSubscription';
import { renderPlanCards, renderPlansFallback } from './precosHtml';

const plan = (over: Partial<Plan>): Plan => ({
  id: over.slug ?? 'x', slug: 'x', name: 'X', description: null, price_monthly: 0,
  max_clients: 10, max_users: 2, max_ai_calls_month: 0, features: {}, tabela_precos: null, ...over,
});

describe('renderPlanCards', () => {
  it('ordena como a vitrine e usa só os preços recebidos', () => {
    const html = renderPlanCards([
      plan({ slug: 'enterprise', name: 'Enterprise', price_monthly: null }),
      plan({ slug: 'premium', name: 'Premium', price_monthly: 349 }),
      plan({ slug: 'free', name: 'Gratuito', price_monthly: 0 }),
    ]);
    const order = ['Premium', 'Enterprise'].map((n) => html.indexOf(`<h2>${n}</h2>`));
    expect(order).toEqual([...order].sort((a, b) => a - b));
    // O Gratuito antigo saiu da vitrine: hoje há teste grátis de 14 dias.
    expect(html).not.toContain('<h2>Gratuito</h2>');
    expect(html).toContain('Começar teste grátis');
    expect(html).toMatch(/R\$\s349,00\/mês/);
    expect(html).toContain('href="/register"');
    expect(html).toContain('Sob consulta');
  });

  it('escapa texto vindo do banco', () => {
    const html = renderPlanCards([plan({ slug: 'novo', name: '<img src=x onerror=alert(1)>', price_monthly: 10 })]);
    expect(html).not.toContain('<img');
    expect(html).toContain('&lt;img src=x onerror=alert(1)&gt;');
  });

  it('catálogo vazio não gera lista; aviso de carregamento fica ocupado', () => {
    expect(renderPlanCards([])).toBe('');
    expect(renderPlansFallback('loading')).toContain('aria-busy="true"');
    expect(renderPlansFallback('error')).not.toContain('aria-busy');
  });
});
