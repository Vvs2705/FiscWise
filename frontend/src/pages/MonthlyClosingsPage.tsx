import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  CalendarCheck2, Search, RefreshCw, AlertTriangle, CheckCircle2,
  Circle, ChevronRight, Loader2,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { PageHeader } from '@/components/ui/PageHeader';
import { MetricCard } from '@/components/ui/OperationalStates';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { FeatureGate } from '@/components/ui/FeatureGate';
import { fetchMonthlyClosings, generateMonthlyClosings } from '@/features/monthly-closing/api';
import { MonthlyClosing } from '@/features/monthly-closing/types';
import { cn } from '@/lib/utils';

const COMPETENCE_OPTIONS = [
  { value: '2026-05', label: 'Maio/2026' },
  { value: '2026-04', label: 'Abril/2026' },
  { value: '2026-03', label: 'Março/2026' },
];

function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 100 ? 'text-emerald-400 bg-emerald-500/10' :
    score >= 80 ? 'text-blue-400 bg-blue-500/10' :
    score >= 50 ? 'text-yellow-400 bg-yellow-500/10' :
    'text-red-400 bg-red-500/10';

  return (
    <span className={cn('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-bold tabular-nums', color)}>
      {score}%
    </span>
  );
}

function ProgressBar({ value, max, className }: { value: number; max: number; className?: string }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  const color = pct >= 100 ? 'bg-emerald-500' : pct >= 50 ? 'bg-yellow-500' : 'bg-red-500';
  return (
    <div className={cn('h-1.5 w-full overflow-hidden rounded-full bg-muted', className)}>
      <div className={cn('h-full rounded-full transition-all', color)} style={{ width: `${pct}%` }} />
    </div>
  );
}

