import { useMutation, useQueryClient } from '@tanstack/react-query';
import { invoicesService } from '../services/invoices.service';

export function useInvoiceEmission() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      const initRes = await invoicesService.emitInvoice(id);
      return initRes;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      queryClient.invalidateQueries({ queryKey: ['invoice', data.id] });
      queryClient.invalidateQueries({ queryKey: ['invoice-events', data.id] });
    },
  });
}
