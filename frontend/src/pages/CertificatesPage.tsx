'use client';
import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { api, getApiErrorMessage } from '@/lib/api';
import { Plus, Trash2, LayoutGrid, List, Search, Bell, BookOpen } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CertificateCard } from '@/components/ui/Card';
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
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if ((location.state as { openCreate?: boolean } | null)?.openCreate) {
      setOpen(true);
      window.history.replaceState({}, '');
    }
  }, [location.state]);
  const [search, setSearch] = useState('');
  const [selectedClient, setSelectedClient] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [selectedType, setSelectedType] = useState('');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

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
    const payload: CertificateCreate = {
      ...values,
      valid_from: values.valid_from === '' ? undefined : values.valid_from,
    };
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

  const handleWarnClient = (
    clientId: string,
    clientName: string,
    certLabel: string,
    daysLeft: number,
  ) => (e: React.MouseEvent) => {
    e.stopPropagation();
    toast.promise(
      api.post('/api/v1/notifications/cert-expiry-warning', {
        client_id: clientId,
        client_name: clientName,
        cert_label: certLabel,
        days_until_expiry: daysLeft,
      }),
      {
        loading: `Enviando aviso de vencimento para ${clientName}...`,
        success: `Aviso do certificado "${certLabel}" enviado com sucesso!`,
        error: (err) => getApiErrorMessage(err, 'Erro ao enviar aviso.'),
      }
    );
  };

  const total = certificates?.length ?? 0;
  const expiring30 = certificates?.filter((c) => daysUntil(c.valid_until) <= 30 && daysUntil(c.valid_until) > 0).length ?? 0;
  const a1Count = certificates?.filter((c) => c.certificate_type === 'A1').length ?? 0;

  const filteredCertificates = (certificates ?? []).filter((cert) => {
    const client = clients?.find((c) => c.id === cert.client_id);
    const clientName = client?.name?.toLowerCase() || '';
    const label = cert.label?.toLowerCase() || '';
    const query = search.toLowerCase();

    const matchesSearch = clientName.includes(query) || label.includes(query);
    const matchesClient = !selectedClient || cert.client_id === selectedClient;
    const matchesStatus = !selectedStatus || cert.status === selectedStatus;
    const matchesType = !selectedType || cert.certificate_type === selectedType;

    return matchesSearch && matchesClient && matchesStatus && matchesType;
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold md:text-3xl bg-clip-text text-transparent bg-gradient-to-r from-teal-400 via-emerald-400 to-sky-400">
            Certificados Digitais
          </h1>
          <p className="text-muted-foreground mt-1">
            Monitore certificados A1 e A3 com alertas de vencimento integrados.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate('/aprender')}
            className="h-9 border-teal-500/25 bg-teal-500/10 text-teal-300 hover:bg-teal-500/20 gap-1.5"
            title="Aprender sobre esta tela"
          >
            <BookOpen className="h-4 w-4" />
            <span>Guia</span>
          </Button>
          <Button onClick={() => setOpen(true)} size="sm" className="bg-gradient-to-r from-teal-500 to-emerald-600 hover:from-teal-600 hover:to-emerald-700 shadow-md">
            <Plus className="mr-1.5 h-4 w-4" aria-hidden="true" />
            Novo certificado
          </Button>
        </div>
      </div>

      {isError && <ErrorState message="Nao foi possivel carregar os certificados." />}

      {/* KPI Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card className="bg-card/45 backdrop-blur-sm border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
              Total Gerenciado
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-extrabold text-foreground">{isLoading ? '...' : total}</div>
          </CardContent>
        </Card>
        <Card className="bg-card/45 backdrop-blur-sm border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-amber-500 uppercase tracking-wider">
              Vencendo em 30 dias
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-extrabold text-amber-500">
              {isLoading ? '...' : expiring30}
            </div>
          </CardContent>
        </Card>
        <Card className="bg-card/45 backdrop-blur-sm border-border/50 sm:col-span-2 lg:col-span-1">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
              Tipo A1
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-extrabold text-foreground">{isLoading ? '...' : a1Count}</div>
          </CardContent>
        </Card>
      </div>

      {/* Search and Filters toolbar */}
      <Card className="p-4 bg-card/40 backdrop-blur-md border-border/50">
        <div className="flex flex-col lg:flex-row gap-4 justify-between lg:items-center">
          <div className="flex flex-1 flex-col sm:flex-row gap-3">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Buscar por cliente ou rótulo..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9 bg-muted/20 border-border/50 focus:border-teal-500/50"
              />
            </div>

            <Select
              value={selectedClient}
              onChange={(e) => setSelectedClient(e.target.value)}
              className="sm:w-[200px] bg-muted/20 border-border/50"
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
              className="sm:w-[150px] bg-muted/20 border-border/50"
            >
              <option value="">Todos Status</option>
              <option value="valid">Em dia</option>
              <option value="expiring">Vencendo</option>
              <option value="expired">Vencido</option>
              <option value="revoked">Revogado</option>
            </Select>

            <Select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="sm:w-[150px] bg-muted/20 border-border/50"
            >
              <option value="">Todos Tipos</option>
              <option value="A1">A1</option>
              <option value="A3">A3</option>
              <option value="NF-e">NF-e</option>
              <option value="NFS-e">NFS-e</option>
              <option value="CT-e">CT-e</option>
              <option value="Outros">Outros</option>
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

      {/* Main Content Area */}
      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <LoadingCards count={6} />
        </div>
      ) : filteredCertificates.length === 0 ? (
        <Card className="bg-card/45 backdrop-blur-sm border-border/50">
          <CardContent className="pt-6">
            <EmptyState
              title="Nenhum certificado encontrado"
              description="Nenhum certificado atende aos filtros selecionados. Tente ajustar os filtros ou cadastre um novo certificado."
              action={
                <Button size="sm" onClick={() => setOpen(true)} className="bg-primary/10 text-primary border border-primary/20 hover:bg-primary/20">
                  Novo certificado
                </Button>
              }
            />
          </CardContent>
        </Card>
      ) : viewMode === 'grid' ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filteredCertificates.map((cert) => {
            const client = clients?.find((c) => c.id === cert.client_id);
            const clientName = client?.name || 'Cliente Desconhecido';
            const days = daysUntil(cert.valid_until);
            const displayLabel = `${clientName} - ${cert.label}`;

            return (
              <div key={cert.id} className="relative group">
                <CertificateCard
                  label={displayLabel}
                  type={cert.certificate_type}
                  expiryDate={dateBR(cert.valid_until)}
                  daysRemaining={days}
                  onWarnClient={handleWarnClient(cert.client_id, clientName, cert.label, days)}
                />
                <button
                  type="button"
                  onClick={() => handleDelete(cert.id, cert.label)}
                  className="absolute top-4 right-4 z-10 p-1.5 rounded-lg bg-card border border-border/50 text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all opacity-0 group-hover:opacity-100 focus:opacity-100"
                  aria-label={`Excluir certificado ${cert.label}`}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            );
          })}
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Cliente & Rótulo</TableHead>
              <TableHead>Tipo</TableHead>
              <TableHead>Emissão</TableHead>
              <TableHead>Vencimento</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Prazo</TableHead>
              <TableHead className="text-right">Ações</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredCertificates.map((cert) => {
              const client = clients?.find((c) => c.id === cert.client_id);
              const clientName = client?.name || 'Cliente Desconhecido';
              const days = daysUntil(cert.valid_until);

              return (
                <TableRow key={cert.id}>
                  <TableCell>
                    <div className="font-semibold text-foreground">{clientName}</div>
                    <div className="text-xs text-muted-foreground">{cert.label}</div>
                  </TableCell>
                  <TableCell>
                    <Badge className="bg-muted/50 text-foreground border-border/30">
                      {cert.certificate_type}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {cert.valid_from ? dateBR(cert.valid_from) : '—'}
                  </TableCell>
                  <TableCell className="font-medium text-foreground">
                    {dateBR(cert.valid_until)}
                  </TableCell>
                  <TableCell>
                    <Badge variant={statusVariant[cert.status]}>
                      {statusLabel[cert.status]}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={urgencyVariant(days)}>
                      {days > 0 ? `${days} dias` : days === 0 ? 'Vence hoje' : 'Vencido'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center justify-end gap-2">
                      {days <= 30 && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={handleWarnClient(cert.client_id, clientName, cert.label, days)}
                          className="h-8 text-xs text-teal-400 hover:text-teal-300 hover:bg-teal-500/10 gap-1.5"
                          title="Avisar cliente por e-mail"
                        >
                          <Bell className="h-3.5 w-3.5" />
                          <span>Notificar</span>
                        </Button>
                      )}
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleDelete(cert.id, cert.label)}
                        className="h-8 text-xs text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                        title="Excluir certificado"
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

      {/* Dialog creation form */}
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
            <Button type="submit" disabled={isSubmitting} className="bg-gradient-to-r from-teal-500 to-emerald-600 text-white">
              {isSubmitting ? 'Salvando...' : 'Salvar certificado'}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
