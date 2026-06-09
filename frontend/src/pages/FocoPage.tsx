import { useState } from 'react';
import {
  Target, AlertTriangle, Clock, Calendar, Users, Building2,
  FileText, Search, RefreshCw, Zap,
  ChevronRight,
} from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { MetricCard } from '@/components/ui/OperationalStates';
import { RiskBadge, StatusBadge } from '@/components/ui/StatusBadge';
import { FeatureGate } from '@/components/ui/FeatureGate';
import { cn } from '@/lib/utils';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';

// Mock focus items
type FocusGroup = 'critical' | 'today' | 'week' | 'waiting_client' | 'waiting_organ';
type FocusItemType = 'obligation' | 'invoice' | 'guide' | 'ecac' | 'document' | 'closing' | 'certificate' | 'power';

interface FocusItem {
  id: string;
  group: FocusGroup;
  type: FocusItemType;
  title: string;
  client: string;
  competence: string;
  deadline: string;
  risk: 'critical' | 'high' | 'medium' | 'low';
  status: string;
  responsible: string;
  primaryAction: { label: string; href?: string; onClick?: () => void };
  secondaryAction?: { label: string; href?: string };
}

const MOCK_FOCUS: FocusItem[] = [
  {
    id: 'f1', group: 'critical', type: 'obligation',
    title: 'DCTFWeb — vence hoje',
    client: 'Tech Solutions Ltda', competence: 'Mai/2026',
    deadline: 'Hoje 23:59', risk: 'critical', status: 'pending',
    responsible: 'Você',
    primaryAction: { label: 'Transmitir agora', href: '/obrigacoes' },
    secondaryAction: { label: 'Ver detalhes', href: '/obrigacoes' },
  },
  {
    id: 'f2', group: 'critical', type: 'invoice',
    title: 'NFS-e rejeitada — corrigir e reemitir',
    client: 'Comércio São Paulo ME', competence: 'Mai/2026',
    deadline: 'Hoje', risk: 'critical', status: 'rejected',
    responsible: 'Você',
    primaryAction: { label: 'Corrigir nota', href: '/notas-fiscais' },
  },
  {
    id: 'f3', group: 'critical', type: 'ecac',
    title: 'Intimação malha fina IRPJ',
    client: 'Construtora Horizonte SA', competence: '2023',
    deadline: '20/06/2026', risk: 'critical', status: 'unread',
    responsible: 'Você',
    primaryAction: { label: 'Ver intimação', href: '/caixa-postal-fiscal' },
    secondaryAction: { label: 'Criar tarefa', href: '/caixa-postal-fiscal' },
  },
  {
    id: 'f4', group: 'today', type: 'guide',
    title: 'DAS Simples — enviar ao cliente',
    client: 'Comércio São Paulo ME', competence: 'Mai/2026',
    deadline: 'Hoje', risk: 'high', status: 'generated',
    responsible: 'Você',
    primaryAction: { label: 'Enviar ao cliente', href: '/guias' },
  },
  {
    id: 'f5', group: 'today', type: 'closing',
    title: 'Iniciar fechamento mensal',
    client: 'Agência Digital Express ME', competence: 'Mai/2026',
    deadline: '31/05/2026', risk: 'medium', status: 'not_started',
    responsible: 'Você',
    primaryAction: { label: 'Abrir fechamento', href: '/fechamento' },
  },
  {
    id: 'f6', group: 'week', type: 'certificate',
    title: 'Certificado vencendo em 15 dias',
    client: 'Tech Solutions Ltda', competence: '—',
    deadline: '10/06/2026', risk: 'medium', status: 'expiring',
    responsible: 'Você',
    primaryAction: { label: 'Renovar certificado', href: '/certificados' },
  },
  {
    id: 'f7', group: 'waiting_client', type: 'document',
    title: 'Extratos bancários pendentes',
    client: 'Construtora Horizonte SA', competence: 'Mai/2026',
    deadline: '28/05/2026', risk: 'medium', status: 'pending',
    responsible: 'Cliente',
    primaryAction: { label: 'Enviar WhatsApp', href: '/whatsapp' },
    secondaryAction: { label: 'Ver documentos', href: '/documentos' },
  },
  {
    id: 'f8', group: 'waiting_organ', type: 'power',
    title: 'Procuração e-CAC — aguardando validação',
    client: 'Clínica Saúde Total Ltda', competence: '—',
    deadline: '—', risk: 'low', status: 'pending',
    responsible: 'Receita Federal',
    primaryAction: { label: 'Ver procuração', href: '/procuracoes' },
  },
];

