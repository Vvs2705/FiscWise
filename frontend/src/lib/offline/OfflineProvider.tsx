import { useEffect, type ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/stores/authStore';
import { getTenantId } from '@/lib/auth';
import { registerServiceWorker } from './pwa';
import { startOfflineRuntime } from './runtime';
import './install';

/**
 * Monta a camada offline-first: service worker, banco local do escritório,
 * dispositivo e gatilhos de sincronização. Fica dentro do QueryClientProvider
 * para invalidar as queries quando o banco local muda.
 */
export function OfflineProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const role = useAuthStore((s) => s.user?.role);
  const tenantId = isAuthenticated && role !== 'client' ? getTenantId() : null;

  useEffect(() => {
    if (import.meta.env.PROD) registerServiceWorker();
  }, []);

  useEffect(() => {
    if (!tenantId) return;
    return startOfflineRuntime({
      tenantId,
      onChanged: (entities) => {
        void queryClient.invalidateQueries({ queryKey: ['operations'] });
        if (entities.has('invoice')) {
          void queryClient.invalidateQueries({ queryKey: ['invoices'] });
          void queryClient.invalidateQueries({ queryKey: ['invoice'] });
        }
      },
    });
  }, [tenantId, queryClient]);

  return <>{children}</>;
}
