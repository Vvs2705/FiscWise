import { useMemo, useState } from 'react';
import {
  BarChart3, Download, TrendingUp,
  Users, FileText, Coins, AlertTriangle, CheckCircle2, Clock,
  Calendar,
} from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { MetricCard, EmptyState } from '@/components/ui/OperationalStates';
import { LoadingCards, ErrorState } from '@/components/ui/StateViews';
import { PermissionGate } from '@/components/ui/PermissionGate';
import { FeatureGate } from '@/components/ui/FeatureGate';
import { usePermission } from '@/lib/hooks/usePermission';
import { moneyBRL } from '@/lib/hooks/useOperations';
import { useReportsOperational, useReportsSummary, type OperationalReport } from '@/lib/hooks/useReports';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

type ReportBar = { label: string; value: number; color: string };
type ReportCardData = {
  id: string;
  title: string;
  description: string;
  icon: typeof BarChart3;
  data: ReportBar[];
  total: number;
};

const MONTHS_PT = [
  'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
  'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
];

function currentCompetence() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

/** Últimas 6 competências (mês atual e anteriores), como options. */
function competenceOptions() {
  const now = new Date();
  return Array.from({ length: 6 }, (_, i) => {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    return { value, label: `${MONTHS_PT[d.getMonth()]}/${d.getFullYear()}` };
  });
}

function competenceLabel(competence: string) {
  const [year, month] = competence.split('-').map(Number);
  return `${MONTHS_PT[(month ?? 1) - 1]}/${year}`;
}

function buildReports(op: OperationalReport): ReportCardData[] {
  return [
    {
      id: 'clientes-situacao',
      title: 'Clientes por situação',
      description: 'Distribuição da carteira por status cadastral.',
      icon: Users,
      total: op.clients_by_status.total,
      data: [
        { label: 'Ativos', value: op.clients_by_status.active, color: 'bg-success' },
        { label: 'Onboarding', value: op.clients_by_status.onboarding, color: 'bg-info' },
        { label: 'Inativos', value: op.clients_by_status.inactive, color: 'bg-muted' },
      ],
    },
    {
      id: 'obrigacoes-status',
      title: 'Obrigações por status',
      description: 'Cumprimento de obrigações na competência selecionada.',
      icon: CheckCircle2,
      total: op.obligations_by_status.total,
      data: [
        { label: 'Cumpridas', value: op.obligations_by_status.delivered, color: 'bg-success' },
        { label: 'Em andamento', value: op.obligations_by_status.in_progress, color: 'bg-info' },
        { label: 'Pendentes', value: op.obligations_by_status.pending, color: 'bg-warning' },
        { label: 'Atrasadas', value: op.obligations_by_status.overdue, color: 'bg-destructive' },
      ],
    },
    {
      id: 'guias-aberto',
      title: 'Guias por status',
      description: 'Guias da competência: pagas, aguardando e vencidas.',
      icon: Coins,
      total: op.guias_by_status.total,
      data: [
        { label: 'Pagas', value: op.guias_by_status.paid, color: 'bg-success' },
        { label: 'Aguardando', value: op.guias_by_status.awaiting, color: 'bg-warning' },
        { label: 'Vencidas', value: op.guias_by_status.overdue, color: 'bg-destructive' },
      ],
    },
    {
      id: 'fechamentos',
      title: 'Fechamentos por competência',
      description: 'Status dos fechamentos mensais na competência.',
      icon: Calendar,
      total: op.closings_by_status.total,
      data: [
        { label: 'Concluídos', value: op.closings_by_status.completed, color: 'bg-success' },
        { label: 'Em andamento', value: op.closings_by_status.in_progress, color: 'bg-info' },
        { label: 'Bloqueados', value: op.closings_by_status.blocked, color: 'bg-destructive' },
        { label: 'Não iniciados', value: op.closings_by_status.not_started, color: 'bg-muted' },
      ],
    },
    {
      id: 'notas-competencia',
      title: 'Notas fiscais por competência',
      description: 'Registros de NFS-e na competência (dados do FiscWise).',
      icon: FileText,
      total: op.invoices_by_status.total,
      data: [
        { label: 'Emitidas', value: op.invoices_by_status.issued, color: 'bg-success' },
        { label: 'Rejeitadas', value: op.invoices_by_status.rejected, color: 'bg-destructive' },
        { label: 'Canceladas', value: op.invoices_by_status.cancelled, color: 'bg-muted' },
      ],
    },
    {
      id: 'procuracoes-vencendo',
      title: 'Procurações vencendo',
      description: 'Procurações e-CAC que vencem nos próximos 90 dias.',
      icon: Clock,
      total: op.proxies_expiring.total,
      data: [
        { label: '≤ 30 dias', value: op.proxies_expiring.d30, color: 'bg-destructive' },
        { label: '31-60 dias', value: op.proxies_expiring.d60, color: 'bg-warning' },
        { label: '61-90 dias', value: op.proxies_expiring.d90, color: 'bg-warning' },
      ],
    },
  ];
}

