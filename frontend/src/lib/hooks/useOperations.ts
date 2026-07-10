import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { api } from '@/lib/api';
import type { ClientAiSummary, ClientDocument as AiClientDocument } from '@/lib/aiDocuments';

export type ClientStatus = 'active' | 'inactive' | 'onboarding';
export type EntityType = 'pj' | 'pf';
export type DeadlineStatus = 'pending' | 'completed' | 'overdue' | 'cancelled';
export type DeadlinePriority = 'low' | 'medium' | 'high';
export type DocumentStatus = 'available' | 'missing' | 'expired' | 'review';
export type CertificateStatus = 'valid' | 'expiring' | 'expired' | 'revoked';
export type ReceivableStatus = 'pending' | 'paid' | 'overdue' | 'cancelled';

export interface AccountingClient {
  id: string;
  tenant_id: string;
  client_code: string;
  name: string;
  document?: string | null;
  entity_type: EntityType;
  tax_regime?: string | null;
  email?: string | null;
  phone?: string | null;
  municipal_registration?: string | null;
  state_registration?: string | null;
  status: ClientStatus;
  notes?: string | null;
  // Honorários
  monthly_fee?: string | number | null;
  billing_day?: number | null;
  annual_adjustment_percent?: string | number | null;
  created_at: string;
  updated_at: string;
  responsible_name?: string | null;
  responsible_cpf?: string | null;
  responsible_address?: string | null;
  responsible_phone?: string | null;
  responsible_email?: string | null;
}

export interface AccountingClientCreate {
  name: string;
  document?: string;
  entity_type: EntityType;
  tax_regime?: string;
  email?: string;
  phone?: string;
  municipal_registration?: string;
  state_registration?: string;
  status: ClientStatus;
  notes?: string;
  // Honorários
  monthly_fee?: number | null;
  billing_day?: number;
  annual_adjustment_percent?: number | null;
  // Responsible person
  responsible_name?: string;
  responsible_cpf?: string;
  responsible_address?: string;
  responsible_phone?: string;
  responsible_email?: string;
}

export interface DeadlineItem {
  id: string;
  tenant_id: string;
  client_id: string;
  title: string;
  category: string;
  due_date: string;
  status: DeadlineStatus;
  priority: DeadlinePriority;
  description?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
  is_recurring: boolean;
  recurrence_interval?: 'weekly' | 'monthly' | 'quarterly' | 'yearly' | null;
  recurrence_parent_id?: string | null;
}

export interface DeadlineCreate {
  client_id: string;
  title: string;
  category: string;
  due_date: string;
  status: DeadlineStatus;
  priority: DeadlinePriority;
  description?: string;
  is_recurring?: boolean;
  recurrence_interval?: 'weekly' | 'monthly' | 'quarterly' | 'yearly' | null;
}


