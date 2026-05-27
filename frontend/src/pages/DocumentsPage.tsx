'use client';
import { useCallback, useRef, useState, useEffect, useMemo } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import {
  Plus,
  Trash2,
  Download,
  Upload,
  X,
  FileText,
  FileSpreadsheet,
  FileBadge,
  Users,
  Building2,
  CreditCard,
  FileSignature,
  FolderOpen,
  ChevronDown,
  Sparkles,
  Search,
  Filter,
  LayoutList,
  LayoutGrid,
  Eye,
  BookOpen,
} from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import { startTour } from '@/lib/tours';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Dialog } from '@/components/ui/Dialog';
import { FormField } from '@/components/ui/FormField';
import { EmptyState, ErrorState, PageSpinner } from '@/components/ui/StateViews';
import { DocumentPreviewDrawer } from '@/components/DocumentPreviewDrawer';
import { DocumentCard } from '@/components/ui/Card';
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
  useDocuments,
  useCreateDocument,
  useDeleteDocument,
  useUploadDocument,
  type DocumentCreate,
  type DocumentStatus,
  type ClientDocument,
} from '@/lib/hooks/useOperations';
import { buildDocumentAiView } from '@/lib/aiDocuments';

/* ─── Tipos de documento por categoria ─────────────────────────── */

interface DocType {
  value: string;
  label: string;
  autoExpireYears?: number;
  autoName?: string;
}

interface DocCategory {
  label: string;
  Icon: React.ElementType;
  color: string;
  types: DocType[];
}

const DOC_CATEGORIES: DocCategory[] = [
  {
    label: 'Fiscal',
    Icon: FileSpreadsheet,
    color: 'text-blue-600',
    types: [
      { value: 'SPED Fiscal', label: 'SPED Fiscal' },
      { value: 'SPED Contribuicoes', label: 'SPED Contribuições' },
      { value: 'ECF', label: 'ECF — Escrituração Contábil Fiscal' },
      { value: 'DCTF', label: 'DCTF' },
      { value: 'PGDAS', label: 'PGDAS (Simples Nacional)' },
      { value: 'EFD ICMS/IPI', label: 'EFD ICMS/IPI' },
      { value: 'NFe', label: 'NF-e' },
      { value: 'NFS-e', label: 'NFS-e' },
    ],
  },
  {
    label: 'Contábil',
    Icon: FileText,
    color: 'text-emerald-600',
    types: [
      { value: 'Balanco Patrimonial', label: 'Balanço Patrimonial' },
      { value: 'DRE', label: 'DRE — Demonstração de Resultado' },
      { value: 'Balancete', label: 'Balancete' },
      { value: 'DLPA', label: 'DLPA' },
      { value: 'Fluxo de Caixa', label: 'Fluxo de Caixa' },
    ],
  },
  {
    label: 'Certificado Digital',
    Icon: FileBadge,
    color: 'text-purple-600',
    types: [
      { value: 'e-CNPJ A1', label: 'e-CNPJ A1', autoExpireYears: 1 },
      { value: 'e-CNPJ A3', label: 'e-CNPJ A3', autoExpireYears: 3 },
      { value: 'e-CPF A1', label: 'e-CPF A1', autoExpireYears: 1 },
      { value: 'e-CPF A3', label: 'e-CPF A3', autoExpireYears: 3 },
      { value: 'NF-e A1', label: 'NF-e A1', autoExpireYears: 1 },
    ],
  },
  {
    label: 'Trabalhista',
    Icon: Users,
    color: 'text-orange-600',
    types: [
      { value: 'Folha de Pagamento', label: 'Folha de Pagamento' },
      { value: 'eSocial', label: 'eSocial' },
      { value: 'FGTS', label: 'FGTS — GFIP/SEFIP' },
      { value: 'CAGED', label: 'CAGED' },
      { value: 'RAIS', label: 'RAIS' },
      { value: 'PPP', label: 'PPP' },
    ],
  },
  {
    label: 'Societário',
    Icon: Building2,
    color: 'text-slate-600',
    types: [
      { value: 'Contrato Social', label: 'Contrato Social' },
      { value: 'Cartao CNPJ', label: 'Cartão CNPJ' },
      { value: 'Alvara de Funcionamento', label: 'Alvará de Funcionamento', autoExpireYears: 1 },
      { value: 'Ata de Reuniao', label: 'Ata de Reunião' },
      { value: 'Procuracao', label: 'Procuração' },
    ],
  },
  {
    label: 'Pessoal',
    Icon: CreditCard,
    color: 'text-rose-600',
    types: [
      { value: 'CPF', label: 'CPF' },
      { value: 'RG', label: 'RG / CNH' },
      { value: 'Comprovante de Residencia', label: 'Comprovante de Residência' },
      { value: 'Titulo de Eleitor', label: 'Título de Eleitor' },
    ],
  },
  {
    label: 'Contratos',
    Icon: FileSignature,
    color: 'text-amber-600',
    types: [
      { value: 'Contrato de Servicos', label: 'Contrato de Prestação de Serviços' },
      { value: 'Termo Aditivo', label: 'Termo Aditivo' },
      { value: 'Distrato', label: 'Distrato' },
    ],
  },
  {
    label: 'Outros',
    Icon: FolderOpen,
    color: 'text-gray-500',
    types: [{ value: 'Outros', label: 'Outros' }],
  },
];

