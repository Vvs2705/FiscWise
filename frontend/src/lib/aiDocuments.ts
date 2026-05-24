export interface AiField {
  label: string;
  value: string;
}

export interface AiDocumentClassification {
  documentType: string;
  summary: string | null;
  confidenceLabel: string | null;
  warning: string | null;
  fields: AiField[];
  tokensUsed: number | null;
  piiMasked: boolean;
}

export interface DocumentAiView {
  parseStatus: string;
  parseStatusLabel: string;
  parseStatusVariant: 'default' | 'info' | 'success' | 'warning' | 'error';
  hasClassification: boolean;
  classification: AiDocumentClassification | null;
  parseError: string | null;
}

export interface ClientDocument {
  id: string;
  tenant_id: string;
  client_id: string;
  name: string;
  document_type: string;
  status: string;
  file_url?: string | null;
  issued_at?: string | null;
  expires_at?: string | null;
  notes?: string | null;
  parse_status?: string | null;
  parsed_data?: Record<string, unknown> | null;
  ai_classification?: Record<string, unknown> | null;
  parse_error?: string | null;
  parsed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ClientAiSummary {
  client_id?: string;
  generated_at?: string | null;
  summary?: string | null;
  risks?: string[] | null;
  next_actions?: string[] | null;
  documents_analyzed?: number | null;
  remaining_quota?: number | null;
  tokens_used?: number | null;
  warning?: string | null;
}

export interface ClientAiSummaryView {
  available: boolean;
  summary: string;
  risks: string[];
  nextActions: string[];
  generatedAt: string | null;
  documentsAnalyzedLabel: string | null;
}

const parseStatusLabels: Record<string, DocumentAiView['parseStatusLabel']> = {
  pending: 'Pendente',
  processing: 'Processando',
  completed: 'Processado',
  failed: 'Falhou',
  not_analyzed: 'Nao analisado',
};

const parseStatusVariants: Record<string, DocumentAiView['parseStatusVariant']> = {
  pending: 'warning',
  processing: 'info',
  completed: 'success',
  failed: 'error',
  not_analyzed: 'default',
};

const extractionFieldLabels: Record<string, string> = {
  competence_month: 'Competencia',
  amount: 'Valor',
  due_date: 'Vencimento',
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function readString(record: Record<string, unknown>, key: string): string | null {
  const value = record[key];
  if (typeof value === 'string' && value.trim()) {
    return value;
  }
  if (typeof value === 'number' && Number.isFinite(value)) {
    return String(value);
  }
  return null;
}

function readNumber(record: Record<string, unknown>, key: string): number | null {
  const value = record[key];
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string' && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function readBoolean(record: Record<string, unknown>, key: string): boolean {
  return record[key] === true;
}

function formatDocumentType(value: string | null): string {
  if (!value) {
    return 'Documento';
  }

  if (value.length <= 4 && value === value.toLowerCase()) {
    return value.toUpperCase();
  }

  return value
    .replace(/[_-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/^./, (first) => first.toUpperCase());
}

function buildConfidenceLabel(value: number | null): string | null {
  if (value === null) {
    return null;
  }

  const normalized = value > 1 ? value : value * 100;
  return `${Math.round(normalized)}%`;
}

function buildExtractedFields(classification: Record<string, unknown>): AiField[] {
  return Object.entries(extractionFieldLabels).flatMap(([key, label]) => {
    const value = readString(classification, key);
    return value ? [{ label, value }] : [];
  });
}

export function buildDocumentAiView(document: ClientDocument): DocumentAiView {
  const parseStatus = document.parse_status ?? 'not_analyzed';
  const parsedData = isRecord(document.parsed_data) ? document.parsed_data : null;
  const rawClassification = parsedData?.ai_classification ?? document.ai_classification;
  const classification = isRecord(rawClassification) ? rawClassification : null;

  if (!classification) {
    return {
      parseStatus,
      parseStatusLabel: parseStatusLabels[parseStatus] ?? parseStatus,
      parseStatusVariant: parseStatusVariants[parseStatus] ?? 'default',
      hasClassification: false,
      classification: null,
      parseError: document.parse_error ?? null,
    };
  }

  return {
    parseStatus,
    parseStatusLabel: parseStatusLabels[parseStatus] ?? parseStatus,
    parseStatusVariant: parseStatusVariants[parseStatus] ?? 'default',
    hasClassification: true,
    classification: {
      documentType: formatDocumentType(readString(classification, 'document_type')),
      summary: readString(classification, 'summary'),
      confidenceLabel: buildConfidenceLabel(readNumber(classification, 'confidence')),
      warning: readString(classification, 'warning'),
      fields: buildExtractedFields(classification),
      tokensUsed: readNumber(classification, 'tokens_used'),
      piiMasked: readBoolean(classification, 'pii_masked'),
    },
    parseError: document.parse_error ?? null,
  };
}

export function buildClientAiSummaryView(summary: ClientAiSummary | null): ClientAiSummaryView {
  if (!summary) {
    return {
      available: false,
      summary: 'Resumo de IA indisponivel para este cliente.',
      risks: [],
      nextActions: [],
      generatedAt: null,
      documentsAnalyzedLabel: null,
    };
  }

  const documentsAnalyzed = summary.documents_analyzed ?? null;

  return {
    available: true,
    summary: summary.summary?.trim() || 'Resumo de IA sem conteudo retornado.',
    risks: summary.risks ?? [],
    nextActions: summary.next_actions ?? [],
    generatedAt: summary.generated_at ?? null,
    documentsAnalyzedLabel:
      documentsAnalyzed === null
        ? null
        : `${documentsAnalyzed} ${documentsAnalyzed === 1 ? 'documento analisado' : 'documentos analisados'}`,
  };
}
