import type { Plan } from '@/lib/hooks/useSubscription';

/** Rótulos das chaves de `plans.features` (backend). Chave desconhecida é humanizada. */
const FEATURE_LABELS: Record<string, string> = {
  calculator: 'Calculadora fiscal',
  ai_chat: 'IA Fiscal',
  pdf_export: 'Exportação em PDF',
  portal_cliente: 'Portal do cliente',
  obrigacoes: 'Motor de obrigações',
  annual_plan: 'Plano anual',
  enterprise: 'Recursos para grandes escritórios',
  migration_assisted: 'Migração assistida',
};

export function featureLabel(key: string): string {
  if (FEATURE_LABELS[key]) return FEATURE_LABELS[key];
  const text = key.replace(/^feature_/, '').replace(/_/g, ' ').trim();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** Lista de recursos do plano montada só com dados do backend (limites + flags ativas). */
export function planFeatureList(plan: Pick<Plan, 'max_clients' | 'max_users' | 'max_ai_calls_month' | 'features'>): string[] {
  const items = [
    plan.max_clients == null ? 'Clientes ilimitados' : `Até ${plan.max_clients} clientes`,
    plan.max_users == null ? 'Usuários ilimitados' : `Até ${plan.max_users} usuários`,
  ];
  if (plan.max_ai_calls_month == null) items.push('IA Fiscal sem limite mensal');
  else if (plan.max_ai_calls_month > 0) items.push(`IA Fiscal (${plan.max_ai_calls_month} mensagens/mês)`);

  for (const [key, enabled] of Object.entries(plan.features ?? {})) {
    if (!enabled || key === 'ai_chat') continue; // IA já descrita pelo limite acima
    items.push(featureLabel(key));
  }
  return items;
}

/** Texto aprovado de cada plano (mesmo da página inicial). O do banco é só reserva. */
const PLAN_COPY: Record<string, string> = {
  intermediario: 'Para escritórios em crescimento: portal do cliente, calendário de obrigações e IA fiscal.',
  premium: 'Sem limite de clientes e usuários, com dossiê em PDF e IA fiscal sem limite mensal.',
  enterprise: 'Para redes e grandes escritórios: migração assistida, SLA dedicado e contrato personalizado.',
};

export function planDescription(plan: Pick<Plan, 'slug' | 'description'>): string | null {
  return PLAN_COPY[plan.slug] ?? plan.description ?? null;
}

/** Plano Gratuito antigo (não existe mais: hoje há teste grátis de 14 dias). */
export function isLegacyFreePlan(plan: Pick<Plan, 'price_monthly'> & { slug?: string }): boolean {
  return plan.slug === 'free' || (plan.price_monthly !== null && Number(plan.price_monthly) === 0);
}

/**
 * Ordem da vitrine: pagos do mais barato ao mais caro, "sob consulta" por último.
 * O plano Gratuito antigo fica de fora (foi trocado pelo teste grátis de 14 dias).
 */
export function sortPlans<T extends Pick<Plan, 'price_monthly'> & { slug?: string }>(plans: T[]): T[] {
  const key = (p: T) => (p.price_monthly === null ? Number.POSITIVE_INFINITY : Number(p.price_monthly));
  return plans.filter((p) => !isLegacyFreePlan(p)).sort((a, b) => key(a) - key(b));
}

/** Preço vindo do backend; nenhum número fixo no frontend. Sem preço = sob consulta. */
export function formatPlanPrice(price: number | string | null | undefined): string {
  if (price === null || price === undefined) return 'Sob consulta';
  if (Number(price) === 0) return 'Grátis';
  return `${Number(price).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}/mês`;
}
