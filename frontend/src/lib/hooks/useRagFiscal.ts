import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

export interface RagDocument {
  id: string;
  tenant_id: string;
  title: string;
  content: string;
  source: string;
  category: string;
  created_at: string;
  updated_at: string;
}

export interface RagDocumentCreateInput {
  title: string;
  content: string;
  source: string;
  category: string;
}

export interface RagDocumentUpdateInput {
  title?: string;
  content?: string;
  source?: string;
  category?: string;
}

const ragKey = ['rag_fiscal'] as const;

export function useRagDocuments(category?: string) {
  return useQuery({
    queryKey: [...ragKey, 'list', category],
    queryFn: async () => {
      const url = category
        ? `/api/v1/rag/documents?category=${encodeURIComponent(category)}`
        : '/api/v1/rag/documents';
      const { data } = await api.get<RagDocument[]>(url);
      return data;
    },
    staleTime: 5 * 60_000,
    retry: false,
  });
}

export function useCreateRagDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: RagDocumentCreateInput) => {
      const { data } = await api.post<RagDocument>('/api/v1/rag/documents', payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ragKey });
    },
  });
}

export function useUpdateRagDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: RagDocumentUpdateInput }) => {
      const { data } = await api.put<RagDocument>(`/api/v1/rag/documents/${id}`, payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ragKey });
    },
  });
}

export function useDeleteRagDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/v1/rag/documents/${id}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ragKey });
    },
  });
}
