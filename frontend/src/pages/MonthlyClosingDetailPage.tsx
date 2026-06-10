import { useState, ElementType } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, Link } from 'react-router-dom';
import {
  CalendarCheck2, CheckCircle2, Circle, MinusCircle,
  AlertTriangle, Download, Loader2, FileText, Coins,
  ListChecks, Shield, ChevronRight,
} from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { FeatureGate } from '@/components/ui/FeatureGate';
import { fetchMonthlyClosing, updateChecklistItem, generateDossier, downloadDossierPdf } from '@/features/monthly-closing/api';
import { ChecklistItem, MonthlyClosing } from '@/features/monthly-closing/types';
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
      const fileName = closing
        ? `dossie-${closing.clientName.replace(/\s+/g, '-').toLowerCase()}-${closing.competence}.pdf`
        : undefined;
      await downloadDossierPdf(id, fileName);
      qc.invalidateQueries({ queryKey: ['monthly-closing', id] });
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

        {activeTab === 'notas' && <TabNotas closing={closing} />}
        {activeTab === 'guias' && <TabGuias closing={closing} />}
        {activeTab === 'obrigacoes' && <TabObrigacoes closing={closing} />}
        {activeTab === 'ecac' && <TabEcac closing={closing} />}
        {activeTab === 'dossie' && (
          <TabDossie
            closing={closing}
            onGenerate={handleGenerateDossier}
            generating={generatingDossier}
          />
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

/* ─── Per-tab sub-components ────────────────────────────────────────────── */

function TabLinkCard({
  title,
  description,
  linkTo,
  linkLabel,
  icon: Icon,
  stats,
  allDone,
}: {
  title: string;
  description: string;
  linkTo: string;
  linkLabel: string;
  icon: ElementType;
  stats: { label: string; value: string; ok: boolean }[];
  allDone: boolean;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div className="flex items-center gap-3">
          <div className={cn(
            'flex h-10 w-10 items-center justify-center rounded-lg',
            allDone ? 'bg-emerald-500/10' : 'bg-orange-500/10',
          )}>
            <Icon className={cn('h-5 w-5', allDone ? 'text-emerald-400' : 'text-orange-400')} />
          </div>
          <div>
            <h3 className="font-semibold text-foreground">{title}</h3>
            <p className="text-xs text-muted-foreground">{description}</p>
          </div>
        </div>
        {allDone
          ? <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-400" />
          : <AlertTriangle className="h-5 w-5 shrink-0 text-orange-400" />}
      </div>

      <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {stats.map(s => (
          <div key={s.label} className="rounded-lg bg-muted/30 px-3 py-2">
            <p className="text-xs text-muted-foreground">{s.label}</p>
            <p className={cn('text-sm font-bold tabular-nums', s.ok ? 'text-emerald-400' : 'text-orange-400')}>{s.value}</p>
          </div>
        ))}
      </div>

      <Link
        to={linkTo}
        className="flex items-center gap-2 text-sm font-medium text-primary hover:text-primary/80 transition-colors"
      >
        {linkLabel}
        <ChevronRight className="h-4 w-4" />
      </Link>
    </div>
  );
}

function TabNotas({ closing }: { closing: MonthlyClosing }) {
  const done = closing.invoicesCount - closing.invoicesPending;
  return (
    <TabLinkCard
      title="Notas Fiscais"
      description={`Competência ${closing.competence}`}
      linkTo="/notas-fiscais"
      linkLabel="Abrir módulo de notas fiscais"
      icon={FileText}
      allDone={closing.invoicesPending === 0}
      stats={[
        { label: 'Emitidas', value: String(done), ok: true },
        { label: 'Pendentes', value: String(closing.invoicesPending), ok: closing.invoicesPending === 0 },
        { label: 'Total', value: String(closing.invoicesCount), ok: true },
        { label: 'Situação', value: closing.invoicesPending === 0 ? 'OK' : 'Pendente', ok: closing.invoicesPending === 0 },
      ]}
    />
  );
}

function TabGuias({ closing }: { closing: MonthlyClosing }) {
  const pending = closing.guidesCount - closing.guidesPaid;
  return (
    <TabLinkCard
      title="Guias de Impostos"
      description={`Competência ${closing.competence}`}
      linkTo="/guias"
      linkLabel="Abrir módulo de guias"
      icon={Coins}
      allDone={pending === 0}
      stats={[
        { label: 'Pagas', value: String(closing.guidesPaid), ok: true },
        { label: 'Pendentes', value: String(pending), ok: pending === 0 },
        { label: 'Total', value: String(closing.guidesCount), ok: true },
        { label: 'Situação', value: pending === 0 ? 'Quitado' : 'Em aberto', ok: pending === 0 },
      ]}
    />
  );
}

function TabObrigacoes({ closing }: { closing: MonthlyClosing }) {
  const pending = closing.obligationsTotal - closing.obligationsDone;
  return (
    <TabLinkCard
      title="Obrigações Acessórias"
      description={`Competência ${closing.competence}`}
      linkTo="/obrigacoes"
      linkLabel="Abrir módulo de obrigações"
      icon={ListChecks}
      allDone={pending === 0}
      stats={[
        { label: 'Cumpridas', value: String(closing.obligationsDone), ok: true },
        { label: 'Pendentes', value: String(pending), ok: pending === 0 },
        { label: 'Total', value: String(closing.obligationsTotal), ok: true },
        { label: 'Situação', value: pending === 0 ? 'OK' : 'Pendente', ok: pending === 0 },
      ]}
    />
  );
}

function TabEcac({ closing }: { closing: MonthlyClosing }) {
  return (
    <TabLinkCard
      title="e-CAC / Situação Fiscal"
      description={`Pendências identificadas na última consulta`}
      linkTo="/ecac"
      linkLabel="Abrir central e-CAC"
      icon={Shield}
      allDone={closing.ecacPendencies === 0}
      stats={[
        { label: 'Pendências', value: String(closing.ecacPendencies), ok: closing.ecacPendencies === 0 },
        { label: 'Bloqueios', value: String(closing.blockers.length), ok: closing.blockers.length === 0 },
        { label: 'Status', value: closing.ecacPendencies === 0 ? 'Regular' : 'Irregular', ok: closing.ecacPendencies === 0 },
        { label: 'Consulta', value: 'e-CAC', ok: true },
      ]}
    />
  );
}

function TabDossie({
  closing,
  onGenerate,
  generating,
}: {
  closing: MonthlyClosing;
  onGenerate: () => void;
  generating: boolean;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-6 space-y-4">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
          <Download className="h-5 w-5 text-primary" />
        </div>
        <div>
          <h3 className="font-semibold text-foreground">Dossiê do Fechamento</h3>
          <p className="text-xs text-muted-foreground">
            Compila notas, guias, obrigações e checklist em um único documento PDF.
          </p>
        </div>
      </div>

      {closing.dossierGeneratedAt ? (
        <div className="flex items-center gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-4 py-3">
          <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
          <p className="text-sm text-emerald-300">
            Dossiê gerado em {new Date(closing.dossierGeneratedAt).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
          </p>
        </div>
      ) : (
        <div className="flex items-center gap-2 rounded-lg border border-orange-500/20 bg-orange-500/5 px-4 py-3">
          <AlertTriangle className="h-4 w-4 text-orange-400 shrink-0" />
          <p className="text-sm text-orange-300">Dossiê ainda não foi gerado para este fechamento.</p>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 text-sm">
        {[
          { label: 'Cliente', value: closing.clientName },
          { label: 'Competência', value: closing.competence },
          { label: 'Score', value: `${closing.score}%` },
          { label: 'Status', value: closing.status },
        ].map(item => (
          <div key={item.label} className="rounded-lg bg-muted/30 px-3 py-2">
            <p className="text-xs text-muted-foreground">{item.label}</p>
            <p className="text-sm font-medium text-foreground">{item.value}</p>
          </div>
        ))}
      </div>

      <button
        onClick={onGenerate}
        disabled={generating}
        className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-50"
      >
        {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
        {closing.dossierGeneratedAt ? 'Regerar dossiê' : 'Gerar dossiê'}
      </button>
    </div>
  );
}
