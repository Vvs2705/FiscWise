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
    feature_monthly_closing: 'Fechamento mensal',
    feature_portal_client: 'Portal do cliente',
  };
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-border bg-muted/40 p-8 text-center">
      <div className="flex h-10 w-10 items-center justify-center rounded-md bg-muted">
        <Lock className="h-5 w-5 text-muted-foreground" />
      </div>
      <div>
        <p className="text-sm font-medium text-foreground">
          {labels[feature] ?? 'Este recurso'} ainda não está disponível
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          Estamos preparando esta parte do FiscWise. Ela aparece aqui assim que for liberada.
        </p>
      </div>
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
