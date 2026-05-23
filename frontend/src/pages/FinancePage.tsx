'use client';
import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import { Plus, Trash2, CheckCircle2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Dialog } from '@/components/ui/Dialog';
import { FormField } from '@/components/ui/FormField';
import { EmptyState, ErrorState, PageSpinner } from '@/components/ui/StateViews';
import {
  dateBR,
  moneyBRL,
  useClients,
  useReceivables,
  useCreateReceivable,
  useUpdateReceivable,
  useDeleteReceivable,
  type ReceivableCreate,
  type ReceivableStatus,
} from '@/lib/hooks/useOperations';

const schema = z.object({
  client_id: z.string().min(1, 'Selecione um cliente'),
  description: z.string().min(2, 'Descricao deve ter ao menos 2 caracteres'),
  amount: z.coerce.number().positive('Valor deve ser maior que zero'),
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
  const [open, setOpen] = useState(false);
  const { data: receivables, isLoading, isError } = useReceivables();
  const { data: clients } = useClients();
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

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold md:text-3xl">Financeiro</h1>
          <p className="text-muted-foreground">
            Acompanhe honorarios, vencimentos e cobranças em atraso.
          </p>
        </div>
        <Button onClick={() => setOpen(true)} size="sm">
          <Plus className="mr-1.5 h-4 w-4" aria-hidden="true" />
          Nova cobranca
        </Button>
      </div>

      {isError && <ErrorState message="Nao foi possivel carregar as cobranças." />}

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">A receber</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoading ? '...' : moneyBRL(openTotal)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Recebido</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-emerald-600">
              {isLoading ? '...' : moneyBRL(paidTotal)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Em atraso</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-destructive">
              {isLoading ? '...' : moneyBRL(overdueTotal)}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Cobranças</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <PageSpinner />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="pb-3 font-medium">Descricao</th>
                    <th className="pb-3 font-medium">Valor</th>
                    <th className="pb-3 font-medium">Vencimento</th>
                    <th className="pb-3 font-medium">Pago em</th>
                    <th className="pb-3 font-medium">Status</th>
                    <th className="pb-3 font-medium sr-only">Acoes</th>
                  </tr>
                </thead>
                <tbody>
                  {(receivables ?? []).length === 0 && (
                    <tr>
                      <td colSpan={6}>
                        <EmptyState
                          title="Nenhuma cobranca registrada"
                          description="Registre honorarios e cobranças dos clientes."
                          action={
                            <Button size="sm" onClick={() => setOpen(true)}>
                              Nova cobranca
                            </Button>
                          }
                        />
                      </td>
                    </tr>
                  )}
                  {(receivables ?? []).map((r) => (
                    <tr key={r.id} className="border-b last:border-0">
                      <td className="py-4">
                        <div className="font-medium">{r.description}</div>
                        {r.notes && (
                          <div className="text-xs text-muted-foreground">{r.notes}</div>
                        )}
                      </td>
                      <td className="py-4 font-medium">{moneyBRL(r.amount)}</td>
                      <td className="py-4">
                        <span className={r.status === 'overdue' ? 'text-destructive font-medium' : ''}>
                          {dateBR(r.due_date)}
                        </span>
                      </td>
                      <td className="py-4">{dateBR(r.paid_at)}</td>
                      <td className="py-4">
                        <Badge variant={statusVariant[r.status]}>
                          {statusLabel[r.status]}
                        </Badge>
                      </td>
                      <td className="py-4">
                        <div className="flex items-center gap-2">
                          {(r.status === 'pending' || r.status === 'overdue') && (
                            <button
                              type="button"
                              onClick={() => handleMarkPaid(r.id)}
                              className="flex flex-col items-center gap-0.5 rounded p-1 text-muted-foreground hover:text-emerald-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                              aria-label={`Marcar como pago: ${r.description}`}
                              title="Marcar como pago"
                            >
                              <CheckCircle2 className="h-4 w-4" />
                              <span className="text-[9px] font-medium uppercase tracking-wider">Pago</span>
                            </button>
                          )}
                          <button
                            type="button"
                            onClick={() => handleDelete(r.id, r.description)}
                            className="flex flex-col items-center gap-0.5 rounded p-1 text-muted-foreground hover:text-destructive focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            aria-label={`Excluir cobranca ${r.description}`}
                          >
                            <Trash2 className="h-4 w-4" />
                            <span className="text-[9px] font-medium uppercase tracking-wider">Excluir</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

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
                type="number"
                step="0.01"
                min="0.01"
                placeholder="0,00"
                {...register('amount')}
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
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Salvando...' : 'Salvar cobranca'}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
