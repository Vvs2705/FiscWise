// Types for Monthly Closing feature

export type ClosingStatus = 'not_started' | 'in_progress' | 'blocked' | 'ready_for_review' | 'completed' | 'reopened';

export interface ChecklistItem {
  id: string;
  label: string;
  status: 'pending' | 'done' | 'blocked' | 'na';
  notes?: string;
  completedAt?: string;
  completedBy?: string;
}

export interface MonthlyClosing {
  id: string;
  clientId: string;
  clientName: string;
  clientCnpj: string;
  competence: string; // YYYY-MM
  status: ClosingStatus;
  score: number; // 0-100
  blockers: string[];
  checklist: ChecklistItem[];
  invoicesCount: number;
  invoicesPending: number;
  guidesCount: number;
  guidesPaid: number;
  obligationsTotal: number;
  obligationsDone: number;
  ecacPendencies: number;
  documentsTotal: number;
  documentsReceived: number;
  createdAt: string;
  updatedAt: string;
  dossierGeneratedAt?: string;
}
