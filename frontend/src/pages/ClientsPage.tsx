'use client';
import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import { useForm, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import { Plus, Trash2, Download, Upload, Loader2, Lock, Briefcase, Search, X, Filter } from 'lucide-react';
import readXlsxFile from 'read-excel-file';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Dialog } from '@/components/ui/Dialog';
import { SecureNotesDrawer } from '@/components/SecureNotesDrawer';
import { ClientManageDrawer } from '@/components/ClientManageDrawer';
import { FormField } from '@/components/ui/FormField';
import { EmptyState, ErrorState, PageSpinner } from '@/components/ui/StateViews';
import {
  useClients,
  useCreateClient,
  useDeleteClient,
  type AccountingClient,
  type AccountingClientCreate,
  type ClientStatus,
} from '@/lib/hooks/useOperations';

// ---------------------------------------------------------------------------
// Schema
// ---------------------------------------------------------------------------

const schema = z.object({
  name: z.string().min(2, 'Nome deve ter ao menos 2 caracteres'),
  document: z.string().optional(),
  entity_type: z.enum(['pj', 'pf']),
  tax_regime: z.string().optional(),
  email: z.string().email('E-mail invalido').optional().or(z.literal('')),
  phone: z.string().optional(),
  municipal_registration: z.string().optional(),
  state_registration: z.string().optional(),
  status: z.enum(['active', 'inactive', 'onboarding']),
  notes: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

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

interface BrasilApiCnpj {
  razao_social?: string;
  email?: string;
  ddd_telefone_1?: string;
  telefone?: string;
}

async function fetchCnpj(cnpj: string): Promise<BrasilApiCnpj> {
  const response = await fetch(`https://brasilapi.com.br/api/cnpj/v1/${cnpj}`);
  if (!response.ok) throw new Error('CNPJ nao encontrado ou inativo');
  return response.json() as Promise<BrasilApiCnpj>;
}

// ---------------------------------------------------------------------------
// XLSX column map
// ---------------------------------------------------------------------------

const XLSX_COLUMN_MAP: Record<string, keyof FormValues> = {
  'Nome / Razao Social': 'name',
  'CPF / CNPJ': 'document',
  'E-mail': 'email',
  'Telefone': 'phone',
  'Inscricao Municipal': 'municipal_registration',
  'Inscricao Estadual': 'state_registration',
  'Observacoes': 'notes',
  'Regime Tributario': 'tax_regime',
};

// ---------------------------------------------------------------------------
// Sub-component: CNPJ auto-fill watcher
// ---------------------------------------------------------------------------

interface CnpjWatcherProps {
  control: ReturnType<typeof useForm<FormValues>>['control'];
  setValue: ReturnType<typeof useForm<FormValues>>['setValue'];
}

function CnpjWatcher({ control, setValue }: CnpjWatcherProps) {
  const document = useWatch({ control, name: 'document' });
  const [loading, setLoading] = useState(false);
  const [filled, setFilled] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastFetchedRef = useRef<string>('');

  const doFetch = useCallback(
    async (cnpj: string) => {
      if (lastFetchedRef.current === cnpj) return;
      lastFetchedRef.current = cnpj;
      setLoading(true);
      try {
        const data = await fetchCnpj(cnpj);
        if (data.razao_social) setValue('name', data.razao_social);
        if (data.email) setValue('email', data.email);
        const ddd = data.ddd_telefone_1?.trim() ?? '';
        const tel = data.telefone?.trim() ?? '';
        if (ddd || tel) setValue('phone', `${ddd}${tel}`);
        setFilled(true);
        setTimeout(() => setFilled(false), 3000);
      } catch {
        toast('CNPJ nao encontrado ou inativo. Preencha os dados manualmente.', {
          icon: '⚠️',
        });
      } finally {
        setLoading(false);
      }
    },
    [setValue]
  );

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);

    const digits = (document ?? '').replace(/\D/g, '');

    if (digits.length !== 14) return;

    timerRef.current = setTimeout(() => {
      doFetch(digits);
    }, 500);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [document, doFetch]);

  return (
    <>
      {loading && (
        <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
          <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
          Buscando dados...
        </span>
      )}
      {filled && !loading && (
        <span className="inline-flex items-center gap-1 rounded bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">
          Dados preenchidos via Receita Federal
        </span>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Sub-component: XLSX upload drop zone
// ---------------------------------------------------------------------------

interface XlsxUploaderProps {
  setValue: ReturnType<typeof useForm<FormValues>>['setValue'];
}

function XlsxUploader({ setValue }: XlsxUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  async function processFile(file: File) {
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (ext !== 'xlsx') {
      toast.error('Arquivo invalido. Use o modelo .xlsx disponibilizado.');
      return;
    }

    try {
      // read-excel-file aceita o File diretamente — sem FileReader necessário
      const rows = await readXlsxFile(file, { sheet: 'Dados do Cliente' });

      if (rows.length < 2) {
        toast.error('Nenhum dado encontrado no arquivo. Preencha ao menos uma linha.');
        return;
      }

      // Linha 0 = cabeçalhos, linha 1 = primeiro registro de dados
      const headers = rows[0].map(String);
      const dataRow = rows[1];

      const record: Record<string, unknown> = {};
      headers.forEach((header, i) => {
        record[header] = dataRow[i] ?? '';
      });

      let mapped = false;

      for (const [colName, fieldName] of Object.entries(XLSX_COLUMN_MAP)) {
        const rawValue = record[colName];
        if (rawValue !== undefined && rawValue !== '') {
          const value = String(rawValue).trim();
          if (fieldName === 'entity_type') continue; // tratado abaixo
          setValue(fieldName, value);
          mapped = true;
        }
      }

      // entity_type tratado separadamente
      const tipoRaw = record['Tipo (PJ ou PF)'];
      if (tipoRaw !== undefined && tipoRaw !== '') {
        const tipo = String(tipoRaw).trim().toUpperCase();
        setValue('entity_type', tipo === 'PF' ? 'pf' : 'pj');
        mapped = true;
      }

      if (!mapped) {
        toast.error(
          'Nenhuma coluna reconhecida. Verifique se o arquivo segue o modelo disponibilizado.'
        );
        return;
      }

      toast.success('Dados importados do arquivo. Revise antes de salvar.');
    } catch {
      toast.error('Erro ao ler o arquivo. Use o modelo .xlsx disponibilizado.');
    }
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) void processFile(file);
    // reset para permitir re-upload do mesmo arquivo
    e.target.value = '';
  }

  function handleDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) void processFile(file);
  }

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label="Importar dados do modelo XLSX"
      className={`flex cursor-pointer flex-col items-center justify-center gap-1 rounded-lg border-2 border-dashed px-4 py-5 text-center transition-colors ${
        dragging
          ? 'border-primary bg-primary/5'
          : 'border-border hover:border-primary/50 hover:bg-muted/40'
      }`}
      onClick={() => inputRef.current?.click()}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click();
      }}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
    >
      <Upload className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
      <p className="text-sm font-medium">Importar do modelo XLSX</p>
      <p className="text-xs text-muted-foreground">Arraste ou clique para selecionar</p>
      <input
        ref={inputRef}
        type="file"
        accept=".xlsx,.xls"
        className="sr-only"
        onChange={handleChange}
        aria-hidden="true"
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Filter types
// ---------------------------------------------------------------------------

