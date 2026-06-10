import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Globe, FileText, CheckCircle2, Clock,
  AlertTriangle, Coins, Bell, Loader2,
} from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { MetricCard } from '@/components/ui/OperationalStates';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { FeatureGate } from '@/components/ui/FeatureGate';
import { useClients } from '@/lib/hooks/useOperations';
import { fetchPortalPreview } from '@/features/portal/api';
import { cn } from '@/lib/utils';

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

export function PortalClientePage() {
  const [activeTab, setActiveTab] = useState<PortalTab>('overview');
  const [selectedClientId, setSelectedClientId] = useState<string | null>(null);

  const { data: clients, isLoading: clientsLoading } = useClients();
  const clientId = selectedClientId ?? clients?.[0]?.id ?? null;

  const { data: preview, isLoading, error } = useQuery({
    queryKey: ['portal-preview', clientId],
    queryFn: () => fetchPortalPreview(clientId!),
    enabled: !!clientId,
  });

  const pendingDocuments = useMemo(
    () => (preview?.documents ?? []).filter(d => d.status === 'pending').length,
    [preview?.documents],
  );
  const openGuides = useMemo(
    () => (preview?.guides ?? []).filter(g => !['paid', 'paga'].includes(g.status)).length,
    [preview?.guides],
  );
  const pendencies = preview?.pendencies ?? [];

  return (
    <FeatureGate feature="feature_portal_client">
      <div className="space-y-6 p-6">
        <PageHeader
          title="Portal do Cliente"
          subtitle="Visualize o portal como seus clientes o veem. Gerencie solicitações e documentos."
          icon={<Globe className="h-5 w-5" />}
          actions={
            <select
              value={clientId ?? ''}
              onChange={e => setSelectedClientId(e.target.value)}
              aria-label="Selecionar cliente para visualizar o portal"
              className="rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
            >
              {(clients ?? []).map(c => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          }
        />

        {clientsLoading || (isLoading && !!clientId) ? (
          <div className="flex items-center justify-center py-24">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        ) : !clientId ? (
          <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
            <Globe className="h-8 w-8 text-muted-foreground/30" />
            <p className="text-sm font-medium text-foreground">Nenhum cliente cadastrado</p>
            <p className="text-xs text-muted-foreground">
              Cadastre um cliente para visualizar o portal dele.
            </p>
          </div>
        ) : error || !preview ? (
          <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-4 text-sm text-red-300">
            Erro ao carregar o portal deste cliente. Tente novamente.
          </div>
        ) : (
          <>
            {/* Client preview banner */}
            <div className="flex items-center justify-between rounded-xl border border-primary/30 bg-primary/5 p-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/20 text-primary font-bold text-sm">
                  {initials(preview.client.name)}
                </div>
                <div>
                  <p className="text-sm font-semibold text-foreground">{preview.client.name}</p>
                  <p className="text-xs text-muted-foreground">{preview.client.document ?? 'Sem documento cadastrado'}</p>
                </div>
              </div>
              <span className="rounded-full bg-primary/20 px-2.5 py-1 text-xs font-medium text-primary">Modo preview</span>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 overflow-x-auto border-b border-border">
              {PORTAL_TABS.map(tab => (
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
                  {tab.key === 'pending' && pendencies.length > 0 && (
                    <span className="ml-1 rounded-full bg-red-500/20 px-1.5 text-[10px] font-bold text-red-400">
                      {pendencies.length}
                    </span>
                  )}
                </button>
              ))}
            </div>

            {/* Tab: Overview */}
            {activeTab === 'overview' && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <MetricCard
                    title="Fechamento"
                    value={preview.closing ? `${preview.closing.score}%` : '—'}
                    icon={<CheckCircle2 className="h-4 w-4" />}
                    variant={preview.closing && preview.closing.score >= 80 ? 'success' : 'warning'}
                    subtitle={preview.closing ? competenceLabel(preview.closing.competence) : 'Sem fechamento'}
                  />
                  <MetricCard title="Documentos pendentes" value={pendingDocuments} icon={<FileText className="h-4 w-4" />} variant={pendingDocuments > 0 ? 'warning' : 'default'} />
                  <MetricCard title="Ações necessárias" value={pendencies.length} icon={<Bell className="h-4 w-4" />} variant={pendencies.length > 0 ? 'danger' : 'default'} />
                  <MetricCard title="Guias em aberto" value={openGuides} icon={<Coins className="h-4 w-4" />} variant={openGuides > 0 ? 'warning' : 'default'} />
                </div>

                {preview.closing ? (
                  <div className="rounded-xl border border-border bg-card p-5">
                    <h3 className="mb-3 text-sm font-semibold text-foreground">
                      Situação do fechamento — {competenceLabel(preview.closing.competence)}
                    </h3>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                      <div
                        className={cn(
                          'h-full rounded-full transition-all',
                          preview.closing.score >= 80 ? 'bg-emerald-500' : preview.closing.score >= 50 ? 'bg-yellow-500' : 'bg-red-500',
                        )}
                        style={{ width: `${preview.closing.score}%` }}
                      />
                    </div>
                    <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
                      <span>{preview.closing.score}% concluído</span>
                      <StatusBadge status={preview.closing.status} />
                    </div>
                  </div>
                ) : (
                  <div className="rounded-xl border border-border bg-card p-5 text-sm text-muted-foreground">
                    Nenhum fechamento gerado para este cliente ainda.{' '}
                    <Link to="/fechamento" className="text-primary hover:underline">Gerar rotina mensal</Link>
                  </div>
                )}
              </div>
            )}

            {/* Tab: Documents */}
            {activeTab === 'documents' && (
              <div className="space-y-3">
                <p className="text-sm text-muted-foreground">Documentos do cliente no dossiê.</p>
                {preview.documents.length === 0 ? (
                  <p className="py-8 text-center text-sm text-muted-foreground">Nenhum documento registrado para este cliente.</p>
                ) : (
                  preview.documents.map(doc => (
                    <div key={doc.id} className="flex items-center gap-3 rounded-lg border border-border bg-card p-4">
                      <div className={cn(
                        'flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
                        doc.status === 'pending' ? 'bg-orange-500/10 text-orange-400' : 'bg-emerald-500/10 text-emerald-400',
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

            {/* Tab: Guides */}
            {activeTab === 'guides' && (
              <div className="space-y-3">
                <p className="text-sm text-muted-foreground">Guias de pagamento geradas para o cliente.</p>
                {preview.guides.length === 0 ? (
                  <p className="py-8 text-center text-sm text-muted-foreground">
                    Nenhuma guia registrada.{' '}
                    <Link to="/guias" className="text-primary hover:underline">Registrar guia</Link>
                  </p>
                ) : (
                  preview.guides.map(guide => (
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
                      <div className="text-right">
                        <p className="text-sm font-semibold tabular-nums text-foreground">
                          {guide.value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                        </p>
                        <Link to={`/guias/${guide.id}`} className="text-xs text-primary hover:underline">
                          Ver guia
                        </Link>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Tab: Pending */}
            {activeTab === 'pending' && (
              <div className="space-y-3">
                <p className="text-sm text-muted-foreground">Pendências em aberto que envolvem este cliente.</p>
                {pendencies.length === 0 ? (
                  <p className="py-8 text-center text-sm text-muted-foreground">Nenhuma pendência em aberto. Tudo em dia!</p>
                ) : (
                  pendencies.map(p => (
                    <div key={p.id} className="flex items-center gap-3 rounded-lg border border-orange-500/20 bg-orange-500/5 p-4">
                      <AlertTriangle className="h-4 w-4 shrink-0 text-orange-400" />
                      <div className="flex-1">
                        <p className="text-sm font-medium text-foreground">{p.title}</p>
                        {p.deadline && (
                          <p className="text-xs text-muted-foreground">
                            Prazo: {new Date(p.deadline).toLocaleDateString('pt-BR')}
                          </p>
                        )}
                      </div>
                      <Link
                        to="/obrigacoes"
                        className="rounded-lg bg-orange-600/20 px-3 py-1.5 text-xs font-medium text-orange-400 hover:bg-orange-600/30 transition-colors"
                      >
                        Resolver
                      </Link>
                    </div>
                  ))
                )}
              </div>
            )}
          </>
        )}
      </div>
    </FeatureGate>
  );
}
