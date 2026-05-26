import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ecacService, type EcacProxyCreate } from '../services/ecac.service';

export function useProxies() {
  return useQuery({
    queryKey: ['ecac-proxies'],
    queryFn: () => ecacService.listProxies(),
  });
}

export function useCreateProxy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: EcacProxyCreate) => ecacService.createProxy(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ecac-proxies'] });
      queryClient.invalidateQueries({ queryKey: ['ecac-clients-without-proxy'] });
    },
  });
}

export function useProxy(id: string) {
  return useQuery({
    queryKey: ['ecac-proxy', id],
    queryFn: () => ecacService.getProxy(id),
    enabled: !!id,
  });
}

export function useUpdateProxy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<EcacProxyCreate> }) =>
      ecacService.updateProxy(id, data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['ecac-proxies'] });
      queryClient.invalidateQueries({ queryKey: ['ecac-proxy', data.id] });
      queryClient.invalidateQueries({ queryKey: ['ecac-clients-without-proxy'] });
    },
  });
}

export function useExpiringProxies() {
  return useQuery({
    queryKey: ['ecac-proxies-expiring'],
    queryFn: () => ecacService.listExpiringProxies(),
  });
}

export function useFiscalSituation(clientId: string) {
  return useQuery({
    queryKey: ['ecac-fiscal-situation', clientId],
    queryFn: () => ecacService.getFiscalSituation(clientId),
    enabled: !!clientId,
  });
}

export function useRefreshFiscalSituation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (clientId: string) => ecacService.refreshFiscalSituation(clientId),
    onSuccess: (_, clientId) => {
      queryClient.invalidateQueries({ queryKey: ['ecac-fiscal-situation', clientId] });
    },
  });
}

export function useClientsWithoutProxy() {
  return useQuery({
    queryKey: ['ecac-clients-without-proxy'],
    queryFn: () => ecacService.listClientsWithoutProxy(),
  });
}
