// Funções utilitárias de feature flags — exportadas separadamente para compatibilidade com react-refresh

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

export function useFeatureEnabled(feature: string): boolean {
  return ENABLED_FEATURES[feature] ?? false;
}

export function isFeatureEnabled(feature: string): boolean {
  return ENABLED_FEATURES[feature] ?? false;
}

export { ENABLED_FEATURES };
