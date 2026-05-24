'use client';

import { useState, useMemo } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import {
  Trash2,
  CheckCircle2,
  DollarSign,
  AlertCircle,
  Save,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Dialog } from '@/components/ui/Dialog';
import { FormField } from '@/components/ui/FormField';
import { EmptyState, PageSpinner } from '@/components/ui/StateViews';
import {
  useClients,
  useDasPayments,
  useCreateDas,
  useDeleteDas,
  usePayDas,
  type DasPayment,
} from '@/lib/hooks/useOperations';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const MONTHS_PT = [
  'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
  'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
];

function moneyBRL(val: number): string {
  return val.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function dateBR(dateStr: string): string {
  if (!dateStr) return '-';
  const parts = dateStr.split('-');
  if (parts.length !== 3) return dateStr;
  return `${parts[2]}/${parts[1]}/${parts[0]}`;
}

function formatCurrencyBRL(val: number): string {
  if (val === 0) return '';
  return val.toLocaleString('pt-BR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function parseCurrencyBRL(str: string): number {
  const digits = str.replace(/\D/g, '');
  if (!digits) return 0;
  return parseFloat(digits) / 100;
}

// ---------------------------------------------------------------------------
// Form Validation Schema
// ---------------------------------------------------------------------------

const schema = z.object({
  revenue: z.string().min(1, 'Faturamento é obrigatório'),
  tax_amount: z.string().min(1, 'Valor do DAS é obrigatório'),
  due_date: z.string().min(1, 'Data de vencimento é obrigatória'),
  status: z.enum(['pending', 'paid']),
  notes: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function DasMensalPage() {
  const { data: clients, isLoading: clientsLoading } = useClients();
  const [selectedClientId, setSelectedClientId] = useState<string>('');
  const [selectedYear, setSelectedYear] = useState<string>(() => String(new Date().getFullYear()));
  const [openModal, setOpenModal] = useState(false);
  const [editingPeriod, setEditingPeriod] = useState<string | null>(null);

  // Queries & Mutations
  const { data: dasPayments } = useDasPayments(
    selectedClientId || undefined,
    selectedYear
  );
  const createDas = useCreateDas();
  const deleteDas = useDeleteDas();
  const payDas = usePayDas();

  // Form Setup
  const {
    register,
    handleSubmit,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      revenue: '',
      tax_amount: '',
      due_date: '',
      status: 'pending',
      notes: '',
    },
  });

  // Automatically select first client if available
  useMemo(() => {
    if (clients && clients.length > 0 && !selectedClientId) {
      setSelectedClientId(clients[0].id);
    }
  }, [clients, selectedClientId]);

  // Construct map of existing payments
  const dasMap = useMemo(() => {
    const map = new Map<string, DasPayment>();
    if (dasPayments) {
      dasPayments.forEach((p) => {
        map.set(p.period, p);
      });
    }
    return map;
  }, [dasPayments]);

  // Calculate Summary metrics
  const totals = useMemo(() => {
    let paidTotal = 0;
    let pendingTotal = 0;
    let revenueTotal = 0;

    if (dasPayments) {
      dasPayments.forEach((p) => {
        revenueTotal += p.revenue;
        if (p.status === 'paid') {
          paidTotal += p.tax_amount;
        } else {
          pendingTotal += p.tax_amount;
        }
      });
    }

    return { paidTotal, pendingTotal, revenueTotal };
  }, [dasPayments]);

  // Handlers
  const handleOpenLaunch = (monthIdx: number) => {
    if (!selectedClientId) {
      toast.error('Selecione um cliente primeiro.');
      return;
    }
    const monthStr = String(monthIdx + 1).padStart(2, '0');
    const period = `${selectedYear}-${monthStr}`;
    setEditingPeriod(period);

    const existing = dasMap.get(period);
    if (existing) {
      reset({
        revenue: formatCurrencyBRL(existing.revenue),
        tax_amount: formatCurrencyBRL(existing.tax_amount),
        due_date: existing.due_date,
        status: existing.status === 'overdue' ? 'pending' : existing.status,
        notes: existing.notes || '',
      });
    } else {
      // Default due date to the 20th of the following month
      let nextMonth = monthIdx + 2;
      let nextYear = parseInt(selectedYear);
      if (nextMonth > 12) {
        nextMonth = 1;
        nextYear += 1;
      }
      const defaultDueDate = `${nextYear}-${String(nextMonth).padStart(2, '0')}-20`;
      
      reset({
        revenue: '',
        tax_amount: '',
        due_date: defaultDueDate,
        status: 'pending',
        notes: '',
      });
    }

    setOpenModal(true);
  };

  const onSubmit = async (data: FormValues) => {
    if (!selectedClientId || !editingPeriod) return;

    try {
      await createDas.mutateAsync({
        client_id: selectedClientId,
        period: editingPeriod,
        revenue: parseCurrencyBRL(data.revenue),
        tax_amount: parseCurrencyBRL(data.tax_amount),
        due_date: data.due_date,
        status: data.status,
        notes: data.notes,
      });

      toast.success('DAS cadastrado com sucesso!');
      setOpenModal(false);
    } catch (err: unknown) {
      console.error(err);
      const detail =
        typeof err === 'object' && err !== null && 'response' in err
          ? (err as { response?: { data?: { detail?: unknown } } }).response?.data?.detail
          : undefined;
      toast.error(typeof detail === 'string' ? detail : 'Erro ao salvar DAS.');
    }
  };

  const handlePayQuickly = async (dasId: string) => {
    try {
      await payDas.mutateAsync(dasId);
      toast.success('DAS marcado como pago!');
    } catch (err) {
      console.error(err);
      toast.error('Erro ao atualizar DAS.');
    }
  };

  const handleDelete = async (dasId: string) => {
    if (!window.confirm('Deseja realmente excluir este lançamento de DAS?')) return;
    try {
      await deleteDas.mutateAsync(dasId);
      toast.success('Lançamento de DAS removido.');
    } catch (err) {
      console.error(err);
      toast.error('Erro ao remover DAS.');
    }
  };

  if (clientsLoading) {
    return <PageSpinner />;
  }

  if (!clients || clients.length === 0) {
    return (
      <div className="flex h-[80vh] items-center justify-center">
        <EmptyState
          title="Nenhum cliente cadastrado"
          description="Cadastre clientes na aba correspondente antes de gerenciar o DAS."
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header section with filters */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Cadastro de DAS Mensal
          </h1>
          <p className="text-sm text-muted-foreground">
            Acompanhe e registre guias de imposto DAS dos clientes Simples Nacional
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="min-w-[200px]">
            <Select
              value={selectedClientId}
              onChange={(e) => setSelectedClientId(e.target.value)}
              className="w-full"
            >
              {clients.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} {c.document ? `(${c.document})` : ''}
                </option>
              ))}
            </Select>
          </div>

          <div className="w-[100px]">
            <Select
              value={selectedYear}
              onChange={(e) => setSelectedYear(e.target.value)}
              className="w-full"
            >
              {['2027', '2026', '2025', '2024'].map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </Select>
          </div>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="border-border/60 bg-card">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Total Faturamento Declarado
            </CardTitle>
            <DollarSign className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-foreground">
              {moneyBRL(totals.revenueTotal)}
            </p>
            <p className="text-[10px] text-muted-foreground mt-1">
              Ano de referência: {selectedYear}
            </p>
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Total DAS Pago
            </CardTitle>
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-foreground">
              {moneyBRL(totals.paidTotal)}
            </p>
            <p className="text-[10px] text-muted-foreground mt-1">
              Guias quitadas em dia ou atraso
            </p>
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Total DAS em Aberto
            </CardTitle>
            <AlertCircle className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-foreground">
              {moneyBRL(totals.pendingTotal)}
            </p>
            <p className="text-[10px] text-muted-foreground mt-1">
              Guias pendentes de pagamento
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main 12 months spreadsheet table */}
      <Card className="border-border/60 bg-card overflow-hidden">
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-border/80 bg-muted/30 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  <th className="px-5 py-3">Mês de Referência</th>
                  <th className="px-5 py-3 text-right">Faturamento (R$)</th>
                  <th className="px-5 py-3 text-right">Imposto DAS (R$)</th>
                  <th className="px-5 py-3">Vencimento</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3 text-right">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40">
                {MONTHS_PT.map((monthName, idx) => {
                  const monthStr = String(idx + 1).padStart(2, '0');
                  const period = `${selectedYear}-${monthStr}`;
                  const record = dasMap.get(period);

                  return (
                    <tr
                      key={idx}
                      className="hover:bg-muted/10 transition-colors duration-150"
                    >
                      <td className="px-5 py-4 font-semibold text-foreground">
                        {monthName}
                      </td>
                      <td className="px-5 py-4 text-right font-medium text-foreground">
                        {record ? moneyBRL(record.revenue) : '—'}
                      </td>
                      <td className="px-5 py-4 text-right font-bold text-foreground">
                        {record ? moneyBRL(record.tax_amount) : '—'}
                      </td>
                      <td className="px-5 py-4 text-muted-foreground">
                        {record ? dateBR(record.due_date) : '—'}
                      </td>
                      <td className="px-5 py-4">
                        {record ? (
                          <Badge
                            variant={
                              record.status === 'paid'
                                ? 'success'
                                : record.status === 'overdue'
                                ? 'error'
                                : 'warning'
                            }
                          >
                            {record.status === 'paid'
                              ? 'Pago'
                              : record.status === 'overdue'
                              ? 'Vencido'
                              : 'Pendente'}
                          </Badge>
                        ) : (
                          <Badge variant="default">Não Lançado</Badge>
                        )}
                      </td>
                      <td className="px-5 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          {record && record.status !== 'paid' && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-8 px-2 text-emerald-600 hover:bg-emerald-500/10 hover:text-emerald-700"
                              onClick={() => handlePayQuickly(record.id)}
                              title="Marcar como Pago"
                            >
                              <CheckCircle2 className="h-4 w-4" />
                            </Button>
                          )}
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-8 px-3"
                            onClick={() => handleOpenLaunch(idx)}
                          >
                            {record ? 'Editar' : 'Lançar'}
                          </Button>
                          {record && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-8 px-2 text-red-500 hover:bg-red-500/10 hover:text-red-600"
                              onClick={() => handleDelete(record.id)}
                            >
                              <Trash2 className="h-4 w-4" />
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
        </CardContent>
      </Card>

      {/* Launch/Edit Modal */}
      <Dialog open={openModal} onClose={() => setOpenModal(false)} title="Lançar Guia DAS">
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
            Mês de Referência: {editingPeriod ? `${MONTHS_PT[parseInt(editingPeriod.split('-')[1]) - 1]} / ${editingPeriod.split('-')[0]}` : ''}
          </p>

          <FormField label="Faturamento Declarado (R$)" htmlFor="revenue" error={errors.revenue?.message}>
            <div className="relative">
              <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
                R$
              </span>
              <Input
                type="text"
                id="revenue"
                placeholder="0,00"
                className="pl-8"
                {...register('revenue', {
                  onChange: (e) => {
                    setValue('revenue', formatCurrencyBRL(parseCurrencyBRL(e.target.value)));
                  }
                })}
              />
            </div>
          </FormField>

          <FormField label="Valor da Guia DAS (R$)" htmlFor="tax_amount" error={errors.tax_amount?.message}>
            <div className="relative">
              <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
                R$
              </span>
              <Input
                type="text"
                id="tax_amount"
                placeholder="0,00"
                className="pl-8"
                {...register('tax_amount', {
                  onChange: (e) => {
                    setValue('tax_amount', formatCurrencyBRL(parseCurrencyBRL(e.target.value)));
                  }
                })}
              />
            </div>
          </FormField>

          <FormField label="Data de Vencimento" htmlFor="due_date" error={errors.due_date?.message}>
            <Input type="date" id="due_date" {...register('due_date')} />
          </FormField>

          <FormField label="Status de Pagamento" htmlFor="status" error={errors.status?.message}>
            <Select id="status" {...register('status')}>
              <option value="pending">Pendente (Em aberto)</option>
              <option value="paid">Quitado (Pago)</option>
            </Select>
          </FormField>

          <FormField label="Notas / Observações" htmlFor="notes" error={errors.notes?.message}>
            <textarea
              id="notes"
              className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              rows={3}
              placeholder="Ex: Pagar guia no banco conveniado"
              {...register('notes')}
            />
          </FormField>

          <div className="flex justify-end gap-3 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpenModal(false)}
              disabled={isSubmitting}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={isSubmitting} className="flex items-center gap-2">
              <Save className="h-4 w-4" />
              {isSubmitting ? 'Salvando...' : 'Salvar Guia'}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
export default DasMensalPage;
