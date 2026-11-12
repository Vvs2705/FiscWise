/** Perfil do escritório pronto para operar: nome do usuário, razão social e CNPJ do escritório. */
export function getProfileMissingFields(
  user: { full_name?: string | null } | null | undefined,
  tenant: { name?: string | null; document?: string | null } | null | undefined,
): string[] {
  const missing: string[] = [];
  if (!user?.full_name || user.full_name.trim().length < 2) missing.push('seu nome');
  if (!tenant?.name || tenant.name.trim().length < 2) missing.push('nome do escritório');
  const digits = (tenant?.document ?? '').replace(/\D/g, '');
  if (digits.length !== 14 && digits.length !== 11) missing.push('CNPJ do escritório');
  return missing;
}
