import { describe, expect, it } from 'vitest';
import { describePortalAccessResult, isAwaitingClient, mapPortalPreview } from './api';

describe('mapPortalPreview', () => {
  it('converte requested_at para requestedAt e mantém o resto', () => {
    const mapped = mapPortalPreview({
      client: { id: 'c1', name: 'Padaria Boa', document: null },
      closing: { id: 'm1', competence: '2026-09', status: 'in_progress', score: 40 },
      documents: [{ id: 'd1', name: 'Extrato', status: 'pending', requested_at: '2026-10-01T00:00:00' }],
      guides: [{ id: 'g1', type: 'DAS', competence: '2026-09-01', value: 120.5, due: '2026-10-20', status: 'pending' }],
      pendencies: [],
    });

    expect(mapped.documents).toEqual([
      {
        id: 'd1', kind: 'document', name: 'Extrato', status: 'pending',
        requestedAt: '2026-10-01T00:00:00', competence: null, notes: null, fileUrl: null, canUpload: false,
      },
    ]);
    expect(mapped.closing?.score).toBe(40);
    expect(mapped.guides[0]?.value).toBe(120.5);
  });
});

describe('describePortalAccessResult', () => {
  const base = { email: 'c@x.com', expires_at: '2026-11-13T00:00:00Z' };

  it('enviado por e-mail não expõe link', () => {
    const out = describePortalAccessResult({ ...base, sent: true, delivery: 'email' });
    expect(out).toEqual({ kind: 'sent', message: 'Link de acesso enviado para c@x.com.' });
  });

  it('modo manual devolve o link para copiar', () => {
    const out = describePortalAccessResult({
      ...base, sent: false, delivery: 'manual', portal_link: 'https://x/portal/login?token=t',
    });
    expect(out.kind).toBe('manual');
    expect(out.kind === 'manual' && out.link).toBe('https://x/portal/login?token=t');
  });

  it('falha do provedor mostra o motivo', () => {
    const out = describePortalAccessResult({ ...base, sent: false, delivery: 'email', reason: 'Recusado' });
    expect(out).toEqual({ kind: 'failed', message: 'Recusado' });
  });
});

describe('isAwaitingClient', () => {
  it('pedido em aberto conta como pendente; recebido não', () => {
    expect(isAwaitingClient({ status: 'missing', canUpload: true })).toBe(true);
    expect(isAwaitingClient({ status: 'expired', canUpload: false })).toBe(true);
    expect(isAwaitingClient({ status: 'review', canUpload: false })).toBe(false);
    expect(isAwaitingClient({ status: 'available', canUpload: false })).toBe(false);
  });
});
