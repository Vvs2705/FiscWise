import { ReactNode } from 'react';
import { Lock } from 'lucide-react';

// Feature flags — em produção viriam do contexto de tenant/plano.
// Por ora, todas as features estão habilitadas (mock/demo).
const ENABLED_FEATURES: Record<string, boolean> = {
  feature_nfse: true,
  feature_ecac: true,
  feature_certificates: true,
  feature_powers_of_attorney: true,
  feature_fiscal_guides: true,
  feature_fiscal_mailbox: true,
  feature_monthly_closing: true,
  feature_fiscal_dossier: true,
  feature_whatsapp: true,
  feature_public_api: false,
  feature_portal_client: true,
  feature_reports: true,
  feature_teams: false,
  feature_advanced_audit: false,
};

interface FeatureGateProps {
  feature: string;
  children: ReactNode;
  fallback?: ReactNode;
  silent?: boolean; // se true, não renderiza nada ao invés do locked state
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

export function useFeatureEnabled(feature: string): boolean {
  return ENABLED_FEATURES[feature] ?? false;
}
