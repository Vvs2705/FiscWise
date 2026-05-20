export type ClientStatus = 'active' | 'onboarding' | 'attention';
export type OperationalStatus = 'ok' | 'warning' | 'late';

export interface AccountingClient {
  id: string;
  name: string;
  document: string;
  regime: string;
  contact: string;
  status: ClientStatus;
  pendingDocuments: number;
  nextDeadline: string;
  certificateDaysLeft: number;
  receivableStatus: OperationalStatus;
}

export interface DeadlineItem {
  id: string;
  clientName: string;
  title: string;
  dueDate: string;
  status: OperationalStatus;
}

export interface DocumentItem {
  id: string;
  clientName: string;
  type: string;
  competence: string;
  status: 'requested' | 'received' | 'approved' | 'rejected';
}

export interface CertificateItem {
  id: string;
  clientName: string;
  type: 'A1' | 'A3';
  expiresAt: string;
  daysLeft: number;
}

export interface ReceivableItem {
  id: string;
  clientName: string;
  amount: number;
  dueDate: string;
  status: 'open' | 'paid' | 'late';
}

export const clients: AccountingClient[] = [
  {
    id: '1',
    name: 'Silva Servicos Administrativos',
    document: '12.345.678/0001-90',
    regime: 'Simples Nacional',
    contact: '(11) 99999-1001',
    status: 'attention',
    pendingDocuments: 3,
    nextDeadline: '2026-05-20',
    certificateDaysLeft: 12,
    receivableStatus: 'late',
  },
  {
    id: '2',
    name: 'Mariana Costa MEI',
    document: '123.456.789-10',
    regime: 'MEI',
    contact: '(31) 98888-2210',
    status: 'active',
    pendingDocuments: 1,
    nextDeadline: '2026-05-22',
    certificateDaysLeft: 84,
    receivableStatus: 'ok',
  },
  {
    id: '3',
    name: 'Nova Rota Tecnologia LTDA',
    document: '23.456.789/0001-12',
    regime: 'Lucro Presumido',
    contact: '(41) 97777-3003',
    status: 'onboarding',
    pendingDocuments: 5,
    nextDeadline: '2026-05-24',
    certificateDaysLeft: 28,
    receivableStatus: 'warning',
  },
  {
    id: '4',
    name: 'Oliveira Comercio Digital',
    document: '34.567.890/0001-55',
    regime: 'Simples Nacional',
    contact: '(21) 96666-4210',
    status: 'active',
    pendingDocuments: 0,
    nextDeadline: '2026-05-27',
    certificateDaysLeft: 171,
    receivableStatus: 'ok',
  },
];

export const deadlines: DeadlineItem[] = [
  { id: '1', clientName: 'Silva Servicos Administrativos', title: 'DAS mensal', dueDate: '2026-05-20', status: 'late' },
  { id: '2', clientName: 'Mariana Costa MEI', title: 'Declaracao mensal de notas', dueDate: '2026-05-22', status: 'warning' },
  { id: '3', clientName: 'Nova Rota Tecnologia LTDA', title: 'Enviar documentos da folha', dueDate: '2026-05-24', status: 'warning' },
  { id: '4', clientName: 'Oliveira Comercio Digital', title: 'Conferencia de notas fiscais', dueDate: '2026-05-27', status: 'ok' },
];

export const documents: DocumentItem[] = [
  { id: '1', clientName: 'Silva Servicos Administrativos', type: 'Extrato bancario', competence: '05/2026', status: 'requested' },
  { id: '2', clientName: 'Silva Servicos Administrativos', type: 'Notas emitidas', competence: '05/2026', status: 'received' },
  { id: '3', clientName: 'Nova Rota Tecnologia LTDA', type: 'Contrato social', competence: 'Onboarding', status: 'requested' },
  { id: '4', clientName: 'Mariana Costa MEI', type: 'Comprovante DAS', competence: '05/2026', status: 'approved' },
];

export const certificates: CertificateItem[] = [
  { id: '1', clientName: 'Silva Servicos Administrativos', type: 'A1', expiresAt: '2026-06-01', daysLeft: 12 },
  { id: '2', clientName: 'Nova Rota Tecnologia LTDA', type: 'A1', expiresAt: '2026-06-17', daysLeft: 28 },
  { id: '3', clientName: 'Oliveira Comercio Digital', type: 'A3', expiresAt: '2026-11-07', daysLeft: 171 },
];

export const receivables: ReceivableItem[] = [
  { id: '1', clientName: 'Silva Servicos Administrativos', amount: 390, dueDate: '2026-05-10', status: 'late' },
  { id: '2', clientName: 'Nova Rota Tecnologia LTDA', amount: 590, dueDate: '2026-05-20', status: 'open' },
  { id: '3', clientName: 'Mariana Costa MEI', amount: 120, dueDate: '2026-05-15', status: 'paid' },
];

export function statusLabel(status: OperationalStatus) {
  return {
    ok: 'Em dia',
    warning: 'Atenção',
    late: 'Atrasado',
  }[status];
}

export function moneyBRL(value: number) {
  return value.toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  });
}