export interface ClientDocument extends Omit<AiClientDocument, 'status'> {
  id: string;
  tenant_id: string;
  client_id: string;
  name: string;
  document_type: string;
  status: DocumentStatus;
  file_url?: string | null;
  issued_at?: string | null;
  expires_at?: string | null;
  notes?: string | null;
  parse_status?: string | null;
  parsed_data?: Record<string, unknown> | null;
  parse_error?: string | null;
  parsed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentCreate {
  client_id: string;
  name: string;
  document_type: string;
  status: DocumentStatus;
  file_url?: string;
  issued_at?: string;
  expires_at?: string;
  notes?: string;
}

export interface DigitalCertificate {
  id: string;
  tenant_id: string;
  client_id: string;
  label: string;
  certificate_type: string;
  valid_from?: string | null;
  valid_until: string;
  status: CertificateStatus;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CertificateCreate {
  client_id: string;
  label: string;
  certificate_type: string;
  valid_from?: string;
  valid_until: string;
  status: CertificateStatus;
  notes?: string;
}

export interface AccountReceivable {
  id: string;
  tenant_id: string;
  client_id: string;
  description: string;
  amount: string | number;
  due_date: string;
  status: ReceivableStatus;
  paid_at?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReceivableCreate {
  client_id: string;
  description: string;
  amount: number;
  due_date: string;
  status: ReceivableStatus;
  paid_at?: string;
  notes?: string;
}

export interface MonthlyData {
  mes: string;
  valor: number;
}

export interface DailyData {
  dia: string;
  receita: number;
}

export interface ReceivableWithClient {
  id: string;
  client_id: string;
  client_name: string;
  description: string;
  amount: string | number;
  due_date: string;
  status: ReceivableStatus;
  paid_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DashboardOverview {
  active_clients: number;
  pending_deadlines: number;
  overdue_deadlines: number;
  certificates_expiring_30d: number;
  open_receivables: number;
  overdue_receivables: number;
  receivables_amount_open: string | number;
  receivables_amount_overdue: string | number;
  upcoming_deadlines: DeadlineItem[];
  total_received_month: string | number;
  monthly_received: MonthlyData[];
  weekly_received: DailyData[];
  recent_receivables: ReceivableWithClient[];
}

const operationsKey = ['operations'] as const;

export function useDashboardOverview() {
  return useQuery({
    queryKey: [...operationsKey, 'dashboard'],
    queryFn: async () => {
      const { data } = await api.get<DashboardOverview>('/api/v1/dashboard/overview');
      return data;
    },
    refetchInterval: 60_000, // auto-refresh every 60 s for real-time feel
  });
}

// ─── Productivity Dashboard ───────────────────────────────────────────────────

export interface CollaboratorStats {
  user_id: string | null;
  user_name: string;
  pending: number;
  in_progress: number;
  delivered: number;
  overdue: number;
  total: number;
}

export interface ClientPendingStats {
  client_id: string;
  client_name: string;
  pending_count: number;
}

export interface PendingDocumentDto {
  id: string;
  client_name: string;
  document_name: string;
  days_waiting: number;
  status: string;
}

export interface ProductivityOverview {
  competence_month: string; // "2026-05"
  compliance_rate: number;
  total_pending: number;
  total_in_progress: number;
  total_delivered: number;
  total_overdue: number;
  total_blocked: number;
  obligations_by_collaborator: CollaboratorStats[];
  clients_with_most_pending: ClientPendingStats[];
  pending_documents: PendingDocumentDto[];
  docs_awaiting_approval: number;
  certificates_expiring_30d: number;
  overdue_receivables_count: number;
  overdue_receivables_amount: string | number;
}

export function useProductivityOverview(year?: number, month?: number) {
  const params = new URLSearchParams();
  if (year) params.set('year', String(year));
  if (month) params.set('month', String(month));
  const qs = params.toString() ? `?${params.toString()}` : '';

  return useQuery({
    queryKey: [...operationsKey, 'productivity', year, month],
    queryFn: async () => {
      const { data } = await api.get<ProductivityOverview>(
        `/api/v1/dashboard/productivity${qs}`
      );
      return data;
    },
    staleTime: 2 * 60 * 1000, // 2 min
    retry: false, // gracefully skip if user lacks permission
  });
}

export function useClients() {
  return useQuery({
    queryKey: [...operationsKey, 'clients'],
    queryFn: async () => {
      const { data } = await api.get<AccountingClient[]>('/api/v1/clients');
      return data;
    },
  });
}

export function useDeadlines() {
  return useQuery({
    queryKey: [...operationsKey, 'deadlines'],
    queryFn: async () => {
      const { data } = await api.get<DeadlineItem[]>('/api/v1/deadlines');
      return data;
    },
  });
}

export function useDocuments() {
  return useQuery({
    queryKey: [...operationsKey, 'documents'],
    queryFn: async () => {
      const { data } = await api.get<ClientDocument[]>('/api/v1/documents');
      return data;
    },
  });
}

export function useClientDocuments(clientId: string | undefined) {
  return useQuery({
    queryKey: [...operationsKey, 'clients', clientId, 'documents'],
    queryFn: async () => {
      const { data } = await api.get<ClientDocument[]>(`/api/v1/clients/${clientId}/documents`);
      return data;
    },
    enabled: !!clientId,
  });
}

export function useGenerateClientAiSummary() {
  return useMutation({
    mutationFn: async (clientId: string) => {
      try {
        const { data } = await api.post<ClientAiSummary>(
          `/api/v1/clients/${clientId}/ai-summary`
        );
        return data;
      } catch (error) {
        if (!axios.isAxiosError(error)) {
          throw error;
        }

        const statusCode = error.response?.status;
        if (statusCode && [403, 404, 405, 501].includes(statusCode)) {
          return null;
        }

        throw error;
      }
    },
  });
}

export function useCertificates() {
  return useQuery({
    queryKey: [...operationsKey, 'certificates'],
    queryFn: async () => {
      const { data } = await api.get<DigitalCertificate[]>('/api/v1/certificates');
      return data;
    },
  });
}

export function useReceivables() {
  return useQuery({
    queryKey: [...operationsKey, 'receivables'],
    queryFn: async () => {
      const { data } = await api.get<AccountReceivable[]>('/api/v1/receivables');
      return data;
    },
  });
}

function useCreateMutation<TPayload, TResponse>(endpoint: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: TPayload) => {
      const { data } = await api.post<TResponse>(endpoint, payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: operationsKey });
    },
  });
}

function useUpdateMutation<TPayload, TResponse>(endpoint: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: Partial<TPayload> }) => {
      const { data } = await api.patch<TResponse>(`${endpoint}/${id}`, payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: operationsKey });
    },
  });
}