const GROUP_CONFIG: Record<FocusGroup, { label: string; icon: typeof AlertTriangle; color: string; bg: string }> = {
  critical: { label: 'Crítico', icon: AlertTriangle, color: 'text-red-400', bg: 'border-red-500/30 bg-red-500/5' },
  today: { label: 'Hoje', icon: Clock, color: 'text-orange-400', bg: 'border-orange-500/20 bg-orange-500/5' },
  week: { label: 'Esta semana', icon: Calendar, color: 'text-yellow-400', bg: 'border-yellow-500/20 bg-yellow-500/5' },
  waiting_client: { label: 'Aguardando cliente', icon: Users, color: 'text-blue-400', bg: 'border-blue-500/20 bg-blue-500/5' },
  waiting_organ: { label: 'Aguardando órgão', icon: Building2, color: 'text-purple-400', bg: 'border-purple-500/20 bg-purple-500/5' },
};

const TYPE_ICONS: Record<FocusItemType, typeof FileText> = {
  obligation: ListChecks,
  invoice: FileText,
  guide: Coins,
  ecac: ShieldCheck,
  document: FolderKanban,
  closing: CalendarCheck2,
  certificate: Fingerprint,
  power: FileText,
};

// Import remaining icons
import { ListChecks, Coins, ShieldCheck, FolderKanban, CalendarCheck2, Fingerprint } from 'lucide-react';

