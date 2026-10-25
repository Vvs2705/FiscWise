import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Globe, FileText, CheckCircle2, Clock,
  AlertTriangle, Coins, Bell, Loader2, LogOut,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { MetricCard } from '@/components/ui/OperationalStates';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { useAuthStore } from '@/stores/authStore';
import { fetchMyPortal } from '@/features/portal/api';
import { PORTAL_LOGIN } from '@/features/portal/access';
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Portal do cliente final — a tela que o cliente vê depois do link mágico.
// Só leitura: os dados vêm de /portal/my-overview, que o backend resolve pelo
// usuário logado (o cliente nunca escolhe qual cliente ver).
// ---------------------------------------------------------------------------

const PORTAL_TABS = [
  { key: 'overview', label: 'Visão Geral', icon: Globe },
  { key: 'documents', label: 'Documentos', icon: FileText },
  { key: 'guides', label: 'Guias', icon: Coins },
  { key: 'pending', label: 'Pendências', icon: Bell },
] as const;

type PortalTab = typeof PORTAL_TABS[number]['key'];

const MONTH_LABELS = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];

function competenceLabel(competence: string | null | undefined): string {
  if (!competence || competence.length < 7) return '—';
  const month = Number(competence.slice(5, 7));
  return `${MONTH_LABELS[month - 1] ?? competence}/${competence.slice(0, 4)}`;
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(w => w[0]!.toUpperCase())
    .join('');
}

