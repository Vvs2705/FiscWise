import { api } from '@/lib/api';

/** Aggregated portal preview returned by GET /api/v1/portal/preview/{clientId}. */

export interface PortalPreviewClosing {
  id: string;
  competence: string; // YYYY-MM
  status: string;
  score: number;
}

export interface PortalPreviewDocument {
  id: string;
  name: string;
  status: string;
  requestedAt: string | null;
}

export interface PortalPreviewGuide {
  id: string;
  type: string;
  competence: string | null;
  value: number;
  due: string | null;
  status: string;
}

export interface PortalPreviewPendency {
  id: string;
  title: string;
  deadline: string | null;
  status: string;
}

export interface PortalPreview {
  client: { id: string; name: string; document: string | null };
  closing: PortalPreviewClosing | null;
  documents: PortalPreviewDocument[];
  guides: PortalPreviewGuide[];
  pendencies: PortalPreviewPendency[];
}

interface ApiPortalPreview {
  client: { id: string; name: string; document: string | null };
  closing: PortalPreviewClosing | null;
  documents: { id: string; name: string; status: string; requested_at: string | null }[];
  guides: PortalPreviewGuide[];
  pendencies: PortalPreviewPendency[];
}

export async function fetchPortalPreview(clientId: string): Promise<PortalPreview> {
  const { data } = await api.get<ApiPortalPreview>(`/api/v1/portal/preview/${clientId}`);
  return {
    client: data.client,
    closing: data.closing,
    documents: data.documents.map(d => ({
      id: d.id,
      name: d.name,
      status: d.status,
      requestedAt: d.requested_at,
    })),
    guides: data.guides,
    pendencies: data.pendencies,
  };
}
