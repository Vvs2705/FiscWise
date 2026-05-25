'use client';
import { useState, useEffect, useMemo } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import {
  Plus,
  Trash2,
  Check,
  Search,
  Filter,
  X,
  LayoutList,
  LayoutGrid,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Dialog } from '@/components/ui/Dialog';
import { FormField } from '@/components/ui/FormField';
import { EmptyState, ErrorState, LoadingCards } from '@/components/ui/StateViews';
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
  useClients,
  useDeadlines,
  useCreateDeadline,
  useUpdateDeadline,
  useDeleteDeadline,
  type DeadlineCreate,
  type DeadlineStatus,
  type DeadlinePriority,
  type DeadlineItem,
} from '@/lib/hooks/useOperations';

const schema = z.object({
  client_id: z.string().min(1, 'Selecione um cliente'),
  title: z.string().min(2, 'Titulo deve ter ao menos 2 caracteres'),
  category: z.string().min(1, 'Categoria e obrigatoria'),
  due_date: z.string().min(1, 'Data e obrigatoria'),
  priority: z.enum(['low', 'medium', 'high']),
  status: z.enum(['pending', 'completed', 'overdue', 'cancelled']),
  description: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

const statusLabel: Record<DeadlineStatus, string> = {
  pending: 'Pendente',
  completed: 'Concluido',
  overdue: 'Atrasado',
  cancelled: 'Cancelado',
};

const statusVariant: Record<DeadlineStatus, 'warning' | 'success' | 'error' | 'default'> = {
  pending: 'warning',
  completed: 'success',
  overdue: 'error',
  cancelled: 'default',
};

const priorityLabel: Record<DeadlinePriority, string> = {
  low: 'Baixa',
  medium: 'Media',
  high: 'Alta',
};

const priorityVariant: Record<DeadlinePriority, 'default' | 'warning' | 'error'> = {
  low: 'default',
  medium: 'warning',
  high: 'error',
};

export function DeadlinesPage() {
  const [open, setOpen] = useState(false);
  const { data: deadlines, isLoading, isError, refetch } = useDeadlines();
  const { data: clients } = useClients();
  const createMutation = useCreateDeadline();
  const updateMutation = useUpdateDeadline();
  const deleteMutation = useDeleteDeadline();

  // Filters + Views
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');
  const [clientFilter, setClientFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [viewMode, setViewMode] = useState<'list' | 'card'>('list');

  // Search Debouncing
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearchQuery(searchQuery);
    }, 300);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { priority: 'medium', status: 'pending' },
  });

  async function onSubmit(values: FormValues) {
    const payload: DeadlineCreate = { ...values };
    try {
      await createMutation.mutateAsync(payload);
      toast.success('Prazo cadastrado');
      reset();
      setOpen(false);
      refetch();
    } catch {
      toast.error('Erro ao cadastrar prazo. Tente novamente.');
    }
  }

  async function handleQuickComplete(deadline: DeadlineItem) {
    try {
      await updateMutation.mutateAsync({
        id: deadline.id,
        payload: { status: 'completed' },
      });
      toast.success('Prazo marcado como concluído');
      refetch();
    } catch {
      toast.error('Erro ao atualizar status do prazo');
    }
  }

  async function handleDelete(id: string, title: string) {
    if (!confirm(`Excluir prazo "${title}"?`)) return;
    try {
      await deleteMutation.mutateAsync(id);
      toast.success('Prazo removido');
      refetch();
    } catch {
      toast.error('Erro ao remover prazo');
    }
  }

  // Filter logic
  const filteredDeadlines = useMemo(() => {
    if (!deadlines) return [];
    const q = debouncedSearchQuery.trim().toLowerCase();

    return deadlines.filter((d) => {
      if (q) {
        const matchesTitle = d.title.toLowerCase().includes(q);
        const matchesDesc = (d.description ?? '').toLowerCase().includes(q);
        const client = clients?.find((c) => c.id === d.client_id);
        const matchesClient = client ? client.name.toLowerCase().includes(q) : false;
        if (!matchesTitle && !matchesDesc && !matchesClient) return false;
      }
      if (clientFilter && d.client_id !== clientFilter) return false;
      if (categoryFilter && d.category !== categoryFilter) return false;
      if (priorityFilter && d.priority !== priorityFilter) return false;
      if (statusFilter && d.status !== statusFilter) return false;
      return true;
    });
  }, [deadlines, debouncedSearchQuery, clientFilter, categoryFilter, priorityFilter, statusFilter, clients]);

  const hasActiveFilters =
    debouncedSearchQuery.trim() !== '' || clientFilter !== '' || categoryFilter !== '' || priorityFilter !== '' || statusFilter !== '';

  function clearFilters() {
    setSearchQuery('');
    setDebouncedSearchQuery('');
    setClientFilter('');
    setCategoryFilter('');
    setPriorityFilter('');
    setStatusFilter('');
  }

  const total = deadlines?.length ?? 0;
  const pendingCount = deadlines?.filter((d) => d.status === 'pending').length ?? 0;
  const overdueCount = deadlines?.filter((d) => d.status === 'overdue').length ?? 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold md:text-3xl">Agenda e Prazos</h1>
          <p className="text-muted-foreground text-sm">
            Organize vencimentos fiscais, contabeis e rotinas recorrentes da carteira.
          </p>
        </div>
        <Button onClick={() => setOpen(true)} size="sm" className="h-9">
          <Plus className="mr-1.5 h-4 w-4" aria-hidden="true" />
          Novo prazo
        </Button>
      </div>

      {isError && <ErrorState message="Nao foi possivel carregar os prazos." />}

      {/* Summary Cards */}
      <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Prazos mapeados
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoading ? '...' : total}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Pendentes
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoading ? '...' : pendingCount}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Atrasados
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-destructive">
              {isLoading ? '...' : overdueCount}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters Bar */}
      {!isLoading && !isError && (
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
              placeholder="Buscar por prazo, descrição ou cliente..."
              className="w-full rounded-lg border border-border/80 bg-background pl-9 pr-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
              aria-label="Buscar prazos"
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
                value={clientFilter}
                onChange={(e) => setClientFilter(e.target.value)}
                className="rounded-lg border border-border/80 bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all max-w-[150px] truncate"
                aria-label="Filtrar por cliente"
              >
                <option value="">Todos os clientes</option>
                {(clients ?? []).map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>

              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="rounded-lg border border-border/80 bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                aria-label="Filtrar por categoria"
              >
                <option value="">Todas as categorias</option>
                <option value="Fiscal">Fiscal</option>
                <option value="Contabil">Contábil</option>
                <option value="Trabalhista">Trabalhista</option>
                <option value="Societario">Societário</option>
                <option value="Outros">Outros</option>
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
              </select>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="rounded-lg border border-border/80 bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                aria-label="Filtrar por status"
              >
                <option value="">Todos os status</option>
                <option value="pending">Pendente</option>
                <option value="completed">Concluído</option>
                <option value="overdue">Atrasado</option>
                <option value="cancelled">Cancelado</option>
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

      {/* Main List / Cards container */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-2 pb-3">
          <CardTitle className="text-base font-bold">Quadro de Prazos</CardTitle>
          {!isLoading && !isError && deadlines && (
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground font-semibold">
              <Filter className="h-3.5 w-3.5" aria-hidden="true" />
              {hasActiveFilters
                ? `${filteredDeadlines.length} de ${deadlines.length} filtrados`
                : `${deadlines.length} prazos no total`}
            </span>
          )}
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="grid gap-4 lg:grid-cols-2">
              <LoadingCards count={4} />
            </div>
          ) : filteredDeadlines.length === 0 ? (
            <EmptyState
              title="Nenhum prazo encontrado"
              description={hasActiveFilters ? "Tente redefinir seus filtros de busca para encontrar prazos." : "Cadastre o primeiro prazo fiscal ou contabil da carteira."}
              action={
                !hasActiveFilters ? (
                  <Button size="sm" onClick={() => setOpen(true)} className="h-9">
                    Novo prazo
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
                  <TableHead>Prazo</TableHead>
                  <TableHead>Cliente</TableHead>
                  <TableHead>Categoria</TableHead>
                  <TableHead>Prioridade</TableHead>
                  <TableHead>Vencimento</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Ações</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredDeadlines.map((deadline) => {
                  const client = clients?.find((c) => c.id === deadline.client_id);
                  return (
                    <TableRow key={deadline.id}>
                      <TableCell>
                        <div className="font-bold text-foreground">{deadline.title}</div>
                        {deadline.description && (
                          <div className="text-xs text-muted-foreground max-w-[250px] truncate" title={deadline.description}>
                            {deadline.description}
                          </div>
                        )}
                      </TableCell>
                      <TableCell className="font-medium text-foreground/80 max-w-[150px] truncate" title={client?.name}>
                        {client?.name ?? 'Cliente desconhecido'}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">{deadline.category}</TableCell>
                      <TableCell>
                        <Badge variant={priorityVariant[deadline.priority]}>
                          {priorityLabel[deadline.priority]}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs font-medium">
                        <span className={deadline.status === 'overdue' ? 'text-destructive font-bold' : ''}>
                          {dateBR(deadline.due_date)}
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge variant={statusVariant[deadline.status]}>
                          {statusLabel[deadline.status]}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          {deadline.status !== 'completed' && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleQuickComplete(deadline)}
                              className="h-8 gap-1 text-emerald-500 hover:text-emerald-500 hover:bg-emerald-500/10"
                              title="Concluir Prazo"
                            >
                              <Check className="h-4 w-4" />
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDelete(deadline.id, deadline.title)}
                            className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                            title="Excluir Prazo"
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
              {filteredDeadlines.map((deadline) => {
                const client = clients?.find((c) => c.id === deadline.client_id);
                const isOverdue = deadline.status === 'overdue';
                const isCompleted = deadline.status === 'completed';

                return (
                  <Card key={deadline.id} className="flex flex-col justify-between hover:border-primary/45 group">
                    <CardHeader className="pb-2 flex flex-row justify-between items-start gap-3">
                      <div className="min-w-0">
                        <h4 className="font-bold text-foreground text-sm leading-snug group-hover:text-primary transition-colors truncate" title={deadline.title}>
                          {deadline.title}
                        </h4>
                        <p className="text-[10px] text-muted-foreground mt-0.5">{deadline.category}</p>
                      </div>
                      <Badge variant={priorityVariant[deadline.priority]} className="text-[9px]">
                        {priorityLabel[deadline.priority]}
                      </Badge>
                    </CardHeader>
                    <CardContent className="pb-3 text-xs space-y-2 flex-1">
                      {deadline.description && (
                        <p className="text-muted-foreground/80 line-clamp-2 leading-relaxed bg-muted/20 p-2 rounded border border-border/40">
                          {deadline.description}
                        </p>
                      )}
                      <div className="space-y-1 pt-1">
                        <p className="font-medium text-foreground/90 truncate">
                          🏢 <span className="font-semibold">{client?.name ?? 'Desconhecido'}</span>
                        </p>
                        <p className="text-muted-foreground">
                          📅 Vencimento:{' '}
                          <span className={`font-semibold ${isOverdue ? 'text-destructive font-bold' : 'text-foreground'}`}>
                            {dateBR(deadline.due_date)}
                          </span>
                        </p>
                      </div>
                    </CardContent>
                    <CardFooter className="pt-2 border-t border-border/40 flex items-center justify-between gap-2">
                      <Badge variant={statusVariant[deadline.status]}>
                        {statusLabel[deadline.status]}
                      </Badge>
                      <div className="flex items-center gap-1">
                        {!isCompleted && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleQuickComplete(deadline)}
                            className="h-8 gap-1.5 text-emerald-500 hover:bg-emerald-500/10 hover:text-emerald-500 px-2 text-[11px] font-bold"
                          >
                            <Check className="h-3.5 w-3.5" />
                            Concluir
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(deadline.id, deadline.title)}
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

      {/* Modal Novo Prazo */}
      <Dialog open={open} onClose={() => setOpen(false)} title="Novo prazo">
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

          <FormField label="Titulo" htmlFor="title" error={errors.title?.message} required>
            <Input id="title" placeholder="Ex: DCTF Mensal - Fevereiro" {...register('title')} />
          </FormField>

          <FormField label="Categoria" htmlFor="category" error={errors.category?.message} required>
            <Select id="category" {...register('category')}>
              <option value="">Selecione</option>
              <option value="Fiscal">Fiscal</option>
              <option value="Contabil">Contabil</option>
              <option value="Trabalhista">Trabalhista</option>
              <option value="Societario">Societario</option>
              <option value="Outros">Outros</option>
            </Select>
          </FormField>

          <FormField label="Data de vencimento" htmlFor="due_date" error={errors.due_date?.message} required>
            <Input id="due_date" type="date" {...register('due_date')} />
          </FormField>

          <div className="grid grid-cols-2 gap-4">
            <FormField label="Prioridade" htmlFor="priority" required>
              <Select id="priority" {...register('priority')}>
                <option value="low">Baixa</option>
                <option value="medium">Media</option>
                <option value="high">Alta</option>
              </Select>
            </FormField>

            <FormField label="Status" htmlFor="status" required>
              <Select id="status" {...register('status')}>
                <option value="pending">Pendente</option>
                <option value="completed">Concluido</option>
                <option value="overdue">Atrasado</option>
                <option value="cancelled">Cancelado</option>
              </Select>
            </FormField>
          </div>

          <FormField label="Descricao" htmlFor="description" error={errors.description?.message}>
            <Input id="description" placeholder="Detalhe adicional (opcional)" {...register('description')} />
          </FormField>

          <div className="flex justify-end gap-3 pt-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Salvando...' : 'Salvar prazo'}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
