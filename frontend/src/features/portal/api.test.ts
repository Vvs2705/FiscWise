import { describe, expect, it } from 'vitest';
import { mapPortalPreview } from './api';

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
      { id: 'd1', name: 'Extrato', status: 'pending', requestedAt: '2026-10-01T00:00:00' },
    ]);
    expect(mapped.closing?.score).toBe(40);
    expect(mapped.guides[0]?.value).toBe(120.5);
  });
});
