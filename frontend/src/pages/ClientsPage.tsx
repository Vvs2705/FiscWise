'use client';
import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useLocation, useSearchParams, useNavigate } from 'react-router-dom';
import { useForm, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import {
  Plus,
  Archive,
  Download,
  Upload,
  Loader2,
  Lock,
  Briefcase,
  Search,
  X,
  Filter,
  UserCheck,
  UserX,
  LayoutList,
  LayoutGrid,
  BookOpen,
} from 'lucide-react';
import { startTour } from '@/lib/tours';
import readXlsxFile from 'read-excel-file';
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Dialog } from '@/components/ui/Dialog';
import { SecureNotesDrawer } from '@/components/SecureNotesDrawer';
import { ClientDetailsDrawer } from '@/features/clients/components/ClientDetailsDrawer';
import { FormField } from '@/components/ui/FormField';
import { EmptyState, ErrorState, PageSpinner } from '@/components/ui/StateViews';
import { ProgressRing } from '@/components/ui/ProgressRing';
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/Table';
import {
  useClients,
  useCreateClient,
  useDeleteClient,
  useDeadlines,
  type AccountingClient,
  type AccountingClientCreate,
  type ClientStatus,
  type DeadlineItem,
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
        <span className="inline-flex items-center gap-1 rounded bg-success/10 px-2 py-0.5 text-xs font-medium text-success">
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
      const rows = await readXlsxFile(file, { sheet: 'Dados do Cliente' });

      if (rows.length < 2) {
        toast.error('Nenhum dado encontrado no arquivo. Preencha ao menos uma linha.');
        return;
      }

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
          if (fieldName === 'entity_type') continue;
          setValue(fieldName, value);
          mapped = true;
        }
      }

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

type StatusFilter = '' | 'active' | 'onboarding';
type ClientView = 'operational' | 'inactive';
type TipoFilter = '' | 'pj' | 'pf';
type RegimeFilter = '' | 'Simples Nacional' | 'Lucro Presumido' | 'Lucro Real' | 'MEI';

// ---------------------------------------------------------------------------
// Sub-components for Row & Card
// ---------------------------------------------------------------------------

interface ClientItemProps {
  client: AccountingClient;
  deadlines: DeadlineItem[];
  onManage: () => void;
  onNotes: () => void;
  onDeactivate: () => void;
}

function ClientTableRow({ client, deadlines, onManage, onNotes, onDeactivate }: ClientItemProps) {
  const clientDeadlines = useMemo(() => deadlines.filter((d) => d.client_id === client.id), [deadlines, client.id]);
  const pendingCount = useMemo(() => clientDeadlines.filter((d) => d.status !== 'completed').length, [clientDeadlines]);
  
  const lastAction = useMemo(() => {
    if (clientDeadlines.length === 0) return 'Nenhuma';
    const sorted = [...clientDeadlines].sort(
      (a, b) => new Date(b.updated_at || b.created_at).getTime() - new Date(a.updated_at || a.created_at).getTime()
    );
    const last = sorted[0];
    const dateStr = new Date(last.updated_at || last.created_at).toLocaleDateString('pt-BR');
    return `${last.title} (${dateStr})`;
  }, [clientDeadlines]);

  const healthScore = useMemo(() => {
    let score = 100;
    const overdueDl = clientDeadlines.filter((d) => d.status === 'overdue').length;
    score -= overdueDl * 15;
    return Math.max(0, Math.min(100, score));
  }, [clientDeadlines]);

  return (
    <TableRow>
      <TableCell>
        <span className="font-mono text-xs bg-muted px-1.5 py-0.5 rounded text-muted-foreground">
          #{client.client_code}
        </span>
      </TableCell>
      <TableCell>
        <div className="font-bold text-foreground">{client.name}</div>
        {client.document && <div className="text-xs text-muted-foreground font-mono">{client.document}</div>}
      </TableCell>
      <TableCell className="uppercase text-xs font-semibold text-muted-foreground">
        {client.entity_type}
      </TableCell>
      <TableCell>
        {client.tax_regime ? (
          <Badge className="border-primary/20 bg-primary/5 text-primary text-xs">
            {client.tax_regime}
          </Badge>
        ) : (
          <span className="text-xs text-muted-foreground">-</span>
        )}
      </TableCell>
      <TableCell>
        <div className="text-xs">{client.email ?? '-'}</div>
        {client.phone && <div className="text-xs text-muted-foreground">{client.phone}</div>}
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          <ProgressRing score={healthScore} size={28} strokeWidth={2.5} />
          <span className="text-xs font-semibold text-foreground/80">{pendingCount} pendentes</span>
        </div>
      </TableCell>
      <TableCell className="max-w-[180px] truncate text-xs text-muted-foreground" title={lastAction}>
        {lastAction}
      </TableCell>
      <TableCell>
        <Badge variant={statusVariant[client.status]}>
          {statusLabel[client.status]}
        </Badge>
      </TableCell>
      <TableCell className="text-right">
        <div className="flex items-center justify-end gap-1.5">
          <Button
            variant="ghost"
            size="sm"
            onClick={onManage}
            className="h-8 gap-1 text-primary hover:text-primary hover:bg-primary/10"
            title="Gerenciar Empresa"
          >
            <Briefcase className="h-4 w-4" />
            <span className="sr-only sm:not-sr-only text-[10px] uppercase font-bold tracking-wider">Gerenciar</span>
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={onNotes}
            className="h-8 gap-1 text-warning hover:text-warning hover:bg-warning/10"
            title="Notas seguras"
          >
            <Lock className="h-4 w-4" />
            <span className="sr-only sm:not-sr-only text-[10px] uppercase font-bold tracking-wider">Notas</span>
          </Button>
          {client.status !== 'inactive' && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onDeactivate}
              className="h-8 gap-1 text-destructive hover:text-destructive hover:bg-destructive/10"
              title="Desativar cliente"
            >
              <Archive className="h-4 w-4" />
              <span className="sr-only sm:not-sr-only text-[10px] uppercase font-bold tracking-wider">Desativar</span>
            </Button>
          )}
        </div>
      </TableCell>
    </TableRow>
  );
}