export function PortalDashboardPage() {
  const [activeTab, setActiveTab] = useState<PortalTab>('overview');
  const logout = useAuthStore((state) => state.logout);

  const { data: portal, isLoading, error } = useQuery({
    queryKey: ['portal-my-overview'],
    queryFn: fetchMyPortal,
  });

  const pendingDocuments = useMemo(
    () => (portal?.documents ?? []).filter(d => d.status === 'pending').length,
    [portal?.documents],
  );
  const openGuides = useMemo(
    () => (portal?.guides ?? []).filter(g => !['paid', 'paga'].includes(g.status)).length,
    [portal?.guides],
  );
  const pendencies = portal?.pendencies ?? [];

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card">
        <div className="mx-auto flex max-w-4xl items-center justify-between gap-3 px-4 py-3">
          <div className="flex items-center gap-2">
            <Globe className="h-5 w-5 text-primary" />
            <span className="text-sm font-semibold text-foreground">Portal do Cliente</span>
            <span className="text-xs text-muted-foreground">· FiscWise</span>
          </div>
          <Button variant="outline" size="sm" onClick={() => logout(PORTAL_LOGIN)}>
            <LogOut className="mr-1.5 h-3.5 w-3.5" />
            Sair
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-4xl space-y-6 px-4 py-6">
        {isLoading ? (
          <div className="flex items-center justify-center py-24">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        ) : error || !portal ? (
          <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-4 text-sm text-destructive">
            Não foi possível carregar seus dados. Tente novamente ou fale com seu escritório contábil.
          </div>
        ) : (
          <>
            <div className="flex items-center gap-3 rounded-xl border border-border bg-card p-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/20 text-sm font-bold text-primary">
                {initials(portal.client.name)}
              </div>
              <div>
                <p className="text-sm font-semibold text-foreground">{portal.client.name}</p>
                <p className="text-xs text-muted-foreground">{portal.client.document ?? 'Sem documento cadastrado'}</p>
              </div>
            </div>

            <div className="flex gap-1 overflow-x-auto border-b border-border" role="tablist">
              {PORTAL_TABS.map(tab => (
                <button
                  key={tab.key}
                  role="tab"
                  aria-selected={activeTab === tab.key}
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
                  {tab.key === 'pending' && pendencies.length > 0 && (
                    <span className="ml-1 rounded-full bg-destructive/20 px-1.5 text-[10px] font-bold text-destructive">
                      {pendencies.length}
                    </span>
                  )}
                </button>
              ))}
            </div>

            {activeTab === 'overview' && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <MetricCard
                    title="Fechamento"
                    value={portal.closing ? `${portal.closing.score}%` : '—'}
                    icon={<CheckCircle2 className="h-4 w-4" />}
                    variant={portal.closing && portal.closing.score >= 80 ? 'success' : 'warning'}
                    subtitle={portal.closing ? competenceLabel(portal.closing.competence) : 'Sem fechamento'}
                  />
                  <MetricCard title="Documentos pendentes" value={pendingDocuments} icon={<FileText className="h-4 w-4" />} variant={pendingDocuments > 0 ? 'warning' : 'default'} />
                  <MetricCard title="Ações necessárias" value={pendencies.length} icon={<Bell className="h-4 w-4" />} variant={pendencies.length > 0 ? 'danger' : 'default'} />
                  <MetricCard title="Guias em aberto" value={openGuides} icon={<Coins className="h-4 w-4" />} variant={openGuides > 0 ? 'warning' : 'default'} />
                </div>

                {portal.closing ? (
                  <div className="rounded-xl border border-border bg-card p-5">
                    <h3 className="mb-3 text-sm font-semibold text-foreground">
                      Situação do fechamento — {competenceLabel(portal.closing.competence)}
                    </h3>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                      <div
                        className={cn(
                          'h-full rounded-full transition-all',
                          portal.closing.score >= 80 ? 'bg-success' : portal.closing.score >= 50 ? 'bg-warning' : 'bg-destructive',
                        )}
                        style={{ width: `${portal.closing.score}%` }}
                      />
                    </div>
                    <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
                      <span>{portal.closing.score}% concluído</span>
                      <StatusBadge status={portal.closing.status} />
                    </div>
                  </div>
                ) : (
                  <div className="rounded-xl border border-border bg-card p-5 text-sm text-muted-foreground">
                    Seu escritório ainda não iniciou o fechamento do mês.
                  </div>
                )}
              </div>
            )}

            {activeTab === 'documents' && (
              <div className="space-y-3">
                <p className="text-sm text-muted-foreground">Documentos registrados pelo seu escritório.</p>
                {portal.documents.length === 0 ? (
                  <p className="py-8 text-center text-sm text-muted-foreground">Nenhum documento registrado.</p>
                ) : (
                  portal.documents.map(doc => (
                    <div key={doc.id} className="flex items-center gap-3 rounded-lg border border-border bg-card p-4">
                      <div className={cn(
                        'flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
                        doc.status === 'pending' ? 'bg-warning/10 text-warning' : 'bg-success/10 text-success',
                      )}>
                        {doc.status === 'pending' ? <Clock className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-foreground">{doc.name}</p>
                        {doc.requestedAt && (
                          <p className="text-xs text-muted-foreground">
                            Registrado em {new Date(doc.requestedAt).toLocaleDateString('pt-BR')}
                          </p>
                        )}
                      </div>
                      <StatusBadge status={doc.status} />
                    </div>
                  ))
                )}
              </div>
            )}

            {activeTab === 'guides' && (
              <div className="space-y-3">
                <p className="text-sm text-muted-foreground">Guias de pagamento geradas para você.</p>
                {portal.guides.length === 0 ? (
                  <p className="py-8 text-center text-sm text-muted-foreground">Nenhuma guia registrada.</p>
                ) : (
                  portal.guides.map(guide => (
                    <div key={guide.id} className="flex items-center gap-3 rounded-lg border border-border bg-card p-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-medium text-foreground">{guide.type}</p>
                          <StatusBadge status={guide.status} />
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {competenceLabel(guide.competence)}
                          {guide.due && ` · Vencimento: ${new Date(guide.due).toLocaleDateString('pt-BR')}`}
                        </p>
                      </div>
                      <p className="text-sm font-semibold tabular-nums text-foreground">
                        {guide.value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                      </p>
                    </div>
                  ))
                )}
              </div>
            )}

            {activeTab === 'pending' && (
              <div className="space-y-3">
                <p className="text-sm text-muted-foreground">Pendências em aberto com o seu escritório.</p>
                {pendencies.length === 0 ? (
                  <p className="py-8 text-center text-sm text-muted-foreground">Nenhuma pendência em aberto. Tudo em dia!</p>
                ) : (
                  pendencies.map(p => (
                    <div key={p.id} className="flex items-center gap-3 rounded-lg border border-warning/20 bg-warning/5 p-4">
                      <AlertTriangle className="h-4 w-4 shrink-0 text-warning" />
                      <div className="flex-1">
                        <p className="text-sm font-medium text-foreground">{p.title}</p>
                        {p.deadline && (
                          <p className="text-xs text-muted-foreground">
                            Prazo: {new Date(p.deadline).toLocaleDateString('pt-BR')}
                          </p>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}

export default PortalDashboardPage;
