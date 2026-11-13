import type { Plan } from '@/lib/hooks/useSubscription';
import { formatPlanPrice, planDescription, planFeatureList, sortPlans } from './planFeatures';

/*
 * HTML dos cards da página estática /precos (precos.html).
 *
 * A mesma função roda em dois lugares, para o resultado ser idêntico:
 * - no build (vite.config.ts, plugin precosPrerender): pré-renderiza com o
 *   catálogo que a API devolve naquele momento, para buscadores e prévias;
 * - no navegador (src/precos.ts): busca o catálogo de novo e substitui, então
 *   o visitante sempre vê o preço atual do banco.
 * Nenhum preço fixo aqui: tudo vem de GET /api/v1/subscription/plans.
 */

const ESCAPES: Record<string, string> = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

export function escapeHtml(value: unknown): string {
  return String(value ?? '').replace(/[&<>"']/g, (c) => ESCAPES[c]);
}

const BRL = (n: number) => n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

function planCard(plan: Plan): string {
  const price = plan.price_monthly === null ? null : Number(plan.price_monthly);
  const isCustom = price === null;
  const pixRow = plan.tabela_precos?.find((l) => l.ciclo === 'anual');
  const description = planDescription(plan);

  const cta = isCustom
    ? `<a class="btn btn-outline" href="mailto:contato@vstack-solutions.com.br?subject=Plano%20Enterprise%20FiscWise">Falar com a equipe</a>`
    : `<a class="btn btn-primary" href="/register">Começar teste grátis</a>`;

  return [
    '<li class="card">',
    `<h2>${escapeHtml(plan.name)}</h2>`,
    `<p class="price">${escapeHtml(isCustom ? 'Sob consulta' : formatPlanPrice(price))}</p>`,
    pixRow && pixRow.desconto_pix_pct > 0
      ? `<p class="muted">ou ${escapeHtml(BRL(pixRow.pix_total))} por ano no Pix (${escapeHtml(pixRow.desconto_pix_pct)}% de desconto)</p>`
      : '',
    description ? `<p class="muted desc">${escapeHtml(description)}</p>` : '',
    '<ul class="features">',
    ...planFeatureList(plan).map((f) => `<li>${escapeHtml(f)}</li>`),
    '</ul>',
    cta,
    '</li>',
  ].join('');
}

/** Lista de cards na ordem da vitrine. Vazio quando o catálogo veio vazio. */
export function renderPlanCards(plans: Plan[]): string {
  const visible = sortPlans(plans);
  if (visible.length === 0) return '';
  return `<ul class="plans">${visible.map(planCard).join('')}</ul>`;
}

/** Bloco mostrado enquanto (ou quando não) dá para carregar o catálogo. */
export function renderPlansFallback(state: 'loading' | 'error'): string {
  const text =
    state === 'loading'
      ? 'Carregando os planos...'
      : 'Não conseguimos carregar os preços agora. Comece seu teste grátis de 14 dias e veja os planos dentro do sistema.';
  return `<div class="card notice"${state === 'loading' ? ' aria-busy="true"' : ''}><p class="muted">${text}</p><a class="btn btn-primary" href="/register">Testar grátis por 14 dias</a></div>`;
}
