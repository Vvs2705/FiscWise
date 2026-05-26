import { ReactNode } from 'react';
import { Lock } from 'lucide-react';
import { ENABLED_FEATURES } from '@/lib/featureFlags';

interface FeatureGateProps {
  feature: string;
  children: ReactNode;
  fallback?: ReactNode;
  silent?: boolean;
}

function LockedFeature({ feature }: { feature: string }) {
  const labels: Record<string, string> = {
    feature_public_api: 'API Pública',
    feature_teams: 'Times e Carteiras',
    feature_advanced_audit: 'Auditoria Avançada',
  };
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border bg-muted/30 p-8 text-center">
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted">
        <Lock className="h-5 w-5 text-muted-foreground" />
      </div>
      <div>
        <p className="text-sm font-medium text-foreground">
          {labels[feature] ?? 'Funcionalidade'} não disponível no seu plano
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          Faça upgrade para desbloquear este recurso.
        </p>
      </div>
      <button className="mt-1 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground hover:opacity-90 transition-opacity">
        Ver planos
      </button>
    </div>
  );
}

export function FeatureGate({ feature, children, fallback, silent }: FeatureGateProps) {
  const enabled = ENABLED_FEATURES[feature] ?? false;
  if (enabled) return <>{children}</>;
  if (silent) return null;
  if (fallback) return <>{fallback}</>;
  return <LockedFeature feature={feature} />;
}
