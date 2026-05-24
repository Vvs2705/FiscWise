import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import {
  X,
  User,
  Users,
  FileText,
  Plus,
  Trash2,
  Edit2,
  Calendar,
  AlertTriangle,
  Upload,
  Briefcase,
  Save,
  CheckCircle,
  FileDown,
  Sparkles,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Badge } from '@/components/ui/Badge';
import { FormField } from '@/components/ui/FormField';
import {
  useUpdateClient,
  usePartners,
  useCreatePartner,
  useUpdatePartner,
  useDeletePartner,
  useCompanyDocuments,
  useClientDocuments,
  useCreateCompanyDocument,
  useDeleteCompanyDocument,
  useGenerateClientAiSummary,
  useUploadDocument,
  type AccountingClient,
  type CompanyPartner,
} from '@/lib/hooks/useOperations';
import {
  buildClientAiSummaryView,
  buildDocumentAiView,
  type ClientAiSummary,
  type ClientDocument as ParsedClientDocument,
} from '@/lib/aiDocuments';

interface ClientManageDrawerProps {
  open: boolean;
  onClose: () => void;
  client: AccountingClient | null;
}

const DOCUMENT_TYPES = [
  { value: 'cnpj', label: 'CNPJ' },
  { value: 'contrato_social', label: 'Contrato Social' },
  { value: 'inscricao_municipal', label: 'Inscrição Municipal' },
  { value: 'inscricao_estadual', label: 'Inscrição Estadual' },
  { value: 'alvara_funcionamento', label: 'Alvará de Funcionamento' },
  { value: 'licenca_sanitaria', label: 'Licença Sanitária' },
  { value: 'cnes', label: 'CNES' },
  { value: 'alvara_bombeiros', label: 'Alvará do Corpo de Bombeiros' },
  { value: 'cro_juridico', label: 'CRO Jurídico' },
];

const docTypeLabel = (val: string) => {
  return DOCUMENT_TYPES.find((d) => d.value === val)?.label || val.toUpperCase();
};

// Form schema for Client info
const clientSchema = z.object({
  name: z.string().min(2, 'Nome deve ter ao menos 2 caracteres'),
  document: z.string().optional(),
  entity_type: z.enum(['pj', 'pf']),
  tax_regime: z.string().optional(),
  email: z.string().email('E-mail inválido').optional().or(z.literal('')),
  phone: z.string().optional(),
  municipal_registration: z.string().optional(),
  state_registration: z.string().optional(),
  status: z.enum(['active', 'inactive', 'onboarding']),
  notes: z.string().optional(),
  // Responsible fields
  responsible_name: z.string().optional(),
  responsible_cpf: z.string().optional(),
  responsible_address: z.string().optional(),
  responsible_phone: z.string().optional(),
  responsible_email: z.string().email('E-mail inválido').optional().or(z.literal('')),
});

type ClientFormValues = z.infer<typeof clientSchema>;

// Form schema for Partner
const partnerSchema = z.object({
  name: z.string().min(1, 'Nome do sócio é obrigatório'),
  cpf: z.string().min(11, 'CPF deve ter no mínimo 11 dígitos'),
  participation_percentage: z.number().min(0).max(100),
  entry_date: z.string().optional(),
  status: z.string().default('active'),
  notes: z.string().optional(),
});

type PartnerFormValues = z.infer<typeof partnerSchema>;

interface ClientAiSummaryPanelProps {
  summary: ClientAiSummary | null | undefined;
  isGenerating: boolean;
  onGenerate: () => void;
}

