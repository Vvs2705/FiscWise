import { api } from '@/lib/api';

export interface TaxGuideCreate {
  client_id: string;
  tipo: 'DAS' | 'DARF' | 'GPS' | 'ISS' | 'outro';
  competencia: string; // YYYY-MM-DD
  valor: number;
  vencimento: string; // YYYY-MM-DD
  status?: 'pendente' | 'enviada' | 'paga' | 'atrasada';
}

export interface TaxGuideResponse extends TaxGuideCreate {
  id: string;
  tenant_id: string;
  pdf_storage_path?: string;
  comprovante_storage_path?: string;
  enviada_em?: string;
  paga_em?: string;
  created_at: string;
}

export const guiasService = {
  createGuide: async (data: TaxGuideCreate): Promise<TaxGuideResponse> => {
    const res = await api.post<TaxGuideResponse>('/api/v1/guias', data);
    return res.data;
  },

  listGuides: async (params?: { tipo?: string; status?: string; client_id?: string; competencia?: string }): Promise<TaxGuideResponse[]> => {
    const res = await api.get<TaxGuideResponse[]>('/api/v1/guias', { params });
    return res.data;
  },

  getGuide: async (id: string): Promise<TaxGuideResponse> => {
    const res = await api.get<TaxGuideResponse>(`/api/v1/guias/${id}`);
    return res.data;
  },

  uploadPdf: async (id: string, file: File): Promise<TaxGuideResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await api.post<TaxGuideResponse>(`/api/v1/guias/${id}/upload-pdf`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return res.data;
  },

  uploadComprovante: async (id: string, file: File): Promise<TaxGuideResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await api.post<TaxGuideResponse>(`/api/v1/guias/${id}/upload-comprovante`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return res.data;
  },

  markPaid: async (id: string): Promise<TaxGuideResponse> => {
    const res = await api.put<TaxGuideResponse>(`/api/v1/guias/${id}/mark-paid`);
    return res.data;
  },

  getPdfUrl: async (id: string): Promise<{ url: string }> => {
    const res = await api.get<{ url: string }>(`/api/v1/guias/${id}/pdf`);
    return res.data;
  },

  getComprovanteUrl: async (id: string): Promise<{ url: string }> => {
    const res = await api.get<{ url: string }>(`/api/v1/guias/${id}/comprovante`);
    return res.data;
  },

  listPendingReceipts: async (): Promise<TaxGuideResponse[]> => {
    const res = await api.get<TaxGuideResponse[]>('/api/v1/guias/pending-receipt');
    return res.data;
  },
};
