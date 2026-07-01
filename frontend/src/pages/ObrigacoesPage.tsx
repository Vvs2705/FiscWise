'use client';

import { useState, useMemo, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { toast } from 'sonner';
import {
  CheckCircle2,
  AlertCircle,
  Clock,
  ClipboardList,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Plus,
  Search,
  X,
  Filter,
  LayoutList,
  LayoutGrid,
  Trash2,
  Play,
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { Input } from '@/components/ui/Input';
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle } from '@/components/ui/Drawer';
import { FormField } from '@/components/ui/FormField';
import { EmptyState, PageSpinner, ErrorState } from '@/components/ui/StateViews';
import { RequireRole } from '@/components/RequireRole';
import { api } from '@/lib/api';
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/Table';

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

const STATUS_CONFIG: Record<string, { label: string; variant: 'warning' | 'success' | 'error' | 'default' | 'info' }> = {
  pending:     { label: 'Pendente',     variant: 'warning' },
  in_progress: { label: 'Em andamento', variant: 'info' },
  delivered:   { label: 'Entregue',     variant: 'success' },
  overdue:     { label: 'Vencido',      variant: 'error' },
  cancelled:   { label: 'Cancelado',    variant: 'default' },
};

const PRIORITY_CONFIG: Record<string, { label: string; color: string; variant: 'default' | 'warning' | 'error' | 'success' }> = {
  low:      { label: 'Baixa',    color: 'text-muted-foreground', variant: 'default' },
  medium:   { label: 'Média',    color: 'text-info', variant: 'default' },
  high:     { label: 'Alta',     color: 'text-warning', variant: 'warning' },
  critical: { label: 'Crítica',  color: 'text-destructive', variant: 'error' },
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
    staleTime: 10 * 60 * 1000,
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

function useCreateObligationInstance() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<ObligationInstance> & { custom_name?: string }) => {
      const res = await api.post('/api/v1/obligations/instances', payload);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['obligation-instances'] });
    },
  });
}

