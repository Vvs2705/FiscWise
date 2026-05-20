'use client';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import { Plus, Trash2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Dialog } from '@/components/ui/Dialog';
import { FormField } from '@/components/ui/FormField';
import { EmptyState, ErrorState, LoadingCards } from '@/components/ui/StateViews';
import {
  dateBR,
  useClients,
  useDeadlines,
  useCreateDeadline,
  useDeleteDeadline,
  type DeadlineCreate,
  type DeadlineStatus,
  type DeadlinePriority,
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
  const { data: deadlines, isLoading, isError } = useDeadlines();
  const { data: clients } = useClients();
  const createMutation = useCreateDeadline();
  const deleteMutation = useDeleteDeadline();

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
    } catch {
      toast.error('Erro ao cadastrar prazo. Tente novamente.');
    }
  }

  async function handleDelete(id: string, title: string) {
    if (!confirm(`Excluir prazo "${title}"?`)) return;
    try {
      await deleteMutation.mutateAsync(id);
      toast.success('Prazo removido');
    } catch {
      toast.error('Erro ao remover prazo');
    }
  }

  const total = deadlines?.length ?? 0;
  const pendingCount = deadlines?.filter((d) => d.status === 'pending').length ?? 0;
  const overdueCount = deadlines?.filter((d) => d.status === 'overdue').length ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold md:text-3xl">Agenda e Prazos</h1>
          <p className="text-muted-foreground">
            Organize vencimentos fiscais, contabeis e rotinas recorrentes da carteira.
          </p>
        </div>
        <Button onClick={() => setOpen(true)} size="sm">
          <Plus className="mr-1.5 h-4 w-4" aria-hidden="true" />
          Novo prazo
        </Button>
      </div>

      {isError && <ErrorState message="Nao foi possivel carregar os prazos." />}

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Prazos mapeados</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoading ? '...' : total}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Pendentes</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoading ? '...' : pendingCount}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Atrasados</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-destructive">
              {isLoading ? '...' : overdueCount}
            </div>
          </CardContent>
        </Card>
      </div>

      {isLoading ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <LoadingCards count={4} />
        </div>
      ) : (deadlines ?? []).length === 0 ? (
        <Card>
          <CardContent className="pt-6">
            <EmptyState
              title="Nenhum prazo cadastrado"
              description="Cadastre o primeiro prazo fiscal ou contabil da carteira."
              action={
                <Button size="sm" onClick={() => setOpen(true)}>
                  Novo prazo
                </Button>
              }
            />
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {(deadlines ?? []).map((deadline) => (
            <Card key={deadline.id}>
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-3">
                  <CardTitle className="text-base">{deadline.title}</CardTitle>
                  <div className="flex items-center gap-2 shrink-0">
                    <Badge variant={priorityVariant[deadline.priority]}>
                      {priorityLabel[deadline.priority]}
                    </Badge>
                    <Badge variant={statusVariant[deadline.status]}>
                      {statusLabel[deadline.status]}
                    </Badge>
                    <button
                      type="button"
                      onClick={() => handleDelete(deadline.id, deadline.title)}
                      className="rounded p-1 text-muted-foreground hover:text-destructive focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      aria-label={`Excluir prazo ${deadline.title}`}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-1 text-sm">
                <p className="text-muted-foreground">{deadline.category}</p>
                {deadline.description && (
                  <p className="text-muted-foreground">{deadline.description}</p>
                )}
                <p className="font-medium">
                  Vencimento:{' '}
                  <span className={deadline.status === 'overdue' ? 'text-destructive' : ''}>
                    {dateBR(deadline.due_date)}
                  </span>
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

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
