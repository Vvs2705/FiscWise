import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import {
  CalendarCheck2, CheckCircle2, Circle, MinusCircle,
  AlertTriangle, Download, Loader2, FileText, Coins,
  ListChecks, Shield,
} from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { FeatureGate } from '@/components/ui/FeatureGate';
import { fetchMonthlyClosing, updateChecklistItem, generateDossier } from '@/features/monthly-closing/api';
import { ChecklistItem } from '@/features/monthly-closing/types';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

function ScoreRing({ score }: { score: number }) {
  const color = score >= 100 ? '#10b981' : score >= 80 ? '#3b82f6' : score >= 50 ? '#eab308' : '#ef4444';
  const circumference = 2 * Math.PI * 40;
  const strokeDash = (score / 100) * circumference;

  return (
    <div className="relative flex h-24 w-24 items-center justify-center">
      <svg className="absolute inset-0 -rotate-90" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="40" fill="none" stroke="currentColor" strokeWidth="8" className="text-muted/30" />
        <circle
          cx="50" cy="50" r="40" fill="none"
          stroke={color} strokeWidth="8"
          strokeDasharray={`${strokeDash} ${circumference}`}
          strokeLinecap="round"
          className="transition-all duration-500"
        />
      </svg>
      <div className="text-center">
        <p className="text-2xl font-bold tabular-nums" style={{ color }}>{score}</p>
        <p className="text-[10px] text-muted-foreground">score</p>
      </div>
    </div>
  );
}

const CHECKLIST_STATUS_ICONS = {
  done: <CheckCircle2 className="h-4 w-4 text-emerald-400" />,
  pending: <Circle className="h-4 w-4 text-muted-foreground" />,
  blocked: <AlertTriangle className="h-4 w-4 text-red-400" />,
  na: <MinusCircle className="h-4 w-4 text-muted-foreground/50" />,
};