function findDocType(value: string): DocType | undefined {
  for (const cat of DOC_CATEGORIES) {
    const found = cat.types.find((t) => t.value === value);
    if (found) return found;
  }
  return undefined;
}

function addYears(isoDate: string, years: number): string {
  const d = new Date(`${isoDate}T00:00:00`);
  d.setFullYear(d.getFullYear() + years);
  return d.toISOString().split('T')[0];
}

/* ─── Schema do formulário ──────────────────────────────────────── */

const schema = z.object({
  client_id: z.string().min(1, 'Selecione um cliente'),
  name: z.string().min(2, 'Nome deve ter ao menos 2 caracteres'),
  document_type: z.string().min(1, 'Tipo é obrigatorio'),
  status: z.enum(['available', 'missing', 'expired', 'review']),
  issued_at: z.string().optional(),
  expires_at: z.string().optional(),
  notes: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

/* ─── Constantes de badge ────────────────────────────────────────── */

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

/* ─── Componente de upload de arquivo ──────────────────────────── */

interface FileDropZoneProps {
  file: File | null;
  onChange: (f: File | null) => void;
  uploading?: boolean;
}

function FileDropZone({ file, onChange, uploading }: FileDropZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const f = e.dataTransfer.files[0];
      if (f) onChange(f);
    },
    [onChange],
  );

  if (file) {
    return (
      <div className="flex items-center gap-3 rounded-xl border border-dashed border-primary/40 bg-primary/5 px-4 py-3">
        <FileText className="h-5 w-5 shrink-0 text-primary animate-pulse" />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-foreground">{file.name}</p>
          <p className="text-xs text-muted-foreground">
            {(file.size / 1024).toFixed(0)} KB
            {uploading && ' · Enviando...'}
          </p>
        </div>
        <button
          type="button"
          onClick={() => onChange(null)}
          className="shrink-0 rounded p-1 text-muted-foreground hover:text-destructive transition-colors"
          disabled={uploading}
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    );
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      className={`flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed px-4 py-6 text-center transition-all duration-200
        ${dragging ? 'border-primary bg-primary/5 shadow-glow-sm scale-[0.99]' : 'border-border hover:border-primary/50 hover:bg-muted/40'}`}
    >
      <Upload className="h-6 w-6 text-muted-foreground hover:text-primary transition-colors" />
      <div>
        <p className="text-sm font-semibold">Arraste ou clique para selecionar</p>
        <p className="text-xs text-muted-foreground mt-0.5">PDF, XML, XLSX, ZIP, PNG, JPG — até 20 MB</p>
      </div>
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        accept=".pdf,.xml,.xlsx,.xls,.zip,.png,.jpg,.jpeg,.pfx,.p12"
        onChange={(e) => e.target.files?.[0] && onChange(e.target.files[0])}
      />
    </div>
  );
}

/* ─── Seletor de tipo de documento ─────────────────────────────── */

interface DocTypeSelectorProps {
  value: string;
  onChange: (v: string) => void;
}