function useDeleteObligationInstance() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/v1/obligations/instances/${id}`);
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
  const cfg = PRIORITY_CONFIG[priority] ?? { label: priority, color: '', variant: 'default' as const };
  return <Badge variant={cfg.variant}>{cfg.label}</Badge>;
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
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <ClipboardList className="h-4 w-4 text-primary" />
            Catálogo de Obrigações ({rules.length} regras ativas)
          </CardTitle>
          {expanded ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
        </div>
      </CardHeader>
      {expanded && (
        <CardContent>
          <div className="space-y-4">
            {Object.entries(groups).map(([jurisdiction, jRules]) => (
              <div key={jurisdiction} className="border-b last:border-0 pb-3 last:pb-0">
                <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                  {JURISDICTION_LABEL[jurisdiction] ?? jurisdiction}
                </p>
                <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                  {jRules.map((r) => (
                    <div key={r.id} className="rounded-lg border border-border bg-muted/10 px-3 py-2 text-xs flex flex-col justify-between hover:border-primary/30 transition-colors">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-mono text-xs font-bold text-primary">{r.code}</span>
                        <span className="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                          {r.recurrence === 'monthly' ? 'Mensal' : r.recurrence === 'yearly' ? 'Anual' : r.recurrence}
                          {r.due_day ? ` • dia ${r.due_day}` : ''}
                        </span>
                      </div>
                      <p className="mt-1.5 font-medium text-foreground">{r.name}</p>
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
// Create Obligation Drawer
// ---------------------------------------------------------------------------

interface CreateObligationDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  clients: Client[];
  rules: ObligationRule[];
  defaultCompetence: string;
}

function CreateObligationDrawer({ isOpen, onClose, clients, rules, defaultCompetence }: CreateObligationDrawerProps) {
  const createMutation = useCreateObligationInstance();
  const [clientId, setClientId] = useState('');
  const [ruleId, setRuleId] = useState('');
  const [competence, setCompetence] = useState(defaultCompetence.slice(0, 7)); // YYYY-MM
  const [dueDate, setDueDate] = useState('');
  const [priority, setPriority] = useState<'low' | 'medium' | 'high' | 'critical'>('medium');
  const [notes, setNotes] = useState('');
  const [customName, setCustomName] = useState('');

  const selectedRule = useMemo(() => rules.find((r) => r.id === ruleId), [rules, ruleId]);

  useEffect(() => {
    if (selectedRule && selectedRule.due_day && competence) {
      const [year, month] = competence.split('-').map(Number);
      const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(selectedRule.due_day).padStart(2, '0')}`;
      setDueDate(dateStr);
    }
  }, [selectedRule, competence]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!clientId) {
      toast.error('Selecione um cliente');
      return;
    }
    if (!ruleId && !customName) {
      toast.error('Informe o nome da obrigação manual');
      return;
    }
    if (!dueDate) {
      toast.error('Selecione uma data de vencimento');
      return;
    }

    const payload = {
      client_id: clientId,
      rule_id: ruleId || null,
      competence_month: `${competence}-01`,
      due_date: dueDate,
      status: 'pending' as const,
      priority,
      notes: notes || null,
      custom_name: ruleId ? undefined : customName,
    };

    try {
      await createMutation.mutateAsync(payload);
      toast.success('Obrigação criada com sucesso');
      setClientId('');
      setRuleId('');
      setDueDate('');
      setNotes('');
      setCustomName('');
      onClose();
    } catch {
      toast.error('Erro ao criar obrigação');
    }
  };

  return (
    <Drawer open={isOpen} onOpenChange={(open) => !open && onClose()} direction="right">
      <DrawerContent className="fixed inset-y-0 right-0 bottom-0 top-0 mt-0 h-full w-full max-w-lg rounded-t-none border-l border-border bg-card shadow-token flex flex-col p-6 overflow-y-auto scrollbar">
        <DrawerHeader className="px-0 pb-4 border-b">
          <DrawerTitle className="text-lg font-bold">Nova Obrigação</DrawerTitle>
        </DrawerHeader>

        <form onSubmit={handleSubmit} className="space-y-4 py-4">
          <FormField label="Cliente" required>
            <Select value={clientId} onChange={(e) => setClientId(e.target.value)}>
              <option value="">Selecione o cliente</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
          </FormField>

          <FormField label="Obrigação / Regra" required>
            <Select value={ruleId} onChange={(e) => setRuleId(e.target.value)}>
              <option value="">Obrigação Avulsa (Manual)</option>
              {rules.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.code} - {r.name}
                </option>
              ))}
            </Select>
          </FormField>

          {!ruleId && (
            <FormField label="Nome da Obrigação Avulsa" required>
              <Input
                value={customName}
                onChange={(e) => setCustomName(e.target.value)}
                placeholder="Ex: Taxa de Localização Municipal"
              />
            </FormField>
          )}

          <div className="grid grid-cols-2 gap-4">
            <FormField label="Competência (Mês/Ano)" required>
              <Input
                type="month"
                value={competence}
                onChange={(e) => setCompetence(e.target.value)}
              />
            </FormField>

            <FormField label="Vencimento" required>
              <Input
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
              />
            </FormField>
          </div>

          <FormField label="Prioridade" required>
            <Select
              value={priority}
              onChange={(e) =>
                setPriority(e.target.value as 'low' | 'medium' | 'high' | 'critical')
              }
            >
              <option value="low">Baixa</option>
              <option value="medium">Média</option>
              <option value="high">Alta</option>
              <option value="critical">Crítica</option>
            </Select>
          </FormField>

          <FormField label="Observações / Detalhes">
            <Input
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Ex: Guia consolidada anual"
            />
          </FormField>

          <div className="flex justify-end gap-3 pt-4 border-t">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? 'Salvando...' : 'Salvar Obrigação'}
            </Button>
          </div>
        </form>
      </DrawerContent>
    </Drawer>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export function ObrigacoesPage() {
  const location = useLocation();
  const [selectedMonth, setSelectedMonth] = useState<string>(getCurrentMonthIso);
  const [selectedClientId, setSelectedClientId] = useState<string>('');

  const { data: rules, isLoading: rulesLoading } = useObligationRules();
  const { data: clients, isLoading: clientsLoading } = useClients();
  const {
    data: instances,
    isLoading: instancesLoading,
    error: instancesError,
    refetch,
  } = useObligationInstances(selectedMonth, selectedClientId || undefined);

  const updateInstance = useUpdateObligationInstance();
  const deleteInstance = useDeleteObligationInstance();
  const triggerGeneration = useTriggerGeneration();

  // Filters + Views
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('');
  const [viewMode, setViewMode] = useState<'list' | 'card'>('list');
  const [createOpen, setCreateOpen] = useState(false);

  useEffect(() => {
    if ((location.state as { openCreate?: boolean } | null)?.openCreate) {
      setCreateOpen(true);
      window.history.replaceState({}, '');
    }
  }, [location.state]);

  // Search Debouncing
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearchQuery(searchQuery);
    }, 300);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  const clientMap = useMemo(() => {
    const m = new Map<string, Client>();
    (clients ?? []).forEach((c) => m.set(c.id, c));
    return m;
  }, [clients]);

  const ruleMap = useMemo(() => {
    const m = new Map<string, ObligationRule>();
    (rules ?? []).forEach((r) => m.set(r.id, r));
    return m;
  }, [rules]);

  // Filter Logic
  const filteredInstances = useMemo(() => {
    if (!instances) return [];
    const q = debouncedSearchQuery.trim().toLowerCase();

    return instances.filter((inst) => {
      if (q) {
        const client = clientMap.get(inst.client_id);
        const rule = inst.rule_id ? ruleMap.get(inst.rule_id) : null;
        const matchesClient = client ? client.name.toLowerCase().includes(q) : false;
        const matchesRuleCode = rule ? rule.code.toLowerCase().includes(q) : false;
        const matchesRuleName = rule ? rule.name.toLowerCase().includes(q) : false;
        const matchesNotes = (inst.notes ?? '').toLowerCase().includes(q);
        if (!matchesClient && !matchesRuleCode && !matchesRuleName && !matchesNotes) return false;
      }
      if (priorityFilter && inst.priority !== priorityFilter) return false;
      if (statusFilter && inst.status !== statusFilter) return false;
      return true;
    });
  }, [instances, debouncedSearchQuery, priorityFilter, statusFilter, clientMap, ruleMap]);

  const hasActiveFilters = debouncedSearchQuery.trim() !== '' || priorityFilter !== '' || statusFilter !== '';

  const clearFilters = () => {
    setSearchQuery('');
    setDebouncedSearchQuery('');
    setPriorityFilter('');
    setStatusFilter('');
  };

  const stats = useMemo(() => {
    if (!instances) return { total: 0, pending: 0, delivered: 0, overdue: 0 };
    return {
      total:     instances.length,
      pending:   instances.filter((i) => i.status === 'pending' || i.status === 'in_progress').length,
      delivered: instances.filter((i) => i.status === 'delivered').length,
      overdue:   instances.filter((i) => i.status === 'overdue').length,
    };
  }, [instances]);

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
      refetch();
    } catch {
      toast.error('Erro ao atualizar status.');
    }
  };

  const handleDeleteInstance = async (id: string) => {
    if (!confirm('Excluir esta obrigação da carteira?')) return;
    try {
      await deleteInstance.mutateAsync(id);
      toast.success('Obrigação excluída com sucesso');
      refetch();
    } catch {
      toast.error('Erro ao excluir obrigação.');
    }
  };

  const handleTriggerGeneration = async () => {
    const [year, month] = selectedMonth.split('-').map(Number);
    try {
      const result = await triggerGeneration.mutateAsync({ year, month });
      toast.success(`Geração concluída: ${result.created} criadas, ${result.skipped} já existentes.`);
      refetch();
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
          <Select
            value={selectedMonth}
            onChange={(e) => setSelectedMonth(e.target.value)}
            className="min-w-[180px] h-9"
          >
            {monthOptions.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </Select>

          <Select
            value={selectedClientId}
            onChange={(e) => setSelectedClientId(e.target.value)}
            className="min-w-[180px] h-9"
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
              className="flex items-center gap-1.5 h-9"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${triggerGeneration.isPending ? 'animate-spin' : ''}`} />
              Gerar automáticas
            </Button>
          </RequireRole>

          <Button onClick={() => setCreateOpen(true)} size="sm" className="h-9 gap-1.5">
            <Plus className="h-4 w-4" />
            Nova obrigação
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground font-mono">Total</CardTitle>
            <ClipboardList className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{stats.total}</p>
            <p className="text-[10px] text-muted-foreground">obrigações no período</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground font-mono">Pendentes</CardTitle>
            <Clock className="h-4 w-4 text-warning" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-warning">{stats.pending}</p>
            <p className="text-[10px] text-muted-foreground">aguardando ação</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground font-mono">Entregues</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-success" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-success">{stats.delivered}</p>
            <p className="text-[10px] text-muted-foreground">concluídas no prazo</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground font-mono">Vencidas</CardTitle>
            <AlertCircle className="h-4 w-4 text-destructive" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-destructive">{stats.overdue}</p>
            <p className="text-[10px] text-muted-foreground">com prazo expirado</p>
          </CardContent>
        </Card>
      </div>

      {/* Rules reference */}
      {rules && rules.length > 0 && <RulesPanel rules={rules} />}

      {/* Filters Bar */}
      {!instancesLoading && !instancesError && (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          {/* Search input */}
          <div className="relative flex-1">
            <Search
              className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none"
              aria-hidden="true"
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Buscar por obrigação, notas ou cliente..."
              className="w-full rounded-lg border border-border/80 bg-background pl-9 pr-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
              aria-label="Buscar obrigações"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>

          {/* Selects + View Mode toggles */}
          <div className="flex flex-wrap gap-2 items-center justify-between sm:justify-start">
            <div className="flex flex-wrap gap-2 items-center">
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="rounded-lg border border-border/80 bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                aria-label="Filtrar por status"
              >
                <option value="">Todos os status</option>
                <option value="pending">Pendente</option>
                <option value="in_progress">Em andamento</option>
                <option value="delivered">Entregue</option>
                <option value="overdue">Vencido</option>
                <option value="cancelled">Cancelado</option>
              </select>

              <select
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value)}
                className="rounded-lg border border-border/80 bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                aria-label="Filtrar por prioridade"
              >
                <option value="">Todas prioridades</option>
                <option value="low">Baixa</option>
                <option value="medium">Média</option>
                <option value="high">Alta</option>
                <option value="critical">Crítica</option>
              </select>

              {hasActiveFilters && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={clearFilters}
                  className="h-9 gap-1.5"
                >
                  <X className="h-3.5 w-3.5" aria-hidden="true" />
                  Limpar filtros
                </Button>
              )}
            </div>

            {/* View Mode Toggle */}
            <div className="flex items-center gap-1 border border-border/80 rounded-lg p-1 bg-card/45 backdrop-blur-sm">
              <button
                type="button"
                onClick={() => setViewMode('list')}
                className={`p-1.5 rounded-md text-xs font-bold flex items-center gap-1 transition-all ${
                  viewMode === 'list'
                    ? 'bg-primary text-primary-foreground shadow-glow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
                title="Visualização em Lista"
              >
                <LayoutList className="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                onClick={() => setViewMode('card')}
                className={`p-1.5 rounded-md text-xs font-bold flex items-center gap-1 transition-all ${
                  viewMode === 'card'
                    ? 'bg-primary text-primary-foreground shadow-glow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
                title="Visualização em Cards"
              >
                <LayoutGrid className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Instances Table / Cards */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-2 pb-3">
          <CardTitle className="text-base font-bold">Obrigações da Competência</CardTitle>
          {!instancesLoading && !instancesError && instances && (
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground font-semibold">
              <Filter className="h-3.5 w-3.5" aria-hidden="true" />
              {hasActiveFilters
                ? `${filteredInstances.length} de ${instances.length} filtradas`
                : `${instances.length} obrigações no total`}
            </span>
          )}
        </CardHeader>
        <CardContent>
          {instancesLoading ? (
            <PageSpinner />
          ) : instancesError ? (
            <ErrorState message="Não foi possível carregar as obrigações." />
          ) : filteredInstances.length === 0 ? (
            <EmptyState
              title="Nenhuma obrigação encontrada"
              description={hasActiveFilters ? "Tente redefinir seus filtros para encontrar obrigações." : "Configure o perfil fiscal dos clientes ou crie uma nova obrigação manual."}
              action={
                !hasActiveFilters ? (
                  <Button size="sm" onClick={() => setCreateOpen(true)} className="h-9">
                    Nova obrigação
                  </Button>
                ) : (
                  <Button size="sm" variant="outline" onClick={clearFilters} className="h-9">
                    Limpar filtros
                  </Button>
                )
              }
            />
          ) : viewMode === 'list' ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Obrigação</TableHead>
                  <TableHead>Cliente</TableHead>
                  <TableHead>Âmbito</TableHead>
                  <TableHead>Vencimento</TableHead>
                  <TableHead>Prioridade</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Ações</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredInstances.map((inst) => {
                  const client = clientMap.get(inst.client_id);
                  const rule = inst.rule_id ? ruleMap.get(inst.rule_id) : null;
                  const isDelivered = inst.status === 'delivered';
                  const isCancelled = inst.status === 'cancelled';

                  return (
                    <TableRow key={inst.id}>
                      <TableCell>
                        {rule ? (
                          <div>
                            <span className="font-mono text-xs font-bold text-primary">{rule.code}</span>
                            <p className="text-xs text-muted-foreground">{rule.name}</p>
                          </div>
                        ) : (
                          <div>
                            <span className="font-bold text-foreground">Avulsa</span>
                            <p className="text-xs text-muted-foreground">{inst.notes || 'Sem descrição'}</p>
                          </div>
                        )}
                      </TableCell>
                      <TableCell className="font-medium text-foreground/80 max-w-[150px] truncate" title={client?.name}>
                        {client?.name ?? 'Cliente desconhecido'}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {rule ? JURISDICTION_LABEL[rule.jurisdiction] : 'Manual'}
                      </TableCell>
                      <TableCell className="text-xs font-medium">
                        <span className={inst.status === 'overdue' ? 'text-destructive font-bold animate-pulse' : ''}>
                          {dateBR(inst.due_date)}
                        </span>
                      </TableCell>
                      <TableCell>
                        <PriorityLabel priority={inst.priority} />
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={inst.status} />
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          {!isDelivered && !isCancelled && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-8 w-8 p-0 text-success hover:bg-success/10 hover:text-success"
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
                              className="h-8 gap-1 text-primary hover:bg-primary/10 hover:text-primary px-2 text-[10px] font-bold uppercase tracking-wider"
                              title="Iniciar"
                              onClick={() => handleStatusChange(inst.id, 'in_progress')}
                            >
                              <Play className="h-3 w-3" />
                              <span>Iniciar</span>
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDeleteInstance(inst.id)}
                            className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                            title="Excluir Obrigação"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {filteredInstances.map((inst) => {
                const client = clientMap.get(inst.client_id);
                const rule = inst.rule_id ? ruleMap.get(inst.rule_id) : null;
                const isDelivered = inst.status === 'delivered';
                const isOverdue = inst.status === 'overdue';

                return (
                  <Card key={inst.id} className="flex flex-col justify-between hover:border-primary/45 group">
                    <CardHeader className="pb-2 flex flex-row justify-between items-start gap-3">
                      <div className="min-w-0">
                        {rule ? (
                          <>
                            <span className="font-mono text-[10px] text-primary font-bold">{rule.code}</span>
                            <h4 className="font-bold text-foreground text-sm leading-snug mt-1 truncate" title={rule.name}>
                              {rule.name}
                            </h4>
                          </>
                        ) : (
                          <>
                            <span className="font-bold text-xs text-muted-foreground">Avulsa</span>
                            <h4 className="font-bold text-foreground text-sm leading-snug mt-1 truncate" title={inst.notes || 'Sem descrição'}>
                              {inst.notes || 'Sem descrição'}
                            </h4>
                          </>
                        )}
                      </div>
                      <PriorityLabel priority={inst.priority} />
                    </CardHeader>
                    <CardContent className="pb-3 text-xs space-y-2 flex-1">
                      <div className="space-y-1 bg-muted/15 rounded-lg p-2 border">
                        <p className="font-medium text-foreground/90 truncate">
                          🏢 <span className="font-semibold">{client?.name ?? 'Desconhecido'}</span>
                        </p>
                        <p className="text-muted-foreground">
                          📅 Vencimento:{' '}
                          <span className={`font-semibold ${isOverdue ? 'text-destructive font-bold' : 'text-foreground'}`}>
                            {dateBR(inst.due_date)}
                          </span>
                        </p>
                        <p className="text-[10px] text-muted-foreground">
                          Âmbito: {rule ? JURISDICTION_LABEL[rule.jurisdiction] : 'Manual'}
                        </p>
                      </div>
                    </CardContent>
                    <CardFooter className="pt-2 border-t border-border/40 flex items-center justify-between gap-2">
                      <StatusBadge status={inst.status} />
                      <div className="flex items-center gap-1">
                        {!isDelivered && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleStatusChange(inst.id, 'delivered')}
                            className="h-8 gap-1 text-success hover:bg-success/10 hover:text-success text-[10px] font-bold uppercase tracking-wider"
                          >
                            <CheckCircle2 className="h-3.5 w-3.5" />
                            Entregar
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteInstance(inst.id)}
                          className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </CardFooter>
                  </Card>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Obligation Drawer */}
      <CreateObligationDrawer
        isOpen={createOpen}
        onClose={() => setCreateOpen(false)}
        clients={clients ?? []}
        rules={rules ?? []}
        defaultCompetence={selectedMonth}
      />
    </div>
  );
}

export default ObrigacoesPage;