export function MonthlyClosingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [generatingDossier, setGeneratingDossier] = useState(false);
  const [activeTab, setActiveTab] = useState<'checklist' | 'notas' | 'guias' | 'obrigacoes' | 'ecac' | 'dossie'>('checklist');

  const qc = useQueryClient();

  const { data: closing, isLoading, error } = useQuery({
    queryKey: ['monthly-closing', id],
    queryFn: () => fetchMonthlyClosing(id!),
    enabled: !!id,
  });

  const checklistMutation = useMutation({
    mutationFn: ({ itemId, status }: { itemId: string; status: ChecklistItem['status'] }) =>
      updateChecklistItem(id!, itemId, status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['monthly-closing', id] });
      toast.success('Checklist atualizado');
    },
    onError: () => toast.error('Erro ao atualizar checklist'),
  });

  const handleGenerateDossier = async () => {
    if (!id) return;
    setGeneratingDossier(true);
    try {
      await generateDossier(id);
      toast.success('Dossiê gerado! Download iniciado.');
    } catch {
      toast.error('Erro ao gerar dossiê');
    } finally {
      setGeneratingDossier(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error || !closing) {
    return (
      <div className="p-6">
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-4 text-sm text-red-300">
          Fechamento não encontrado.
        </div>
      </div>
    );
  }

  const tabs = [
    { key: 'checklist', label: 'Checklist', icon: CheckCircle2 },
    { key: 'notas', label: 'Notas Fiscais', icon: FileText },
    { key: 'guias', label: 'Guias', icon: Coins },
    { key: 'obrigacoes', label: 'Obrigações', icon: ListChecks },
    { key: 'ecac', label: 'e-CAC', icon: Shield },
    { key: 'dossie', label: 'Dossiê', icon: Download },
  ] as const;

  return (
    <FeatureGate feature="feature_monthly_closing">
      <div className="space-y-6 p-6">
        <PageHeader
          title={`${closing.clientName} — ${closing.competence}`}
          subtitle="Detalhamento do fechamento mensal"
          icon={<CalendarCheck2 className="h-5 w-5" />}
          breadcrumb={[
            { label: 'Fechamento Mensal', href: '/fechamento' },
            { label: closing.clientName },
          ]}
          actions={
            <div className="flex items-center gap-2">
              <StatusBadge status={closing.status} />
              <button
                onClick={handleGenerateDossier}
                disabled={generatingDossier}
                className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                {generatingDossier ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                Gerar dossiê
              </button>
            </div>
          }
        />

        {/* Blockers */}
        {closing.blockers.length > 0 && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-4">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="h-4 w-4 text-red-400" />
              <span className="text-sm font-semibold text-red-300">Bloqueios ativos</span>
            </div>
            <ul className="space-y-1">
              {closing.blockers.map((b, i) => (
                <li key={i} className="text-xs text-red-300/80 flex items-center gap-1.5">
                  <span className="h-1 w-1 rounded-full bg-red-400" />
                  {b}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Summary row */}
        <div className="flex flex-wrap items-center gap-6 rounded-xl border border-border bg-card p-6">
          <ScoreRing score={closing.score} />
          <div className="grid flex-1 grid-cols-2 gap-4 sm:grid-cols-4">
            <Stat label="Notas" value={`${closing.invoicesCount - closing.invoicesPending}/${closing.invoicesCount}`} pending={closing.invoicesPending > 0} />
            <Stat label="Guias pagas" value={`${closing.guidesPaid}/${closing.guidesCount}`} pending={closing.guidesPaid < closing.guidesCount} />
            <Stat label="Obrigações" value={`${closing.obligationsDone}/${closing.obligationsTotal}`} pending={closing.obligationsDone < closing.obligationsTotal} />
            <Stat label="Documentos" value={`${closing.documentsReceived}/${closing.documentsTotal}`} pending={closing.documentsReceived < closing.documentsTotal} />
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 overflow-x-auto border-b border-border pb-0">
          {tabs.map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={cn(
                'flex items-center gap-1.5 whitespace-nowrap px-4 py-2.5 text-sm font-medium border-b-2 transition-colors',
                activeTab === tab.key
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground',
              )}
            >
              <tab.icon className="h-3.5 w-3.5" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {activeTab === 'checklist' && (
          <div className="space-y-2">
            {closing.checklist.map(item => (
              <div
                key={item.id}
                className={cn(
                  'flex items-start gap-3 rounded-lg border border-border bg-card p-4 transition-colors',
                  item.status === 'done' && 'opacity-60',
                  item.status === 'blocked' && 'border-red-500/20 bg-red-500/5',
                )}
              >
                <span className="mt-0.5 shrink-0">{CHECKLIST_STATUS_ICONS[item.status]}</span>
                <div className="flex-1">
                  <p className={cn('text-sm font-medium', item.status === 'done' && 'line-through text-muted-foreground')}>
                    {item.label}
                  </p>
                  {item.notes && <p className="mt-0.5 text-xs text-muted-foreground">{item.notes}</p>}
                  {item.completedAt && (
                    <p className="mt-0.5 text-xs text-emerald-400/80">
                      Concluído em {new Date(item.completedAt).toLocaleDateString('pt-BR')}
                    </p>
                  )}
                </div>
                <div className="flex shrink-0 items-center gap-1">
                  {item.status !== 'done' && (
                    <button
                      onClick={() => checklistMutation.mutate({ itemId: item.id, status: 'done' })}
                      disabled={checklistMutation.isPending}
                      className="rounded px-2.5 py-1 text-xs font-medium bg-emerald-600/20 text-emerald-400 hover:bg-emerald-600/40 transition-colors"
                    >
                      Marcar como feito
                    </button>
                  )}
                  {item.status === 'done' && (
                    <button
                      onClick={() => checklistMutation.mutate({ itemId: item.id, status: 'pending' })}
                      disabled={checklistMutation.isPending}
                      className="rounded px-2.5 py-1 text-xs font-medium bg-muted text-muted-foreground hover:text-foreground transition-colors"
                    >
                      Desfazer
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab !== 'checklist' && (
          <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
              {(() => {
                const tab = tabs.find(t => t.key === activeTab);
                return tab ? <tab.icon className="h-6 w-6 text-muted-foreground" /> : null;
              })()}
            </div>
            <p className="text-sm font-medium text-foreground">
              {tabs.find(t => t.key === activeTab)?.label}
            </p>
            <p className="text-xs text-muted-foreground">
              Integração com módulo disponível. Os dados serão carregados automaticamente.
            </p>
          </div>
        )}
      </div>
    </FeatureGate>
  );
}

function Stat({ label, value, pending }: { label: string; value: string; pending: boolean }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={cn('text-sm font-semibold tabular-nums', pending ? 'text-orange-400' : 'text-emerald-400')}>
        {value}
      </p>
    </div>
  );
}
