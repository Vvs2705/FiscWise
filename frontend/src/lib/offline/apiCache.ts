/**
 * Cache HTTP do service worker com respostas GET da API (OFFLINE_SYNC.md 7.1).
 *
 * O cache é chaveado só pela URL, então é apagado sempre que a sessão acaba
 * (logout explícito, revogação, 401 que desloga) e quando entra um escritório
 * diferente do último neste navegador (navegador compartilhado). Módulo sem
 * Dexie para o interceptor de `api.ts` não puxar o banco local.
 */
export const API_CACHE_NAME = 'fiscwise-api';

/** Último escritório que abriu sessão neste navegador (sobrevive ao logout). */
export const LAST_TENANT_KEY = 'fiscwise_last_tenant_id';

export async function clearApiCache(): Promise<void> {
  try {
    if (typeof caches !== 'undefined') await caches.delete(API_CACHE_NAME);
  } catch {
    // sem Cache Storage (contexto inseguro/teste): nada a limpar
  }
}

/** Antes de abrir a sessão: se o escritório mudou, descarta o cache do anterior. */
export async function clearApiCacheIfTenantChanged(tenantId: string): Promise<void> {
  let last: string | null = null;
  try {
    last = localStorage.getItem(LAST_TENANT_KEY);
  } catch {
    // storage bloqueado: limpa por precaução
  }
  if (last !== tenantId) await clearApiCache();
  try {
    localStorage.setItem(LAST_TENANT_KEY, tenantId);
  } catch {
    // storage bloqueado: na próxima sessão limpa de novo
  }
}