export function FocoPage() {
  const [search, setSearch] = useState('');
  const [activeGroup, setActiveGroup] = useState<FocusGroup | 'all'>('all');
  const handleRefresh = () => toast.info('Lista de foco atualizada.');

  const groups = Object.entries(GROUP_CONFIG) as [FocusGroup, typeof GROUP_CONFIG[FocusGroup]][];

  const filtered = MOCK_FOCUS.filter(item => {
    if (activeGroup !== 'all' && item.group !== activeGroup) return false;
    if (search && !item.title.toLowerCase().includes(search.toLowerCase()) &&
        !item.client.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const criticalCount = MOCK_FOCUS.filter(i => i.group === 'critical').length;
  const todayCount = MOCK_FOCUS.filter(i => i.group === 'today').length;
  const waitingCount = MOCK_FOCUS.filter(i => ['waiting_client', 'waiting_organ'].includes(i.group)).length;

  return (
    <FeatureGate feature="feature_monthly_closing">
      <div className="space-y-6 p-6">
        <PageHeader
          title="Foco de Hoje"
          subtitle="O que precisa de ação imediata agora."
          icon={<Target className="h-5 w-5" />}
          actions={
            <button
              type="button"
              onClick={handleRefresh}
              aria-label="Atualizar lista de foco"
              className="flex items-center gap-2 rounded-lg bg-muted px-3 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              <RefreshCw className="h-4 w-4" />
              <span className="hidden sm:inline">Atualizar</span>
            </button>
          }
        />

        {/* Metrics */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <MetricCard title="Críticos" value={criticalCount} icon={<AlertTriangle className="h-4 w-4" />} variant="danger" />
          <MetricCard title="Vencem hoje" value={todayCount} icon={<Clock className="h-4 w-4" />} variant="warning" />
          <MetricCard title="Aguardando cliente" value={waitingCount} icon={<Users className="h-4 w-4" />} variant="default" />
          <MetricCard title="Total pendente" value={filtered.length} icon={<Target className="h-4 w-4" />} variant="default" />
        </div>

        {/* Group filter tabs */}
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setActiveGroup('all')}
            className={cn('rounded-full px-3 py-1.5 text-xs font-medium transition-colors',
              activeGroup === 'all' ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:text-foreground')}
          >
            Todos ({MOCK_FOCUS.length})
          </button>
          {groups.map(([key, cfg]) => {
            const count = MOCK_FOCUS.filter(i => i.group === key).length;
            if (count === 0) return null;
            return (
              <button
                key={key}
                onClick={() => setActiveGroup(key)}
                className={cn('flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors',
                  activeGroup === key ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:text-foreground')}
              >
                <cfg.icon className="h-3 w-3" />
                {cfg.label} ({count})
              </button>
            );
          })}
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="search"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Buscar por título ou cliente..."
            aria-label="Buscar itens de foco por título ou cliente"
            className="w-full rounded-lg border border-border bg-card py-2.5 pl-9 pr-4 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
          />
        </div>

        {/* Groups */}
        {activeGroup === 'all'
          ? groups.map(([key, cfg]) => {
              const items = filtered.filter(i => i.group === key);
              if (items.length === 0) return null;
              return (
                <FocusGroup key={key} group={key} config={cfg} items={items} />
              );
            })
          : <FocusGroup
              group={activeGroup as FocusGroup}
              config={GROUP_CONFIG[activeGroup as FocusGroup]}
              items={filtered}
            />
        }

        {filtered.length === 0 && (
          <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/10">
              <Target className="h-6 w-6 text-emerald-400" />
            </div>
            <p className="text-sm font-medium text-foreground">Nenhum item pendente</p>
            <p className="text-xs text-muted-foreground">Você está em dia. Bom trabalho!</p>
          </div>
        )}
      </div>
    </FeatureGate>
  );
}

function FocusGroup({
  config,
  items,
}: {
  group: FocusGroup;
  config: typeof GROUP_CONFIG[FocusGroup];
  items: FocusItem[];
}) {
  return (
    <div>
      <div className={cn('mb-3 flex items-center gap-2 rounded-lg border px-3 py-2', config.bg)}>
        <config.icon className={cn('h-4 w-4', config.color)} />
        <span className={cn('text-sm font-semibold', config.color)}>{config.label}</span>
        <span className="ml-auto text-xs text-muted-foreground">{items.length} item{items.length !== 1 ? 's' : ''}</span>
      </div>
      <div className="space-y-2">
        {items.map(item => <FocusItemCard key={item.id} item={item} />)}
      </div>
    </div>
  );
}

function FocusItemCard({ item }: { item: FocusItem }) {
  const Icon = TYPE_ICONS[item.type] ?? FileText;
  return (
    <div className="flex items-start gap-3 rounded-xl border border-border bg-card p-4 transition-all hover:border-primary/30 hover:shadow-sm">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-muted">
        <Icon className="h-4 w-4 text-muted-foreground" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium text-foreground">{item.title}</span>
          <RiskBadge risk={item.risk} />
          <StatusBadge status={item.status} />
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
          <span className="flex items-center gap-1"><Users className="h-3 w-3" />{item.client}</span>
          <span className="flex items-center gap-1"><Calendar className="h-3 w-3" />{item.competence}</span>
          <span className="flex items-center gap-1"><Clock className="h-3 w-3" />Prazo: {item.deadline}</span>
        </div>
      </div>
      <div className="flex shrink-0 flex-wrap items-center gap-2">
        {item.primaryAction.href ? (
          <Link
            to={item.primaryAction.href}
            className="flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground hover:opacity-90 transition-opacity"
          >
            <Zap className="h-3 w-3" />
            {item.primaryAction.label}
          </Link>
        ) : (
          <button
            onClick={item.primaryAction.onClick}
            className="flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground hover:opacity-90 transition-opacity"
          >
            <Zap className="h-3 w-3" />
            {item.primaryAction.label}
          </button>
        )}
        {item.secondaryAction?.href && (
          <Link
            to={item.secondaryAction.href}
            className="flex items-center gap-1 rounded-lg border border-border px-2.5 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            {item.secondaryAction.label}
            <ChevronRight className="h-3 w-3" />
          </Link>
        )}
      </div>
    </div>
  );
}
