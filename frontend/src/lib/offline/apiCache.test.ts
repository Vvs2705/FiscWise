import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { API_CACHE_NAME, LAST_TENANT_KEY, clearApiCacheIfTenantChanged } from './apiCache';

describe('cache de API do service worker', () => {
  const deleted: string[] = [];
  beforeEach(() => {
    deleted.length = 0;
    const store = new Map<string, string>();
    vi.stubGlobal('localStorage', {
      getItem: (k: string) => store.get(k) ?? null,
      setItem: (k: string, v: string) => void store.set(k, v),
      removeItem: (k: string) => void store.delete(k),
    });
    vi.stubGlobal('caches', { delete: async (name: string) => (deleted.push(name), true) });
  });
  afterEach(() => vi.unstubAllGlobals());

  it('apaga o cache quando entra um escritório diferente do último', async () => {
    await clearApiCacheIfTenantChanged('tenant-a'); // primeiro login no navegador: limpa por precaução
    expect(deleted).toEqual([API_CACHE_NAME]);
    await clearApiCacheIfTenantChanged('tenant-a'); // mesmo escritório: mantém o cache offline
    expect(deleted).toHaveLength(1);
    await clearApiCacheIfTenantChanged('tenant-b');
    expect(deleted).toHaveLength(2);
    expect(localStorage.getItem(LAST_TENANT_KEY)).toBe('tenant-b');
  });
});
