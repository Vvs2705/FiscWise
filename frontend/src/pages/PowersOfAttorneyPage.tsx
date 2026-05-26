import { useState } from 'react';
import {
  FileText, Plus, Search, AlertTriangle, CheckCircle2,
  Clock, ChevronRight,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { PageHeader } from '@/components/ui/PageHeader';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { MetricCard, EmptyState, WarningPanel } from '@/components/ui/OperationalStates';
import { FeatureGate } from '@/components/ui/FeatureGate';
import { cn } from '@/lib/utils';

interface PowerOfAttorney {
  id: string;
  clientId: string;
  clientName: string;
  cnpjGrantor: string;
  cnpjAttorney: string;
  services: string[];
  validUntil: string;
  status: 'pending' | 'active' | 'expired' | 'revoked' | 'invalid' | 'unknown';
  provider: string;
  lastVerified: string;
  notes?: string;
}

const MOCK_POWERS: PowerOfAttorney[] = [
  {
    id: 'pow-001',
    clientId: 'cli-001',
    clientName: 'Tech Solutions Ltda',
    cnpjGrantor: '12.345.678/0001-90',
    cnpjAttorney: '00.111.222/0001-33',
    services: ['Consulta de pendências', 'Emissão de certidões', 'DAS/DARF'],
    validUntil: '2026-06-10',
    status: 'active',
    provider: 'e-CAC Receita Federal',
    lastVerified: '2026-05-20T09:00:00Z',
  },
  {
    id: 'pow-002',
    clientId: 'cli-002',
    clientName: 'Comércio São Paulo ME',
    cnpjGrantor: '98.765.432/0001-11',
    cnpjAttorney: '00.111.222/0001-33',
    services: ['Simples Nacional', 'Consulta de pendências'],
    validUntil: '2026-12-31',
    status: 'active',
    provider: 'e-CAC Receita Federal',
    lastVerified: '2026-05-25T10:00:00Z',
  },
  {
    id: 'pow-003',
    clientId: 'cli-003',
    clientName: 'Construtora Horizonte SA',
    cnpjGrantor: '11.222.333/0001-44',
    cnpjAttorney: '00.111.222/0001-33',
    services: ['REFIS', 'Parcelamentos', 'Consulta de pendências'],
    validUntil: '2026-03-01',
    status: 'expired',
    provider: 'PGFN',
    lastVerified: '2026-04-01T08:00:00Z',
    notes: 'Vencida — cliente precisa renovar',
  },
  {
    id: 'pow-004',
    clientId: 'cli-004',
    clientName: 'Clínica Saúde Total Ltda',
    cnpjGrantor: '55.666.777/0001-22',
    cnpjAttorney: '00.111.222/0001-33',
    services: ['Consulta de pendências', 'Caixa postal'],
    validUntil: '2026-11-15',
    status: 'active',
    provider: 'e-CAC Receita Federal',
    lastVerified: '2026-05-26T08:00:00Z',
  },
  {
    id: 'pow-005',
    clientId: 'cli-005',
    clientName: 'Agência Digital Express ME',
    cnpjGrantor: '33.444.555/0001-66',
    cnpjAttorney: '—',
    services: [],
    validUntil: '—',
    status: 'pending',
    provider: '—',
    lastVerified: '—',
    notes: 'Cliente ainda não assinou a procuração digital',
  },
];

const STATUS_OPTIONS = [
  { value: 'all', label: 'Todos' },
  { value: 'active', label: 'Ativas' },
  { value: 'pending', label: 'Pendentes' },
  { value: 'expired', label: 'Vencidas' },
  { value: 'revoked', label: 'Revogadas' },
];

function daysUntil(dateStr: string): number {
  if (dateStr === '—') return 9999;
  const diff = new Date(dateStr).getTime() - new Date().getTime();
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

export function PowersOfAttorneyPage() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  const filtered = MOCK_POWERS.filter(p => {
    if (statusFilter !== 'all' && p.status !== statusFilter) return false;
    if (search && !p.clientName.toLowerCase().includes(search.toLowerCase()) &&
        !p.cnpjGrantor.includes(search)) return false;
    return true;
  });

  const activeCount = MOCK_POWERS.filter(p => p.status === 'active').length;
  const expiredCount = MOCK_POWERS.filter(p => p.status === 'expired').length;
  const expiringSoon = MOCK_POWERS.filter(p => p.status === 'active' && daysUntil(p.validUntil) <= 30).length;
  const pendingCount = MOCK_POWERS.filter(p => p.status === 'pending').length;

  return (
    <FeatureGate feature="feature_powers_of_attorney">
      <div className="space-y-6 p-6">
        <PageHeader
          title="Procurações"
          subtitle="Gerencie as procurações digitais de todos os clientes."
          icon={<FileText className="h-5 w-5" />}
          actions={
            <Link
              to="/procuracoes/nova"
              className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:opacity-90 transition-opacity"
            >
              <Plus className="h-4 w-4" />
              Nova procuração
            </Link>
          }
        />

        {/* Alert vencidas */}
        {expiredCount > 0 && (
          <WarningPanel
            title={`${expiredCount} procuração${expiredCount > 1 ? 'ões' : ''} vencida${expiredCount > 1 ? 's' : ''}`}
            description="Procurações vencidas bloqueiam consultas e-CAC, emissão de guias e caixa postal fiscal."
            variant="danger"
          />
        )}
        {expiringSoon > 0 && (
          <WarningPanel
            title={`${expiringSoon} procuração${expiringSoon > 1 ? 'ões' : ''} vencendo em 30 dias`}
            description="Renove antes do vencimento para evitar interrupção dos serviços."
            variant="warning"
          />
        )}

        {/* Metrics */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <MetricCard title="Ativas" value={activeCount} icon={<CheckCircle2 className="h-4 w-4" />} variant="success" />
          <MetricCard title="Vencendo em 30d" value={expiringSoon} icon={<Clock className="h-4 w-4" />} variant="warning" />
          <MetricCard title="Vencidas" value={expiredCount} icon={<AlertTriangle className="h-4 w-4" />} variant="danger" />
          <MetricCard title="Pendentes" value={pendingCount} icon={<Clock className="h-4 w-4" />} variant="default" />
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Buscar por cliente ou CNPJ..."
              className="w-full rounded-lg border border-border bg-card py-2 pl-9 pr-4 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
            />
          </div>
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            className="rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
          >
            {STATUS_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>

        {/* Table */}
        {filtered.length === 0 ? (
          <EmptyState
            icon={<FileText className="h-6 w-6" />}
            title="Nenhuma procuração encontrada"
            description="Cadastre procurações para habilitar consultas e-CAC e emissão de guias."
            action={
              <Link
                to="/procuracoes/nova"
                className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:opacity-90 transition-opacity"
              >
                Cadastrar procuração
              </Link>
            }
          />
        ) : (
          <div className="overflow-hidden rounded-xl border border-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/30">
                  <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground">Cliente</th>
                  <th className="hidden px-4 py-3 text-left text-xs font-semibold text-muted-foreground md:table-cell">Serviços</th>
                  <th className="hidden px-4 py-3 text-left text-xs font-semibold text-muted-foreground lg:table-cell">Provider</th>
                  <th className="hidden px-4 py-3 text-left text-xs font-semibold text-muted-foreground sm:table-cell">Validade</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground">Status</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-muted-foreground">Ações</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(pow => {
                  const days = daysUntil(pow.validUntil);
                  const expiring = pow.status === 'active' && days <= 30;
                  return (
                    <tr key={pow.id} className="border-b border-border/50 last:border-0 transition-colors hover:bg-muted/20">
                      <td className="px-4 py-3">
                        <div>
                          <p className="font-medium text-foreground">{pow.clientName}</p>
                          <p className="text-xs text-muted-foreground">{pow.cnpjGrantor}</p>
                          {pow.notes && <p className="text-xs text-orange-400 mt-0.5">{pow.notes}</p>}
                        </div>
                      </td>
                      <td className="hidden px-4 py-3 md:table-cell">
                        <div className="flex flex-wrap gap-1">
                          {pow.services.slice(0, 2).map(s => (
                            <span key={s} className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">{s}</span>
                          ))}
                          {pow.services.length > 2 && (
                            <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">+{pow.services.length - 2}</span>
                          )}
                        </div>
                      </td>
                      <td className="hidden px-4 py-3 text-xs text-muted-foreground lg:table-cell">{pow.provider}</td>
                      <td className="hidden px-4 py-3 sm:table-cell">
                        <div>
                          <p className={cn('text-xs', expiring ? 'text-orange-400 font-semibold' : 'text-muted-foreground')}>
                            {pow.validUntil === '—' ? '—' : new Date(pow.validUntil).toLocaleDateString('pt-BR')}
                          </p>
                          {expiring && <p className="text-[10px] text-orange-400/80">em {days} dias</p>}
                        </div>
                      </td>
                      <td className="px-4 py-3"><StatusBadge status={pow.status} /></td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-2">
                          {(pow.status === 'expired' || expiring) && (
                            <button className="rounded-lg border border-orange-500/30 px-2.5 py-1 text-xs font-medium text-orange-400 hover:bg-orange-500/10 transition-colors">
                              Renovar
                            </button>
                          )}
                          <Link
                            to={`/procuracoes/${pow.id}`}
                            className="rounded p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                          >
                            <ChevronRight className="h-3.5 w-3.5" />
                          </Link>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </FeatureGate>
  );
}