function useDeleteMutation(endpoint: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`${endpoint}/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: operationsKey });
    },
  });
}

export function useCreateClient() {
  return useCreateMutation<AccountingClientCreate, AccountingClient>('/api/v1/clients');
}

export function useCreateDeadline() {
  return useCreateMutation<DeadlineCreate, DeadlineItem>('/api/v1/deadlines');
}

export function useCreateDocument() {
  return useCreateMutation<DocumentCreate, ClientDocument>('/api/v1/documents');
}

export function useCreateCertificate() {
  return useCreateMutation<CertificateCreate, DigitalCertificate>('/api/v1/certificates');
}

export function useCreateReceivable() {
  return useCreateMutation<ReceivableCreate, AccountReceivable>('/api/v1/receivables');
}

export function useUpdateReceivable() {
  return useUpdateMutation<ReceivableCreate, AccountReceivable>('/api/v1/receivables');
}

export function useDeleteClient() {
  return useDeleteMutation('/api/v1/clients');
}

export function useDeleteDeadline() {
  return useDeleteMutation('/api/v1/deadlines');
}

export function useUpdateDeadline() {
  return useUpdateMutation<DeadlineCreate, DeadlineItem>('/api/v1/deadlines');
}

export function useDeleteDocument() {
  return useDeleteMutation('/api/v1/documents');
}

export function useDeleteCertificate() {
  return useDeleteMutation('/api/v1/certificates');
}

export function useDeleteReceivable() {
  return useDeleteMutation('/api/v1/receivables');
}

export function useUploadDocument() {
  return useMutation({
    mutationFn: async (file: File): Promise<{ url: string; path: string }> => {
      const form = new FormData();
      form.append('file', file);
      const { data } = await api.post<{ url: string; path: string }>(
        '/api/v1/documents/upload',
        form,
        { headers: { 'Content-Type': 'multipart/form-data' } },
      );
      return data;
    },
  });
}

export function moneyBRL(value: string | number | null | undefined) {
  return Number(value ?? 0).toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  });
}

export function dateBR(value: string | null | undefined) {
  if (!value) {
    return '-';
  }

  return new Date(`${value}T00:00:00`).toLocaleDateString('pt-BR');
}

export interface CompanyPartner {
  id: string;
  client_id: string;
  tenant_id: string;
  name: string;
  cpf: string;
  participation_percentage: number;
  entry_date?: string | null;
  status: string;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PartnerCreate {
  name: string;
  cpf: string;
  participation_percentage: number;
  entry_date?: string;
  status?: string;
  notes?: string;
}

export interface CompanyDocument {
  id: string;
  client_id: string;
  tenant_id: string;
  document_type: string;
  file_url: string;
  upload_date: string;
  expiration_date?: string | null;
  status: string;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CompanyDocumentCreate {
  document_type: string;
  file_url: string;
  expiration_date?: string;
  status?: string;
  notes?: string;
}

export function useUpdateClient() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: Partial<AccountingClientCreate> }) => {
      const { data } = await api.put<AccountingClient>(`/api/v1/clients/${id}`, payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: operationsKey });
    },
  });
}

export function usePartners(clientId: string) {
  return useQuery({
    queryKey: [...operationsKey, 'clients', clientId, 'partners'],
    queryFn: async () => {
      const { data } = await api.get<CompanyPartner[]>(`/api/v1/clients/${clientId}/partners`);
      return data;
    },
    enabled: !!clientId,
  });
}

export function useCreatePartner(clientId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: PartnerCreate) => {
      const { data } = await api.post<CompanyPartner>(`/api/v1/clients/${clientId}/partners`, payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [...operationsKey, 'clients', clientId, 'partners'] });
    },
  });
}

export function useUpdatePartner(clientId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: Partial<PartnerCreate> }) => {
      const { data } = await api.put<CompanyPartner>(`/api/v1/clients/${clientId}/partners/${id}`, payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [...operationsKey, 'clients', clientId, 'partners'] });
    },
  });
}

export function useDeletePartner(clientId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/v1/clients/${clientId}/partners/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [...operationsKey, 'clients', clientId, 'partners'] });
    },
  });
}

export function useCompanyDocuments(clientId: string) {
  return useQuery({
    queryKey: [...operationsKey, 'clients', clientId, 'company-documents'],
    queryFn: async () => {
      const { data } = await api.get<CompanyDocument[]>(`/api/v1/clients/${clientId}/company-documents`);
      return data;
    },
    enabled: !!clientId,
  });
}

export function useCreateCompanyDocument(clientId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: CompanyDocumentCreate) => {
      const { data } = await api.post<CompanyDocument>(`/api/v1/clients/${clientId}/company-documents`, payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [...operationsKey, 'clients', clientId, 'company-documents'] });
    },
  });
}

export function useDeleteCompanyDocument(clientId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/v1/clients/${clientId}/company-documents/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [...operationsKey, 'clients', clientId, 'company-documents'] });
    },
  });
}

export function useExpiringCompanyDocuments(clientId: string, days = 30) {
  return useQuery({
    queryKey: [...operationsKey, 'clients', clientId, 'company-documents', 'expiring-soon', days],
    queryFn: async () => {
      const { data } = await api.get<CompanyDocument[]>(`/api/v1/clients/${clientId}/company-documents/expiring-soon`, {
        params: { days_threshold: days },
      });
      return data;
    },
    enabled: !!clientId,
  });
}

/* ─── DAS MONTHLY PAYMENTS ────────────────────────────────────────── */

export interface DasPayment {
  id: string;
  tenant_id: string;
  client_id: string;
  client_name?: string | null;
  period: string;
  revenue: number;
  tax_amount: number;
  due_date: string;
  status: 'pending' | 'paid' | 'overdue';
  paid_at?: string | null;
  file_url?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DasPaymentCreate {
  client_id: string;
  period: string;
  revenue: number;
  tax_amount: number;
  due_date: string;
  status: string;
  notes?: string;
}

export interface DasPaymentUpdate {
  revenue?: number;
  tax_amount?: number;
  due_date?: string;
  status?: string;
  file_url?: string;
  notes?: string;
}

export function useDasPayments(clientId?: string, year?: string) {
  return useQuery({
    queryKey: [...operationsKey, 'das', clientId, year],
    queryFn: async () => {
      const { data } = await api.get<DasPayment[]>('/api/v1/das', {
        params: { client_id: clientId, year },
      });
      return data;
    },
  });
}

export function useCreateDas() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: DasPaymentCreate) => {
      const { data } = await api.post<DasPayment>('/api/v1/das', payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: operationsKey });
    },
  });
}

export function useUpdateDas() {
  return useUpdateMutation<DasPaymentUpdate, DasPayment>('/api/v1/das');
}

export function useDeleteDas() {
  return useDeleteMutation('/api/v1/das');
}

export function usePayDas() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.patch<DasPayment>(`/api/v1/das/${id}/pay`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: operationsKey });
    },
  });
}

// ─── Billing / Honorários ─────────────────────────────────────────────────────

export interface ClientBillingConfig {
  client_id: string;
  client_name: string;
  monthly_fee: string | number | null;
  billing_day: number;
  annual_adjustment_percent: string | number | null;
}

export interface ClientBillingHistoryItem {
  id: string;
  description: string;
  amount: string | number;
  due_date: string;
  status: ReceivableStatus;
  paid_at: string | null;
  created_at: string;
}

export interface InadimplenciaClientItem {
  client_id: string;
  client_name: string;
  document: string | null;
  email: string | null;
  overdue_count: number;
  overdue_total: string | number;
  oldest_due_date: string;
  days_overdue: number;
}

export interface InadimplenciaReport {
  generated_at: string;
  total_clients: number;
  total_overdue_count: number;
  total_overdue_amount: string | number;
  clients: InadimplenciaClientItem[];
}

export function useClientBillingConfig(clientId: string | undefined) {
  return useQuery({
    queryKey: [...operationsKey, 'billing-config', clientId],
    queryFn: async () => {
      const { data } = await api.get<ClientBillingConfig>(
        `/api/v1/clients/${clientId}/billing-config`
      );
      return data;
    },
    enabled: !!clientId,
    staleTime: 5 * 60_000,
  });
}

export function useUpdateClientBillingConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      clientId,
      payload,
    }: {
      clientId: string;
      payload: Partial<Pick<ClientBillingConfig, 'monthly_fee' | 'billing_day' | 'annual_adjustment_percent'>>;
    }) => {
      const { data } = await api.patch<ClientBillingConfig>(
        `/api/v1/clients/${clientId}/billing-config`,
        payload
      );
      return data;
    },
    onSuccess: (_, { clientId }) => {
      qc.invalidateQueries({ queryKey: [...operationsKey, 'billing-config', clientId] });
      qc.invalidateQueries({ queryKey: [...operationsKey, 'clients'] });
    },
  });
}

export function useClientBillingHistory(clientId: string | undefined) {
  return useQuery({
    queryKey: [...operationsKey, 'billing-history', clientId],
    queryFn: async () => {
      const { data } = await api.get<ClientBillingHistoryItem[]>(
        `/api/v1/clients/${clientId}/billing-history`
      );
      return data;
    },
    enabled: !!clientId,
    staleTime: 2 * 60_000,
  });
}

export function useInadimplenciaReport() {
  return useQuery({
    queryKey: [...operationsKey, 'inadimplencia'],
    queryFn: async () => {
      const { data } = await api.get<InadimplenciaReport>('/api/v1/financeiro/inadimplencia');
      return data;
    },
    staleTime: 5 * 60_000,
    retry: false,
  });
}
