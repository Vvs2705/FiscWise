import { api } from '@/lib/api';

export interface InvoiceIssuerCreate {
  cnpj: string;
  inscricao_municipal?: string;
  regime_tributario: string;
  municipio_ibge: string;
  cod_servico_lc116?: string;
  aliquota_iss?: number;
  retencao_iss?: boolean;
}

export interface InvoiceIssuerResponse extends InvoiceIssuerCreate {
  id: string;
  tenant_id: string;
  created_at: string;
  updated_at: string;
}

export interface InvoiceCreate {
  issuer_id: string;
  client_id?: string;
  valor_servico: number;
  valor_deducoes?: number;
  valor_iss?: number;
  descricao_servico: string;
  competencia: string; // YYYY-MM-DD
  tomador_nome?: string;
  tomador_cpf_cnpj?: string;
  tomador_email?: string;
  tomador_municipio_ibge?: string;
}

export interface InvoiceResponse extends InvoiceCreate {
  id: string;
  tenant_id: string;
  status: string;
  numero?: string;
  serie?: string;
  provider_protocol?: string;
  pdf_storage_path?: string;
  xml_storage_path?: string;
  /** Emitida/cancelada pelo provider simulado: sem valor fiscal. */
  simulated?: boolean;
  issued_at?: string;
  cancelled_at?: string;
  created_at: string;
  updated_at: string;
}

export interface InvoiceEventResponse {
  id: string;
  invoice_id: string;
  event_type: string;
  payload?: unknown;
  created_at: string;
}

export interface InvoiceRejectionResponse {
  id: string;
  invoice_id: string;
  codigo_rejeicao?: string;
  descricao: string;
  created_at: string;
}

/** Os endpoints exigem os headers de autenticação, então um <a href> simples não serve. */
async function downloadInvoiceFile(path: string, fileName: string): Promise<void> {
  const { data } = await api.get<Blob>(path, { responseType: 'blob' });
  const url = window.URL.createObjectURL(data);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}

/** Erro de download vem como Blob: extrai o "detail" do JSON para a mensagem. */
export async function downloadErrorMessage(err: unknown, fallback: string): Promise<string> {
  const data = (err as { response?: { data?: unknown } })?.response?.data;
  if (data instanceof Blob) {
    try {
      const parsed = JSON.parse(await data.text()) as { detail?: unknown };
      if (typeof parsed.detail === 'string') return parsed.detail;
    } catch {
      return fallback;
    }
  }
  return fallback;
}

export const invoicesService = {
  createIssuer: async (data: InvoiceIssuerCreate): Promise<InvoiceIssuerResponse> => {
    const res = await api.post<InvoiceIssuerResponse>('/api/v1/invoices/issuers', data);
    return res.data;
  },

  listIssuers: async (): Promise<InvoiceIssuerResponse[]> => {
    const res = await api.get<InvoiceIssuerResponse[]>('/api/v1/invoices/issuers');
    return res.data;
  },

  createInvoice: async (data: InvoiceCreate): Promise<InvoiceResponse> => {
    const res = await api.post<InvoiceResponse>('/api/v1/invoices', data);
    return res.data;
  },

  listInvoices: async (params?: { status?: string; client_id?: string; competencia?: string }): Promise<InvoiceResponse[]> => {
    const res = await api.get<InvoiceResponse[]>('/api/v1/invoices', { params });
    return res.data;
  },

  getInvoice: async (id: string): Promise<InvoiceResponse> => {
    const res = await api.get<InvoiceResponse>(`/api/v1/invoices/${id}`);
    return res.data;
  },

  emitInvoice: async (id: string): Promise<InvoiceResponse> => {
    const res = await api.post<InvoiceResponse>(`/api/v1/invoices/${id}/emit`);
    return res.data;
  },

  cancelInvoice: async (id: string, reason: string): Promise<InvoiceResponse> => {
    const res = await api.post<InvoiceResponse>(`/api/v1/invoices/${id}/cancel`, { reason });
    return res.data;
  },

  /** Baixa o DANFSe (PDF gerado pelo backend) pelo cliente autenticado. */
  downloadPdf: async (id: string, numero?: string): Promise<void> => {
    await downloadInvoiceFile(`/api/v1/invoices/${id}/pdf`, `nfse-${numero || id}.pdf`);
  },

  /** Baixa o XML da nota guardado no banco. */
  downloadXml: async (id: string, numero?: string): Promise<void> => {
    await downloadInvoiceFile(`/api/v1/invoices/${id}/xml`, `nfse-${numero || id}.xml`);
  },

  listEvents: async (id: string): Promise<InvoiceEventResponse[]> => {
    const res = await api.get<InvoiceEventResponse[]>(`/api/v1/invoices/${id}/events`);
    return res.data;
  },

  listRejections: async (id: string): Promise<InvoiceRejectionResponse[]> => {
    const res = await api.get<InvoiceRejectionResponse[]>(`/api/v1/invoices/${id}/rejections`);
    return res.data;
  },
};
