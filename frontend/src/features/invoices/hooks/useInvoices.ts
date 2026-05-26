import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { invoicesService, type InvoiceIssuerCreate, type InvoiceCreate } from '../services/invoices.service';

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

export function useInvoice(id: string) {
  return useQuery({
    queryKey: ['invoice', id],
    queryFn: () => invoicesService.getInvoice(id),
    enabled: !!id,
  });
}

export function useCreateInvoice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: InvoiceCreate) => invoicesService.createInvoice(data),
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
