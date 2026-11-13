import { useEffect, type ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/stores/authStore';
import { getTenantId } from '@/lib/auth';
import './install';

/**
 * Monta a camada offline-first: service worker, banco local do escritório,
 * dispositivo e gatilhos de sincronização. Fica dentro do QueryClientProvider
 * para invalidar as queries quando o banco local muda.
 *
 * O motor offline (Dexie, sincronização, criptografia local) e o registro do
 * service worker vêm sob demanda: assim a tela de login, que não usa nada
 * disso, não baixa esse código antes do primeiro render (LCP do /login).
 * `./install` continua estático porque precisa ouvir o `beforeinstallprompt`
 * desde o início.
 */
export function OfflineProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const role = useAuthStore((s) => s.user?.role);
  const tenantId = isAuthenticated && role !== 'client' ? getTenantId() : null;

  useEffect(() => {
    if (!import.meta.env.PROD) return;
    void import('./pwa').then((m) => m.registerServiceWorker()).catch(() => {});
  }, []);

  useEffect(() => {
    if (!tenantId) return;
    let cancelado = false;
    let parar: (() => void) | undefined;
    void import('./runtime')
      .then(({ startOfflineRuntime }) => {
        if (cancelado) return;
        parar = startOfflineRuntime({
          tenantId,
          onChanged: (entities) => {
            void queryClient.invalidateQueries({ queryKey: ['operations'] });
            if (entities.has('invoice')) {
              void queryClient.invalidateQueries({ queryKey: ['invoices'] });
              void queryClient.invalidateQueries({ queryKey: ['invoice'] });
            }
          },
        });
      })
      .catch(() => {});
    return () => {
      cancelado = true;
      parar?.();
    };
  }, [tenantId, queryClient]);

  return <>{children}</>;
}
