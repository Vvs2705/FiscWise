import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { guiasService, type TaxGuideCreate } from '../services/guias.service';

export function useGuides(filters?: { tipo?: string; status?: string; client_id?: string; competencia?: string }) {
  return useQuery({
    queryKey: ['tax-guides', filters],
    queryFn: () => guiasService.listGuides(filters),
  });
}

export function useCreateGuide() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: TaxGuideCreate) => guiasService.createGuide(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tax-guides'] });
      queryClient.invalidateQueries({ queryKey: ['pending-receipts'] });
    },
  });
}

export function useGuide(id: string) {
  return useQuery({
    queryKey: ['tax-guide', id],
    queryFn: () => guiasService.getGuide(id),
    enabled: !!id,
  });
}

export function useUploadPdf() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) =>
      guiasService.uploadPdf(id, file),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['tax-guides'] });
      queryClient.invalidateQueries({ queryKey: ['tax-guide', data.id] });
    },
  });
}

export function useUploadComprovante() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) =>
      guiasService.uploadComprovante(id, file),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['tax-guides'] });
      queryClient.invalidateQueries({ queryKey: ['tax-guide', data.id] });
      queryClient.invalidateQueries({ queryKey: ['pending-receipts'] });
    },
  });
}

export function useMarkPaid() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => guiasService.markPaid(id),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['tax-guides'] });
      queryClient.invalidateQueries({ queryKey: ['tax-guide', data.id] });
      queryClient.invalidateQueries({ queryKey: ['pending-receipts'] });
    },
  });
}

export function usePendingReceipts() {
  return useQuery({
    queryKey: ['pending-receipts'],
    queryFn: () => guiasService.listPendingReceipts(),
  });
}