function DocTypeSelector({ value, onChange }: DocTypeSelectorProps) {
  const [open, setOpen] = useState(false);
  const [expandedCat, setExpandedCat] = useState<string | null>(null);

  const selectedType = value ? findDocType(value) : null;
  const selectedCat = value
    ? DOC_CATEGORIES.find((c) => c.types.some((t) => t.value === value))
    : null;

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between rounded-lg border border-border/80 bg-background px-3 py-2 text-sm transition-all hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
      >
        <span className={selectedType ? 'text-foreground font-semibold' : 'text-muted-foreground'}>
          {selectedType
            ? `${selectedCat?.label} · ${selectedType.label}`
            : 'Selecione a categoria e tipo'}
        </span>
        <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 w-full rounded-lg border border-border/80 bg-card shadow-lg max-h-72 overflow-y-auto scrollbar">
          <div className="py-1">
            {DOC_CATEGORIES.map((cat) => {
              const isExpanded = expandedCat === cat.label;
              return (
                <div key={cat.label}>
                  <button
                    type="button"
                    onClick={() => setExpandedCat(isExpanded ? null : cat.label)}
                    className="flex w-full items-center gap-2 px-3 py-2 text-sm font-semibold hover:bg-muted"
                  >
                    <cat.Icon className={`h-4 w-4 ${cat.color}`} />
                    <span className="flex-1 text-left">{cat.label}</span>
                    <ChevronDown
                      className={`h-3 w-3 text-muted-foreground transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                    />
                  </button>
                  {isExpanded &&
                    cat.types.map((t) => (
                      <button
                        key={t.value}
                        type="button"
                        onClick={() => {
                          onChange(t.value);
                          setOpen(false);
                          setExpandedCat(null);
                        }}
                        className={`flex w-full items-center gap-2 pl-8 pr-3 py-1.5 text-xs hover:bg-muted
                          ${t.value === value ? 'bg-primary/10 text-primary font-bold' : 'text-foreground/80'}`}
                      >
                        {t.label}
                        {t.autoExpireYears && (
                          <span className="ml-auto text-[10px] text-muted-foreground">
                            {t.autoExpireYears}a
                          </span>
                        )}
                      </button>
                    ))}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

/* ─── Ícone de categoria por tipo ──────────────────────────────── */

function DocTypeIcon({ docType }: { docType: string }) {
  const cat = DOC_CATEGORIES.find((c) => c.types.some((t) => t.value === docType));
  if (!cat) return <FileText className="h-4 w-4 text-muted-foreground" />;
  return <cat.Icon className={`h-4 w-4 ${cat.color}`} />;
}

interface DocumentAiCellProps {
  document: ClientDocument;
}

function DocumentAiCell({ document }: DocumentAiCellProps) {
  const aiView = buildDocumentAiView(document);

  return (
    <div className="max-w-[280px] space-y-1.5">
      <Badge variant={aiView.parseStatusVariant}>{aiView.parseStatusLabel}</Badge>
      {aiView.classification ? (
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-1.5 text-xs font-semibold">
            <Sparkles className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
            <span>{aiView.classification.documentType}</span>
            {aiView.classification.confidenceLabel && (
              <span className="text-muted-foreground text-[10px]">
                ({aiView.classification.confidenceLabel})
              </span>
            )}
          </div>
          {aiView.classification.fields.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {aiView.classification.fields.map((field) => (
                <span
                  key={field.label}
                  className="rounded bg-muted border px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground"
                >
                  {field.label}: {field.value}
                </span>
              ))}
            </div>
          )}
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">
          {aiView.parseError ?? 'Aguardando processamento.'}
        </p>
      )}
    </div>
  );
}

/* ─── Página principal ──────────────────────────────────────────── */

export function DocumentsPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if ((location.state as { openCreate?: boolean } | null)?.openCreate) {
      setOpen(true);
      window.history.replaceState({}, '');
    }
  }, [location.state]);
  const [file, setFile] = useState<File | null>(null);

  // Filter and preview states
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');
  const [clientFilter, setClientFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedPreviewDoc, setSelectedPreviewDoc] = useState<ClientDocument | null>(null);
  const [viewMode, setViewMode] = useState<'list' | 'card'>('list');

  const { data: documents, isLoading, isError } = useDocuments();
  const { data: clients } = useClients();
  const createMutation = useCreateDocument();
  const deleteMutation = useDeleteDocument();
  const uploadMutation = useUploadDocument();

  // Search Debouncing
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearchQuery(searchQuery);
    }, 300);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  const {
    register,
    handleSubmit,
    reset,
    control,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { status: 'missing' },
  });

  const watchedType = watch('document_type');
  const watchedIssued = watch('issued_at');

  const handleTypeChange = useCallback(
    (newType: string, currentIssuedAt?: string) => {
      const dt = findDocType(newType);
      if (!dt) return;

      const issued = currentIssuedAt || watchedIssued;

      if (dt.autoExpireYears && issued) {
        setValue('expires_at', addYears(issued, dt.autoExpireYears));
      }
    },
    [setValue, watchedIssued],
  );

  const handleIssuedChange = useCallback(
    (newIssued: string) => {
      const dt = findDocType(watchedType);
      if (dt?.autoExpireYears && newIssued) {
        setValue('expires_at', addYears(newIssued, dt.autoExpireYears));
      }
    },
    [setValue, watchedType],
  );

  async function onSubmit(values: FormValues) {
    let fileUrl: string | undefined;

    if (file) {
      try {
        const result = await uploadMutation.mutateAsync(file);
        fileUrl = result.url;
      } catch {
        toast.error('Erro ao enviar arquivo. Tente novamente.');
        return;
      }
    }

    const payload: DocumentCreate = {
      ...values,
      issued_at: values.issued_at === '' ? undefined : values.issued_at,
      expires_at: values.expires_at === '' ? undefined : values.expires_at,
      file_url: fileUrl,
    };

    try {
      await createMutation.mutateAsync(payload);
      toast.success('Documento registrado');
      reset();
      setFile(null);
      setOpen(false);
    } catch {
      toast.error('Erro ao registrar documento. Tente novamente.');
    }
  }

  function handleClose() {
    reset();
    setFile(null);
    setOpen(false);
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

  const isUploading = uploadMutation.isPending;
  const isBusy = isSubmitting || isUploading;

  // Filter Logic
  const filteredDocuments = useMemo(() => {
    if (!documents) return [];
    const q = debouncedSearchQuery.trim().toLowerCase();

    return documents.filter((doc) => {
      if (q) {
        const matchesName = doc.name.toLowerCase().includes(q);
        const matchesNotes = (doc.notes ?? '').toLowerCase().includes(q);
        const client = clients?.find((c) => c.id === doc.client_id);
        const matchesClient = client ? client.name.toLowerCase().includes(q) : false;
        if (!matchesName && !matchesNotes && !matchesClient) return false;
      }
      if (clientFilter && doc.client_id !== clientFilter) return false;
      if (categoryFilter) {
        const cat = DOC_CATEGORIES.find((c) => c.label === categoryFilter);
        if (cat) {
          const typeMatches = cat.types.some((t) => t.value === doc.document_type);
          if (!typeMatches) return false;
        } else if (doc.document_type !== categoryFilter) {
          return false;
        }
      }
      if (statusFilter && doc.status !== statusFilter) return false;
      return true;
    });
  }, [documents, debouncedSearchQuery, clientFilter, categoryFilter, statusFilter, clients]);

  const hasActiveFilters =
    debouncedSearchQuery.trim() !== '' || clientFilter !== '' || categoryFilter !== '' || statusFilter !== '';

  function clearFilters() {
    setSearchQuery('');
    setDebouncedSearchQuery('');
    setClientFilter('');
    setCategoryFilter('');
    setStatusFilter('');
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold md:text-3xl">Documentos</h1>
          <p className="text-muted-foreground text-sm">
            Controle solicitacoes, recebimentos e situacao documental por cliente.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => startTour('documents', navigate, '/documentos')}
            className="h-9 border-teal-500/25 bg-teal-500/10 text-teal-300 hover:bg-teal-500/20 gap-1.5"
            title="Aprender sobre esta tela"
          >
            <BookOpen className="h-4 w-4" />
            <span>Guia</span>
          </Button>
          <Button id="tour-docs-upload" onClick={() => setOpen(true)} size="sm" className="h-9">
            <Plus className="mr-1.5 h-4 w-4" aria-hidden="true" />
            Novo documento
          </Button>
        </div>
      </div>

      {isError && <ErrorState message="Nao foi possivel carregar os documentos." />}

      {/* Contadores */}
      <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Disponiveis
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoading ? '...' : availableCount}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Pendentes
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoading ? '...' : missingCount}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Em revisao
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoading ? '...' : reviewCount}</div>
          </CardContent>
        </Card>
      </div>

      {/* Filters Bar */}
      {!isLoading && !isError && (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
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
              placeholder="Buscar por nome, notas ou cliente..."
              className="w-full rounded-lg border border-border/80 bg-background pl-9 pr-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
              aria-label="Buscar documentos"
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

          {/* Selects + View Modes */}
          <div className="flex flex-wrap gap-2 items-center justify-between sm:justify-start">
            <div className="flex flex-wrap gap-2 items-center">
              <select
                value={clientFilter}
                onChange={(e) => setClientFilter(e.target.value)}
                className="rounded-lg border border-border/80 bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all max-w-[160px] truncate"
                aria-label="Filtrar por cliente"
              >
                <option value="">Todos os clientes</option>
                {(clients ?? []).map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>

              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="rounded-lg border border-border/80 bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                aria-label="Filtrar por categoria"
              >
                <option value="">Todas as categorias</option>
                {DOC_CATEGORIES.map((cat) => (
                  <option key={cat.label} value={cat.label}>
                    {cat.label}
                  </option>
                ))}
              </select>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="rounded-lg border border-border/80 bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                aria-label="Filtrar por status"
              >
                <option value="">Todos os status</option>
                <option value="available">Disponíveis</option>
                <option value="missing">Pendentes</option>
                <option value="review">Em revisão</option>
                <option value="expired">Vencidos</option>
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

      {/* Main Content Area */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-2 pb-3">
          <CardTitle className="text-base font-bold">Esteira documental</CardTitle>
          {!isLoading && !isError && documents && (
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground font-semibold">
              <Filter className="h-3.5 w-3.5" aria-hidden="true" />
              {hasActiveFilters
                ? `${filteredDocuments.length} de ${documents.length} filtrados`
                : `${documents.length} no total`}
            </span>
          )}
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <PageSpinner />
          ) : filteredDocuments.length === 0 ? (
            <EmptyState
              title="Nenhum documento encontrado"
              description={hasActiveFilters ? "Tente ajustar seus filtros para encontrar o que procura." : "Registre documentos dos clientes para controlar a esteira."}
              action={
                !hasActiveFilters ? (
                  <Button size="sm" onClick={() => setOpen(true)} className="h-9">
                    Novo documento
                  </Button>
                ) : (
                  <Button size="sm" variant="outline" onClick={clearFilters} className="h-9">
                    Limpar filtros
                  </Button>
                )
              }
            />
          ) : viewMode === 'list' ? (
            <Table id="tour-docs-table">
              <TableHeader>
                <TableRow>
                  <TableHead>Documento</TableHead>
                  <TableHead>Cliente</TableHead>
                  <TableHead>Categoria</TableHead>
                  <TableHead>Emissao</TableHead>
                  <TableHead>Vencimento</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>IA</TableHead>
                  <TableHead className="text-right">Ações</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredDocuments.map((doc) => {
                  const client = clients?.find((c) => c.id === doc.client_id);
                  return (
                    <TableRow key={doc.id}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <DocTypeIcon docType={doc.document_type} />
                          <div>
                            <div className="font-bold text-foreground">{doc.name}</div>
                            {doc.notes && (
                              <div className="text-xs text-muted-foreground max-w-[200px] truncate" title={doc.notes}>
                                {doc.notes}
                              </div>
                            )}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="font-medium text-foreground/80 max-w-[150px] truncate" title={client?.name}>
                        {client?.name ?? 'Cliente desconhecido'}
                      </TableCell>
                      <TableCell className="text-muted-foreground text-xs">{doc.document_type}</TableCell>
                      <TableCell className="text-xs">{dateBR(doc.issued_at)}</TableCell>
                      <TableCell className="text-xs">
                        <span className={doc.status === 'expired' ? 'font-bold text-destructive animate-pulse' : ''}>
                          {dateBR(doc.expires_at)}
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge variant={statusVariant[doc.status]}>
                          {statusLabel[doc.status]}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <DocumentAiCell document={doc} />
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          {doc.file_url && (
                            <>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setSelectedPreviewDoc(doc)}
                                className="h-8 gap-1 text-primary hover:text-primary hover:bg-primary/10"
                                title="Visualizar documento"
                              >
                                <Eye className="h-4 w-4" />
                              </Button>
                              <a href={doc.file_url} download className="block">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground"
                                  title="Baixar"
                                >
                                  <Download className="h-4 w-4" />
                                </Button>
                              </a>
                            </>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDelete(doc.id, doc.name)}
                            className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                            title="Excluir documento"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {filteredDocuments.map((doc) => {
                const client = clients?.find((c) => c.id === doc.client_id);
                return (
                  <DocumentCard
                    key={doc.id}
                    name={doc.name}
                    type={`${client?.name ?? 'Cliente'} · ${doc.document_type}`}
                    date={`Vencimento: ${dateBR(doc.expires_at)}`}
                    status={doc.status}
                    onClick={() => setSelectedPreviewDoc(doc)}
                  />
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Inline Document Preview Drawer */}
      <DocumentPreviewDrawer
        document={selectedPreviewDoc}
        isOpen={!!selectedPreviewDoc}
        onClose={() => setSelectedPreviewDoc(null)}
      />

      {/* Modal novo documento */}
      <Dialog open={open} onClose={handleClose} title="Novo documento">
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          {/* Cliente */}
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

          {/* Tipo (seletor com categorias) */}
          <FormField
            label="Categoria / Tipo"
            htmlFor="document_type"
            error={errors.document_type?.message}
            required
          >
            <Controller
              name="document_type"
              control={control}
              render={({ field }) => (
                <DocTypeSelector
                  value={field.value ?? ''}
                  onChange={(v) => {
                    field.onChange(v);
                    handleTypeChange(v);
                  }}
                />
              )}
            />
          </FormField>

          {/* Nome */}
          <FormField label="Nome do documento" htmlFor="name" error={errors.name?.message} required>
            <Input
              id="name"
              placeholder={watchedType ? `Ex: ${watchedType} Jan/2026` : 'Ex: SPED Fiscal Jan/2026'}
              {...register('name')}
            />
          </FormField>

          {/* Status */}
          <FormField label="Status" htmlFor="status" required>
            <Select id="status" {...register('status')}>
              <option value="missing">Pendente</option>
              <option value="available">Disponivel</option>
              <option value="review">Em revisao</option>
              <option value="expired">Vencido</option>
            </Select>
          </FormField>

          {/* Datas */}
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Data de emissao" htmlFor="issued_at" error={errors.issued_at?.message}>
              <Input
                id="issued_at"
                type="date"
                {...register('issued_at', {
                  onChange: (e) => handleIssuedChange(e.target.value),
                })}
              />
            </FormField>
            <FormField
              label="Data de vencimento"
              htmlFor="expires_at"
              error={errors.expires_at?.message}
            >
              <Input id="expires_at" type="date" {...register('expires_at')} />
            </FormField>
          </div>

          {/* Upload de arquivo */}
          <FormField label="Arquivo" htmlFor="file_upload">
            <FileDropZone file={file} onChange={setFile} uploading={isUploading} />
            {findDocType(watchedType)?.autoExpireYears && (
              <p className="mt-1 text-xs text-muted-foreground">
                Certificado {watchedType} — vencimento calculado automaticamente a partir da emissao.
              </p>
            )}
          </FormField>

          {/* Observacoes */}
          <FormField label="Observacoes" htmlFor="notes" error={errors.notes?.message}>
            <Input id="notes" placeholder="Anotacoes (opcional)" {...register('notes')} />
          </FormField>

          <div className="flex justify-end gap-3 pt-2">
            <Button type="button" variant="outline" onClick={handleClose} disabled={isBusy}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isBusy}>
              {isUploading ? 'Enviando arquivo...' : isSubmitting ? 'Salvando...' : 'Salvar documento'}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