export function ReportsPage() {
  const [competence, setCompetence] = useState(currentCompetence);
  const { hasRole } = usePermission();
  const isAdmin = hasRole('admin');

  const { data: op, isLoading, isError } = useReportsOperational(competence);
  const { data: summary } = useReportsSummary(competence, isAdmin);

  const options = useMemo(competenceOptions, []);
  const reports = useMemo(() => (op ? buildReports(op) : []), [op]);

  const summaryMetrics = useMemo(() => {
    if (!summary) return [];
    const label = competenceLabel(summary.competence);
    return [
      { title: 'Receita faturada', value: moneyBRL(summary.revenue_billed), subtitle: label, icon: <TrendingUp className="h-4 w-4" />, variant: 'success' as const },
      { title: 'Receita recebida', value: moneyBRL(summary.revenue_received), subtitle: label, icon: <Coins className="h-4 w-4" />, variant: 'success' as const },
      { title: 'Inadimplência', value: moneyBRL(summary.overdue_amount), subtitle: `${summary.overdue_clients} cliente${summary.overdue_clients === 1 ? '' : 's'}`, icon: <AlertTriangle className="h-4 w-4" />, variant: 'danger' as const },
      { title: 'Clientes ativos', value: summary.active_clients, subtitle: `${summary.new_clients_month} novo${summary.new_clients_month === 1 ? '' : 's'} este mês`, icon: <Users className="h-4 w-4" />, variant: 'default' as const },
    ];
  }, [summary]);

  return (
    <FeatureGate feature="feature_reports">
      <div className="space-y-6 p-6">
        <PageHeader
          title="Relatórios"
          subtitle="Visão consolidada da operação fiscal, financeira e de compliance."
          icon={<BarChart3 className="h-5 w-5" />}
          actions={
            <div className="flex items-center gap-2">
              <select
                value={competence}
                onChange={e => setCompetence(e.target.value)}
                className="rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
              >
                {options.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
              <button
                onClick={() => toast.info('Exportação XLSX disponível em breve.')}
                className="flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground hover:opacity-90 transition-opacity"
              >
                <Download className="h-4 w-4" />
                <span className="hidden sm:inline">Exportar XLSX</span>
              </button>
            </div>
          }
        />

        {/* Financial summary — owner/admin only */}
        <PermissionGate requiredRole="admin" silent>
          <div>
            <h2 className="mb-3 text-sm font-semibold text-muted-foreground uppercase tracking-wide">Resumo financeiro</h2>
            {summaryMetrics.length === 0 ? (
              <EmptyState
                icon={<Coins className="h-5 w-5" />}
                title="Sem dados financeiros nesta competência"
                description="Nenhuma receita, recebimento ou inadimplência registrada no período."
              />
            ) : (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {summaryMetrics.map(m => (
                  <MetricCard key={m.title} {...m} />
                ))}
              </div>
            )}
          </div>
        </PermissionGate>

        {/* Report cards grid */}
        <div>
          <h2 className="mb-3 text-sm font-semibold text-muted-foreground uppercase tracking-wide">Relatórios operacionais</h2>
          {isLoading ? (
            <LoadingCards count={6} />
          ) : isError ? (
            <ErrorState message="Não foi possível carregar os relatórios. Tente novamente." />
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {reports.map(report => (
                <ReportCard key={report.id} report={report} />
              ))}
            </div>
          )}
        </div>
      </div>
    </FeatureGate>
  );
}

function ReportCard({ report }: { report: ReportCardData }) {
  const isEmpty = report.total === 0;
  return (
    <div className="rounded-xl border border-border bg-card p-5 hover:shadow-token-sm transition-shadow">
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <report.icon className="h-4 w-4 text-muted-foreground" />
            <h3 className="text-sm font-semibold text-foreground">{report.title}</h3>
          </div>
          <p className="text-xs text-muted-foreground">{report.description}</p>
        </div>
      </div>

      {isEmpty ? (
        <p className="py-6 text-center text-xs text-muted-foreground">
          Sem dados nesta competência.
        </p>
      ) : (
        <>
          {/* Mini bar chart */}
          <div className="space-y-2">
            {report.data.map(item => {
              const pct = report.total > 0 ? Math.round((item.value / report.total) * 100) : 0;
              return (
                <div key={item.label}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-muted-foreground">{item.label}</span>
                    <span className="text-xs font-semibold tabular-nums text-foreground">{item.value}</span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                    <div
                      className={cn('h-full rounded-full transition-all', item.color)}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          <div className="mt-4 flex items-center justify-between border-t border-border pt-3">
            <span className="text-xs text-muted-foreground">Total: <strong className="text-foreground">{report.total}</strong></span>
          </div>
        </>
      )}
    </div>
  );
}
