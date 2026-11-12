import { ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { Lock } from 'lucide-react';
import { ENABLED_FEATURES } from '@/lib/featureFlags';

interface FeatureGateProps {
  feature: string;
  children: ReactNode;
  fallback?: ReactNode;
  silent?: boolean;
}

function LockedFeature({ feature }: { feature: string }) {
  const navigate = useNavigate();
  const labels: Record<string, string> = {
    feature_public_api: 'API Pública',
    feature_teams: 'Times e Carteiras',
    feature_advanced_audit: 'Auditoria Avançada',
  };
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-border bg-muted/40 p-8 text-center">
      <div className="flex h-10 w-10 items-center justify-center rounded-md bg-muted">
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
      <button type="button" onClick={() => navigate('/configuracoes')} className="mt-1 inline-flex h-8 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground shadow-sm transition-colors duration-100 hover:bg-primary/90 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2">
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