function ClientAiSummaryPanel({ summary, isGenerating, onGenerate }: ClientAiSummaryPanelProps) {
  const view = buildClientAiSummaryView(summary ?? null);

  return (
    <div className="rounded-xl border border-primary/20 bg-primary/5 p-4 space-y-3">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-primary" aria-hidden="true" />
          <h3 className="text-sm font-bold text-foreground uppercase tracking-wide">
            Resumo IA do Cliente
          </h3>
        </div>
        {view.documentsAnalyzedLabel && (
          <span className="text-xs font-medium text-muted-foreground">
            {view.documentsAnalyzedLabel}
          </span>
        )}
      </div>

      <p className="text-sm text-foreground">{view.summary}</p>

      <Button
        type="button"
        size="sm"
        variant={view.available ? 'outline' : 'default'}
        onClick={onGenerate}
        disabled={isGenerating}
        className="gap-1.5"
      >
        <Sparkles className="h-4 w-4" aria-hidden="true" />
        {isGenerating ? 'Gerando...' : view.available ? 'Atualizar resumo' : 'Gerar resumo'}
      </Button>

      {view.available && (view.risks.length > 0 || view.nextActions.length > 0) && (
        <div className="grid gap-3 md:grid-cols-2">
          {view.risks.length > 0 && (
            <div className="space-y-1">
              <p className="text-xs font-semibold uppercase text-muted-foreground">Riscos</p>
              <ul className="space-y-1 text-xs text-muted-foreground">
                {view.risks.map((risk) => (
                  <li key={risk}>- {risk}</li>
                ))}
              </ul>
            </div>
          )}
          {view.nextActions.length > 0 && (
            <div className="space-y-1">
              <p className="text-xs font-semibold uppercase text-muted-foreground">Proximas acoes</p>
              <ul className="space-y-1 text-xs text-muted-foreground">
                {view.nextActions.map((action) => (
                  <li key={action}>- {action}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

interface ParsedDocumentsPanelProps {
  documents: ParsedClientDocument[];
  isLoading: boolean;
}

function ParsedDocumentsPanel({ documents, isLoading }: ParsedDocumentsPanelProps) {
  if (isLoading) {
    return (
      <div className="rounded-xl border border-dashed bg-muted/5 p-4 text-sm text-muted-foreground">
        Carregando documentos analisados...
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="rounded-xl border border-dashed bg-muted/5 p-4 text-sm text-muted-foreground">
        Nenhum documento operacional com IA encontrado para este cliente.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {documents.map((document) => {
        const aiView = buildDocumentAiView(document);

        return (
          <div key={document.id} className="rounded-xl border bg-card p-4 space-y-2">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="font-semibold text-foreground">{document.name}</p>
                <p className="text-xs text-muted-foreground">{document.document_type}</p>
              </div>
              <Badge variant={aiView.parseStatusVariant}>{aiView.parseStatusLabel}</Badge>
            </div>

            {aiView.classification ? (
              <div className="space-y-2">
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <span className="inline-flex items-center gap-1 font-medium">
                    <Sparkles className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                    {aiView.classification.documentType}
                  </span>
                  {aiView.classification.confidenceLabel && (
                    <span className="text-muted-foreground">
                      Confianca {aiView.classification.confidenceLabel}
                    </span>
                  )}
                </div>
                {aiView.classification.fields.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {aiView.classification.fields.map((field) => (
                      <span
                        key={field.label}
                        className="rounded bg-muted px-1.5 py-0.5 text-[11px] text-muted-foreground"
                      >
                        {field.label}: {field.value}
                      </span>
                    ))}
                  </div>
                )}
                {aiView.classification.summary && (
                  <p className="text-xs text-muted-foreground">
                    {aiView.classification.summary}
                  </p>
                )}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">
                {aiView.parseError ?? 'Classificacao de IA ainda nao disponivel.'}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}

export function ClientManageDrawer({ open, onClose, client }: ClientManageDrawerProps) {
  const [activeTab, setActiveTab] = useState<'info' | 'partners' | 'documents'>('info');

  // Partners states
  const [partnerToEdit, setPartnerToEdit] = useState<CompanyPartner | null>(null);
  const [showPartnerForm, setShowPartnerForm] = useState(false);

  // Documents states
  const [selectedDocType, setSelectedDocType] = useState('cnpj');
  const [docExpiration, setDocExpiration] = useState('');
  const [docNotes, setDocNotes] = useState('');
  const [uploadingFile, setUploadingFile] = useState(false);
  const [clientAiSummary, setClientAiSummary] = useState<ClientAiSummary | null>(null);

  // Queries & Mutations
  const updateClientMutation = useUpdateClient();
  const { data: partners = [], refetch: refetchPartners } = usePartners(client?.id ?? '');
  const createPartnerMutation = useCreatePartner(client?.id ?? '');
  const updatePartnerMutation = useUpdatePartner(client?.id ?? '');
  const deletePartnerMutation = useDeletePartner(client?.id ?? '');

  const { data: companyDocs = [], refetch: refetchDocs } = useCompanyDocuments(client?.id ?? '');
  const { data: parsedClientDocs = [], isLoading: isLoadingParsedDocs } = useClientDocuments(client?.id);
  const createDocMutation = useCreateCompanyDocument(client?.id ?? '');
  const deleteDocMutation = useDeleteCompanyDocument(client?.id ?? '');
  const generateAiSummaryMutation = useGenerateClientAiSummary();
  const uploadFileMutation = useUploadDocument();

  // React Hook Forms
  const {
    register: registerClient,
    handleSubmit: handleSubmitClient,
    reset: resetClient,
    formState: { errors: clientErrors, isSubmitting: isSavingClient },
  } = useForm<ClientFormValues>({
    resolver: zodResolver(clientSchema),
  });

  const {
    register: registerPartner,
    handleSubmit: handleSubmitPartner,
    reset: resetPartner,
    setValue: setPartnerValue,
    formState: { errors: partnerErrors, isSubmitting: isSavingPartner },
  } = useForm<PartnerFormValues>({
    resolver: zodResolver(partnerSchema),
    defaultValues: { participation_percentage: 0, status: 'active' },
  });

  // Load client data into form
  useEffect(() => {
    if (client) {
      resetClient({
        name: client.name,
        document: client.document || '',
        entity_type: client.entity_type,
        tax_regime: client.tax_regime || '',
        email: client.email || '',
        phone: client.phone || '',
        municipal_registration: client.municipal_registration || '',
        state_registration: client.state_registration || '',
        status: client.status,
        notes: client.notes || '',
        responsible_name: client.responsible_name || '',
        responsible_cpf: client.responsible_cpf || '',
        responsible_address: client.responsible_address || '',
        responsible_phone: client.responsible_phone || '',
        responsible_email: client.responsible_email || '',
      });
      setClientAiSummary(null);
      refetchPartners();
      refetchDocs();
    }
  }, [client, resetClient, refetchPartners, refetchDocs]);

  // Load partner data for editing
  useEffect(() => {
    if (partnerToEdit) {
      setPartnerValue('name', partnerToEdit.name);
      setPartnerValue('cpf', partnerToEdit.cpf);
      setPartnerValue('participation_percentage', Number(partnerToEdit.participation_percentage));
      setPartnerValue('entry_date', partnerToEdit.entry_date || '');
      setPartnerValue('status', partnerToEdit.status);
      setPartnerValue('notes', partnerToEdit.notes || '');
      setShowPartnerForm(true);
    } else {
      resetPartner({
        name: '',
        cpf: '',
        participation_percentage: 0,
        entry_date: '',
        status: 'active',
        notes: '',
      });
    }
  }, [partnerToEdit, setPartnerValue, resetPartner]);

  if (!open || !client) return null;

  // Handle client updates
  async function onClientSubmit(values: ClientFormValues) {
    if (!client) return;
    try {
      await updateClientMutation.mutateAsync({
        id: client.id,
        payload: {
          ...values,
          email: values.email || undefined,
          responsible_email: values.responsible_email || undefined,
        },
      });
      toast.success('Informações atualizadas com sucesso');
    } catch {
      toast.error('Erro ao atualizar informações do cliente');
    }
  }

  // Handle partner creation / update
  async function onPartnerSubmit(values: PartnerFormValues) {
    try {
      if (partnerToEdit) {
        await updatePartnerMutation.mutateAsync({
          id: partnerToEdit.id,
          payload: values,
        });
        toast.success('Sócio atualizado com sucesso');
      } else {
        await createPartnerMutation.mutateAsync(values);
        toast.success('Sócio cadastrado com sucesso');
      }
      setShowPartnerForm(false);
      setPartnerToEdit(null);
      resetPartner();
      refetchPartners();
    } catch {
      toast.error('Erro ao salvar sócio. Certifique-se de que o CPF é único.');
    }
  }

  // Handle partner deletion
  async function handleDeletePartner(id: string, name: string) {
    if (!confirm(`Remover sócio "${name}"?`)) return;
    try {
      await deletePartnerMutation.mutateAsync(id);
      toast.success('Sócio removido');
      refetchPartners();
    } catch {
      toast.error('Erro ao remover sócio');
    }
  }

  async function handleGenerateAiSummary() {
    if (!client) return;

    try {
      const summary = await generateAiSummaryMutation.mutateAsync(client.id);
      setClientAiSummary(summary);
      if (summary) {
        toast.success('Resumo de IA gerado');
      } else {
        toast.error('Resumo de IA indisponivel neste ambiente');
      }
    } catch {
      toast.error('Erro ao gerar resumo de IA');
    }
  }

  // Handle document upload
  async function handleDocUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadingFile(true);
    try {
      // Upload to Supabase/API storage
      const uploadRes = await uploadFileMutation.mutateAsync(file);

      // Create document entry in database
      await createDocMutation.mutateAsync({
        document_type: selectedDocType,
        file_url: uploadRes.url,
        expiration_date: docExpiration || undefined,
        notes: docNotes || undefined,
      });

      toast.success('Documento enviado com sucesso');
      setDocExpiration('');
      setDocNotes('');
      refetchDocs();
    } catch {
      toast.error('Erro ao enviar documento');
    } finally {
      setUploadingFile(false);
      // Reset file input
      e.target.value = '';
    }
  }

  // Handle document deletion
  async function handleDeleteDoc(id: string, type: string) {
    if (!confirm(`Excluir documento "${docTypeLabel(type)}"?`)) return;
    try {
      await deleteDocMutation.mutateAsync(id);
      toast.success('Documento removido');
      refetchDocs();
    } catch {
      toast.error('Erro ao remover documento');
    }
  }

  // Expiration threshold alerts (30 days)
  const isExpiringSoon = (expDateStr?: string | null) => {
    if (!expDateStr) return false;
    const expDate = new Date(expDateStr);
    const today = new Date();
    const diffTime = expDate.getTime() - today.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays >= 0 && diffDays <= 30;
  };

  const isExpired = (expDateStr?: string | null) => {
    if (!expDateStr) return false;
    const expDate = new Date(expDateStr);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return expDate < today;
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer Container */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="drawer-title"
        className="fixed right-0 top-0 z-50 flex h-full w-full max-w-2xl flex-col border-l border-border bg-background shadow-2xl transition-all duration-300 ease-in-out"
      >
        {/* Drawer Header */}
        <div className="flex shrink-0 items-center justify-between border-b border-border bg-muted/20 px-6 py-5">
          <div className="flex items-center gap-3">
            <Briefcase className="h-5 w-5 text-primary animate-pulse" />
            <div>
              <h2 id="drawer-title" className="text-lg font-bold text-foreground">
                Gerenciar Empresa
              </h2>
              <p className="text-xs text-muted-foreground font-mono">
                {client.name} {client.document ? `· ${client.document}` : ''}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-1.5 hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
            aria-label="Fechar"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Tab switcher */}
        <div className="flex border-b border-border bg-muted/10 px-6">
          <button
            onClick={() => setActiveTab('info')}
            className={`flex items-center gap-2 border-b-2 px-4 py-3.5 text-sm font-semibold transition-all ${
              activeTab === 'info'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            <User className="h-4 w-4" />
            Cadastro & Responsável
          </button>
          <button
            onClick={() => setActiveTab('partners')}
            className={`flex items-center gap-2 border-b-2 px-4 py-3.5 text-sm font-semibold transition-all ${
              activeTab === 'partners'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            <Users className="h-4 w-4" />
            Sócios ({partners.length})
          </button>
          <button
            onClick={() => setActiveTab('documents')}
            className={`flex items-center gap-2 border-b-2 px-4 py-3.5 text-sm font-semibold transition-all ${
              activeTab === 'documents'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            <FileText className="h-4 w-4" />
            Documentos Oficiais ({companyDocs.length})
          </button>
        </div>

        {/* Drawer Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* TAB 1: CLIENT AND RESPONSIBLE REGISTRATION */}
          {activeTab === 'info' && (
            <form onSubmit={handleSubmitClient(onClientSubmit)} className="space-y-6">
              <div className="space-y-4">
                <h3 className="text-sm font-bold text-foreground uppercase tracking-wide">
                  Dados da Empresa
                </h3>
                <FormField
                  label="Nome / Razão Social"
                  htmlFor="name"
                  error={clientErrors.name?.message}
                  required
                >
                  <Input id="name" {...registerClient('name')} />
                </FormField>

                <div className="grid grid-cols-2 gap-4">
                  <FormField
                    label="CPF / CNPJ"
                    htmlFor="document"
                    error={clientErrors.document?.message}
                  >
                    <Input id="document" {...registerClient('document')} />
                  </FormField>

                  <FormField label="Tipo de Entidade" htmlFor="entity_type" required>
                    <Select id="entity_type" {...registerClient('entity_type')}>
                      <option value="pj">Pessoa Jurídica</option>
                      <option value="pf">Pessoa Física</option>
                    </Select>
                  </FormField>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <FormField label="Regime Tributário" htmlFor="tax_regime">
                    <Select id="tax_regime" {...registerClient('tax_regime')}>
                      <option value="">Selecione</option>
                      <option value="Simples Nacional">Simples Nacional</option>
                      <option value="Lucro Presumido">Lucro Presumido</option>
                      <option value="Lucro Real">Lucro Real</option>
                      <option value="MEI">MEI</option>
                    </Select>
                  </FormField>

                  <FormField label="Status" htmlFor="status" required>
                    <Select id="status" {...registerClient('status')}>
                      <option value="active">Ativo</option>
                      <option value="onboarding">Onboarding</option>
                      <option value="inactive">Inativo</option>
                    </Select>
                  </FormField>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <FormField label="E-mail" htmlFor="email" error={clientErrors.email?.message}>
                    <Input id="email" type="email" {...registerClient('email')} />
                  </FormField>
                  <FormField label="Telefone" htmlFor="phone">
                    <Input id="phone" {...registerClient('phone')} />
                  </FormField>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <FormField label="Inscrição Municipal" htmlFor="municipal_registration">
                    <Input id="municipal_registration" {...registerClient('municipal_registration')} />
                  </FormField>
                  <FormField label="Inscrição Estadual" htmlFor="state_registration">
                    <Input id="state_registration" {...registerClient('state_registration')} />
                  </FormField>
                </div>

                <FormField label="Observações Internas" htmlFor="notes">
                  <Input id="notes" {...registerClient('notes')} />
                </FormField>
              </div>

              {/* Responsible section */}
              <div className="rounded-xl border border-muted bg-muted/20 p-5 space-y-4">
                <div className="flex items-center gap-2">
                  <User className="h-4.5 w-4.5 text-primary" />
                  <h3 className="text-sm font-bold text-foreground uppercase tracking-wide">
                    Responsável pelo CNPJ
                  </h3>
                </div>

                <FormField label="Nome do Responsável" htmlFor="responsible_name">
                  <Input id="responsible_name" {...registerClient('responsible_name')} />
                </FormField>

                <div className="grid grid-cols-2 gap-4">
                  <FormField label="CPF do Responsável" htmlFor="responsible_cpf">
                    <Input id="responsible_cpf" placeholder="000.000.000-00" {...registerClient('responsible_cpf')} />
                  </FormField>
                  <FormField label="Telefone do Responsável" htmlFor="responsible_phone">
                    <Input id="responsible_phone" {...registerClient('responsible_phone')} />
                  </FormField>
                </div>

                <FormField label="E-mail do Responsável" htmlFor="responsible_email" error={clientErrors.responsible_email?.message}>
                  <Input id="responsible_email" type="email" {...registerClient('responsible_email')} />
                </FormField>

                <FormField label="Endereço Completo" htmlFor="responsible_address">
                  <Input id="responsible_address" {...registerClient('responsible_address')} />
                </FormField>
              </div>

              <div className="flex justify-end pt-4 border-t border-border">
                <Button type="submit" disabled={isSavingClient} className="gap-2">
                  <Save className="h-4 w-4" />
                  {isSavingClient ? 'Salvando...' : 'Salvar Alterações'}
                </Button>
              </div>
            </form>
          )}

          {/* TAB 2: COMPANY PARTNERS (SÓCIOS) */}
          {activeTab === 'partners' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-foreground uppercase tracking-wide">
                  Quadro de Sócios e Administradores
                </h3>
                {!showPartnerForm && (
                  <Button
                    onClick={() => {
                      setPartnerToEdit(null);
                      setShowPartnerForm(true);
                    }}
                    size="sm"
                    className="gap-1.5"
                  >
                    <Plus className="h-4 w-4" />
                    Novo Sócio
                  </Button>
                )}
              </div>

              {/* Partner Add/Edit Form */}
              {showPartnerForm && (
                <form
                  onSubmit={handleSubmitPartner(onPartnerSubmit)}
                  className="rounded-xl border border-primary/20 bg-primary/5 p-5 space-y-4"
                >
                  <div className="flex items-center justify-between border-b border-primary/10 pb-2">
                    <h4 className="text-xs font-bold text-primary uppercase">
                      {partnerToEdit ? 'Editar Sócio' : 'Cadastrar Novo Sócio'}
                    </h4>
                    <button
                      type="button"
                      onClick={() => {
                        setShowPartnerForm(false);
                        setPartnerToEdit(null);
                      }}
                      className="text-muted-foreground hover:text-foreground text-xs font-semibold"
                    >
                      Cancelar
                    </button>
                  </div>

                  <FormField
                    label="Nome Completo"
                    htmlFor="partner_name"
                    error={partnerErrors.name?.message}
                    required
                  >
                    <Input id="partner_name" {...registerPartner('name')} />
                  </FormField>

                  <div className="grid grid-cols-2 gap-4">
                    <FormField
                      label="CPF do Sócio"
                      htmlFor="partner_cpf"
                      error={partnerErrors.cpf?.message}
                      required
                    >
                      <Input id="partner_cpf" placeholder="000.000.000-00" {...registerPartner('cpf')} />
                    </FormField>

                    <FormField
                      label="Participação (%)"
                      htmlFor="participation_percentage"
                      error={partnerErrors.participation_percentage?.message}
                      required
                    >
                      <Input
                        id="participation_percentage"
                        type="number"
                        step="0.01"
                        {...registerPartner('participation_percentage', { valueAsNumber: true })}
                      />
                    </FormField>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <FormField label="Data de Entrada" htmlFor="entry_date">
                      <Input id="entry_date" type="date" {...registerPartner('entry_date')} />
                    </FormField>

                    <FormField label="Status" htmlFor="partner_status">
                      <Select id="partner_status" {...registerPartner('status')}>
                        <option value="active">Ativo</option>
                        <option value="inactive">Inativo</option>
                      </Select>
                    </FormField>
                  </div>

                  <FormField label="Notas / Observações" htmlFor="partner_notes">
                    <Input id="partner_notes" placeholder="Ex: Sócio Administrador" {...registerPartner('notes')} />
                  </FormField>

                  <div className="flex justify-end pt-2">
                    <Button type="submit" disabled={isSavingPartner} size="sm" className="gap-1">
                      <CheckCircle className="h-4 w-4" />
                      {isSavingPartner ? 'Salvando...' : 'Salvar Sócio'}
                    </Button>
                  </div>
                </form>
              )}

              {/* Partners List */}
              <div className="space-y-3">
                {partners.length === 0 ? (
                  <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-8 text-center bg-muted/5">
                    <Users className="h-8 w-8 text-muted-foreground/30 mb-2" />
                    <p className="text-sm font-medium text-muted-foreground">Nenhum sócio cadastrado</p>
                    <p className="text-xs text-muted-foreground/70">
                      Adicione os sócios para completar a ficha da empresa.
                    </p>
                  </div>
                ) : (
                  partners.map((partner) => (
                    <div
                      key={partner.id}
                      className="group flex items-center justify-between rounded-xl border p-4 bg-card hover:bg-muted/10 transition-colors"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-foreground">{partner.name}</span>
                          <Badge variant={partner.status === 'active' ? 'success' : 'default'}>
                            {partner.status === 'active' ? 'Ativo' : 'Inativo'}
                          </Badge>
                          <span className="text-xs font-mono font-bold text-primary bg-primary/10 px-2 py-0.5 rounded">
                            {partner.participation_percentage}%
                          </span>
                        </div>
                        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <strong>CPF:</strong> {partner.cpf}
                          </span>
                          {partner.entry_date && (
                            <span className="flex items-center gap-1">
                              <Calendar className="h-3 w-3" />
                              <strong>Entrada:</strong> {new Date(partner.entry_date + 'T00:00:00').toLocaleDateString('pt-BR')}
                            </span>
                          )}
                          {partner.notes && (
                            <span>
                              <strong>Obs:</strong> {partner.notes}
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity">
                        <button
                          type="button"
                          onClick={() => setPartnerToEdit(partner)}
                          className="flex flex-col items-center gap-0.5 rounded p-1 text-muted-foreground hover:text-primary hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                          aria-label="Editar"
                        >
                          <Edit2 className="h-4 w-4" />
                          <span className="text-[9px] font-medium uppercase tracking-wider">Editar</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDeletePartner(partner.id, partner.name)}
                          className="flex flex-col items-center gap-0.5 rounded p-1 text-muted-foreground hover:text-destructive hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                          aria-label="Excluir"
                        >
                          <Trash2 className="h-4 w-4" />
                          <span className="text-[9px] font-medium uppercase tracking-wider">Excluir</span>
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* TAB 3: COMPANY DOCUMENTS (DOCUMENTOS) */}
          {activeTab === 'documents' && (
            <div className="space-y-6">
              {/* Expiring Docs warning banner */}
              {companyDocs.some((d) => isExpiringSoon(d.expiration_date) || isExpired(d.expiration_date)) && (
                <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-4 flex gap-3">
                  <AlertTriangle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
                  <div>
                    <h4 className="text-sm font-bold text-destructive">
                      Documentos Vencendo em Breve ou Expirados
                    </h4>
                    <p className="text-xs text-destructive/80 mt-1">
                      Abaixo há documentos com vencimento próximo ou já expirados. Providencie a renovação do alvará ou licença.
                    </p>
                  </div>
                </div>
              )}

              <ClientAiSummaryPanel
                summary={clientAiSummary}
                isGenerating={generateAiSummaryMutation.isPending}
                onGenerate={handleGenerateAiSummary}
              />

              <div className="space-y-3">
                <h3 className="text-sm font-bold text-foreground uppercase tracking-wide">
                  Documentos Operacionais com IA
                </h3>
                <ParsedDocumentsPanel documents={parsedClientDocs} isLoading={isLoadingParsedDocs} />
              </div>

              {/* Upload Document section */}
              <div className="rounded-xl border p-5 bg-card space-y-4">
                <h3 className="text-sm font-bold text-foreground uppercase tracking-wide">
                  Fazer Upload de Novo Documento
                </h3>

                <div className="grid grid-cols-2 gap-4">
                  <FormField label="Tipo de Documento" htmlFor="document_type">
                    <Select
                      id="document_type"
                      value={selectedDocType}
                      onChange={(e) => setSelectedDocType(e.target.value)}
                    >
                      {DOCUMENT_TYPES.map((type) => (
                        <option key={type.value} value={type.value}>
                          {type.label}
                        </option>
                      ))}
                    </Select>
                  </FormField>

                  <FormField label="Data de Vencimento" htmlFor="doc_expiration">
                    <Input
                      id="doc_expiration"
                      type="date"
                      value={docExpiration}
                      onChange={(e) => setDocExpiration(e.target.value)}
                    />
                  </FormField>
                </div>

                <FormField label="Notas do Documento" htmlFor="doc_notes">
                  <Input
                    id="doc_notes"
                    placeholder="Ex: Ano base 2026 (opcional)"
                    value={docNotes}
                    onChange={(e) => setDocNotes(e.target.value)}
                  />
                </FormField>

                <div className="flex justify-end pt-2">
                  <label className="cursor-pointer">
                    <input
                      type="file"
                      accept=".pdf,.jpg,.jpeg,.png"
                      className="sr-only"
                      onChange={handleDocUpload}
                      disabled={uploadingFile}
                    />
                    <span className="inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow hover:bg-primary/95 transition-colors">
                      <Upload className="h-4 w-4" />
                      {uploadingFile ? 'Enviando...' : 'Selecionar & Enviar Arquivo'}
                    </span>
                  </label>
                </div>
              </div>

              {/* Uploaded Documents List */}
              <div className="space-y-3">
                <h3 className="text-sm font-bold text-foreground uppercase tracking-wide">
                  Documentos Cadastrados
                </h3>

                {companyDocs.length === 0 ? (
                  <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-8 text-center bg-muted/5">
                    <FileText className="h-8 w-8 text-muted-foreground/30 mb-2" />
                    <p className="text-sm font-medium text-muted-foreground">Nenhum documento arquivado</p>
                    <p className="text-xs text-muted-foreground/70">
                      Faça o upload de CNPJ, Contratos Sociais e Alvarás para mantê-los organizados.
                    </p>
                  </div>
                ) : (
                  companyDocs.map((doc) => {
                    const expiring = isExpiringSoon(doc.expiration_date);
                    const expired = isExpired(doc.expiration_date);
                    return (
                      <div
                        key={doc.id}
                        className="group flex items-center justify-between rounded-xl border p-4 bg-card hover:bg-muted/10 transition-colors"
                      >
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-foreground">
                              {docTypeLabel(doc.document_type)}
                            </span>
                            <Badge
                              variant={
                                expired
                                  ? 'error'
                                  : expiring
                                  ? 'warning'
                                  : doc.status === 'valid'
                                  ? 'success'
                                  : 'default'
                              }
                            >
                              {expired
                                ? 'Expirado'
                                : expiring
                                ? 'Expira em breve'
                                : doc.status.toUpperCase()}
                            </Badge>
                          </div>
                          <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                            <span>
                              <strong>Enviado em:</strong>{' '}
                              {new Date(doc.upload_date).toLocaleDateString('pt-BR')}
                            </span>
                            {doc.expiration_date && (
                              <span className="flex items-center gap-1">
                                <Calendar className="h-3 w-3" />
                                <strong>Vencimento:</strong>{' '}
                                {new Date(doc.expiration_date + 'T00:00:00').toLocaleDateString('pt-BR')}
                              </span>
                            )}
                            {doc.notes && (
                              <span>
                                <strong>Notas:</strong> {doc.notes}
                              </span>
                            )}
                          </div>
                        </div>

                        <div className="flex items-center gap-2.5 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity">
                          <a
                            href={doc.file_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex flex-col items-center gap-0.5 rounded p-1.5 text-muted-foreground hover:text-primary hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            title="Visualizar Documento"
                          >
                            <FileDown className="h-4.5 w-4.5" />
                            <span className="text-[9px] font-medium uppercase tracking-wider">Baixar</span>
                          </a>
                          <button
                            type="button"
                            onClick={() => handleDeleteDoc(doc.id, doc.document_type)}
                            className="flex flex-col items-center gap-0.5 rounded p-1.5 text-muted-foreground hover:text-destructive hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            aria-label="Excluir"
                            title="Excluir Documento"
                          >
                            <Trash2 className="h-4.5 w-4.5" />
                            <span className="text-[9px] font-medium uppercase tracking-wider">Excluir</span>
                          </button>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
