/**
 * Quem pode ver qual área do app.
 *
 * O app tem duas áreas: a do escritório (equipe: member/admin/owner) e o
 * portal do cliente final (role "client"). O backend já barra o cliente nas
 * rotas da equipe; aqui só evitamos levar cada um para a tela errada.
 */
export type AppArea = 'office' | 'portal';

export const PORTAL_HOME = '/portal/dashboard';
export const PORTAL_LOGIN = '/portal/login';
export const OFFICE_HOME = '/painel';
export const OFFICE_LOGIN = '/login';

/** Para onde redirecionar, ou null quando o acesso é permitido. */
export function areaRedirect(
  area: AppArea,
  isAuthenticated: boolean,
  role: string | null | undefined,
): string | null {
  const isClient = role === 'client';

  if (!isAuthenticated) return area === 'portal' ? PORTAL_LOGIN : OFFICE_LOGIN;
  if (area === 'portal' && !isClient) return OFFICE_HOME;
  if (area === 'office' && isClient) return PORTAL_HOME;
  return null;
}
