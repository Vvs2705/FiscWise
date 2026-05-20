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
import { EmptyState, ErrorState, PageSpinner } from '@/components/ui/StateViews';
import {
  useClients,
  useCreateClient,
  useDeleteClient,
  type AccountingClientCreate,
  type ClientStatus,
} from '@/lib/hooks/useOperations';

const schema = z.object({
  name: z.string().min(2, 'Nome deve ter ao menos 2 caracteres'),
  document: z.string().optional(),
  entity_type: z.enum(['pj', 'pf']),
  tax_regime: z.string().optional(),
  email: z.string().email('E-mail invalido').optional().or(z.literal('')),
  phone: z.string().optional(),
  status: z.enum(['active', 'inactive', 'onboarding']),
  notes: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

const statusLabel: Record<ClientStatus, string> = {
  active: 'Ativo',
  inactive: 'Inativo',
  onboarding: 'Onboarding',
};

const statusVariant: Record<ClientStatus, 'success' | 'warning' | 'default'> = {
  active: 'success',
  inactive: 'default',
  onboarding: 'warning',
};

export function ClientsPage() {
  const [open, setOpen] = useState(false);
  const { data: clients, isLoading, isError } = useClients();
  const createMutation = useCreateClient();
  const deleteMutation = useDeleteClient();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { entity_type: 'pj', status: 'active' },
  });

  async function onSubmit(values: FormValues) {
    const payload: AccountingClientCreate = {
      ...values,
      email: values.email || undefined,
    };
    try {
      await createMutation.mutateAsync(payload);
      toast.success('Cliente cadastrado com sucesso');
      reset();
      setOpen(false);
    } catch {
      toast.error('Erro ao cadastrar cliente. Tente novamente.');
    }
  }

  async function handleDelete(id: string, name: string) {
    if (!confirm(`Excluir cliente "${name}"? Esta acao nao pode ser desfeita.`)) return;
    try {
      await deleteMutation.mutateAsync(id);
      toast.success('Cliente removido');
    } catch {
      toast.error('Erro ao remover cliente');
    }
  }

  const total = clients?.length ?? 0;
  const activeCount = clients?.filter((c) => c.status === 'active').length ?? 0;
  const onboardingCount = clients?.filter((c) => c.status === 'onboarding').length ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold md:text-3xl">Clientes</h1>
          <p className="text-muted-foreground">
            Acompanhe a carteira e situacao operacional de cada cliente.
          </p>
        </div>
        <Button onClick={() => setOpen(true)} size="sm">
          <Plus className="mr-1.5 h-4 w-4" aria-hidden="true" />
          Novo cliente
        </Button>
      </div>

      {isError && <ErrorState message="Nao foi possivel carregar os clientes. Verifique sua conexao." />}

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total de clientes</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoading ? '...' : total}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Ativos</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoading ? '...' : activeCount}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Em onboarding</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoading ? '...' : onboardingCount}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Carteira de clientes</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <PageSpinner />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[680px] text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="pb-3 font-medium">Cliente</th>
                    <th className="pb-3 font-medium">Tipo</th>
                    <th className="pb-3 font-medium">Regime</th>
                    <th className="pb-3 font-medium">Contato</th>
                    <th className="pb-3 font-medium">Status</th>
                    <th className="pb-3 font-medium sr-only">Acoes</th>
                  </tr>
                </thead>
                <tbody>
                  {(clients ?? []).length === 0 && (
                    <tr>
                      <td colSpan={6}>
                        <EmptyState
                          title="Nenhum cliente cadastrado"
                          description="Cadastre seu primeiro cliente clicando em Novo cliente."
                        />
                      </td>
                    </tr>
                  )}
                  {(clients ?? []).map((client) => (
                    <tr key={client.id} className="border-b last:border-0">
                      <td className="py-4">
                        <div className="font-medium">{client.name}</div>
                        {client.document && (
                          <div className="text-muted-foreground">{client.document}</div>
                        )}
                      </td>
                      <td className="py-4 uppercase text-xs font-medium">
                        {client.entity_type}
                      </td>
                      <td className="py-4">{client.tax_regime ?? '-'}</td>
                      <td className="py-4">
                        <div>{client.email ?? '-'}</div>
                        {client.phone && (
                          <div className="text-muted-foreground">{client.phone}</div>
                        )}
                      </td>
                      <td className="py-4">
                        <Badge variant={statusVariant[client.status]}>
                          {statusLabel[client.status]}
                        </Badge>
                      </td>
                      <td className="py-4">
                        <button
                          type="button"
                          onClick={() => handleDelete(client.id, client.name)}
                          className="rounded p-1 text-muted-foreground hover:text-destructive focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                          aria-label={`Excluir cliente ${client.name}`}
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={open} onClose={() => setOpen(false)} title="Novo cliente">
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <FormField label="Nome / Razao social" htmlFor="name" error={errors.name?.message} required>
            <Input id="name" placeholder="Ex: Empresa XYZ Ltda" {...register('name')} />
          </FormField>

          <div className="grid grid-cols-2 gap-4">
            <FormField label="CPF / CNPJ" htmlFor="document" error={errors.document?.message}>
              <Input id="document" placeholder="00.000.000/0001-00" {...register('document')} />
            </FormField>

            <FormField label="Tipo" htmlFor="entity_type" required>
              <Select id="entity_type" {...register('entity_type')}>
                <option value="pj">Pessoa Juridica</option>
                <option value="pf">Pessoa Fisica</option>
              </Select>
            </FormField>
          </div>

          <FormField label="Regime tributario" htmlFor="tax_regime" error={errors.tax_regime?.message}>
            <Select id="tax_regime" {...register('tax_regime')}>
              <option value="">Selecione</option>
              <option value="Simples Nacional">Simples Nacional</option>
              <option value="Lucro Presumido">Lucro Presumido</option>
              <option value="Lucro Real">Lucro Real</option>
              <option value="MEI">MEI</option>
            </Select>
          </FormField>

          <div className="grid grid-cols-2 gap-4">
            <FormField label="E-mail" htmlFor="email" error={errors.email?.message}>
              <Input id="email" type="email" placeholder="contato@empresa.com" {...register('email')} />
            </FormField>
            <FormField label="Telefone" htmlFor="phone" error={errors.phone?.message}>
              <Input id="phone" placeholder="(11) 99999-9999" {...register('phone')} />
            </FormField>
          </div>

          <FormField label="Status" htmlFor="status" required>
            <Select id="status" {...register('status')}>
              <option value="active">Ativo</option>
              <option value="onboarding">Onboarding</option>
              <option value="inactive">Inativo</option>
            </Select>
          </FormField>

          <FormField label="Observacoes" htmlFor="notes" error={errors.notes?.message}>
            <Input id="notes" placeholder="Anotacoes internas (opcional)" {...register('notes')} />
          </FormField>

          <div className="flex justify-end gap-3 pt-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Salvando...' : 'Salvar cliente'}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
