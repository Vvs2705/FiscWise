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
  useCertificates,
  useCreateCertificate,
  useDeleteCertificate,
  type CertificateCreate,
  type CertificateStatus,
} from '@/lib/hooks/useOperations';

const schema = z.object({
  client_id: z.string().min(1, 'Selecione um cliente'),
  label: z.string().min(2, 'Rotulo deve ter ao menos 2 caracteres'),
  certificate_type: z.enum(['A1', 'A3', 'NF-e', 'NFS-e', 'CT-e', 'Outros']),
  valid_from: z.string().optional(),
  valid_until: z.string().min(1, 'Data de vencimento e obrigatoria'),
  status: z.enum(['valid', 'expiring', 'expired', 'revoked']),
  notes: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

const statusLabel: Record<CertificateStatus, string> = {
  valid: 'Em dia',
  expiring: 'Vencendo',
  expired: 'Vencido',
  revoked: 'Revogado',
};

const statusVariant: Record<CertificateStatus, 'success' | 'warning' | 'error' | 'default'> = {
  valid: 'success',
  expiring: 'warning',
  expired: 'error',
  revoked: 'default',
};

/** Calcula dias ate o vencimento a partir de uma string ISO date */
function daysUntil(dateStr: string): number {
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  const target = new Date(`${dateStr}T00:00:00`);
  return Math.round((target.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
}

function urgencyVariant(days: number): 'success' | 'warning' | 'error' {
  if (days <= 15) return 'error';
  if (days <= 30) return 'warning';
  return 'success';
}

export function CertificatesPage() {
  const [open, setOpen] = useState(false);
  const { data: certificates, isLoading, isError } = useCertificates();
  const { data: clients } = useClients();
  const createMutation = useCreateCertificate();
  const deleteMutation = useDeleteCertificate();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { certificate_type: 'A1', status: 'valid' },
  });

  async function onSubmit(values: FormValues) {
    const payload: CertificateCreate = { ...values };
    try {
      await createMutation.mutateAsync(payload);
      toast.success('Certificado registrado');
      reset();
      setOpen(false);
    } catch {
      toast.error('Erro ao registrar certificado. Tente novamente.');
    }
  }

  async function handleDelete(id: string, label: string) {
    if (!confirm(`Excluir certificado "${label}"?`)) return;
    try {
      await deleteMutation.mutateAsync(id);
      toast.success('Certificado removido');
    } catch {
      toast.error('Erro ao remover certificado');
    }
  }

  const total = certificates?.length ?? 0;
  const expiring30 = certificates?.filter((c) => daysUntil(c.valid_until) <= 30 && daysUntil(c.valid_until) > 0).length ?? 0;
  const a1Count = certificates?.filter((c) => c.certificate_type === 'A1').length ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold md:text-3xl">Certificados Digitais</h1>
          <p className="text-muted-foreground">
            Monitore certificados A1 e A3 com alertas de vencimento.
          </p>
        </div>
        <Button onClick={() => setOpen(true)} size="sm">
          <Plus className="mr-1.5 h-4 w-4" aria-hidden="true" />
          Novo certificado
        </Button>
      </div>

      {isError && <ErrorState message="Nao foi possivel carregar os certificados." />}

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoading ? '...' : total}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Vencendo em 30 dias</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-amber-600">{isLoading ? '...' : expiring30}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Tipo A1</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoading ? '...' : a1Count}</div>
          </CardContent>
        </Card>
      </div>

      {isLoading ? (
        <div className="grid gap-4 lg:grid-cols-3">
          <LoadingCards count={3} />
        </div>
      ) : (certificates ?? []).length === 0 ? (
        <Card>
          <CardContent className="pt-6">
            <EmptyState
              title="Nenhum certificado registrado"
              description="Cadastre os certificados digitais dos clientes para monitorar vencimentos."
              action={
                <Button size="sm" onClick={() => setOpen(true)}>
                  Novo certificado
                </Button>
              }
            />
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 lg:grid-cols-3">
          {(certificates ?? []).map((cert) => {
            const days = daysUntil(cert.valid_until);
            return (
              <Card key={cert.id}>
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-3">
                    <CardTitle className="text-base">{cert.label}</CardTitle>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <Badge variant={statusVariant[cert.status]}>
                        {statusLabel[cert.status]}
                      </Badge>
                      <button
                        type="button"
                        onClick={() => handleDelete(cert.id, cert.label)}
                        className="flex flex-col items-center gap-0.5 rounded p-1 text-muted-foreground hover:text-destructive focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        aria-label={`Excluir certificado ${cert.label}`}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        <span className="text-[9px] font-medium uppercase tracking-wider">Excluir</span>
                      </button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div className="flex justify-between gap-3">
                    <span className="text-muted-foreground">Tipo</span>
                    <span className="font-medium">{cert.certificate_type}</span>
                  </div>
                  {cert.valid_from && (
                    <div className="flex justify-between gap-3">
                      <span className="text-muted-foreground">Emissao</span>
                      <span className="font-medium">{dateBR(cert.valid_from)}</span>
                    </div>
                  )}
                  <div className="flex justify-between gap-3">
                    <span className="text-muted-foreground">Vencimento</span>
                    <span className="font-medium">{dateBR(cert.valid_until)}</span>
                  </div>
                  <div className="flex justify-between gap-3">
                    <span className="text-muted-foreground">Dias restantes</span>
                    <Badge variant={urgencyVariant(days)}>
                      {days > 0 ? `${days} dias` : days === 0 ? 'Vence hoje' : 'Vencido'}
                    </Badge>
                  </div>
                  {cert.notes && (
                    <p className="text-xs text-muted-foreground pt-1">{cert.notes}</p>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      <Dialog open={open} onClose={() => setOpen(false)} title="Novo certificado">
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

          <FormField label="Rotulo / Identificacao" htmlFor="label" error={errors.label?.message} required>
            <Input id="label" placeholder="Ex: Cert A1 - Empresa XYZ 2026" {...register('label')} />
          </FormField>

          <div className="grid grid-cols-2 gap-4">
            <FormField label="Tipo" htmlFor="certificate_type" required>
              <Select id="certificate_type" {...register('certificate_type')}>
                <option value="A1">A1</option>
                <option value="A3">A3</option>
                <option value="NF-e">NF-e</option>
                <option value="NFS-e">NFS-e</option>
                <option value="CT-e">CT-e</option>
                <option value="Outros">Outros</option>
              </Select>
            </FormField>

            <FormField label="Status" htmlFor="status" required>
              <Select id="status" {...register('status')}>
                <option value="valid">Em dia</option>
                <option value="expiring">Vencendo</option>
                <option value="expired">Vencido</option>
                <option value="revoked">Revogado</option>
              </Select>
            </FormField>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <FormField label="Data de emissao" htmlFor="valid_from" error={errors.valid_from?.message}>
              <Input id="valid_from" type="date" {...register('valid_from')} />
            </FormField>
            <FormField label="Data de vencimento" htmlFor="valid_until" error={errors.valid_until?.message} required>
              <Input id="valid_until" type="date" {...register('valid_until')} />
            </FormField>
          </div>

          <FormField label="Observacoes" htmlFor="notes" error={errors.notes?.message}>
            <Input id="notes" placeholder="Numero de serie, informacoes adicionais..." {...register('notes')} />
          </FormField>

          <div className="flex justify-end gap-3 pt-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Salvando...' : 'Salvar certificado'}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
