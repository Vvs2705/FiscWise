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

/** Preço vindo do backend; nenhum número fixo no frontend. */
export function formatPlanPrice(price: number | string | null | undefined): string {
  if (price === null || price === undefined || Number(price) === 0) return 'Grátis';
  return `${Number(price).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}/mês`;
}