type StatusFilter = '' | 'active' | 'inactive' | 'onboarding';
type TipoFilter = '' | 'pj' | 'pf';
type RegimeFilter = '' | 'Simples Nacional' | 'Lucro Presumido' | 'Lucro Real' | 'MEI';

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export function ClientsPage() {
  const [open, setOpen] = useState(false);
  const [secureNotes, setSecureNotes] = useState<{ id: string; name: string } | null>(null);
  const [selectedClient, setSelectedClient] = useState<AccountingClient | null>(null);
  const { data: clients, isLoading, isError } = useClients();
  const location = useLocation();

  // Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('');
  const [tipoFilter, setTipoFilter] = useState<TipoFilter>('');
  const [regimeFilter, setRegimeFilter] = useState<RegimeFilter>('');

  // Abre o dialog automaticamente quando vindo do dashboard com state { openCreate: true }
  useEffect(() => {
    if ((location.state as { openCreate?: boolean } | null)?.openCreate) {
      setOpen(true);
      // Limpa o state para não reabrir ao voltar para a página
      window.history.replaceState({}, '');
    }
  }, [location.state]);

  const createMutation = useCreateClient();
  const deleteMutation = useDeleteClient();

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    control,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { entity_type: 'pj', status: 'active' },
  });

  function handleClose() {
    reset();
    setOpen(false);
  }

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

  // Derived: are any filters active?
  const hasActiveFilters =
    searchQuery.trim() !== '' || statusFilter !== '' || tipoFilter !== '' || regimeFilter !== '';

  // Client-side filtering via useMemo
  const filteredClients = useMemo(() => {
    if (!clients) return [];

    const q = searchQuery.trim().toLowerCase();

    return clients.filter((client) => {
      // Search query: name, document, email
      if (q) {
        const matchesName = client.name.toLowerCase().includes(q);
        const matchesDoc = (client.document ?? '').toLowerCase().includes(q);
        const matchesEmail = (client.email ?? '').toLowerCase().includes(q);
        if (!matchesName && !matchesDoc && !matchesEmail) return false;
      }

      // Status filter
      if (statusFilter && client.status !== statusFilter) return false;

      // Tipo filter
      if (tipoFilter && client.entity_type !== tipoFilter) return false;

      // Regime filter
      if (regimeFilter && client.tax_regime !== regimeFilter) return false;

      return true;
    });
  }, [clients, searchQuery, statusFilter, tipoFilter, regimeFilter]);

  function clearFilters() {
    setSearchQuery('');
    setStatusFilter('');
    setTipoFilter('');
    setRegimeFilter('');
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold md:text-3xl">Clientes</h1>
          <p className="text-muted-foreground">
            Acompanhe a carteira e situacao operacional de cada cliente.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <a href="/template-cadastro-cliente.xlsx" download>
            <Button variant="outline" size="sm">
              <Download className="mr-1.5 h-4 w-4" aria-hidden="true" />
              Modelo XLSX
            </Button>
          </a>
          <Button onClick={() => setOpen(true)} size="sm">
            <Plus className="mr-1.5 h-4 w-4" aria-hidden="true" />
            Novo cliente
          </Button>
        </div>
      </div>

      {isError && (
        <ErrorState message="Nao foi possivel carregar os clientes. Verifique sua conexao." />
      )}

      {/* Summary cards */}
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

      {/* Filters bar */}
      {!isLoading && !isError && (
        <div className="flex flex-wrap gap-3">
          {/* Search input — takes most of the space */}
          <div className="relative flex-1 min-w-[200px]">
            <Search
              className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none"
              aria-hidden="true"
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Buscar por nome, CNPJ/CPF ou e-mail..."
              className="w-full rounded-md border border-border bg-background pl-9 pr-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
              aria-label="Buscar clientes"
            />
          </div>

          {/* Selects row + clear button */}
          <div className="flex flex-wrap gap-2 items-center">
            {/* Status filter */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
              className="rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
              aria-label="Filtrar por status"
            >
              <option value="">Todos os status</option>
              <option value="active">Ativo</option>
              <option value="inactive">Inativo</option>
              <option value="onboarding">Onboarding</option>
            </select>

            {/* Tipo filter */}
            <select
              value={tipoFilter}
              onChange={(e) => setTipoFilter(e.target.value as TipoFilter)}
              className="rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
              aria-label="Filtrar por tipo"
            >
              <option value="">Todos os tipos</option>
              <option value="pj">Pessoa Jurídica</option>
              <option value="pf">Pessoa Física</option>
            </select>

            {/* Regime filter */}
            <select
              value={regimeFilter}
              onChange={(e) => setRegimeFilter(e.target.value as RegimeFilter)}
              className="rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
              aria-label="Filtrar por regime tributário"
            >
              <option value="">Todos os regimes</option>
              <option value="Simples Nacional">Simples Nacional</option>
              <option value="Lucro Presumido">Lucro Presumido</option>
              <option value="Lucro Real">Lucro Real</option>
              <option value="MEI">MEI</option>
            </select>

            {/* Clear filters button — only when filters are active */}
            {hasActiveFilters && (
              <button
                type="button"
                onClick={clearFilters}
                className="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-colors focus:outline-none focus:ring-2 focus:ring-ring"
                aria-label="Limpar filtros"
              >
                <X className="h-3.5 w-3.5" aria-hidden="true" />
                Limpar filtros
              </button>
            )}
          </div>
        </div>
      )}

      {/* Clients table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-2 pb-3">
          <CardTitle className="text-base">Carteira de clientes</CardTitle>
          {/* Counter */}
          {!isLoading && !isError && clients && (
            <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
              <Filter className="h-3.5 w-3.5" aria-hidden="true" />
              {hasActiveFilters
                ? `${filteredClients.length} de ${total} clientes`
                : `${total} ${total === 1 ? 'cliente' : 'clientes'}`}
            </span>
          )}
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <PageSpinner />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[740px] text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="pb-3 font-medium">Codigo</th>
                    <th className="pb-3 font-medium">Cliente</th>
                    <th className="pb-3 font-medium">Tipo</th>
                    <th className="pb-3 font-medium">Regime</th>
                    <th className="pb-3 font-medium">Contato</th>
                    <th className="pb-3 font-medium">Status</th>
                    <th className="pb-3 font-medium text-right pr-4">Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {/* Empty state: no clients at all */}
                  {total === 0 && (
                    <tr>
                      <td colSpan={7}>
                        <EmptyState
                          title="Nenhum cliente cadastrado"
                          description="Cadastre seu primeiro cliente clicando em Novo cliente."
                        />
                      </td>
                    </tr>
                  )}

                  {/* Empty state: clients exist but filters return nothing */}
                  {total > 0 && filteredClients.length === 0 && (
                    <tr>
                      <td colSpan={7}>
                        <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
                          <Search className="h-8 w-8 text-muted-foreground/50" aria-hidden="true" />
                          <div>
                            <p className="font-medium text-foreground">Nenhum cliente encontrado</p>
                            <p className="mt-1 text-sm text-muted-foreground">
                              Nenhum cliente corresponde aos filtros aplicados.{' '}
                              <button
                                type="button"
                                onClick={clearFilters}
                                className="underline underline-offset-2 hover:text-foreground transition-colors"
                              >
                                Limpar filtros
                              </button>{' '}
                              para ver todos os clientes.
                            </p>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}

                  {/* Filtered rows */}
                  {filteredClients.map((client) => (
                    <tr key={client.id} className="border-b last:border-0">
                      <td className="py-4">
                        <span className="font-mono text-xs bg-muted px-1.5 py-0.5 rounded text-muted-foreground">
                          #{client.client_code}
                        </span>
                      </td>
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
                      <td className="py-4 text-right pr-4">
                        <div className="flex items-center justify-end gap-3">
                          <button
                            type="button"
                            onClick={() => setSelectedClient(client)}
                            className="flex flex-col items-center gap-0.5 rounded p-1 text-muted-foreground hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            aria-label={`Gerenciar cliente ${client.name}`}
                            title="Gerenciar Empresa"
                          >
                            <Briefcase className="h-4 w-4" />
                            <span className="text-[9px] font-medium uppercase tracking-wider">Gerenciar</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => setSecureNotes({ id: client.id, name: client.name })}
                            className="flex flex-col items-center gap-0.5 rounded p-1 text-muted-foreground hover:text-amber-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            aria-label={`Notas seguras de ${client.name}`}
                            title="Notas seguras"
                          >
                            <Lock className="h-4 w-4" />
                            <span className="text-[9px] font-medium uppercase tracking-wider">Anotações</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDelete(client.id, client.name)}
                            className="flex flex-col items-center gap-0.5 rounded p-1 text-muted-foreground hover:text-destructive focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            aria-label={`Excluir cliente ${client.name}`}
                            title="Excluir cliente"
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

      {/* Secure notes drawer */}
      <SecureNotesDrawer
        open={!!secureNotes}
        onClose={() => setSecureNotes(null)}
        clientId={secureNotes?.id ?? ''}
        clientName={secureNotes?.name ?? ''}
      />

      {/* Client management drawer */}
      <ClientManageDrawer
        open={!!selectedClient}
        onClose={() => setSelectedClient(null)}
        client={selectedClient}
      />

      {/* New client dialog */}
      <Dialog
        open={open}
        onClose={handleClose}
        title="Novo cliente"
        className="max-w-xl"
        footer={
          <div className="flex justify-end gap-3">
            <Button type="button" variant="outline" onClick={handleClose}>
              Cancelar
            </Button>
            <Button type="submit" form="new-client-form" disabled={isSubmitting}>
              {isSubmitting ? 'Salvando...' : 'Salvar cliente'}
            </Button>
          </div>
        }
      >
        <form id="new-client-form" onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          {/* Feature 3c: XLSX upload */}
          <XlsxUploader setValue={setValue} />

          <div className="relative">
            <div className="absolute inset-0 flex items-center" aria-hidden="true">
              <span className="w-full border-t" />
            </div>
            <div className="relative flex justify-center">
              <span className="bg-background px-2 text-xs text-muted-foreground">
                ou preencha manualmente
              </span>
            </div>
          </div>

          <FormField
            label="Nome / Razao social"
            htmlFor="name"
            error={errors.name?.message}
            required
          >
            <Input id="name" placeholder="Ex: Empresa XYZ Ltda" {...register('name')} />
          </FormField>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <FormField
                label="CPF / CNPJ"
                htmlFor="document"
                error={errors.document?.message}
              >
                <Input
                  id="document"
                  placeholder="00.000.000/0001-00 ou CPF"
                  {...register('document')}
                />
              </FormField>
              {/* Feature 2: CNPJ auto-fill status */}
              <CnpjWatcher control={control} setValue={setValue} />
            </div>

            <FormField label="Tipo" htmlFor="entity_type" required>
              <Select id="entity_type" {...register('entity_type')}>
                <option value="pj">Pessoa Juridica</option>
                <option value="pf">Pessoa Fisica</option>
              </Select>
            </FormField>
          </div>

          <FormField
            label="Regime tributario"
            htmlFor="tax_regime"
            error={errors.tax_regime?.message}
          >
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
              <Input
                id="email"
                type="email"
                placeholder="contato@empresa.com"
                {...register('email')}
              />
            </FormField>
            <FormField label="Telefone" htmlFor="phone" error={errors.phone?.message}>
              <Input id="phone" placeholder="(11) 99999-9999" {...register('phone')} />
            </FormField>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <FormField
              label="Inscricao Municipal"
              htmlFor="municipal_registration"
              error={errors.municipal_registration?.message}
            >
              <Input
                id="municipal_registration"
                placeholder="Opcional"
                {...register('municipal_registration')}
              />
            </FormField>
            <FormField
              label="Inscricao Estadual"
              htmlFor="state_registration"
              error={errors.state_registration?.message}
            >
              <Input
                id="state_registration"
                placeholder="Opcional"
                {...register('state_registration')}
              />
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
            <Input
              id="notes"
              placeholder="Anotacoes internas (opcional)"
              {...register('notes')}
            />
          </FormField>

        </form>
      </Dialog>
    </div>
  );
}
