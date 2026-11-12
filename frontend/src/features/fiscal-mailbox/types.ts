// Types for Fiscal Mailbox feature

export type MailboxMessageRisk = 'critical' | 'high' | 'medium' | 'low' | 'none';
export type MailboxMessageStatus = 'unread' | 'read' | 'in_progress' | 'resolved' | 'archived';

export interface MailboxMessage {
  id: string;
  clientId: string;
  clientName: string;
  clientCnpj: string;
  subject: string;
  summary: string;
  body: string;
  organ: string; // RFB, PGFN, SEFAZ, etc.
  receivedAt: string;
  deadline: string | null;
  risk: MailboxMessageRisk;
  status: MailboxMessageStatus;
  taskCreated: boolean;
  obligationLinked: string | null;
  tags: string[];
  /** Mensagem gerada pelo provider simulado (não veio da Receita). */
  simulated: boolean;
}

export interface MailboxProviderStatus {
  provider: string;
  simulated: boolean;
  syncAvailable: boolean;
  message: string | null;
}
