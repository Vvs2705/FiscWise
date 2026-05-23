import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

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
}

export interface DeadlineCreate {
  client_id: string;
  title: string;
  category: string;
  due_date: string;
  status: DeadlineStatus;
  priority: DeadlinePriority;
  description?: string;
}

export interface ClientDocument {
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