function ClientGridCard({ client, deadlines, onManage, onNotes, onDeactivate }: ClientItemProps) {
  const clientDeadlines = useMemo(() => deadlines.filter((d) => d.client_id === client.id), [deadlines, client.id]);
  const pendingCount = useMemo(() => clientDeadlines.filter((d) => d.status !== 'completed').length, [clientDeadlines]);

  const lastAction = useMemo(() => {
    if (clientDeadlines.length === 0) return 'Nenhuma';
    const sorted = [...clientDeadlines].sort(
      (a, b) => new Date(b.updated_at || b.created_at).getTime() - new Date(a.updated_at || a.created_at).getTime()
    );
    const last = sorted[0];
    const dateStr = new Date(last.updated_at || last.created_at).toLocaleDateString('pt-BR');
    return `${last.title} (${dateStr})`;
  }, [clientDeadlines]);

  const healthScore = useMemo(() => {
    let score = 100;
    const overdueDl = clientDeadlines.filter((d) => d.status === 'overdue').length;
    score -= overdueDl * 15;
    return Math.max(0, Math.min(100, score));
  }, [clientDeadlines]);

  return (
    <Card className="hover:border-primary/40 relative group flex flex-col justify-between h-full">
      <CardHeader className="pb-3 flex flex-row justify-between items-start gap-4">
        <div className="min-w-0">
          <span className="font-mono text-[10px] bg-muted px-1.5 py-0.5 rounded text-muted-foreground">
            #{client.client_code}
          </span>
          <h4 className="font-bold text-foreground text-base leading-tight mt-2 truncate" title={client.name}>
            {client.name}
          </h4>
          {client.document && (
            <p className="text-xs text-muted-foreground font-mono mt-1 truncate">{client.document}</p>
          )}
        </div>
        <ProgressRing score={healthScore} size={36} strokeWidth={3} />
      </CardHeader>

      <CardContent className="pb-4 space-y-3 flex-1 flex flex-col justify-between">
        <div className="space-y-3">
          <div className="flex flex-wrap gap-1.5">
            <Badge variant={statusVariant[client.status]}>{statusLabel[client.status]}</Badge>
            <Badge className="border-primary/20 bg-primary/5 text-primary">
              {client.tax_regime ?? 'Não informado'}
            </Badge>
            <Badge className="uppercase text-[10px]">
              {client.entity_type}
            </Badge>
          </div>

          <div className="text-xs space-y-1 bg-muted/20 rounded-lg p-2.5 border border-border/40">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Prazos pendentes:</span>
              <span className="font-semibold text-foreground">{pendingCount} itens</span>
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-muted-foreground shrink-0">Última ação:</span>
              <span className="font-semibold text-foreground truncate text-right w-full" title={lastAction}>
                {lastAction}
              </span>
            </div>
          </div>
        </div>

        <div className="text-xs text-muted-foreground space-y-0.5 pt-3">
          <p className="truncate" title={client.email || ''}>📧 {client.email || 'Sem e-mail'}</p>
          <p>📞 {client.phone || 'Sem telefone'}</p>
        </div>
      </CardContent>

      <CardFooter className="pt-3 border-t border-border/40 flex justify-between gap-1.5">
        <Button
          variant="ghost"
          size="sm"
          onClick={onManage}
          className="flex-1 h-8 gap-1.5 text-primary hover:bg-primary/10 hover:text-primary"
        >
          <Briefcase className="h-3.5 w-3.5" />
          <span>Gerenciar</span>
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={onNotes}
          className="flex-1 h-8 gap-1.5 text-warning hover:bg-warning/10 hover:text-warning"
        >
          <Lock className="h-3.5 w-3.5" />
          <span>Notas</span>
        </Button>
        {client.status !== 'inactive' && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onDeactivate}
            className="h-8 w-8 p-0 text-destructive hover:bg-destructive/10 hover:text-destructive"
            title="Desativar cliente"
          >
            <Archive className="h-3.5 w-3.5" />
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export function ClientsPage() {
  const [open, setOpen] = useState(false);
  const [secureNotes, setSecureNotes] = useState<{ id: string; name: string } | null>(null);
  const [selectedClientId, setSelectedClientId] = useState<string | null>(null);
  const { data: clients, isLoading, isError } = useClients();
  const { data: deadlines = [] } = useDeadlines();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  // View state: list (table) vs card grid
  const [viewMode, setViewMode] = useState<'list' | 'card'>('list');

  // Filter state
  const [clientView, setClientView] = useState<ClientView>('operational');
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('');
  const [tipoFilter, setTipoFilter] = useState<TipoFilter>('');
  const [regimeFilter, setRegimeFilter] = useState<RegimeFilter>('');

  // Search Debouncing
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearchQuery(searchQuery);
    }, 300);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  // Handle URL redirect query parameters (e.g. ?id=... from global search)
  const idParam = searchParams.get('id');
  useEffect(() => {
    if (idParam) {
      setSelectedClientId(idParam);
      // clean query params to avoid re-opening
      searchParams.delete('id');
      setSearchParams(searchParams, { replace: true });
    }
  }, [idParam, searchParams, setSearchParams]);

  // Open creation modal if navigated with openCreate state
  useEffect(() => {
    if ((location.state as { openCreate?: boolean } | null)?.openCreate) {
      setOpen(true);
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

  async function handleDeactivate(id: string, name: string) {
    if (
      !confirm(
        `Desativar cliente "${name}"? Ele saira da carteira operacional e ficara disponivel na aba Desativados.`
      )
    ) {
      return;
    }

    try {
      await deleteMutation.mutateAsync(id);
      toast.success('Cliente desativado');
    } catch {
      toast.error('Erro ao desativar cliente');
    }
  }

  const total = clients?.length ?? 0;
  const activeCount = clients?.filter((c) => c.status === 'active').length ?? 0;
  const onboardingCount = clients?.filter((c) => c.status === 'onboarding').length ?? 0;
  const inactiveCount = clients?.filter((c) => c.status === 'inactive').length ?? 0;
  const operationalCount = activeCount + onboardingCount;

  const hasActiveFilters =
    debouncedSearchQuery.trim() !== '' || statusFilter !== '' || tipoFilter !== '' || regimeFilter !== '';

  const visibleClients = useMemo(() => {
    if (!clients) return [];
    return clients.filter((client) =>
      clientView === 'operational' ? client.status !== 'inactive' : client.status === 'inactive'
    );
  }, [clients, clientView]);

  const filteredClients = useMemo(() => {
    const q = debouncedSearchQuery.trim().toLowerCase();

    return visibleClients.filter((client) => {
      if (q) {
        const matchesName = client.name.toLowerCase().includes(q);
        const matchesDoc = (client.document ?? '').toLowerCase().includes(q);
        const matchesEmail = (client.email ?? '').toLowerCase().includes(q);
        if (!matchesName && !matchesDoc && !matchesEmail) return false;
      }
      if (statusFilter && client.status !== statusFilter) return false;
      if (tipoFilter && client.entity_type !== tipoFilter) return false;
      if (regimeFilter && client.tax_regime !== regimeFilter) return false;
      return true;
    });
  }, [visibleClients, debouncedSearchQuery, statusFilter, tipoFilter, regimeFilter]);

  function clearFilters() {
    setSearchQuery('');
    setDebouncedSearchQuery('');
    setStatusFilter('');
    setTipoFilter('');
    setRegimeFilter('');
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 id="tour-clients-title" className="text-2xl font-bold md:text-3xl">Clientes</h1>
          <p className="text-muted-foreground text-sm">
            Acompanhe a carteira e situacao operacional de cada cliente.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => startTour('clients', navigate, '/clientes')}
            className="h-9 border-primary/25 bg-primary/10 text-primary hover:bg-primary/20 gap-1.5"
            title="Aprender sobre esta tela"
          >
            <BookOpen className="h-4 w-4" />
            <span>Guia</span>
          </Button>
          <a href="/template-cadastro-cliente.xlsx" download>
            <Button variant="outline" size="sm" className="h-9">
              <Download className="mr-1.5 h-4 w-4" aria-hidden="true" />
              Modelo XLSX
            </Button>
          </a>
          <Button onClick={() => setOpen(true)} size="sm" className="h-9">
            <Plus className="mr-1.5 h-4 w-4" aria-hidden="true" />
            Novo cliente
          </Button>
        </div>
      </div>

      {isError && (
        <ErrorState message="Nao foi possivel carregar os clientes. Verifique sua conexao." />
      )}

      {/* Summary cards */}
      <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Total de clientes
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoading ? '...' : total}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Carteira operacional
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoading ? '...' : operationalCount}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Em onboarding
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoading ? '...' : onboardingCount}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Desativados
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoading ? '...' : inactiveCount}</div>
          </CardContent>
        </Card>
      </div>

      {!isLoading && !isError && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border/80 bg-card/45 p-2 backdrop-blur-sm">
          <div
            className="flex gap-1"
            role="tablist"
            aria-label="Separar clientes por status operacional"
          >
            <button
              type="button"
              role="tab"
              aria-selected={clientView === 'operational'}
              onClick={() => setClientView('operational')}
              className={`inline-flex items-center gap-2 rounded-md px-3.5 py-1.5 text-xs font-bold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                clientView === 'operational'
                  ? 'bg-primary text-primary-foreground shadow-glow-sm'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground'
              }`}
            >
              <UserCheck className="h-4 w-4" aria-hidden="true" />
              Ativos
              <span className="rounded bg-background/20 px-1.5 py-0.5 text-[10px]">
                {operationalCount}
              </span>
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={clientView === 'inactive'}
              onClick={() => {
                setClientView('inactive');
                setStatusFilter('');
              }}
              className={`inline-flex items-center gap-2 rounded-md px-3.5 py-1.5 text-xs font-bold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                clientView === 'inactive'
                  ? 'bg-primary text-primary-foreground shadow-glow-sm'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground'
              }`}
            >
              <UserX className="h-4 w-4" aria-hidden="true" />
              Desativados
              <span className="rounded bg-background/20 px-1.5 py-0.5 text-[10px]">
                {inactiveCount}
              </span>
            </button>
          </div>
          <p className="px-2 text-xs text-muted-foreground">
            {clientView === 'operational'
              ? 'Clientes ativos e em onboarding aparecem na rotina diaria.'
              : 'Clientes desativados ficam fora dos fluxos operacionais.'}
          </p>
        </div>
      )}

      {/* Filters bar */}
      {!isLoading && !isError && (
        <div id="tour-clients-search" className="flex flex-col gap-3 sm:flex-row sm:items-center">
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
              placeholder="Buscar por nome, CNPJ/CPF ou e-mail..."
              className="w-full rounded-lg border border-border/80 bg-background pl-9 pr-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
              aria-label="Buscar clientes"
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

          {/* Selects + View Mode Toggles */}
          <div className="flex flex-wrap gap-2 items-center justify-between sm:justify-start">
            <div className="flex flex-wrap gap-2 items-center">
              {clientView === 'operational' && (
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
                  className="rounded-lg border border-border/80 bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                  aria-label="Filtrar carteira ativa por status"
                >
                  <option value="">Ativos + onboarding</option>
                  <option value="active">Somente ativos</option>
                  <option value="onboarding">Somente onboarding</option>
                </select>
              )}

              <select
                value={tipoFilter}
                onChange={(e) => setTipoFilter(e.target.value as TipoFilter)}
                className="rounded-lg border border-border/80 bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                aria-label="Filtrar por tipo"
              >
                <option value="">Todos os tipos</option>
                <option value="pj">Pessoa Jurídica</option>
                <option value="pf">Pessoa Física</option>
              </select>

              <select
                value={regimeFilter}
                onChange={(e) => setRegimeFilter(e.target.value as RegimeFilter)}
                className="rounded-lg border border-border/80 bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                aria-label="Filtrar por regime tributário"
              >
                <option value="">Todos os regimes</option>
                <option value="Simples Nacional">Simples Nacional</option>
                <option value="Lucro Presumido">Lucro Presumido</option>
                <option value="Lucro Real">Lucro Real</option>
                <option value="MEI">MEI</option>
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

            {/* List vs Card Toggle */}
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

      {/* Main clients content (Table vs Grid) */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-2 pb-3">
          <CardTitle className="text-base font-bold">
            {clientView === 'operational' ? 'Carteira ativa' : 'Clientes desativados'}
          </CardTitle>
          {!isLoading && !isError && clients && (
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground font-semibold">
              <Filter className="h-3.5 w-3.5" aria-hidden="true" />
              {hasActiveFilters
                ? `${filteredClients.length} de ${visibleClients.length} filtrados`
                : `${visibleClients.length} cadastrados`}
            </span>
          )}
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <PageSpinner />
          ) : total === 0 ? (
            <EmptyState
              title="Nenhum cliente cadastrado"
              description="Cadastre seu primeiro cliente clicando em Novo cliente."
            />
          ) : visibleClients.length === 0 && !hasActiveFilters ? (
            <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
              {clientView === 'operational' ? (
                <UserCheck className="h-8 w-8 text-muted-foreground/50" aria-hidden="true" />
              ) : (
                <UserX className="h-8 w-8 text-muted-foreground/50" aria-hidden="true" />
              )}
              <div>
                <p className="font-bold text-foreground">
                  {clientView === 'operational' ? 'Nenhum cliente ativo' : 'Nenhum cliente desativado'}
                </p>
                <p className="mt-1 text-sm text-muted-foreground">
                  {clientView === 'operational'
                    ? 'Clientes inativos ficam fora desta carteira. Cadastre ou reative um cliente para ver aqui.'
                    : 'Quando um cliente for desativado, ele aparecerá nesta aba.'}
                </p>
              </div>
            </div>
          ) : filteredClients.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
              <Search className="h-8 w-8 text-muted-foreground/50" aria-hidden="true" />
              <div>
                <p className="font-bold text-foreground">Nenhum cliente encontrado</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Nenhum cliente corresponde aos filtros aplicados.{' '}
                  <button
                    type="button"
                    onClick={clearFilters}
                    className="underline text-primary hover:text-primary/80 transition-colors"
                  >
                    Limpar filtros
                  </button>{' '}
                  para ver todos.
                </p>
              </div>
            </div>
          ) : viewMode === 'list' ? (
            <Table id="tour-clients-table">
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[100px]">Código</TableHead>
                  <TableHead>Cliente</TableHead>
                  <TableHead className="w-[80px]">Tipo</TableHead>
                  <TableHead>Regime</TableHead>
                  <TableHead>Contato</TableHead>
                  <TableHead>Checklist</TableHead>
                  <TableHead>Última Ação</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Ações</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredClients.map((client) => (
                  <ClientTableRow
                    key={client.id}
                    client={client}
                    deadlines={deadlines}
                    onManage={() => setSelectedClientId(client.id)}
                    onNotes={() => setSecureNotes({ id: client.id, name: client.name })}
                    onDeactivate={() => handleDeactivate(client.id, client.name)}
                  />
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {filteredClients.map((client) => (
                <ClientGridCard
                  key={client.id}
                  client={client}
                  deadlines={deadlines}
                  onManage={() => setSelectedClientId(client.id)}
                  onNotes={() => setSecureNotes({ id: client.id, name: client.name })}
                  onDeactivate={() => handleDeactivate(client.id, client.name)}
                />
              ))}
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

      {/* Client details drawer */}
      <ClientDetailsDrawer
        isOpen={!!selectedClientId}
        onClose={() => setSelectedClientId(null)}
        clientId={selectedClientId}
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
