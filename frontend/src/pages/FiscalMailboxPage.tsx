import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Mail, Search, RefreshCw, AlertTriangle, CheckCircle2, ExternalLink } from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { StatusBadge, RiskBadge } from '@/components/ui/StatusBadge';
import { EmptyState, ErrorState, SkeletonTable } from '@/components/ui/OperationalStates';
import { FeatureGate } from '@/components/ui/FeatureGate';
import { fetchMailboxMessages, markMessageResolved } from '@/features/fiscal-mailbox/api';
import { MailboxMessage } from '@/features/fiscal-mailbox/types';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

const RISK_OPTIONS: { value: string; label: string }[] = [
  { value: 'all', label: 'Todos os riscos' },
  { value: 'critical', label: 'Crítico' },
  { value: 'high', label: 'Alto' },
  { value: 'medium', label: 'Médio' },
  { value: 'low', label: 'Baixo' },
];

const STATUS_OPTIONS = [
  { value: 'all', label: 'Todos os status' },
  { value: 'unread', label: 'Não lidas' },
  { value: 'read', label: 'Lidas' },
  { value: 'in_progress', label: 'Em andamento' },
  { value: 'resolved', label: 'Resolvidas' },
];

export function FiscalMailboxPage() {
  const [search, setSearch] = useState('');
  const [riskFilter, setRiskFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selected, setSelected] = useState<MailboxMessage | null>(null);

  const qc = useQueryClient();

  const { data: messages, isLoading, error, refetch } = useQuery({
    queryKey: ['fiscal-mailbox', riskFilter, statusFilter],
    queryFn: () => fetchMailboxMessages({ risk: riskFilter, status: statusFilter }),
  });

  const resolveMutation = useMutation({
    mutationFn: markMessageResolved,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['fiscal-mailbox'] });
      toast.success('Mensagem marcada como resolvida');
      setSelected(null);
    },
    onError: () => toast.error('Erro ao marcar como resolvida'),
  });

  const filtered = (messages ?? []).filter(m =>
    !search ||
    m.subject.toLowerCase().includes(search.toLowerCase()) ||
    m.clientName.toLowerCase().includes(search.toLowerCase())
  );

  const unreadCount = (messages ?? []).filter(m => m.status === 'unread').length;
  const criticalCount = (messages ?? []).filter(m => m.risk === 'critical').length;

  return (
    <FeatureGate feature="feature_fiscal_mailbox">
      <div className="flex h-full flex-col p-6 gap-4">
        <PageHeader
          title="Caixa Postal Fiscal"
          subtitle="Mensagens e intimações da Receita Federal, PGFN e demais órgãos."
          icon={<Mail className="h-5 w-5" />}
          breadcrumb={[{ label: 'Caixa Postal Fiscal' }]}
          actions={
            <button
              onClick={() => refetch()}
              className="flex items-center gap-2 rounded-lg bg-muted px-3 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              <RefreshCw className="h-4 w-4" />
              <span className="hidden sm:inline">Sincronizar</span>
            </button>
          }
        />

        {/* Alert banners */}
        {criticalCount > 0 && (
          <div className="flex items-center gap-3 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3">
            <AlertTriangle className="h-4 w-4 shrink-0 text-red-400" />
            <p className="text-sm text-red-300">
              <span className="font-semibold">{criticalCount} mensagem{criticalCount > 1 ? 'ns' : ''} crítica{criticalCount > 1 ? 's' : ''}</span> exigindo ação imediata.
            </p>
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-wrap gap-3">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Buscar por assunto ou cliente..."
              className="w-full rounded-lg border border-border bg-card py-2 pl-9 pr-4 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
            />
          </div>
          <select
            value={riskFilter}
            onChange={e => setRiskFilter(e.target.value)}
            className="rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
          >
            {RISK_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            className="rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
          >
            {STATUS_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>

        {/* Summary stats */}
        <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
          <span>{filtered.length} mensagem{filtered.length !== 1 ? 'ns' : ''}</span>
          {unreadCount > 0 && (
            <span className="font-medium text-orange-400">{unreadCount} não lida{unreadCount !== 1 ? 's' : ''}</span>
          )}
        </div>

        {/* Content */}
        {isLoading ? (
          <SkeletonTable rows={5} cols={5} />
        ) : error ? (
          <ErrorState description="Não foi possível carregar as mensagens. Verifique a conexão." action={
            <button onClick={() => refetch()} className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground">
              Tentar novamente
            </button>
          } />
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={<Mail className="h-6 w-6" />}
            title="Nenhuma mensagem fiscal"
            description="Nenhum cliente conectado à Caixa Postal Fiscal. Cadastre certificado e procuração para iniciar consultas oficiais."
          />
        ) : (
          <div className="overflow-hidden rounded-xl border border-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/30">
                  <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground">Assunto</th>
                  <th className="hidden px-4 py-3 text-left text-xs font-semibold text-muted-foreground sm:table-cell">Cliente</th>
                  <th className="hidden px-4 py-3 text-left text-xs font-semibold text-muted-foreground md:table-cell">Órgão</th>
                  <th className="hidden px-4 py-3 text-left text-xs font-semibold text-muted-foreground lg:table-cell">Prazo</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground">Risco</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground">Status</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-muted-foreground">Ações</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(msg => (
                  <tr
                    key={msg.id}
                    className={cn(
                      'border-b border-border/50 last:border-0 transition-colors hover:bg-muted/20 cursor-pointer',
                      msg.status === 'unread' && 'bg-primary/5',
                    )}
                    onClick={() => setSelected(msg)}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {msg.status === 'unread' && (
                          <span className="h-2 w-2 shrink-0 rounded-full bg-primary" />
                        )}
                        <span className={cn('font-medium', msg.status === 'unread' ? 'text-foreground' : 'text-muted-foreground')}>
                          {msg.subject}
                        </span>
                      </div>
                    </td>
                    <td className="hidden px-4 py-3 text-muted-foreground sm:table-cell">{msg.clientName}</td>
                    <td className="hidden px-4 py-3 text-muted-foreground md:table-cell">{msg.organ}</td>
                    <td className="hidden px-4 py-3 text-muted-foreground lg:table-cell">
                      {msg.deadline ? new Date(msg.deadline).toLocaleDateString('pt-BR') : '—'}
                    </td>
                    <td className="px-4 py-3"><RiskBadge risk={msg.risk} /></td>
                    <td className="px-4 py-3"><StatusBadge status={msg.status} /></td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={e => { e.stopPropagation(); setSelected(msg); }}
                          className="rounded p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                          title="Ver detalhes"
                        >
                          <ExternalLink className="h-3.5 w-3.5" />
                        </button>
                        {msg.status !== 'resolved' && (
                          <button
                            onClick={e => { e.stopPropagation(); resolveMutation.mutate(msg.id); }}
                            className="rounded p-1.5 text-muted-foreground hover:bg-emerald-500/10 hover:text-emerald-400 transition-colors"
                            title="Marcar como resolvida"
                          >
                            <CheckCircle2 className="h-3.5 w-3.5" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Detail drawer */}
        {selected && (
          <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60" onClick={() => setSelected(null)}>
            <div
              className="w-full max-w-2xl rounded-t-2xl sm:rounded-2xl border border-border bg-card p-6 shadow-2xl max-h-[85vh] overflow-y-auto"
              onClick={e => e.stopPropagation()}
            >
              <div className="flex items-start justify-between gap-4 mb-4">
                <div>
                  <h2 className="text-base font-semibold text-foreground">{selected.subject}</h2>
                  <p className="text-sm text-muted-foreground">{selected.clientName} · {selected.organ}</p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <RiskBadge risk={selected.risk} />
                  <StatusBadge status={selected.status} />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 mb-4 text-sm">
                <div className="rounded-lg bg-muted/30 p-3">
                  <p className="text-xs text-muted-foreground">Recebida</p>
                  <p className="font-medium">{new Date(selected.receivedAt).toLocaleDateString('pt-BR')}</p>
                </div>
                <div className="rounded-lg bg-muted/30 p-3">
                  <p className="text-xs text-muted-foreground">Prazo</p>
                  <p className="font-medium">{selected.deadline ? new Date(selected.deadline).toLocaleDateString('pt-BR') : '—'}</p>
                </div>
              </div>

              <div className="rounded-lg border border-border bg-muted/20 p-4 mb-4">
                <p className="text-xs font-semibold text-muted-foreground mb-2">MENSAGEM</p>
                <pre className="whitespace-pre-wrap font-sans text-sm text-foreground leading-relaxed">{selected.body}</pre>
              </div>

              <div className="flex flex-wrap gap-2">
                {selected.status !== 'resolved' && (
                  <button
                    onClick={() => resolveMutation.mutate(selected.id)}
                    disabled={resolveMutation.isPending}
                    className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 transition-colors disabled:opacity-50"
                  >
                    <CheckCircle2 className="h-4 w-4" />
                    Marcar resolvida
                  </button>
                )}
                <button
                  onClick={() => {
                    navigator.clipboard?.writeText(selected.id);
                    toast.info('ID da mensagem copiado.');
                  }}
                  className="flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                >
                  <ExternalLink className="h-4 w-4" />
                  Copiar ID
                </button>
                <button
                  onClick={() => setSelected(null)}
                  className="ml-auto rounded-lg px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                >
                  Fechar
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </FeatureGate>
  );
}
