'use client';

import { useState, useMemo } from 'react';
import toast from 'react-hot-toast';
import {
  CheckCircle2,
  AlertCircle,
  Clock,
  ClipboardList,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  User2,
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { EmptyState, PageSpinner, ErrorState } from '@/components/ui/StateViews';
import { RequireRole } from '@/components/RequireRole';
import { api } from '@/lib/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ObligationRule {
  id: string;
  code: string;
  name: string;
  description: string | null;
  jurisdiction: 'federal' | 'estadual' | 'municipal';
  recurrence: string;
  due_day: number | null;
  active: boolean;
}

interface ObligationInstance {
  id: string;
  client_id: string;
  rule_id: string | null;
  competence_month: string;
  due_date: string;
  status: 'pending' | 'in_progress' | 'delivered' | 'overdue' | 'cancelled';
  priority: 'low' | 'medium' | 'high' | 'critical';
  assigned_to: string | null;
  notes: string | null;
  completed_at: string | null;
  created_at: string;
}

interface Client {
  id: string;
  name: string;
  document: string | null;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const MONTHS_PT = [
  'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
  'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
];

function getCurrentMonthIso(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`;
}

function dateBR(dateStr: string): string {
  if (!dateStr) return '—';
  const [y, m, d] = dateStr.split('-');
  return `${d}/${m}/${y}`;
}

const STATUS_CONFIG: Record<string, { label: string; variant: 'success' | 'warning' | 'error' | 'default' | 'info' }> = {
  pending:     { label: 'Pendente',     variant: 'warning' },
  in_progress: { label: 'Em andamento', variant: 'info' },
  delivered:   { label: 'Entregue',     variant: 'success' },
  overdue:     { label: 'Vencido',      variant: 'error' },
  cancelled:   { label: 'Cancelado',    variant: 'default' },
};

const PRIORITY_CONFIG: Record<string, { label: string; color: string }> = {
  low:      { label: 'Baixa',    color: 'text-muted-foreground' },
  medium:   { label: 'Média',    color: 'text-blue-500' },
  high:     { label: 'Alta',     color: 'text-amber-500' },
  critical: { label: 'Crítica',  color: 'text-red-500' },
};

const JURISDICTION_LABEL: Record<string, string> = {
  federal:    'Federal',
  estadual:   'Estadual',
  municipal:  'Municipal',
};

// ---------------------------------------------------------------------------
// API hooks
// ---------------------------------------------------------------------------

function useObligationRules() {
  return useQuery<ObligationRule[]>({
    queryKey: ['obligation-rules'],
    queryFn: async () => {
      const res = await api.get('/api/v1/obligations/rules');
      return res.data;
    },
    staleTime: 10 * 60 * 1000, // 10 min — rules rarely change
  });
}

function useObligationInstances(competenceMonth: string, clientId?: string) {
  return useQuery<ObligationInstance[]>({
    queryKey: ['obligation-instances', competenceMonth, clientId],
    queryFn: async () => {
      const params: Record<string, string> = { competence_month: competenceMonth };
      if (clientId) params.client_id = clientId;
      const res = await api.get('/api/v1/obligations/instances', { params });
      return res.data;
    },
    enabled: !!competenceMonth,
  });
}

function useClients() {
  return useQuery<Client[]>({
    queryKey: ['clients'],
    queryFn: async () => {
      const res = await api.get('/api/v1/clients');
      return res.data;
    },
  });
}

function useUpdateObligationInstance() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, updates }: { id: string; updates: Partial<ObligationInstance> }) => {
      const res = await api.patch(`/api/v1/obligations/instances/${id}`, updates);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['obligation-instances'] });
    },
  });
}

function useTriggerGeneration() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ year, month }: { year: number; month: number }) => {
      const res = await api.post('/api/v1/obligations/generate', { year, month });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['obligation-instances'] });
    },
  });
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] ?? { label: status, variant: 'default' as const };
  return <Badge variant={cfg.variant}>{cfg.label}</Badge>;
}

function PriorityLabel({ priority }: { priority: string }) {
  const cfg = PRIORITY_CONFIG[priority] ?? { label: priority, color: '' };
  return <span className={`text-xs font-semibold ${cfg.color}`}>{cfg.label}</span>;
}

// ---------------------------------------------------------------------------
// Rules Reference Panel
// ---------------------------------------------------------------------------

function RulesPanel({ rules }: { rules: ObligationRule[] }) {
  const [expanded, setExpanded] = useState(false);
  const groups = useMemo(() => {
    const map: Record<string, ObligationRule[]> = {};
    rules.forEach((r) => {
      if (!map[r.jurisdiction]) map[r.jurisdiction] = [];
      map[r.jurisdiction].push(r);
    });
    return map;
  }, [rules]);

  return (
    <Card className="border-border/60 bg-card">
      <CardHeader
        className="cursor-pointer select-none"
        onClick={() => setExpanded((e) => !e)}
      >
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold">
            Catálogo de Obrigações ({rules.length} regras ativas)
          </CardTitle>
          {expanded ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
        </div>
      </CardHeader>
      {expanded && (
        <CardContent>
          <div className="space-y-4">
            {Object.entries(groups).map(([jurisdiction, jRules]) => (
              <div key={jurisdiction}>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  {JURISDICTION_LABEL[jurisdiction] ?? jurisdiction}
                </p>
                <div className="grid gap-2 sm:grid-cols-2">
                  {jRules.map((r) => (
                    <div key={r.id} className="rounded-md border border-border/60 bg-muted/20 px-3 py-2">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs font-bold text-primary">{r.code}</span>
                        <span className="text-[10px] text-muted-foreground capitalize">
                          {r.recurrence === 'monthly' ? 'Mensal' : r.recurrence === 'yearly' ? 'Anual' : r.recurrence}
                          {r.due_day ? ` • dia ${r.due_day}` : ''}
                        </span>
                      </div>
                      <p className="mt-0.5 text-xs text-foreground">{r.name}</p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export function ObrigacoesPage() {
  const [selectedMonth, setSelectedMonth] = useState<string>(getCurrentMonthIso);
  const [selectedClientId, setSelectedClientId] = useState<string>('');

  const { data: rules, isLoading: rulesLoading } = useObligationRules();
  const { data: clients, isLoading: clientsLoading } = useClients();
  const {
    data: instances,
    isLoading: instancesLoading,
    error: instancesError,
  } = useObligationInstances(selectedMonth, selectedClientId || undefined);

  const updateInstance = useUpdateObligationInstance();
  const triggerGeneration = useTriggerGeneration();

  // Build client lookup map
  const clientMap = useMemo(() => {
    const m = new Map<string, Client>();
    (clients ?? []).forEach((c) => m.set(c.id, c));
    return m;
  }, [clients]);

  // Build rule lookup map
  const ruleMap = useMemo(() => {
    const m = new Map<string, ObligationRule>();
    (rules ?? []).forEach((r) => m.set(r.id, r));
    return m;
  }, [rules]);

  // Summary stats
  const stats = useMemo(() => {
    if (!instances) return { total: 0, pending: 0, delivered: 0, overdue: 0 };
    return {
      total:     instances.length,
      pending:   instances.filter((i) => i.status === 'pending' || i.status === 'in_progress').length,
      delivered: instances.filter((i) => i.status === 'delivered').length,
      overdue:   instances.filter((i) => i.status === 'overdue').length,
    };
  }, [instances]);

  // Month selector options: current month ± 12 months
  const monthOptions = useMemo(() => {
    const options = [];
    const now = new Date();
    for (let i = -6; i <= 6; i++) {
      const d = new Date(now.getFullYear(), now.getMonth() + i, 1);
      const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`;
      const label = `${MONTHS_PT[d.getMonth()]} ${d.getFullYear()}`;
      options.push({ value: iso, label });
    }
    return options;
  }, []);

  const handleStatusChange = async (instanceId: string, newStatus: string) => {
    try {
      await updateInstance.mutateAsync({ id: instanceId, updates: { status: newStatus as ObligationInstance['status'] } });
      toast.success('Status atualizado!');
    } catch {
      toast.error('Erro ao atualizar status.');
    }
  };

  const handleTriggerGeneration = async () => {
    const [year, month] = selectedMonth.split('-').map(Number);
    try {
      const result = await triggerGeneration.mutateAsync({ year, month });
      toast.success(`Geração concluída: ${result.created} criadas, ${result.skipped} já existentes.`);
    } catch {
      toast.error('Erro ao gerar obrigações.');
    }
  };

  if (rulesLoading || clientsLoading) return <PageSpinner />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Obrigações Fiscais
          </h1>
          <p className="text-sm text-muted-foreground">
            Acompanhe e gerencie as obrigações fiscais dos seus clientes por competência
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Month filter */}
          <Select
            value={selectedMonth}
            onChange={(e) => setSelectedMonth(e.target.value)}
            className="min-w-[180px]"
          >
            {monthOptions.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </Select>

          {/* Client filter */}
          <Select
            value={selectedClientId}
            onChange={(e) => setSelectedClientId(e.target.value)}
            className="min-w-[180px]"
          >
            <option value="">Todos os clientes</option>
            {(clients ?? []).map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </Select>

          <RequireRole allowedRoles={['owner']}>
            <Button
              variant="outline"
              size="sm"
              onClick={handleTriggerGeneration}
              disabled={triggerGeneration.isPending}
              className="flex items-center gap-1.5"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${triggerGeneration.isPending ? 'animate-spin' : ''}`} />
              Gerar obrigações
            </Button>
          </RequireRole>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 sm:grid-cols-4">
        <Card className="border-border/60 bg-card">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Total</CardTitle>
            <ClipboardList className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{stats.total}</p>
            <p className="text-[10px] text-muted-foreground">obrigações no período</p>
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Pendentes</CardTitle>
            <Clock className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-amber-500">{stats.pending}</p>
            <p className="text-[10px] text-muted-foreground">aguardando ação</p>
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Entregues</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-emerald-500">{stats.delivered}</p>
            <p className="text-[10px] text-muted-foreground">concluídas no prazo</p>
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Vencidas</CardTitle>
            <AlertCircle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-red-500">{stats.overdue}</p>
            <p className="text-[10px] text-muted-foreground">com prazo expirado</p>
          </CardContent>
        </Card>
      </div>

      {/* Rules reference */}
      {rules && rules.length > 0 && <RulesPanel rules={rules} />}

      {/* Instances Table */}
      <Card className="border-border/60 bg-card overflow-hidden">
        <CardHeader className="border-b border-border/60 px-5 py-4">
          <CardTitle className="text-sm font-semibold">
            Obrigações da Competência
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {instancesLoading ? (
            <div className="flex items-center justify-center py-16">
              <div className="h-6 w-6 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            </div>
          ) : instancesError ? (
            <div className="p-6">
              <ErrorState message="Não foi possível carregar as obrigações." />
            </div>
          ) : !instances || instances.length === 0 ? (
            <div className="p-6">
              <EmptyState
                title="Nenhuma obrigação encontrada"
                description={
                  selectedClientId
                    ? 'Este cliente não possui obrigações para o período selecionado. Configure o perfil fiscal do cliente e gere as obrigações.'
                    : 'Nenhuma obrigação registrada para este período. Clique em "Gerar obrigações" para criar automaticamente com base nos perfis fiscais dos clientes.'
                }
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-border/80 bg-muted/30 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    <th className="px-5 py-3">Cliente</th>
                    <th className="px-5 py-3">Obrigação</th>
                    <th className="px-5 py-3">Âmbito</th>
                    <th className="px-5 py-3">Vencimento</th>
                    <th className="px-5 py-3">Prioridade</th>
                    <th className="px-5 py-3">Status</th>
                    <th className="px-5 py-3 text-right">Ações</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/40">
                  {instances.map((inst) => {
                    const client = clientMap.get(inst.client_id);
                    const rule = inst.rule_id ? ruleMap.get(inst.rule_id) : null;
                    return (
                      <tr key={inst.id} className="hover:bg-muted/10 transition-colors duration-150">
                        <td className="px-5 py-4">
                          <div className="flex items-center gap-2">
                            <User2 className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                            <span className="font-medium text-foreground">
                              {client?.name ?? inst.client_id.slice(0, 8)}
                            </span>
                          </div>
                        </td>
                        <td className="px-5 py-4">
                          {rule ? (
                            <div>
                              <span className="font-mono text-xs font-bold text-primary">{rule.code}</span>
                              <p className="text-xs text-muted-foreground">{rule.name}</p>
                            </div>
                          ) : (
                            <span className="text-muted-foreground">Obrigação manual</span>
                          )}
                        </td>
                        <td className="px-5 py-4 text-xs text-muted-foreground">
                          {rule ? JURISDICTION_LABEL[rule.jurisdiction] : '—'}
                        </td>
                        <td className="px-5 py-4 font-medium">
                          {dateBR(inst.due_date)}
                        </td>
                        <td className="px-5 py-4">
                          <PriorityLabel priority={inst.priority} />
                        </td>
                        <td className="px-5 py-4">
                          <StatusBadge status={inst.status} />
                        </td>
                        <td className="px-5 py-4 text-right">
                          <div className="flex items-center justify-end gap-1">
                            {inst.status !== 'delivered' && inst.status !== 'cancelled' && (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-7 px-2 text-emerald-600 hover:bg-emerald-500/10"
                                title="Marcar como entregue"
                                onClick={() => handleStatusChange(inst.id, 'delivered')}
                              >
                                <CheckCircle2 className="h-4 w-4" />
                              </Button>
                            )}
                            {inst.status === 'pending' && (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-7 px-2 text-blue-500 hover:bg-blue-500/10 text-xs"
                                onClick={() => handleStatusChange(inst.id, 'in_progress')}
                              >
                                Iniciar
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default ObrigacoesPage;
