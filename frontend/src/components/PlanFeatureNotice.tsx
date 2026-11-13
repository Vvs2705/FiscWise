import { Link } from 'react-router-dom';
import { Lock } from 'lucide-react';
import { useSubscriptionUsage, useTenantInfo } from '@/lib/hooks/useSubscription';
import { featureLabel, planLacksFeature } from '@/features/subscription/planFeatures';
import { useAuthStore } from '@/stores/authStore';

/**
 * O plano atual não inclui o recurso (`plans.features[key] === false`)?
 * Conta vencida fica de fora: a faixa do teste (TrialBanner) já explica o
 * "só leitura", e esta mensagem diria o contrário ("faça upgrade do plano").
 */
function usePlanLacksFeature(key: string): boolean {
  const role = useAuthStore((s) => s.user?.role);
  const isOffice = !!role && role !== 'client';
  const { data: usage } = useSubscriptionUsage();
  const { data: tenant } = useTenantInfo(isOffice);
  if (!isOffice || tenant?.acesso_expirado) return false;
  return planLacksFeature(usage?.features, key);
}

/** Aviso no topo da tela de um recurso fora do plano. A consulta continua; cadastrar e editar, não. */
export function PlanFeatureNotice({ feature }: { feature: string }) {
  const lacks = usePlanLacksFeature(feature);
  const isOwner = useAuthStore((s) => s.user?.role === 'owner');
  if (!lacks) return null;
  return (
    <div
      role="status"
      className="flex flex-wrap items-center gap-x-3 gap-y-2 rounded-lg border border-warning/40 bg-warning/10 px-4 py-3 text-sm text-foreground"
    >
      <Lock className="h-4 w-4 shrink-0 text-warning" aria-hidden="true" />
      <p className="min-w-0 flex-1">
        <strong className="font-semibold">{featureLabel(feature)} não faz parte do seu plano.</strong>{' '}
        Você pode consultar o que já existe, mas não cadastrar nem editar.{' '}
        {isOwner ? 'Mude de plano para liberar.' : 'Peça ao responsável pelo escritório para mudar de plano.'}
      </p>
      {isOwner && (
        <Link
          to="/assinatura"
          className="inline-flex h-8 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          Ver planos
        </Link>
      )}
    </div>
  );
}