export function MonthlyClosingsPage() {
  const [competence, setCompetence] = useState('2026-05');
  const [search, setSearch] = useState('');

  const { data: closings, isLoading, error, refetch } = useQuery({
    queryKey: ['monthly-closings', competence],
    queryFn: () => fetchMonthlyClosings(competence),
  });

  const generateRoutine = useMutation({
    mutationFn: () => generateMonthlyClosings(competence),
    onSuccess: (r) => {
      toast.success(
        r.created > 0
          ? `Rotina de ${competence} gerada: ${r.created} cliente${r.created > 1 ? 's' : ''} com checklist criado.`
          : 'Todos os clientes já têm fechamento nesta competência.',
      );
      refetch();
    },
    onError: () => toast.error('Erro ao gerar rotina mensal.'),
  });

  const filtered = (closings ?? []).filter(c =>
    !search ||
    c.clientName.toLowerCase().includes(search.toLowerCase()) ||
    c.clientCnpj.includes(search)
  );

  const stats = {
    total: closings?.length ?? 0,
    completed: closings?.filter(c => c.status === 'completed').length ?? 0,
    blocked: closings?.filter(c => c.status === 'blocked').length ?? 0,
    notStarted: closings?.filter(c => c.status === 'not_started').length ?? 0,
  };

  return (
    <FeatureGate feature="feature_monthly_closing">
      <div className="space-y-6 p-6">
        <PageHeader
          title="Fechamento Mensal"
          subtitle="Controle a esteira de fechamento de todos os clientes por competência."
          icon={<CalendarCheck2 className="h-5 w-5" />}
          actions={
            <div className="flex items-center gap-2">
              <select
                value={competence}
                onChange={e => setCompetence(e.target.value)}
                className="rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
              >
                {COMPETENCE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
              <button
                onClick={() => refetch()}
                className="flex items-center gap-2 rounded-lg bg-muted px-3 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
              >
                <RefreshCw className="h-4 w-4" />
              </button>
            </div>
          }
        />

        {/* Metrics */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <MetricCard title="Total clientes" value={stats.total} icon={<CalendarCheck2 className="h-4 w-4" />} />
          <MetricCard title="Concluídos" value={stats.completed} icon={<CheckCircle2 className="h-4 w-4" />} variant="success" />
          <MetricCard title="Bloqueados" value={stats.blocked} icon={<AlertTriangle className="h-4 w-4" />} variant="danger" />
          <MetricCard title="Não iniciados" value={stats.notStarted} icon={<Circle className="h-4 w-4" />} variant="warning" />
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Buscar por cliente ou CNPJ..."
            className="w-full rounded-lg border border-border bg-card py-2.5 pl-9 pr-4 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
          />
        </div>

        {/* Table */}
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        ) : error ? (
          <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-4 text-sm text-red-300">
            Erro ao carregar fechamentos. Tente novamente.
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
            <CalendarCheck2 className="h-8 w-8 text-muted-foreground/30" />
            <p className="text-sm font-medium text-foreground">Nenhum fechamento nesta competência</p>
            <p className="text-xs text-muted-foreground">
              Gere a rotina mensal para montar obrigações, guias, notas e pendências.
            </p>
            <button
              onClick={() => generateRoutine.mutate()}
              disabled={generateRoutine.isPending}
              className="mt-2 flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {generateRoutine.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Gerar rotina mensal
            </button>
          </div>
        ) : (
          <div className="overflow-hidden rounded-xl border border-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/30">
                  <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground">Cliente</th>
                  <th className="hidden px-4 py-3 text-left text-xs font-semibold text-muted-foreground sm:table-cell">Status</th>
                  <th className="hidden px-4 py-3 text-left text-xs font-semibold text-muted-foreground md:table-cell">Score</th>
                  <th className="hidden px-4 py-3 text-left text-xs font-semibold text-muted-foreground lg:table-cell">Notas</th>
                  <th className="hidden px-4 py-3 text-left text-xs font-semibold text-muted-foreground lg:table-cell">Guias</th>
                  <th className="hidden px-4 py-3 text-left text-xs font-semibold text-muted-foreground xl:table-cell">Obrigações</th>
                  <th className="hidden px-4 py-3 text-left text-xs font-semibold text-muted-foreground xl:table-cell">Bloqueios</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-muted-foreground">Ações</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(closing => (
                  <ClosingRow key={closing.id} closing={closing} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </FeatureGate>
  );
}

function ClosingRow({ closing }: { closing: MonthlyClosing }) {
  return (
    <tr className="border-b border-border/50 last:border-0 transition-colors hover:bg-muted/20">
      <td className="px-4 py-3">
        <div>
          <p className="font-medium text-foreground">{closing.clientName}</p>
          <p className="text-xs text-muted-foreground">{closing.clientCnpj}</p>
        </div>
      </td>
      <td className="hidden px-4 py-3 sm:table-cell">
        <StatusBadge status={closing.status} />
      </td>
      <td className="hidden px-4 py-3 md:table-cell">
        <div className="flex flex-col gap-1">
          <ScoreBadge score={closing.score} />
          <ProgressBar value={closing.score} max={100} className="w-16" />
        </div>
      </td>
      <td className="hidden px-4 py-3 lg:table-cell">
        <span className={cn('text-xs', closing.invoicesPending > 0 ? 'text-orange-400' : 'text-muted-foreground')}>
          {closing.invoicesCount - closing.invoicesPending}/{closing.invoicesCount}
        </span>
      </td>
      <td className="hidden px-4 py-3 lg:table-cell">
        <span className={cn('text-xs', closing.guidesPaid < closing.guidesCount ? 'text-orange-400' : 'text-muted-foreground')}>
          {closing.guidesPaid}/{closing.guidesCount}
        </span>
      </td>
      <td className="hidden px-4 py-3 xl:table-cell">
        <span className={cn('text-xs', closing.obligationsDone < closing.obligationsTotal ? 'text-orange-400' : 'text-muted-foreground')}>
          {closing.obligationsDone}/{closing.obligationsTotal}
        </span>
      </td>
      <td className="hidden px-4 py-3 xl:table-cell">
        {closing.blockers.length > 0 ? (
          <span className="inline-flex items-center gap-1 text-xs text-red-400">
            <AlertTriangle className="h-3 w-3" />
            {closing.blockers.length}
          </span>
        ) : (
          <span className="text-xs text-emerald-400">—</span>
        )}
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center justify-end gap-2">
          <Link
            to={`/fechamento/${closing.id}`}
            className="flex items-center gap-1 rounded-lg border border-border px-2.5 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            Abrir
            <ChevronRight className="h-3 w-3" />
          </Link>
        </div>
      </td>
    </tr>
  );
}
