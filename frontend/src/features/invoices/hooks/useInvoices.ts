import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { invoicesService, type InvoiceIssuerCreate, type InvoiceCreate, type InvoiceResponse } from '../services/invoices.service';
import { useLocalDb } from '@/lib/offline/hooks';
import { createInvoiceDraft } from '@/lib/offline/repositories';

export function useIssuers() {
  return useQuery({
    queryKey: ['invoice-issuers'],
    queryFn: () => invoicesService.listIssuers(),
  });
}

export function useCreateIssuer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: InvoiceIssuerCreate) => invoicesService.createIssuer(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoice-issuers'] });
    },
  });
}

export function useInvoices(filters?: { status?: string; client_id?: string; competencia?: string }) {
  return useQuery({
    queryKey: ['invoices', filters],
    queryFn: () => invoicesService.listInvoices(filters),
  });
}

/**
 * Nota pela API; com banco local, se a API não responder (offline) ou ainda não
 * conhecer a nota (rascunho criado offline, push pendente), usa a cópia local.
 */
export function useInvoice(id: string) {
  const db = useLocalDb();
  return useQuery({
    queryKey: ['invoice', id],
    queryFn: async (): Promise<InvoiceResponse> => {
      try {
        return await invoicesService.getInvoice(id);
      } catch (error) {
        const fallback = axios.isAxiosError(error) && (!error.response || error.response.status === 404);
        if (db && fallback) {
          const local = await db.invoices.get(id);
          if (local) return local;
        }
        throw error;
      }
    },
    enabled: !!id,
    networkMode: db ? 'always' : 'online',
  });
}

/** Rascunho local-first: com banco local o rascunho nasce offline e sobe pela outbox. */
export function useCreateInvoice() {
  const queryClient = useQueryClient();
  const db = useLocalDb();
  return useMutation({
    mutationFn: (data: InvoiceCreate): Promise<InvoiceResponse> =>
      db ? createInvoiceDraft(db, data) : invoicesService.createInvoice(data),
    networkMode: db ? 'always' : 'online',
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
    },
  });
}

export function useCancelInvoice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      invoicesService.cancelInvoice(id, reason),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      queryClient.invalidateQueries({ queryKey: ['invoice', data.id] });
      queryClient.invalidateQueries({ queryKey: ['invoice-events', data.id] });
    },
  });
}

export function useInvoiceEvents(id: string) {
  return useQuery({
    queryKey: ['invoice-events', id],
    queryFn: () => invoicesService.listEvents(id),
    enabled: !!id,
  });
}

export function useInvoiceRejections(id: string) {
  return useQuery({
    queryKey: ['invoice-rejections', id],
    queryFn: () => invoicesService.listRejections(id),
    enabled: !!id,
  });
}
