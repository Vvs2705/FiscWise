import { useState } from 'react';
import {
  BarChart3, Download, TrendingUp,
  Users, FileText, Coins, AlertTriangle, CheckCircle2, Clock,
  Calendar,
} from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { MetricCard } from '@/components/ui/OperationalStates';
import { PermissionGate } from '@/components/ui/PermissionGate';
import { FeatureGate } from '@/components/ui/FeatureGate';
import { cn } from '@/lib/utils';

// Mock BI data
const REPORTS = [
  {
    id: 'clientes-risco',
    title: 'Clientes por risco fiscal',
    description: 'Distribui clientes por nível de risco: crítico, alto, médio, baixo.',
    icon: AlertTriangle,
    data: [
      { label: 'Crítico', value: 2, color: 'bg-red-500' },
      { label: 'Alto', value: 4, color: 'bg-orange-500' },
      { label: 'Médio', value: 8, color: 'bg-yellow-500' },
      { label: 'Baixo', value: 15, color: 'bg-emerald-500' },
    ],
    total: 29,
  },
  {
    id: 'obrigacoes-status',
    title: 'Obrigações por status',
    description: 'Acompanhe o cumprimento de obrigações acessórias e principais.',
    icon: CheckCircle2,
    data: [
      { label: 'Cumpridas', value: 47, color: 'bg-emerald-500' },
      { label: 'Pendentes', value: 12, color: 'bg-yellow-500' },
      { label: 'Atrasadas', value: 3, color: 'bg-red-500' },
    ],
    total: 62,
  },
  {
    id: 'notas-competencia',
    title: 'Notas fiscais por competência',
    description: 'Evolução mensal de emissão, rejeição e cancelamento.',
    icon: FileText,
    data: [
      { label: 'Emitidas', value: 143, color: 'bg-emerald-500' },
      { label: 'Rejeitadas', value: 7, color: 'bg-red-500' },
      { label: 'Canceladas', value: 4, color: 'bg-muted' },
    ],
    total: 154,
  },
  {
    id: 'guias-aberto',
    title: 'Guias em aberto',
    description: 'Guias geradas e ainda não pagas por cliente e competência.',
    icon: Coins,
    data: [
      { label: 'Pagas', value: 38, color: 'bg-emerald-500' },
      { label: 'Aguardando', value: 11, color: 'bg-yellow-500' },
      { label: 'Vencidas', value: 3, color: 'bg-red-500' },
    ],
    total: 52,
  },
  {
    id: 'fechamentos',
    title: 'Fechamentos por competência',
    description: 'Status de todos os fechamentos mensais na competência atual.',
    icon: Calendar,
    data: [
      { label: 'Concluídos', value: 8, color: 'bg-emerald-500' },
      { label: 'Em andamento', value: 12, color: 'bg-blue-500' },
      { label: 'Bloqueados', value: 3, color: 'bg-red-500' },
      { label: 'Não iniciados', value: 6, color: 'bg-muted' },
    ],
    total: 29,
  },
  {
    id: 'procuracoes-vencendo',
    title: 'Procurações vencendo',
    description: 'Procurações que vencem nos próximos 30, 60 e 90 dias.',
    icon: Clock,
    data: [
      { label: '≤ 30 dias', value: 2, color: 'bg-red-500' },
      { label: '31-60 dias', value: 4, color: 'bg-orange-500' },
      { label: '61-90 dias', value: 3, color: 'bg-yellow-500' },
    ],
    total: 9,
  },
];

const SUMMARY_METRICS = [
  { title: 'Receita faturada', value: 'R$ 48.200', subtitle: 'Mai/2026', icon: <TrendingUp className="h-4 w-4" />, variant: 'success' as const },
  { title: 'Receita recebida', value: 'R$ 41.700', subtitle: 'Mai/2026', icon: <Coins className="h-4 w-4" />, variant: 'success' as const },
  { title: 'Inadimplência', value: 'R$ 6.500', subtitle: '3 clientes', icon: <AlertTriangle className="h-4 w-4" />, variant: 'danger' as const },
  { title: 'Clientes ativos', value: '29', subtitle: '2 novos este mês', icon: <Users className="h-4 w-4" />, variant: 'default' as const },
];

export function ReportsPage() {
  const [competence, setCompetence] = useState('2026-05');

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
                <option value="2026-05">Maio/2026</option>
                <option value="2026-04">Abril/2026</option>
                <option value="2026-03">Março/2026</option>
              </select>
              <button className="flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground hover:opacity-90 transition-opacity">
                <Download className="h-4 w-4" />
                <span className="hidden sm:inline">Exportar XLSX</span>
              </button>
            </div>
          }
        />

        {/* Financial summary — owner/admin only */}
        <PermissionGate requiredRole="financeiro">
          <div>
            <h2 className="mb-3 text-sm font-semibold text-muted-foreground uppercase tracking-wide">Resumo financeiro</h2>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {SUMMARY_METRICS.map(m => (
                <MetricCard key={m.title} {...m} />
              ))}
            </div>
          </div>
        </PermissionGate>

        {/* Report cards grid */}
        <div>
          <h2 className="mb-3 text-sm font-semibold text-muted-foreground uppercase tracking-wide">Relatórios operacionais</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {REPORTS.map(report => (
              <ReportCard key={report.id} report={report} />
            ))}
          </div>
        </div>
      </div>
    </FeatureGate>
  );
}

function ReportCard({ report }: { report: typeof REPORTS[number] }) {
  return (
    <div className="rounded-xl border border-border bg-card p-5 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <report.icon className="h-4 w-4 text-muted-foreground" />
            <h3 className="text-sm font-semibold text-foreground">{report.title}</h3>
          </div>
          <p className="text-xs text-muted-foreground">{report.description}</p>
        </div>
        <button
          className="shrink-0 rounded p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          title="Exportar CSV"
        >
          <Download className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Mini bar chart */}
      <div className="space-y-2">
        {report.data.map(item => {
          const pct = Math.round((item.value / report.total) * 100);
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
        <button className="text-xs text-primary hover:underline">Ver detalhes →</button>
      </div>
    </div>
  );
}
