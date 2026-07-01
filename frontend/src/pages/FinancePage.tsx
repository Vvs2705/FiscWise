'use client';
import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import {
  Plus,
  Trash2,
  CheckCircle2,
  TrendingDown,
  LayoutGrid,
  List,
  Search,
  DollarSign,
  CreditCard,
  AlertTriangle,
  BarChart3,
  Calendar,
  User,
  BookOpen,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, MetricCard } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Dialog } from '@/components/ui/Dialog';
import { FormField } from '@/components/ui/FormField';
import { EmptyState, ErrorState, PageSpinner } from '@/components/ui/StateViews';
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/Table';
import {
  dateBR,
  moneyBRL,
  useClients,
  useReceivables,
  useCreateReceivable,
  useUpdateReceivable,
  useDeleteReceivable,
  useInadimplenciaReport,
  type ReceivableCreate,
  type ReceivableStatus,
} from '@/lib/hooks/useOperations';
import { usePermission } from '@/lib/hooks/usePermission';
import { formatCurrencyBRL, parseCurrencyBRL } from '@/lib/utils';

const schema = z.object({
  client_id: z.string().min(1, 'Selecione um cliente'),
  description: z.string().min(2, 'Descricao deve ter ao menos 2 caracteres'),
  amount: z.preprocess(
    (val) => (typeof val === 'string' ? parseCurrencyBRL(val) : val),
    z.number().positive('Valor deve ser maior que zero')
  ),
  due_date: z.string().min(1, 'Data e obrigatoria'),
  status: z.enum(['pending', 'paid', 'overdue', 'cancelled']),
  paid_at: z.string().optional(),
  notes: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

const statusLabel: Record<ReceivableStatus, string> = {
  pending: 'Em aberto',
  paid: 'Pago',
  overdue: 'Atrasado',
  cancelled: 'Cancelado',
};

const statusVariant: Record<ReceivableStatus, 'warning' | 'success' | 'error' | 'default'> = {
  pending: 'warning',
  paid: 'success',
  overdue: 'error',
  cancelled: 'default',
};

export function FinancePage() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [selectedClient, setSelectedClient] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [viewMode, setViewMode] = useState<'list' | 'grid'>('list');

  const { data: receivables, isLoading, isError } = useReceivables();
  const { data: clients } = useClients();
  const { hasRole } = usePermission();
  const isAdminOrOwner = hasRole('admin');
  const { data: inadimplencia } = useInadimplenciaReport();
  const location = useLocation();

  // Abre o dialog automaticamente quando vindo do dashboard com state { openCreate: true }
  useEffect(() => {
    if ((location.state as { openCreate?: boolean } | null)?.openCreate) {
      setOpen(true);
      window.history.replaceState({}, '');
    }
  }, [location.state]);

  const createMutation = useCreateReceivable();
  const updateMutation = useUpdateReceivable();
  const deleteMutation = useDeleteReceivable();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { status: 'pending' },
  });

  async function onSubmit(values: FormValues) {
    const payload: ReceivableCreate = {
      ...values,
      paid_at: values.paid_at || undefined,
    };
    try {
      await createMutation.mutateAsync(payload);
      toast.success('Cobranca registrada');
      reset();
      setOpen(false);
    } catch {
      toast.error('Erro ao registrar cobranca. Tente novamente.');
    }
  }

  async function handleMarkPaid(id: string) {
    try {
      await updateMutation.mutateAsync({
        id,
        payload: { status: 'paid', paid_at: new Date().toISOString().split('T')[0] },
      });
      toast.success('Marcado como pago');
    } catch {
      toast.error('Erro ao atualizar cobranca');
    }
  }

  async function handleDelete(id: string, description: string) {
    if (!confirm(`Excluir cobranca "${description}"?`)) return;
    try {
      await deleteMutation.mutateAsync(id);
      toast.success('Cobranca removida');
    } catch {
      toast.error('Erro ao remover cobranca');
    }
  }

  const openTotal = (receivables ?? [])
    .filter((r) => r.status === 'pending' || r.status === 'overdue')
    .reduce((sum, r) => sum + Number(r.amount), 0);

  const paidTotal = (receivables ?? [])
    .filter((r) => r.status === 'paid')
    .reduce((sum, r) => sum + Number(r.amount), 0);

  const overdueTotal = (receivables ?? [])
    .filter((r) => r.status === 'overdue')
    .reduce((sum, r) => sum + Number(r.amount), 0);

  const paidList = (receivables ?? []).filter((r) => r.status === 'paid');
  const ticketMedio = paidList.length > 0
    ? paidList.reduce((sum, r) => sum + Number(r.amount), 0) / paidList.length
    : 0;

  const filteredReceivables = (receivables ?? []).filter((r) => {
    const client = clients?.find((c) => c.id === r.client_id);
    const clientName = client?.name?.toLowerCase() || '';
    const desc = r.description?.toLowerCase() || '';
    const notes = r.notes?.toLowerCase() || '';
    const query = search.toLowerCase();

    const matchesSearch = clientName.includes(query) || desc.includes(query) || notes.includes(query);
    const matchesClient = !selectedClient || r.client_id === selectedClient;
    const matchesStatus = !selectedStatus || r.status === selectedStatus;

    return matchesSearch && matchesClient && matchesStatus;
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold md:text-3xl bg-clip-text text-transparent bg-gradient-to-r from-primary via-primary to-primary/60">
            Financeiro
          </h1>
          <p className="text-muted-foreground mt-1">
            Acompanhe honorários recorrentes, vencimentos e controle cobranças em atraso.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate('/aprender')}
            className="h-9 border-primary/25 bg-primary/10 text-primary hover:bg-primary/20 gap-1.5"
            title="Aprender sobre esta tela"
          >
            <BookOpen className="h-4 w-4" />
            <span>Guia</span>
          </Button>
          <Button onClick={() => setOpen(true)} size="sm" className="bg-gradient-to-r from-primary to-primary hover:from-primary hover:to-primary shadow-token-sm">
            <Plus className="mr-1.5 h-4 w-4" aria-hidden="true" />
            Nova cobranca
          </Button>
        </div>
      </div>

      {isError && <ErrorState message="Nao foi possivel carregar as cobranças." />}

      {/* KPI Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="A receber"
          value={isLoading ? '...' : moneyBRL(openTotal)}
          icon={CreditCard}
          className="bg-card/45 backdrop-blur-sm border-border/50"
        />
        <MetricCard
          title="Recebido"
          value={isLoading ? '...' : moneyBRL(paidTotal)}
          icon={DollarSign}
          className="bg-card/45 backdrop-blur-sm border-border/50 text-success"
        />
        <MetricCard
          title="Em atraso"
          value={isLoading ? '...' : moneyBRL(overdueTotal)}
          icon={AlertTriangle}
          className="bg-card/45 backdrop-blur-sm border-border/50 text-destructive"
        />
        <MetricCard
          title="Ticket Médio"
          value={isLoading ? '...' : moneyBRL(ticketMedio)}
          icon={BarChart3}
          className="bg-card/45 backdrop-blur-sm border-border/50"
        />
      </div>

      {/* Filters Toolbar */}
      <Card className="p-4 bg-card/40 backdrop-blur-md border-border/50">
        <div className="flex flex-col lg:flex-row gap-4 justify-between lg:items-center">
          <div className="flex flex-1 flex-col sm:flex-row gap-3">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Buscar por descrição ou cliente..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9 bg-muted/20 border-border/50 focus:border-primary/50"
              />
            </div>

            <Select
              value={selectedClient}
              onChange={(e) => setSelectedClient(e.target.value)}
              className="sm:w-[220px] bg-muted/20 border-border/50"
            >
              <option value="">Todos os Clientes</option>
              {(clients ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>

            <Select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="sm:w-[180px] bg-muted/20 border-border/50"
            >
              <option value="">Todos Status</option>
              <option value="pending">Em aberto</option>
              <option value="paid">Pago</option>
              <option value="overdue">Atrasado</option>
              <option value="cancelled">Cancelado</option>
            </Select>
          </div>

          <div className="flex items-center gap-2 self-end lg:self-auto border-t lg:border-t-0 pt-3 lg:pt-0 border-border/30">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 rounded-lg transition-all ${
                viewMode === 'grid'
                  ? 'bg-primary/10 text-primary border border-primary/20'
                  : 'text-muted-foreground hover:bg-muted/30 border border-transparent'
              }`}
              title="Exibição em Grid"
            >
              <LayoutGrid className="h-4 w-4" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 rounded-lg transition-all ${
                viewMode === 'list'
                  ? 'bg-primary/10 text-primary border border-primary/20'
                  : 'text-muted-foreground hover:bg-muted/30 border border-transparent'
              }`}
              title="Exibição em Lista"
            >
              <List className="h-4 w-4" />
            </button>
          </div>
        </div>
      </Card>

      {/* Main List/Grid View */}
      {isLoading ? (
        <PageSpinner />
      ) : filteredReceivables.length === 0 ? (
        <Card className="bg-card/45 backdrop-blur-sm border-border/50">
          <CardContent className="pt-6">
            <EmptyState
              title="Nenhuma cobrança encontrada"
              description="Nenhum registro atende aos filtros de busca aplicados."
              action={
                <Button size="sm" onClick={() => setOpen(true)} className="bg-primary/10 text-primary border border-primary/20 hover:bg-primary/20">
                  Nova cobranca
                </Button>
              }
            />
          </CardContent>
        </Card>
      ) : viewMode === 'grid' ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filteredReceivables.map((r) => {
            const client = clients?.find((c) => c.id === r.client_id);
            const clientName = client?.name || 'Cliente Desconhecido';

            return (
              <Card key={r.id} className="relative group border border-border/50 hover:border-primary/30 p-5 bg-card/45 backdrop-blur-sm flex flex-col justify-between">
                <div>
                  <div className="flex items-start justify-between mb-3 gap-2">
                    <h4 className="font-bold text-foreground text-base leading-snug line-clamp-2">{r.description}</h4>
                    <Badge variant={statusVariant[r.status]} className="shrink-0">
                      {statusLabel[r.status]}
                    </Badge>
                  </div>

                  <div className="space-y-2 text-sm text-muted-foreground mt-3">
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4 text-primary/70 shrink-0" />
                      <span className="font-medium text-foreground truncate">{clientName}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <DollarSign className="h-4 w-4 text-primary/70 shrink-0" />
                      <span className="font-bold text-foreground">{moneyBRL(r.amount)}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Calendar className="h-4 w-4 text-primary/70 shrink-0" />
                      <span>Vencimento: <strong className={r.status === 'overdue' ? 'text-destructive' : 'text-foreground'}>{dateBR(r.due_date)}</strong></span>
                    </div>
                    {r.paid_at && (
                      <div className="flex items-center gap-2 text-xs text-success bg-success/5 px-2 py-1 rounded border border-success/10 w-fit">
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        <span>Pago em: {dateBR(r.paid_at)}</span>
                      </div>
                    )}
                    {r.notes && (
                      <p className="text-xs italic bg-muted/20 p-2 rounded border border-border/20 mt-2 line-clamp-3">
                        {r.notes}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-end gap-2 mt-5 border-t border-border/20 pt-3">
                  {(r.status === 'pending' || r.status === 'overdue') && (
                    <Button
                      size="sm"
                      className="bg-success/10 text-success hover:bg-success/20 border border-success/20"
                      onClick={() => handleMarkPaid(r.id)}
                    >
                      <CheckCircle2 className="h-3.5 w-3.5 mr-1" />
                      Pago
                    </Button>
                  )}
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleDelete(r.id, r.description)}
                    className="text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Descrição</TableHead>
              <TableHead>Cliente</TableHead>
              <TableHead>Valor</TableHead>
              <TableHead>Vencimento</TableHead>
              <TableHead>Pago em</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Ações</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredReceivables.map((r) => {
              const client = clients?.find((c) => c.id === r.client_id);
              const clientName = client?.name || 'Cliente Desconhecido';

              return (
                <TableRow key={r.id}>
                  <TableCell>
                    <div className="font-semibold text-foreground">{r.description}</div>
                    {r.notes && (
                      <div className="text-xs text-muted-foreground max-w-[300px] truncate" title={r.notes}>
                        {r.notes}
                      </div>
                    )}
                  </TableCell>
                  <TableCell className="font-medium text-foreground">{clientName}</TableCell>
                  <TableCell className="font-bold text-foreground">{moneyBRL(r.amount)}</TableCell>
                  <TableCell>
                    <span className={r.status === 'overdue' ? 'text-destructive font-semibold' : 'text-muted-foreground'}>
                      {dateBR(r.due_date)}
                    </span>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{dateBR(r.paid_at)}</TableCell>
                  <TableCell>
                    <Badge variant={statusVariant[r.status]}>
                      {statusLabel[r.status]}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center justify-end gap-2">
                      {(r.status === 'pending' || r.status === 'overdue') && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleMarkPaid(r.id)}
                          className="h-8 text-xs text-success hover:text-success hover:bg-success/10 gap-1"
                          title="Marcar como Pago"
                        >
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          <span>Pago</span>
                        </Button>
                      )}
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleDelete(r.id, r.description)}
                        className="h-8 text-xs text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                        title="Excluir cobrança"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      )}

      {/* Dialog Form for New Receivable */}
      <Dialog open={open} onClose={() => setOpen(false)} title="Nova cobranca">
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <FormField label="Cliente" htmlFor="client_id" error={errors.client_id?.message} required>
            <Select id="client_id" {...register('client_id')}>
              <option value="">Selecione o cliente</option>
              {(clients ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
          </FormField>

          <FormField label="Descricao" htmlFor="description" error={errors.description?.message} required>
            <Input id="description" placeholder="Ex: Honorarios Contabeis - Maio/2026" {...register('description')} />
          </FormField>

          <div className="grid grid-cols-2 gap-4">
            <FormField label="Valor (R$)" htmlFor="amount" error={errors.amount?.message} required>
              <Input
                id="amount"
                type="text"
                placeholder="0,00"
                {...register('amount', {
                  onChange: (e) => {
                    e.target.value = formatCurrencyBRL(e.target.value);
                  },
                })}
              />
            </FormField>

            <FormField label="Vencimento" htmlFor="due_date" error={errors.due_date?.message} required>
              <Input id="due_date" type="date" {...register('due_date')} />
            </FormField>
          </div>

          <FormField label="Status" htmlFor="status" required>
            <Select id="status" {...register('status')}>
              <option value="pending">Em aberto</option>
              <option value="paid">Pago</option>
              <option value="overdue">Atrasado</option>
              <option value="cancelled">Cancelado</option>
            </Select>
          </FormField>

          <FormField label="Data de pagamento" htmlFor="paid_at" error={errors.paid_at?.message}>
            <Input id="paid_at" type="date" {...register('paid_at')} />
          </FormField>

          <FormField label="Observacoes" htmlFor="notes" error={errors.notes?.message}>
            <Input id="notes" placeholder="Referencia, competencia... (opcional)" {...register('notes')} />
          </FormField>

          <div className="flex justify-end gap-3 pt-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isSubmitting} className="bg-gradient-to-r from-primary to-primary text-white">
              {isSubmitting ? 'Salvando...' : 'Salvar cobranca'}
            </Button>
          </div>
        </form>
      </Dialog>

      {/* ── Inadimplência Report (owner/admin) ── */}
      {isAdminOrOwner && inadimplencia && inadimplencia.total_clients > 0 && (
        <Card className="mt-8 border-destructive/20 dark:border-destructive/40 bg-card/45 backdrop-blur-sm">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-destructive/10 border border-destructive/20">
                <TrendingDown className="h-4 w-4 text-destructive" />
              </div>
              <div>
                <CardTitle className="text-base font-bold text-foreground">Relatório de Inadimplência</CardTitle>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {inadimplencia.total_clients} cliente{inadimplencia.total_clients !== 1 ? 's' : ''} com recebíveis vencidos
                  &nbsp;·&nbsp;Total: <strong className="text-destructive font-bold">{moneyBRL(inadimplencia.total_overdue_amount)}</strong>
                </p>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Cliente</TableHead>
                  <TableHead>E-mail</TableHead>
                  <TableHead className="text-right">Qtd. Cobranças</TableHead>
                  <TableHead className="text-right">Total Vencido</TableHead>
                  <TableHead className="text-right">Dias em Atraso</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {inadimplencia.clients.map((c) => (
                  <TableRow key={c.client_id}>
                    <TableCell className="font-semibold text-foreground">{c.client_name}</TableCell>
                    <TableCell className="text-muted-foreground">{c.email ?? '—'}</TableCell>
                    <TableCell className="text-right font-medium text-foreground">{c.overdue_count}</TableCell>
                    <TableCell className="text-right font-bold text-destructive">
                      {moneyBRL(c.overdue_total)}
                    </TableCell>
                    <TableCell className="text-right">
                      <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold border ${
                        c.days_overdue > 90
                          ? 'bg-destructive/10 text-destructive border-destructive/20'
                          : c.days_overdue > 30
                          ? 'bg-warning/10 text-warning border-warning/20'
                          : 'bg-warning/10 text-warning border-warning/20'
                      }`}>
                        {c.days_overdue} dias
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
