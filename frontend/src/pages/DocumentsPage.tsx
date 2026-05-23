'use client';
import { useCallback, useRef, useState } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
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
} from 'lucide-react';
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
  useUploadDocument,
  type DocumentCreate,
  type DocumentStatus,
} from '@/lib/hooks/useOperations';

/* ─── Tipos de documento por categoria ─────────────────────────── */

interface DocType {
  value: string;
  label: string;
  /** Quantidade de anos para auto-calcular vencimento a partir da emissão */
  autoExpireYears?: number;
  /** Sugestão de nome automático */
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

/** Dado o valor retorna o DocType correspondente */
function findDocType(value: string): DocType | undefined {
  for (const cat of DOC_CATEGORIES) {
    const found = cat.types.find((t) => t.value === value);
    if (found) return found;
  }
  return undefined;
}

/** Adiciona N anos a uma data ISO (YYYY-MM-DD) */
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
      <div className="flex items-center gap-3 rounded-lg border border-dashed border-primary/40 bg-primary/5 px-4 py-3">
        <FileText className="h-5 w-5 shrink-0 text-primary" />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{file.name}</p>
          <p className="text-xs text-muted-foreground">
            {(file.size / 1024).toFixed(0)} KB
            {uploading && ' · Enviando...'}
          </p>
        </div>
        <button
          type="button"
          onClick={() => onChange(null)}
          className="shrink-0 rounded p-1 text-muted-foreground hover:text-destructive"
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
      className={`flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed px-4 py-6 text-center transition-colors
        ${dragging ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50 hover:bg-accent/30'}`}
    >
      <Upload className="h-6 w-6 text-muted-foreground" />
      <div>
        <p className="text-sm font-medium">Arraste ou clique para selecionar</p>
        <p className="text-xs text-muted-foreground">PDF, XML, XLSX, ZIP, PNG, JPG — até 20 MB</p>
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
        className="flex w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <span className={selectedType ? 'text-foreground' : 'text-muted-foreground'}>
          {selectedType
            ? `${selectedCat?.label} · ${selectedType.label}`
            : 'Selecione a categoria e tipo'}
        </span>
        <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 w-full rounded-md border bg-popover shadow-lg">
          <div className="max-h-72 overflow-y-auto py-1">
            {DOC_CATEGORIES.map((cat) => {
              const isExpanded = expandedCat === cat.label;
              return (
                <div key={cat.label}>
                  <button
                    type="button"
                    onClick={() => setExpandedCat(isExpanded ? null : cat.label)}
                    className="flex w-full items-center gap-2 px-3 py-2 text-sm font-medium hover:bg-accent"
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
                        className={`flex w-full items-center gap-2 pl-8 pr-3 py-1.5 text-sm hover:bg-accent
                          ${t.value === value ? 'bg-accent font-medium' : ''}`}
                      >
                        {t.label}
                        {t.autoExpireYears && (
                          <span className="ml-auto text-xs text-muted-foreground">
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

/* ─── Página principal ──────────────────────────────────────────── */

export function DocumentsPage() {
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);

  const { data: documents, isLoading, isError } = useDocuments();
  const { data: clients } = useClients();
  const createMutation = useCreateDocument();
  const deleteMutation = useDeleteDocument();
  const uploadMutation = useUploadDocument();

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

  /** Auto-fill: quando tipo muda, preenche vencimento se possível */
  const handleTypeChange = useCallback(
    (newType: string, currentIssuedAt?: string) => {
      const dt = findDocType(newType);
      if (!dt) return;

      // Auto-fill nome se campo vazio
      // (sem acesso ao watch aqui — feito via setValue)
      const issued = currentIssuedAt || watchedIssued;

      if (dt.autoExpireYears && issued) {
        setValue('expires_at', addYears(issued, dt.autoExpireYears));
      }
    },
    [setValue, watchedIssued],
  );

  /** Auto-recalcula vencimento quando a data de emissão muda */
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

    // 1. Upload do arquivo (se houver)
    if (file) {
      try {
        const result = await uploadMutation.mutateAsync(file);
        fileUrl = result.url;
      } catch {
        toast.error('Erro ao enviar arquivo. Tente novamente.');
        return;
      }
    }

    // 2. Criar registro do documento
    const payload: DocumentCreate = {
      ...values,
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

      {/* Contadores */}
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

      {/* Tabela */}
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
                    <th className="pb-3 font-medium">Categoria</th>
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
                        <div className="flex items-center gap-2">
                          <DocTypeIcon docType={doc.document_type} />
                          <div>
                            <div className="font-medium">{doc.name}</div>
                            {doc.notes && (
                              <div className="text-xs text-muted-foreground">{doc.notes}</div>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="py-4 text-muted-foreground">{doc.document_type}</td>
                      <td className="py-4">{dateBR(doc.issued_at)}</td>
                      <td className="py-4">
                        <span
                          className={doc.status === 'expired' ? 'font-medium text-destructive' : ''}
                        >
                          {dateBR(doc.expires_at)}
                        </span>
                      </td>
                      <td className="py-4">
                        <Badge variant={statusVariant[doc.status]}>
                          {statusLabel[doc.status]}
                        </Badge>
                      </td>
                      <td className="py-4">
                        <div className="flex items-center gap-2">
                          {doc.file_url && (
                            <a
                              href={doc.file_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex flex-col items-center gap-0.5 rounded p-1 text-muted-foreground hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                              aria-label={`Baixar ${doc.name}`}
                            >
                              <Download className="h-4 w-4" />
                              <span className="text-[9px] font-medium uppercase tracking-wider">Baixar</span>
                            </a>
                          )}
                          <button
                            type="button"
                            onClick={() => handleDelete(doc.id, doc.name)}
                            className="flex flex-col items-center gap-0.5 rounded p-1 text-muted-foreground hover:text-destructive focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            aria-label={`Excluir documento ${doc.name}`}
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
