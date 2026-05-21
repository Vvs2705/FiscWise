'use client';
import { useState, useEffect, useRef, useCallback } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import { Plus, Trash2, Download, Upload, Loader2 } from 'lucide-react';
import * as XLSX from 'xlsx';
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

  function processFile(file: File) {
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (ext !== 'xlsx' && ext !== 'xls') {
      toast.error('Arquivo invalido. Use o modelo .xlsx disponibilizado.');
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = new Uint8Array(e.target?.result as ArrayBuffer);
        const workbook = XLSX.read(data, { type: 'array' });

        const sheet = workbook.Sheets['Dados do Cliente'];
        if (!sheet) {
          toast.error('Aba "Dados do Cliente" nao encontrada. Use o modelo correto.');
          return;
        }

        // SheetJS rows as array-of-objects using the first row as keys
        const rows = XLSX.utils.sheet_to_json<Record<string, unknown>>(sheet, { defval: '' });

        if (rows.length === 0) {
          toast.error('Nenhum dado encontrado no arquivo. Preencha ao menos uma linha.');
          return;
        }

        const row = rows[0];
        let mapped = false;

        for (const [colName, fieldName] of Object.entries(XLSX_COLUMN_MAP)) {
          const rawValue = row[colName];
          if (rawValue !== undefined && rawValue !== '') {
            const value = String(rawValue).trim();

            if (fieldName === 'entity_type') {
              // handled separately below
              continue;
            }

            setValue(fieldName, value);
            mapped = true;
          }
        }

        // Handle entity_type separately
        const tipoRaw = row['Tipo (PJ ou PF)'];
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
    };
    reader.readAsArrayBuffer(file);
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) processFile(file);
    // reset input so the same file can be re-uploaded
    e.target.value = '';
  }

  function handleDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) processFile(file);
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
// Main page
// ---------------------------------------------------------------------------

export function ClientsPage() {
  const [open, setOpen] = useState(false);
  const { data: clients, isLoading, isError } = useClients();
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

      {/* Clients table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Carteira de clientes</CardTitle>
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
                    <th className="pb-3 font-medium sr-only">Acoes</th>
                  </tr>
                </thead>
                <tbody>
                  {(clients ?? []).length === 0 && (
                    <tr>
                      <td colSpan={7}>
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
