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
  /** Preenchidos quando o documento veio de um arquivo enviado. */
  file_name?: string | null;
  file_mime?: string | null;
  file_size?: number | null;
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

export interface RagUploadInput {
  file: File;
  title: string;
  category?: string;
}

/** Envia PDF, DOCX, TXT ou MD (até 20 MB); o texto vira conteúdo da base. */
export function useUploadRagDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ file, title, category }: RagUploadInput) => {
      const form = new FormData();
      form.append('file', file);
      form.append('title', title);
      if (category) form.append('category', category);
      const { data } = await api.post<RagDocument>('/api/v1/rag/documents/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ragKey });
    },
  });
}

/** Link temporário do arquivo original; abre em nova aba. */
export async function downloadRagDocument(id: string): Promise<void> {
  const { data } = await api.get<{ url: string }>(`/api/v1/rag/documents/${id}/download`);
  if (data?.url) window.open(data.url, '_blank', 'noopener,noreferrer');
}
