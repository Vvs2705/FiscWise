'use client';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import { Plus, Trash2, ExternalLink } from 'lucide-react';
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
  useClients,
  useDocuments,
  useCreateDocument,
  useDeleteDocument,
  type DocumentCreate,
  type DocumentStatus,
} from '@/lib/hooks/useOperations';

const schema = z.object({
  client_id: z.string().min(1, 'Selecione um cliente'),
  name: z.string().min(2, 'Nome deve ter ao menos 2 caracteres'),
  document_type: z.string().min(1, 'Tipo e obrigatorio'),
  status: z.enum(['available', 'missing', 'expired', 'review']),
  file_url: z.string().url('URL invalida').optional().or(z.literal('')),
  issued_at: z.string().optional(),
  expires_at: z.string().optional(),
  notes: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

const statusLabel: Record<DocumentStatus, string> = {
  available: 'Disponivel',
  missing: 'Pendente',
  expired: 'Vencido',
  review: 'Em revisao',
};

const statusVariant: Record<DocumentStatus, 'success' | 'warning' | 'error' | 'info'> = {
  available: 'success',
  missing: 'warning',
  expired: 'error',
  review: 'info',
};

export function DocumentsPage() {
  const [open, setOpen] = useState(false);
  const { data: documents, isLoading, isError } = useDocuments();
  const { data: clients } = useClients();
  const createMutation = useCreateDocument();
  const deleteMutation = useDeleteDocument();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { status: 'missing' },
  });

  async function onSubmit(values: FormValues) {
    const payload: DocumentCreate = {
      ...values,
      file_url: values.file_url || undefined,
    };
    try {
      await createMutation.mutateAsync(payload);
      toast.success('Documento registrado');
      reset();
      setOpen(false);
    } catch {
      toast.error('Erro ao registrar documento. Tente novamente.');
    }
  }

  async function handleDelete(id: string, name: string) {
    if (!confirm(`Excluir documento "${name}"?`)) return;
    try {
      await deleteMutation.mutateAsync(id);
      toast.success('Documento removido');
    } catch {
      toast.error('Erro ao remover documento');
    }
  }

  const availableCount = documents?.filter((d) => d.status === 'available').length ?? 0;
  const missingCount = documents?.filter((d) => d.status === 'missing').length ?? 0;
  const reviewCount = documents?.filter((d) => d.status === 'review').length ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold md:text-3xl">Documentos</h1>
          <p className="text-muted-foreground">
            Controle solicitacoes, recebimentos e situacao documental por cliente.
          </p>
        </div>
        <Button onClick={() => setOpen(true)} size="sm">
          <Plus className="mr-1.5 h-4 w-4" aria-hidden="true" />
          Novo documento
        </Button>
      </div>

      {isError && <ErrorState message="Nao foi possivel carregar os documentos." />}

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Disponiveis</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoading ? '...' : availableCount}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Pendentes</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoading ? '...' : missingCount}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Em revisao</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoading ? '...' : reviewCount}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Esteira documental</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <PageSpinner />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[680px] text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="pb-3 font-medium">Documento</th>
                    <th className="pb-3 font-medium">Tipo</th>
                    <th className="pb-3 font-medium">Emissao</th>
                    <th className="pb-3 font-medium">Vencimento</th>
                    <th className="pb-3 font-medium">Status</th>
                    <th className="pb-3 font-medium sr-only">Acoes</th>
                  </tr>
                </thead>
                <tbody>
                  {(documents ?? []).length === 0 && (
                    <tr>
                      <td colSpan={6}>
                        <EmptyState
                          title="Nenhum documento registrado"
                          description="Registre documentos dos clientes para controlar a esteira."
                          action={
                            <Button size="sm" onClick={() => setOpen(true)}>
                              Novo documento
                            </Button>
                          }
                        />
                      </td>
                    </tr>
                  )}
                  {(documents ?? []).map((doc) => (
                    <tr key={doc.id} className="border-b last:border-0">
                      <td className="py-4">
                        <div className="font-medium">{doc.name}</div>
                        {doc.notes && (
                          <div className="text-xs text-muted-foreground">{doc.notes}</div>
                        )}
                      </td>
                      <td className="py-4">{doc.document_type}</td>
                      <td className="py-4">{dateBR(doc.issued_at)}</td>
                      <td className="py-4">
                        <span className={doc.status === 'expired' ? 'text-destructive font-medium' : ''}>
                          {dateBR(doc.expires_at)}
                        </span>
                      </td>
                      <td className="py-4">
                        <Badge variant={statusVariant[doc.status]}>
                          {statusLabel[doc.status]}
                        </Badge>
                      </td>
                      <td className="py-4">
                        <div className="flex items-center gap-1">
                          {doc.file_url && (
                            <a
                              href={doc.file_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="rounded p-1 text-muted-foreground hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                              aria-label={`Abrir arquivo ${doc.name}`}
                            >
                              <ExternalLink className="h-4 w-4" />
                            </a>
                          )}
                          <button
                            type="button"
                            onClick={() => handleDelete(doc.id, doc.name)}
                            className="rounded p-1 text-muted-foreground hover:text-destructive focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            aria-label={`Excluir documento ${doc.name}`}
                          >
                            <Trash2 className="h-4 w-4" />
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

      <Dialog open={open} onClose={() => setOpen(false)} title="Novo documento">
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

          <FormField label="Nome do documento" htmlFor="name" error={errors.name?.message} required>
            <Input id="name" placeholder="Ex: SPED Fiscal Jan/2026" {...register('name')} />
          </FormField>

          <FormField label="Tipo" htmlFor="document_type" error={errors.document_type?.message} required>
            <Select id="document_type" {...register('document_type')}>
              <option value="">Selecione</option>
              <option value="SPED Fiscal">SPED Fiscal</option>
              <option value="SPED Contribuicoes">SPED Contribuicoes</option>
              <option value="ECF">ECF</option>
              <option value="DCTF">DCTF</option>
              <option value="NFe">NFe</option>
              <option value="Balancete">Balancete</option>
              <option value="Folha de Pagamento">Folha de Pagamento</option>
              <option value="Outros">Outros</option>
            </Select>
          </FormField>

          <FormField label="Status" htmlFor="status" required>
            <Select id="status" {...register('status')}>
              <option value="missing">Pendente</option>
              <option value="available">Disponivel</option>
              <option value="review">Em revisao</option>
              <option value="expired">Vencido</option>
            </Select>
          </FormField>

          <div className="grid grid-cols-2 gap-4">
            <FormField label="Data de emissao" htmlFor="issued_at" error={errors.issued_at?.message}>
              <Input id="issued_at" type="date" {...register('issued_at')} />
            </FormField>
            <FormField label="Data de vencimento" htmlFor="expires_at" error={errors.expires_at?.message}>
              <Input id="expires_at" type="date" {...register('expires_at')} />
            </FormField>
          </div>

          <FormField label="URL do arquivo" htmlFor="file_url" error={errors.file_url?.message}>
            <Input
              id="file_url"
              type="url"
              placeholder="https://drive.google.com/..."
              {...register('file_url')}
            />
          </FormField>

          <FormField label="Observacoes" htmlFor="notes" error={errors.notes?.message}>
            <Input id="notes" placeholder="Anotacoes (opcional)" {...register('notes')} />
          </FormField>

          <div className="flex justify-end gap-3 pt-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Salvando...' : 'Salvar documento'}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
