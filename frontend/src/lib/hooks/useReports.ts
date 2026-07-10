import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

export interface ClientsByStatus {
  active: number;
  onboarding: number;
  inactive: number;
  total: number;
}

export interface ObligationsByStatus {
  delivered: number;
  pending: number;
  in_progress: number;
  overdue: number;
  total: number;
}

export interface GuiasByStatus {
  paid: number;
  awaiting: number;
  overdue: number;
  total: number;
}

export interface ClosingsByStatus {
  completed: number;
  in_progress: number;
  blocked: number;
  not_started: number;
  total: number;
}

export interface InvoicesByStatus {
  issued: number;
  rejected: number;
  cancelled: number;
  total: number;
}

export interface ProxiesExpiring {
  d30: number;
  d60: number;
  d90: number;
  total: number;
}

export interface OperationalReport {
  competence: string;
  clients_by_status: ClientsByStatus;
  obligations_by_status: ObligationsByStatus;
  guias_by_status: GuiasByStatus;
  closings_by_status: ClosingsByStatus;
  invoices_by_status: InvoicesByStatus;
  proxies_expiring: ProxiesExpiring;
}

export interface ReportsSummary {
  competence: string;
  revenue_billed: string | number;
  revenue_received: string | number;
  overdue_amount: string | number;
  overdue_clients: number;
  active_clients: number;
  new_clients_month: number;
}

const reportsKey = ['reports'] as const;

export function useReportsOperational(competence: string) {
  return useQuery({
    queryKey: [...reportsKey, 'operational', competence],
    queryFn: async () => {
      const { data } = await api.get<OperationalReport>('/api/v1/reports/operational', {
        params: { competence },
      });
      return data;
    },
    staleTime: 2 * 60_000,
  });
}

export function useReportsSummary(competence: string, enabled = true) {
  return useQuery({
    queryKey: [...reportsKey, 'summary', competence],
    queryFn: async () => {
      const { data } = await api.get<ReportsSummary>('/api/v1/reports/summary', {
        params: { competence },
      });
      return data;
    },
    enabled,
    staleTime: 2 * 60_000,
    retry: false, // gracefully skip if user lacks permission (403)
  });
}
