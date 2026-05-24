import { describe, expect, it } from 'vitest';
import {
  buildDocumentAiView,
  buildClientAiSummaryView,
  type ClientAiSummary,
  type ClientDocument,
} from './aiDocuments';

describe('buildDocumentAiView', () => {
  it('normalizes AI classification and extracted fields from parsed document data', () => {
    const document: ClientDocument = {
      id: 'doc-1',
      tenant_id: 'tenant-1',
      client_id: 'client-1',
      name: 'DAS maio.pdf',
      document_type: 'das',
      status: 'available',
      parse_status: 'completed',
      parsed_data: {
        ai_classification: {
          document_type: 'das',
          competence_month: '2026-05',
          amount: '1250.75',
          due_date: '2026-06-20',
          summary: 'Guia DAS da competencia 05/2026.',
          confidence: 0.86,
          warning: 'Resultado estimado.',
        },
      },
      created_at: '2026-05-24T00:00:00Z',
      updated_at: '2026-05-24T00:00:00Z',
    };

    const view = buildDocumentAiView(document);

    expect(view.parseStatusLabel).toBe('Processado');
    expect(view.hasClassification).toBe(true);
    expect(view.classification?.documentType).toBe('DAS');
    expect(view.classification?.confidenceLabel).toBe('86%');
    expect(view.classification?.fields).toEqual([
      { label: 'Competencia', value: '2026-05' },
      { label: 'Valor', value: '1250.75' },
      { label: 'Vencimento', value: '2026-06-20' },
    ]);
  });

  it('keeps missing AI payloads safe for documents from older endpoints', () => {
    const document: ClientDocument = {
      id: 'doc-2',
      tenant_id: 'tenant-1',
      client_id: 'client-1',
      name: 'Contrato.pdf',
      document_type: 'contrato_social',
      status: 'available',
      created_at: '2026-05-24T00:00:00Z',
      updated_at: '2026-05-24T00:00:00Z',
    };

    const view = buildDocumentAiView(document);

    expect(view.parseStatusLabel).toBe('Nao analisado');
    expect(view.hasClassification).toBe(false);
    expect(view.classification).toBeNull();
  });

  it('accepts top-level AI classification returned by the document schema', () => {
    const document: ClientDocument = {
      id: 'doc-3',
      tenant_id: 'tenant-1',
      client_id: 'client-1',
      name: 'Nota fiscal.xml',
      document_type: 'nota_fiscal',
      status: 'available',
      parse_status: 'completed',
      ai_classification: {
        document_type: 'nota_fiscal',
        summary: 'Nota fiscal classificada pelo backend.',
        confidence: 91,
      },
      created_at: '2026-05-24T00:00:00Z',
      updated_at: '2026-05-24T00:00:00Z',
    };

    const view = buildDocumentAiView(document);

    expect(view.hasClassification).toBe(true);
    expect(view.classification?.documentType).toBe('Nota fiscal');
    expect(view.classification?.confidenceLabel).toBe('91%');
  });
});

describe('buildClientAiSummaryView', () => {
  it('returns displayable summary data when the optional endpoint responds', () => {
    const summary: ClientAiSummary = {
      generated_at: '2026-05-24T10:00:00Z',
      summary: 'Cliente com documentos fiscais em dia.',
      risks: ['Validar vencimento do alvara'],
      next_actions: ['Solicitar certidao atualizada'],
      documents_analyzed: 4,
    };

    const view = buildClientAiSummaryView(summary);

    expect(view.available).toBe(true);
    expect(view.summary).toBe(summary.summary);
    expect(view.risks).toEqual(summary.risks);
    expect(view.nextActions).toEqual(summary.next_actions);
    expect(view.documentsAnalyzedLabel).toBe('4 documentos analisados');
  });

  it('marks the summary as unavailable when the endpoint is absent', () => {
    const view = buildClientAiSummaryView(null);

    expect(view.available).toBe(false);
    expect(view.summary).toBe('Resumo de IA indisponivel para este cliente.');
  });
});
