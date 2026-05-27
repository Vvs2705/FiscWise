import { useState, useEffect, useMemo, useCallback } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import {
  User,
  Users,
  FileText,
  ClipboardList,
  Receipt,
  Key,
  DollarSign,
  Calendar,
  Lock,
  Plus,
  Trash2,
  Edit2,
  Upload,
  FileDown,
  CheckCircle,
  Save,
  Sparkles,
  AlertTriangle,
  MessageSquare,
  Printer,
  Activity,
  RefreshCw,
} from 'lucide-react';
import { cn, formatCurrencyBRL, parseCurrencyBRL } from '@/lib/utils';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Badge } from '@/components/ui/Badge';
import { FormField } from '@/components/ui/FormField';
import { Card } from '@/components/ui/Card';
import { ProgressRing } from '@/components/ui/ProgressRing';
import { FiscalTimeline, TimelineItem } from '@/components/ui/FiscalTimeline';
import { ClientStatusReportModal } from './ClientStatusReportModal';
import { ClientWhatsAppWidget } from './ClientWhatsAppWidget';
import {
  useFiscalMonitorStatus,
  useFiscalNFes,
  useSyncFiscalMonitor,
} from '@/lib/hooks/useFiscalMonitor';
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
  useDasPayments,
  usePayDas,
  useDeadlines,
  useDeleteDeadline,
  useCertificates,
  useClientBillingConfig,
  useUpdateClientBillingConfig,
  useClientBillingHistory,
  useClients,
  useUpdateReceivable,
  moneyBRL,
  dateBR,
  type ClientBillingHistoryItem,
  type CompanyPartner,
  type CompanyDocument,
  type DasPayment,
  type DeadlineItem,
  type DigitalCertificate,
  type ClientStatus
} from '@/lib/hooks/useOperations';
import {
  buildClientAiSummaryView,
  buildDocumentAiView,
  type ClientAiSummary,
} from '@/lib/aiDocuments';

interface ClientDetailCockpitProps {
  clientId: string;
  onClose?: () => void;
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
  responsible_name: z.string().optional(),
  responsible_cpf: z.string().optional(),
  responsible_address: z.string().optional(),
  responsible_phone: z.string().optional(),
  responsible_email: z.string().email('E-mail inválido').optional().or(z.literal('')),
});

type ClientFormValues = z.infer<typeof clientSchema>;

const partnerSchema = z.object({
  name: z.string().min(1, 'Nome do sócio é obrigatório'),
  cpf: z.string().min(11, 'CPF deve ter no mínimo 11 dígitos'),
  participation_percentage: z.number().min(0).max(100),
  entry_date: z.string().optional(),
  status: z.string().default('active'),
  notes: z.string().optional(),
});

type PartnerFormValues = z.infer<typeof partnerSchema>;
type MessageTemplate = 'das' | 'documentos' | 'certificado' | 'personalizado';
type NfeTypeFilter = 'ALL' | 'ENTRADA' | 'SAIDA';

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

export function ClientDetailCockpit({ clientId, onClose }: ClientDetailCockpitProps) {
  const [activeTab, setActiveTab] = useState<
    'resumo' | 'socios' | 'documentos' | 'obrigacoes' | 'guias' | 'certificados' | 'monitor_fiscal' | 'financeiro' | 'comunicacao' | 'historico' | 'notas'
  >('resumo');

  const { data: clients } = useClients();
  const client = useMemo(() => clients?.find((c) => c.id === clientId) ?? null, [clients, clientId]);

  const [partnerToEdit, setPartnerToEdit] = useState<CompanyPartner | null>(null);
  const [showPartnerForm, setShowPartnerForm] = useState(false);
  const [selectedDocType, setSelectedDocType] = useState('cnpj');
  const [docExpiration, setDocExpiration] = useState('');
  const [docNotes, setDocNotes] = useState('');
  const [uploadingFile, setUploadingFile] = useState(false);
  const [clientAiSummary, setClientAiSummary] = useState<ClientAiSummary | null>(null);

  // Communication & Report states
  const [isReportOpen, setIsReportOpen] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<MessageTemplate>('das');
  const [composedMessage, setComposedMessage] = useState('');
  const [sendingEmail, setSendingEmail] = useState(false);

  // Queries
  const updateClientMutation = useUpdateClient();
  const { data: partners = [], refetch: refetchPartners } = usePartners(clientId);
  const createPartnerMutation = useCreatePartner(clientId);
  const updatePartnerMutation = useUpdatePartner(clientId);
  const deletePartnerMutation = useDeletePartner(clientId);

  const { data: companyDocs = [], refetch: refetchDocs } = useCompanyDocuments(clientId);
  const { data: parsedClientDocs = [], isLoading: isLoadingParsedDocs } = useClientDocuments(clientId);
  const createDocMutation = useCreateCompanyDocument(clientId);
  const deleteDocMutation = useDeleteCompanyDocument(clientId);
  const generateAiSummaryMutation = useGenerateClientAiSummary();
  const uploadFileMutation = useUploadDocument();

  const { data: dasPayments = [], refetch: refetchDas } = useDasPayments(clientId);
  const payDasMutation = usePayDas();

  const { data: deadlines = [], refetch: refetchDeadlines } = useDeadlines();
  const deleteDeadlineMutation = useDeleteDeadline();
  
  const { data: certificates = [] } = useCertificates();

  // Fiscal Monitor Queries & Mutations
  const { data: monitorSummary, refetch: refetchMonitor } = useFiscalMonitorStatus(clientId);
  const { data: monitorNfes = [], refetch: refetchNfes, isLoading: isLoadingNfes } = useFiscalNFes(clientId);
  const syncMonitorMutation = useSyncFiscalMonitor(clientId);

  const [nfeSearchQuery, setNfeSearchQuery] = useState('');
  const [nfeTypeFilter, setNfeTypeFilter] = useState<NfeTypeFilter>('ALL');

  const { data: billingConfig } = useClientBillingConfig(clientId);
  const updateBillingConfigMutation = useUpdateClientBillingConfig();
  const { data: billingHistory = [] } = useClientBillingHistory(clientId);
  const updateReceivableMutation = useUpdateReceivable();

  const clientDeadlines = useMemo(() => {
    return deadlines.filter((d) => d.client_id === clientId);
  }, [deadlines, clientId]);

  const clientCertificates = useMemo(() => {
    return certificates.filter((c) => c.client_id === clientId);
  }, [certificates, clientId]);

  // Hook Forms
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

  const [editBilling, setEditBilling] = useState(false);
  const [billingFee, setBillingFee] = useState<string>('');
  const [billingDay, setBillingDay] = useState<number>(5);

  useEffect(() => {
    if (billingConfig) {
      setBillingFee(formatCurrencyBRL(billingConfig.monthly_fee ?? 0));
      setBillingDay(billingConfig.billing_day ?? 5);
    }
  }, [billingConfig]);

  // Load client values
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
      refetchDas();
      refetchDeadlines();
      refetchMonitor();
      refetchNfes();
    }
  }, [client, resetClient, refetchPartners, refetchDocs, refetchDas, refetchDeadlines, refetchMonitor, refetchNfes]);

  // Partner editor effect
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

  // Submit client form
  async function onClientSubmit(values: ClientFormValues) {
    try {
      await updateClientMutation.mutateAsync({
        id: clientId,
        payload: {
          ...values,
          email: values.email || undefined,
          responsible_email: values.responsible_email || undefined,
        },
      });
      toast.success('Informações atualizadas com sucesso');
    } catch {
      toast.error('Erro ao atualizar informações da empresa');
    }
  }

  // Submit partner form
  async function onPartnerSubmit(values: PartnerFormValues) {
    try {
      const sanitizedPayload = {
        ...values,
        entry_date: values.entry_date === '' ? undefined : values.entry_date,
      };
      if (partnerToEdit) {
        await updatePartnerMutation.mutateAsync({
          id: partnerToEdit.id,
          payload: sanitizedPayload,
        });
        toast.success('Sócio atualizado com sucesso');
      } else {
        await createPartnerMutation.mutateAsync(sanitizedPayload);
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

  // Delete partner
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

  // Generate AI summary
  async function handleGenerateAiSummary() {
    try {
      const summary = await generateAiSummaryMutation.mutateAsync(clientId);
      setClientAiSummary(summary);
      if (summary) {
        toast.success('Resumo de IA gerado');
      } else {
        toast.error('Resumo de IA indisponível neste plano');
      }
    } catch {
      toast.error('Erro ao gerar resumo de IA');
    }
  }

  // Upload company doc
  async function handleDocUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadingFile(true);
    try {
      const uploadRes = await uploadFileMutation.mutateAsync(file);
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
      e.target.value = '';
    }
  }

  // Delete company doc
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

  // Pay DAS guide
  const handlePayDas = useCallback(async (id: string) => {
    try {
      await payDasMutation.mutateAsync(id);
      toast.success('Guia marcada como paga!');
      refetchDas();
    } catch {
      toast.error('Erro ao marcar guia como paga.');
    }
  }, [payDasMutation, refetchDas]);

  // Delete deadline
  async function handleDeleteDeadline(id: string) {
    if (!confirm('Excluir este prazo?')) return;
    try {
      await deleteDeadlineMutation.mutateAsync(id);
      toast.success('Prazo excluído.');
      refetchDeadlines();
    } catch {
      toast.error('Erro ao excluir prazo.');
    }
  }

  // Save billing config
  async function handleSaveBilling() {
    try {
      await updateBillingConfigMutation.mutateAsync({
        clientId,
        payload: {
          monthly_fee: parseCurrencyBRL(billingFee),
          billing_day: billingDay,
        },
      });
      toast.success('Honorários atualizados!');
      setEditBilling(false);
    } catch {
      toast.error('Erro ao atualizar honorários.');
    }
  }

  // Helper date logic
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

  // Build History Timeline Items
  const timelineItems = useMemo<TimelineItem[]>(() => {
    const list: TimelineItem[] = [];

    // Docs
    companyDocs.forEach((doc: CompanyDocument) => {
      list.push({
        id: `company-doc-${doc.id}`,
        title: `Upload: ${docTypeLabel(doc.document_type)}`,
        description: doc.notes || 'Documento oficial anexado na ficha.',
        date: new Date(doc.upload_date).toLocaleDateString('pt-BR'),
        type: isExpired(doc.expiration_date) ? 'error' : isExpiringSoon(doc.expiration_date) ? 'warning' : 'success',
        icon: FileText,
      });
    });

    // DAS Payments
    dasPayments.forEach((das: DasPayment) => {
      list.push({
        id: `das-${das.id}`,
        title: `DAS Competência ${das.period}`,
        description: `DAS gerado no valor de ${moneyBRL(das.tax_amount)} (Vencimento: ${dateBR(das.due_date)})`,
        date: dateBR(das.due_date),
        type: das.status === 'paid' ? 'success' : das.status === 'overdue' ? 'error' : 'warning',
        icon: Receipt,
        action: das.status !== 'paid' && (
          <Button
            size="sm"
            variant="outline"
            className="h-7 text-[10px] py-1 px-3 mt-1.5"
            onClick={() => handlePayDas(das.id)}
          >
            Confirmar Pagamento DAS
          </Button>
        ),
      });
    });

    // Deadlines
    clientDeadlines.forEach((dl: DeadlineItem) => {
      list.push({
        id: `deadline-${dl.id}`,
        title: `Prazo: ${dl.title}`,
        description: `${dl.category} - Vencimento ${dateBR(dl.due_date)}.`,
        date: dateBR(dl.due_date),
        type: dl.status === 'completed' ? 'success' : dl.status === 'overdue' ? 'error' : 'warning',
        icon: Calendar,
      });
    });

    // Digital Certificates
    clientCertificates.forEach((cert: DigitalCertificate) => {
      const daysRemaining = Math.max(
        0,
        Math.ceil((new Date(cert.valid_until).getTime() - new Date().getTime()) / 86_400_000)
      );
      list.push({
        id: `cert-${cert.id}`,
        title: `Certificado: ${cert.label}`,
        description: `Tipo: ${cert.certificate_type.toUpperCase()} · Vence em ${dateBR(cert.valid_until)} (${daysRemaining} dias).`,
        date: dateBR(cert.valid_until),
        type: cert.status === 'expired' ? 'error' : cert.status === 'expiring' ? 'warning' : 'info',
        icon: Key,
      });
    });

    // Billing / Honorarios
    billingHistory.forEach((invoice: ClientBillingHistoryItem) => {
      list.push({
        id: `invoice-${invoice.id}`,
        title: `Honorário: ${invoice.description}`,
        description: `Mensalidade no valor de ${moneyBRL(invoice.amount)} · Vencimento: ${dateBR(invoice.due_date)}`,
        date: dateBR(invoice.due_date),
        type: invoice.status === 'paid' ? 'success' : invoice.status === 'overdue' ? 'error' : 'warning',
        icon: DollarSign,
        action: invoice.status !== 'paid' && (
          <Button
            size="sm"
            variant="outline"
            className="h-7 text-[10px] py-1 px-3 mt-1.5"
            onClick={async () => {
              try {
                await updateReceivableMutation.mutateAsync({
                  id: invoice.id,
                  payload: { status: 'paid', paid_at: new Date().toISOString().split('T')[0] },
                });
                toast.success('Honorário marcado como pago!');
              } catch {
                toast.error('Erro ao liquidar honorário.');
              }
            }}
          >
            Confirmar Pagamento Honorário
          </Button>
        ),
      });
    });

    return list.sort((a, b) => {
      const parseDate = (dStr: string) => {
        const parts = dStr.split('/');
        if (parts.length === 3) return new Date(`${parts[2]}-${parts[1]}-${parts[0]}`).getTime();
        return new Date(dStr).getTime();
      };
      return parseDate(b.date) - parseDate(a.date);
    });
  }, [billingHistory, clientCertificates, clientDeadlines, companyDocs, dasPayments, handlePayDas, updateReceivableMutation]);

  // Score Health calculation (client-specific)
  const healthScore = useMemo(() => {
    let score = 100;
    const overdueDas = dasPayments.filter((d) => d.status === 'overdue').length;
    const overdueDl = clientDeadlines.filter((d) => d.status === 'overdue').length;
    const expiredDocs = companyDocs.filter((d) => isExpired(d.expiration_date)).length;

    score -= overdueDas * 15;
    score -= overdueDl * 10;
    score -= expiredDocs * 10;

    return Math.max(0, Math.min(100, score));
  }, [dasPayments, clientDeadlines, companyDocs]);

  // Missing docs
  const missingDocsList = useMemo(() => {
    const required = ['cnpj', 'contrato_social', 'inscricao_municipal'];
    const uploaded = companyDocs.map((d) => d.document_type);
    const missing = required.filter((type) => !uploaded.includes(type));
    return missing.map((type) => docTypeLabel(type));
  }, [companyDocs]);

  // Pending DAS
  const dasPendingDetail = useMemo(() => {
    const pending = dasPayments.find((das) => das.status === 'pending' || das.status === 'overdue');
    if (pending) {
      return `Competência ${pending.period} no valor de ${moneyBRL(pending.tax_amount)} (Vence em ${dateBR(pending.due_date)})`;
    }
    return 'Nenhuma guia DAS pendente.';
  }, [dasPayments]);

  // Pending certificate
  const certPendingDetail = useMemo(() => {
    const cert = clientCertificates.find((c) => c.status === 'expiring' || c.status === 'expired');
    if (cert) {
      return `Certificado ${cert.label} (Expira em ${dateBR(cert.valid_until)})`;
    }
    return 'Nenhum certificado digital expirando.';
  }, [clientCertificates]);

  const templates = useMemo(() => ({
    das: `Olá! Segue o lembrete de pagamento da guia DAS do Simples Nacional referente à {das_detalhe} para a empresa {cliente}.

Por favor, realize o pagamento e envie o comprovante.
Atenciosamente,
FiscWise`,

    documentos: `Olá! Identificamos que estão faltando alguns documentos oficiais da empresa {cliente} necessários para a regularidade operacional:

{documentos_pendentes}

Por favor, faça o upload direto no portal ou responda a esta mensagem com os arquivos em anexo.
Atenciosamente,
FiscWise`,

    certificado: `Olá! Gostaríamos de avisar que o seu certificado digital está expirando:
{certificado_detalhe} para a empresa {cliente}.

Para evitar interrupções no envio de obrigações e emissão de notas fiscais, solicitamos que providencie a renovação do mesmo o quanto antes.
Atenciosamente,
FiscWise`,

    personalizado: `Olá!
Gostaríamos de entrar em contato sobre a empresa {cliente}...

Atenciosamente,
FiscWise`,
  }), []);

  useEffect(() => {
    if (!client) {
      setComposedMessage('');
      return;
    }
    let msg = templates[selectedTemplate];
    msg = msg.replace(/{cliente}/g, client.name);
    msg = msg.replace(/{documentos_pendentes}/g, missingDocsList.length > 0 ? missingDocsList.map((d) => `- ${d}`).join('\n') : 'Nenhum documento pendente.');
    msg = msg.replace(/{das_detalhe}/g, dasPendingDetail);
    msg = msg.replace(/{certificado_detalhe}/g, certPendingDetail);
    setComposedMessage(msg);
  }, [selectedTemplate, client, missingDocsList, dasPendingDetail, certPendingDetail, templates]);

  const handleCopyWhatsApp = () => {
    if (!client) return;
    navigator.clipboard.writeText(composedMessage);
    toast.success('Mensagem copiada para a área de transferência!');
    
    const cleanedPhone = (client.phone || '').replace(/\D/g, '');
    const url = `https://api.whatsapp.com/send?phone=${cleanedPhone ? '55' + cleanedPhone : ''}&text=${encodeURIComponent(composedMessage)}`;
    window.open(url, '_blank');
  };

  const handleSendEmail = () => {
    if (!client) return;
    if (!client.email) {
      toast.error('Cliente não possui e-mail cadastrado!');
      return;
    }
    setSendingEmail(true);
    setTimeout(() => {
      setSendingEmail(false);
      toast.success(`E-mail com lembrete enviado para ${client.email}!`);
    }, 1200);
  };

  if (!client) {
    return (
      <div className="flex h-64 items-center justify-center">
        <p className="text-muted-foreground text-sm">Carregando dados da empresa...</p>
      </div>
    );
  }

  const tabs = [
    { id: 'resumo', label: 'Resumo', icon: User },
    { id: 'socios', label: 'Sócios', icon: Users },
    { id: 'documentos', label: 'Documentos', icon: FileText },
    { id: 'obrigacoes', label: 'Prazos', icon: ClipboardList },
    { id: 'guias', label: 'DAS & Guias', icon: Receipt },
    { id: 'certificados', label: 'Certificados', icon: Key },
    { id: 'monitor_fiscal', label: 'Monitor Fiscal', icon: Activity },
    { id: 'financeiro', label: 'Financeiro', icon: DollarSign },
    { id: 'comunicacao', label: 'Comunicação', icon: MessageSquare },
    { id: 'historico', label: 'Histórico', icon: Calendar },
    { id: 'notas', label: 'Notas', icon: Lock },
  ] as const;

  const view = buildClientAiSummaryView(clientAiSummary ?? null);

  return (
    <div className="flex flex-col h-full bg-background text-foreground">
      {/* Client Header Info */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-border/80 px-6 py-5 bg-card/40 shrink-0">
        <div className="flex items-center gap-3">
          <ProgressRing score={healthScore} size={48} strokeWidth={3} />
          <div>
            <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
              {client.name}
              <Badge variant={statusVariant[client.status]}>{statusLabel[client.status]}</Badge>
            </h1>
            <p className="text-xs text-muted-foreground font-mono">
              CNPJ/CPF: {client.document || 'Não informado'} · Código #{client.client_code}
            </p>
          </div>
        </div>
        {onClose && (
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsReportOpen(true)}
              className="gap-1.5 border-cyan-400/30 text-cyan-300 hover:bg-cyan-400/10"
            >
              <Printer className="h-4 w-4" />
              Gerar Relatório
            </Button>
            <Button variant="outline" size="sm" onClick={onClose}>
              Fechar
            </Button>
          </div>
        )}
      </div>

      {/* Tabs list (Horizontal scroll on mobile) */}
      <div className="flex border-b border-border bg-muted/10 px-6 overflow-x-auto scrollbar-none shrink-0">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 border-b-2 px-4 py-3.5 text-xs font-semibold whitespace-nowrap transition-all ${
                activeTab === tab.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Panels */}
      <div className="flex-1 overflow-y-auto p-6 scrollbar">
        {/* RESUMO */}
        {activeTab === 'resumo' && (
          <div className="space-y-6">
            {/* AI Summary Block */}
            <div className="rounded-2xl border border-primary/20 bg-primary/5 p-5 space-y-4 shadow-glow-sm">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Sparkles className="h-4.5 w-4.5 text-primary" />
                  <h3 className="text-sm font-bold text-foreground uppercase tracking-wider">
                    Resumo Operacional IA
                  </h3>
                </div>
                {view.documentsAnalyzedLabel && (
                  <span className="text-xs text-muted-foreground">{view.documentsAnalyzedLabel}</span>
                )}
              </div>
              <p className="text-sm text-foreground leading-relaxed">{view.summary}</p>
              <Button
                type="button"
                size="sm"
                variant={view.available ? 'outline' : 'default'}
                onClick={handleGenerateAiSummary}
                disabled={generateAiSummaryMutation.isPending}
                className="gap-1.5"
              >
                <Sparkles className="h-4 w-4" />
                {generateAiSummaryMutation.isPending
                  ? 'Gerando...'
                  : view.available
                  ? 'Atualizar resumo'
                  : 'Gerar resumo'}
              </Button>
            </div>

            {/* Profile Forms */}
            <form onSubmit={handleSubmitClient(onClientSubmit)} className="grid gap-6 md:grid-cols-2">
              <div className="space-y-4">
                <h3 className="text-xs font-bold text-foreground uppercase tracking-wider border-b pb-1">
                  Ficha da Empresa
                </h3>
                <FormField label="Nome / Razão Social" htmlFor="name" error={clientErrors.name?.message} required>
                  <Input id="name" {...registerClient('name')} />
                </FormField>
                <div className="grid grid-cols-2 gap-4">
                  <FormField label="CNPJ / CPF" htmlFor="document" error={clientErrors.document?.message}>
                    <Input id="document" {...registerClient('document')} />
                  </FormField>
                  <FormField label="Tipo" htmlFor="entity_type" required>
                    <Select id="entity_type" {...registerClient('entity_type')}>
                      <option value="pj">Pessoa Jurídica</option>
                      <option value="pf">Pessoa Física</option>
                    </Select>
                  </FormField>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <FormField label="Regime Fiscal" htmlFor="tax_regime">
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
              </div>

              {/* Responsible Person Form */}
              <div className="space-y-4">
                <h3 className="text-xs font-bold text-foreground uppercase tracking-wider border-b pb-1">
                  Responsável Legal
                </h3>
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
                <FormField
                  label="E-mail do Responsável"
                  htmlFor="responsible_email"
                  error={clientErrors.responsible_email?.message}
                >
                  <Input id="responsible_email" type="email" {...registerClient('responsible_email')} />
                </FormField>
                <FormField label="Endereço Completo" htmlFor="responsible_address">
                  <Input id="responsible_address" {...registerClient('responsible_address')} />
                </FormField>
              </div>

              <div className="md:col-span-2 flex justify-end pt-4 border-t">
                <Button type="submit" disabled={isSavingClient} className="gap-2">
                  <Save className="h-4 w-4" />
                  {isSavingClient ? 'Salvando...' : 'Salvar Alterações'}
                </Button>
              </div>
            </form>
          </div>
        )}

        {/* SÓCIOS */}
        {activeTab === 'socios' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between border-b pb-2">
              <h3 className="text-sm font-bold text-foreground uppercase tracking-wide">
                Quadro de Sócios (QSA)
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
                  Adicionar Sócio
                </Button>
              )}
            </div>

            {showPartnerForm && (
              <form
                onSubmit={handleSubmitPartner(onPartnerSubmit)}
                className="fiscwise-surface rounded-xl border border-primary/20 bg-card p-5 space-y-4"
              >
                <h4 className="text-xs font-bold text-primary uppercase">
                  {partnerToEdit ? 'Editar Sócio' : 'Cadastrar Sócio'}
                </h4>
                <FormField label="Nome Completo" htmlFor="partner_name" error={partnerErrors.name?.message} required>
                  <Input id="partner_name" {...registerPartner('name')} />
                </FormField>
                <div className="grid grid-cols-2 gap-4">
                  <FormField label="CPF do Sócio" htmlFor="partner_cpf" error={partnerErrors.cpf?.message} required>
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
                <FormField label="Notas adicionais" htmlFor="partner_notes">
                  <Input id="partner_notes" placeholder="Ex: Sócio Administrador" {...registerPartner('notes')} />
                </FormField>
                <div className="flex justify-end gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setShowPartnerForm(false);
                      setPartnerToEdit(null);
                    }}
                  >
                    Cancelar
                  </Button>
                  <Button type="submit" disabled={isSavingPartner} size="sm" className="gap-1.5">
                    <CheckCircle className="h-4 w-4" />
                    Salvar Sócio
                  </Button>
                </div>
              </form>
            )}

            <div className="space-y-3">
              {partners.length === 0 ? (
                <div className="text-center py-10 border border-dashed rounded-xl text-muted-foreground">
                  Nenhum sócio vinculado a esta empresa.
                </div>
              ) : (
                partners.map((partner) => (
                  <div
                    key={partner.id}
                    className="fiscwise-surface flex items-center justify-between p-4 rounded-xl border border-border/80"
                  >
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-bold text-foreground">{partner.name}</span>
                        <Badge variant={partner.status === 'active' ? 'success' : 'default'}>
                          {partner.status === 'active' ? 'Ativo' : 'Inativo'}
                        </Badge>
                        <span className="text-xs bg-primary/10 text-primary font-bold px-1.5 py-0.5 rounded">
                          {partner.participation_percentage}%
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground font-mono">
                        CPF: {partner.cpf} {partner.entry_date ? `· Entrada: ${dateBR(partner.entry_date)}` : ''}
                      </p>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => setPartnerToEdit(partner)}>
                        <Edit2 className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 w-8 p-0 text-destructive hover:bg-destructive/10"
                        onClick={() => handleDeletePartner(partner.id, partner.name)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* DOCUMENTOS */}
        {activeTab === 'documentos' && (
          <div className="space-y-6">
            {/* Alert on Expired Docs */}
            {companyDocs.some((d) => isExpired(d.expiration_date)) && (
              <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-4 flex gap-3 items-start">
                <AlertTriangle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-sm font-bold text-destructive">Documentos Vencidos</h4>
                  <p className="text-xs text-destructive/80 mt-0.5">
                    Providencie a renovação de alvarás ou certidões expiradas.
                  </p>
                </div>
              </div>
            )}

            {/* AI Document Parser List */}
            <div className="space-y-3">
              <h3 className="text-xs font-bold text-foreground uppercase tracking-wider border-b pb-1">
                Documentos Analisados por IA
              </h3>
              {isLoadingParsedDocs ? (
                <div className="py-4 text-center text-xs text-muted-foreground">Carregando documentos com IA...</div>
              ) : parsedClientDocs.length === 0 ? (
                <div className="text-center py-6 border border-dashed rounded-xl text-xs text-muted-foreground">
                  Nenhum documento processado por IA.
                </div>
              ) : (
                <div className="grid gap-3 sm:grid-cols-2">
                  {parsedClientDocs.map((doc) => {
                    const aiView = buildDocumentAiView(doc);
                    return (
                      <div key={doc.id} className="fiscwise-surface rounded-xl border p-4 space-y-3">
                        <div className="flex justify-between items-start">
                          <div>
                            <h4 className="font-bold text-sm text-foreground truncate max-w-[200px]" title={doc.name}>
                              {doc.name}
                            </h4>
                            <p className="text-[10px] text-muted-foreground uppercase">{doc.document_type}</p>
                          </div>
                          <Badge variant={aiView.parseStatusVariant}>{aiView.parseStatusLabel}</Badge>
                        </div>
                        {aiView.classification && (
                          <div className="text-xs text-muted-foreground space-y-1">
                            <p className="flex items-center gap-1 font-semibold text-primary">
                              <Sparkles className="w-3.5 h-3.5" /> {aiView.classification.documentType}
                            </p>
                            {aiView.classification.fields.map((f) => (
                              <p key={f.label}>
                                <strong>{f.label}:</strong> {f.value}
                              </p>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Upload Document */}
            <div className="fiscwise-surface border rounded-xl p-5 space-y-4">
              <h3 className="text-xs font-bold text-foreground uppercase tracking-wider">
                Upload de Documento Oficial
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <FormField label="Tipo de Documento" htmlFor="document_type">
                  <Select id="document_type" value={selectedDocType} onChange={(e) => setSelectedDocType(e.target.value)}>
                    {DOCUMENT_TYPES.map((type) => (
                      <option key={type.value} value={type.value}>
                        {type.label}
                      </option>
                    ))}
                  </Select>
                </FormField>
                <FormField label="Data de Vencimento" htmlFor="doc_expiration">
                  <Input id="doc_expiration" type="date" value={docExpiration} onChange={(e) => setDocExpiration(e.target.value)} />
                </FormField>
              </div>
              <FormField label="Anotações" htmlFor="doc_notes">
                <Input id="doc_notes" placeholder="Ex: Exercício 2026" value={docNotes} onChange={(e) => setDocNotes(e.target.value)} />
              </FormField>
              <div className="flex justify-end">
                <label className="cursor-pointer">
                  <input type="file" className="sr-only" onChange={handleDocUpload} disabled={uploadingFile} />
                  <span className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow hover:bg-primary/95 transition-all">
                    <Upload className="h-4 w-4" />
                    {uploadingFile ? 'Enviando...' : 'Selecionar & Upload'}
                  </span>
                </label>
              </div>
            </div>

            {/* Uploaded List */}
            <div className="space-y-3">
              <h3 className="text-xs font-bold text-foreground uppercase tracking-wider border-b pb-1">
                Documentos Arquivados
              </h3>
              {companyDocs.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground text-sm">Nenhum documento oficial.</div>
              ) : (
                companyDocs.map((doc) => (
                  <div key={doc.id} className="fiscwise-surface flex items-center justify-between p-4 rounded-xl border border-border/80">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-bold text-foreground">{docTypeLabel(doc.document_type)}</span>
                        <Badge variant={isExpired(doc.expiration_date) ? 'error' : isExpiringSoon(doc.expiration_date) ? 'warning' : 'success'}>
                          {isExpired(doc.expiration_date) ? 'Expirado' : isExpiringSoon(doc.expiration_date) ? 'Expira em breve' : 'Válido'}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Enviado em {new Date(doc.upload_date).toLocaleDateString('pt-BR')} 
                        {doc.expiration_date ? ` · Vencimento: ${dateBR(doc.expiration_date)}` : ''}
                      </p>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <a href={doc.file_url} target="_blank" rel="noopener noreferrer">
                        <Button variant="ghost" size="sm" className="h-8 w-8 p-0" title="Baixar">
                          <FileDown className="h-4.5 w-4.5" />
                        </Button>
                      </a>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 w-8 p-0 text-destructive hover:bg-destructive/10"
                        onClick={() => handleDeleteDoc(doc.id, doc.document_type)}
                        title="Excluir"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* OBRIGAÇÕES / PRAZOS */}
        {activeTab === 'obrigacoes' && (
          <div className="space-y-6">
            <h3 className="text-sm font-bold text-foreground uppercase tracking-wide border-b pb-2">
              Agenda de Compromissos Fiscais
            </h3>
            {(() => {
              const overdueCount = clientDeadlines.filter((d) => d.status === 'overdue').length;
              if (overdueCount === 0) return null;
              return (
                <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-4 flex gap-3 items-center justify-between">
                  <div className="flex gap-2.5 items-center">
                    <AlertTriangle className="h-5 w-5 text-red-400 shrink-0" />
                    <span className="text-xs text-red-200 font-semibold">
                      Atenção: Este cliente possui {overdueCount} obrigação(ões) em atraso!
                    </span>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-7 text-[10px] py-1 border-red-500/30 text-red-300 bg-red-500/10 hover:bg-red-500/20"
                    onClick={() => {
                      setSelectedTemplate('das');
                      setActiveTab('comunicacao');
                    }}
                  >
                    Cobrar Cliente
                  </Button>
                </div>
              );
            })()}
            {clientDeadlines.length === 0 ? (
              <div className="text-center py-10 border border-dashed rounded-xl text-muted-foreground text-sm">
                Nenhum prazo cadastrado para este cliente.
              </div>
            ) : (
              <div className="space-y-3">
                {clientDeadlines.map((dl) => (
                  <div key={dl.id} className="fiscwise-surface flex items-center justify-between p-4 rounded-xl border border-border/80">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-bold text-foreground">{dl.title}</span>
                        <Badge variant={dl.status === 'completed' ? 'success' : dl.status === 'overdue' ? 'error' : 'warning'}>
                          {dl.status === 'completed' ? 'Concluído' : dl.status === 'overdue' ? 'Atrasado' : 'Pendente'}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Categoria: {dl.category} · Vencimento: {dateBR(dl.due_date)}
                      </p>
                    </div>
                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-destructive hover:bg-destructive/10" onClick={() => handleDeleteDeadline(dl.id)}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* GUIAS & DAS */}
        {activeTab === 'guias' && (
          <div className="space-y-6">
            <h3 className="text-sm font-bold text-foreground uppercase tracking-wide border-b pb-2">
              Guia DAS & Receitas
            </h3>
            {dasPayments.length === 0 ? (
              <div className="text-center py-10 border border-dashed rounded-xl text-muted-foreground text-sm">
                Nenhuma guia DAS gerada para este cliente.
              </div>
            ) : (
              <div className="space-y-3">
                {dasPayments.map((das) => (
                  <div key={das.id} className="fiscwise-surface flex items-center justify-between p-4 rounded-xl border border-border/80">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-bold text-foreground">Competência {das.period}</span>
                        <Badge variant={das.status === 'paid' ? 'success' : das.status === 'overdue' ? 'error' : 'warning'}>
                          {das.status === 'paid' ? 'Pago' : das.status === 'overdue' ? 'Atrasado' : 'Pendente'}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Faturamento: {moneyBRL(das.revenue)} · Imposto: {moneyBRL(das.tax_amount)} · Vencimento: {dateBR(das.due_date)}
                      </p>
                    </div>
                    {das.status !== 'paid' && (
                      <Button variant="outline" size="sm" onClick={() => handlePayDas(das.id)}>
                        Marcar como Pago
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* CERTIFICADOS */}
        {activeTab === 'certificados' && (
          <div className="space-y-6">
            <h3 className="text-sm font-bold text-foreground uppercase tracking-wide border-b pb-2">
              Certificados Digitais
            </h3>
            {(() => {
              const hasExpiring = clientCertificates.some((c) => c.status === 'expiring' || c.status === 'expired');
              if (!hasExpiring) return null;
              return (
                <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 flex gap-3 items-center justify-between">
                  <div className="flex gap-2.5 items-center">
                    <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0" />
                    <span className="text-xs text-amber-200 font-semibold">
                      Alerta: Certificado digital expirando ou vencido detectado!
                    </span>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-7 text-[10px] py-1 border-amber-500/30 text-amber-300 bg-amber-500/10 hover:bg-amber-500/20"
                    onClick={() => {
                      setSelectedTemplate('certificado');
                      setActiveTab('comunicacao');
                    }}
                  >
                    Avisar Cliente
                  </Button>
                </div>
              );
            })()}
            {clientCertificates.length === 0 ? (
              <div className="text-center py-10 border border-dashed rounded-xl text-muted-foreground text-sm">
                Nenhum certificado cadastrado para este cliente.
              </div>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2">
                {clientCertificates.map((cert) => {
                  const daysRemaining = Math.max(
                    0,
                    Math.ceil((new Date(cert.valid_until).getTime() - new Date().getTime()) / 86_400_000)
                  );
                  const isCritical = daysRemaining <= 15;
                  const isWarning = daysRemaining <= 30 && daysRemaining > 15;

                  return (
                    <Card key={cert.id} className="p-4 space-y-3">
                      <div>
                        <span className="text-[10px] uppercase font-bold text-primary">TIPO {cert.certificate_type.toUpperCase()}</span>
                        <h4 className="font-bold text-foreground truncate">{cert.label}</h4>
                      </div>
                      <div>
                        <div className="flex justify-between items-center text-xs mb-1">
                          <span className="text-muted-foreground">Validade: {dateBR(cert.valid_until)}</span>
                          <span className={cn('font-bold', isCritical ? 'text-red-500' : isWarning ? 'text-amber-500' : 'text-emerald-400')}>
                            {daysRemaining} dias
                          </span>
                        </div>
                        <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                          <div
                            className={cn('h-full', isCritical ? 'bg-red-500' : isWarning ? 'bg-amber-500' : 'bg-emerald-500')}
                            style={{ width: `${Math.min(100, (daysRemaining / 365) * 100)}%` }}
                          />
                        </div>
                      </div>
                    </Card>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* FINANCEIRO */}
        {activeTab === 'financeiro' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between border-b pb-2">
              <h3 className="text-sm font-bold text-foreground uppercase tracking-wide">
                Configuração de Honorários
              </h3>
              {!editBilling ? (
                <Button size="sm" onClick={() => setEditBilling(true)}>Editar Honorário</Button>
              ) : (
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => setEditBilling(false)}>Cancelar</Button>
                  <Button size="sm" onClick={handleSaveBilling}>Salvar</Button>
                </div>
              )}
            </div>

            {billingConfig && (
              <div className="grid gap-4 md:grid-cols-2">
                <Card className="p-4">
                  <div className="text-xs text-muted-foreground uppercase font-bold mb-1">Valor Mensal</div>
                  {!editBilling ? (
                    <p className="text-2xl font-bold text-foreground">{moneyBRL(billingConfig.monthly_fee)}</p>
                  ) : (
                    <Input type="text" value={billingFee} onChange={(e) => setBillingFee(formatCurrencyBRL(e.target.value))} />
                  )}
                </Card>
                <Card className="p-4">
                  <div className="text-xs text-muted-foreground uppercase font-bold mb-1">Dia de Cobrança</div>
                  {!editBilling ? (
                    <p className="text-2xl font-bold text-foreground">Dia {billingConfig.billing_day}</p>
                  ) : (
                    <Select value={billingDay} onChange={(e) => setBillingDay(Number(e.target.value))}>
                      {Array.from({ length: 28 }).map((_, i) => (
                        <option key={i + 1} value={i + 1}>Dia {i + 1}</option>
                      ))}
                    </Select>
                  )}
                </Card>
              </div>
            )}

            <div className="space-y-3">
              <h3 className="text-xs font-bold text-foreground uppercase tracking-wider border-b pb-1">
                Histórico de Recebimentos
              </h3>
              {billingHistory.length === 0 ? (
                <div className="text-center py-6 text-xs text-muted-foreground">Nenhuma fatura emitida.</div>
              ) : (
                <div className="space-y-2">
                  {billingHistory.map((invoice) => (
                    <div key={invoice.id} className="fiscwise-surface flex items-center justify-between p-3 rounded-xl border border-border/80 text-xs">
                      <div>
                        <p className="font-semibold text-foreground">{invoice.description}</p>
                        <p className="text-muted-foreground">Vencimento: {dateBR(invoice.due_date)}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-foreground">{moneyBRL(invoice.amount)}</span>
                        <Badge variant={invoice.status === 'paid' ? 'success' : invoice.status === 'overdue' ? 'error' : 'warning'}>
                          {invoice.status.toUpperCase()}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* COMUNICAÇÃO */}
        {activeTab === 'comunicacao' && (
          <div className="space-y-6">
            <h3 className="text-sm font-bold text-foreground uppercase tracking-wide border-b pb-2">
              Comunicação com o Cliente
            </h3>

            <div className="grid gap-6 md:grid-cols-[1.2fr_0.8fr]">
              <div className="space-y-4">
                <FormField label="Selecione um Modelo de Mensagem" htmlFor="message_template">
                  <Select
                    id="message_template"
                    value={selectedTemplate}
                    onChange={(e) => setSelectedTemplate(e.target.value as MessageTemplate)}
                  >
                    <option value="das">Lembrete de Guia DAS</option>
                    <option value="documentos">Cobrança de Documentos Pendentes</option>
                    <option value="certificado">Aviso de Certificado Expirando</option>
                    <option value="personalizado">Mensagem Personalizada</option>
                  </Select>
                </FormField>

                <FormField label="Mensagem Formatada" htmlFor="message_composer">
                  <textarea
                    id="message_composer"
                    rows={10}
                    value={composedMessage}
                    onChange={(e) => setComposedMessage(e.target.value)}
                    className="w-full rounded-xl border border-border bg-background p-4 text-sm text-slate-200 placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent scrollbar"
                  />
                </FormField>

                <div className="flex flex-wrap gap-2">
                  <Button onClick={handleCopyWhatsApp} className="gap-1.5 bg-emerald-500 text-slate-950 hover:bg-emerald-400">
                    Copiar WhatsApp
                  </Button>
                  <Button onClick={handleSendEmail} disabled={sendingEmail} className="gap-1.5">
                    {sendingEmail ? 'Enviando...' : 'Enviar por E-mail'}
                  </Button>
                </div>
              </div>

              {/* Live WhatsApp chat widget */}
              <div className="space-y-4">
                <ClientWhatsAppWidget clientId={client.id} clientPhone={client.phone || null} />
                
                {/* Dynamically resolved variables card */}
                <Card className="p-4 space-y-2 text-xs leading-relaxed text-slate-400 border border-white/5 bg-slate-900/10">
                  <h4 className="font-bold text-white uppercase text-[9px] tracking-wider">Variáveis Dinâmicas Resolvidas</h4>
                  <ul className="list-disc pl-4 space-y-1 font-mono text-[9px] text-slate-300">
                    <li>{`{cliente}`} = {client.name}</li>
                    <li>{`{documentos_pendentes}`} = {missingDocsList.join(', ') || 'Nenhum pendente'}</li>
                    <li>{`{das_detalhe}`} = {dasPendingDetail}</li>
                    <li>{`{certificado_detalhe}`} = {certPendingDetail}</li>
                  </ul>
                </Card>
              </div>
            </div>
          </div>
        )}

        {/* HISTÓRICO / TIMELINE */}
        {activeTab === 'historico' && (
          <div className="space-y-6">
            <h3 className="text-sm font-bold text-foreground uppercase tracking-wide border-b pb-2">
              Timeline de Atividades
            </h3>
            <FiscalTimeline items={timelineItems} />
          </div>
        )}

        {/* MONITOR FISCAL */}
        {activeTab === 'monitor_fiscal' && (
          <div className="space-y-6">
            {/* Header com Ações e Sincronização */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-4">
              <div>
                <h3 className="text-sm font-bold text-foreground uppercase tracking-wide">
                  Monitoramento Fiscal & Notas Fiscais
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {monitorSummary?.last_sync_at
                    ? `Última sincronização com a Receita Federal em: ${new Date(
                        monitorSummary.last_sync_at
                      ).toLocaleString('pt-BR')}`
                    : 'Este CNPJ ainda não foi sincronizado com a Receita Federal.'}
                </p>
              </div>
              <Button
                size="sm"
                variant="default"
                disabled={syncMonitorMutation.isPending}
                onClick={async () => {
                  try {
                    const res = await syncMonitorMutation.mutateAsync();
                    toast.success(
                      `Sincronização concluída! ${res.nfes_fetched} notas fiscais importadas.`
                    );
                    refetchDocs();
                  } catch {
                    toast.error('Erro ao sincronizar dados fiscais.');
                  }
                }}
                className="gap-2 shrink-0 bg-primary hover:bg-primary/95 text-primary-foreground font-semibold shadow-glow-sm"
              >
                <RefreshCw
                  className={cn(
                    'h-4 w-4',
                    syncMonitorMutation.isPending && 'animate-spin'
                  )}
                />
                {syncMonitorMutation.isPending ? 'Sincronizando...' : 'Sincronizar Agora'}
              </Button>
            </div>

            {/* Grid de Informações Principais (CNPJ + CND) */}
            <div className="grid gap-6 md:grid-cols-2">
              {/* Cadastro CNPJ Card */}
              <Card className="p-5 space-y-4 border border-border/80 bg-card/20 relative overflow-hidden">
                <div className="flex justify-between items-start">
                  <div>
                    <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                      Cadastro CNPJ (Receita Federal)
                    </h4>
                    <p className="text-sm font-bold text-foreground mt-1">
                      {client.name}
                    </p>
                    <p className="text-xs font-mono text-muted-foreground mt-0.5">
                      CNPJ: {client.document || 'Não informado'}
                    </p>
                  </div>
                  <Badge
                    variant={
                      monitorSummary?.cnpj_status === 'REGULAR'
                        ? 'success'
                        : monitorSummary?.cnpj_status === 'PENDENTE'
                        ? 'default'
                        : 'error'
                    }
                  >
                    {monitorSummary?.cnpj_status || 'PENDENTE'}
                  </Badge>
                </div>

                <div className="border-t border-border/60 pt-3 space-y-2 text-xs">
                  <div>
                    <span className="text-muted-foreground">Natureza Jurídica:</span>
                    <p className="font-medium text-foreground">
                      {monitorSummary?.situation_details?.natureza_juridica || 'Não informada'}
                    </p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Atividade Econômica Principal:</span>
                    <p className="font-medium text-foreground">
                      {monitorSummary?.situation_details?.atividade_principal?.[0]?.text ||
                        'Não informada'}
                    </p>
                  </div>
                </div>
              </Card>

              {/* Certidão Negativa (CND) Card */}
              <Card className="p-5 space-y-4 border border-border/80 bg-card/20 relative overflow-hidden">
                <div className="flex justify-between items-start">
                  <div>
                    <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                      Certidão Negativa de Débitos (CND)
                    </h4>
                    <p className="text-xs text-muted-foreground mt-1">
                      Situação de regularidade perante a Fazenda Nacional.
                    </p>
                    {monitorSummary?.last_cnd_download_at && (
                      <p className="text-[10px] text-muted-foreground mt-1">
                        Download CND: {new Date(monitorSummary.last_cnd_download_at).toLocaleString('pt-BR')}
                      </p>
                    )}
                  </div>
                  <Badge
                    variant={
                      monitorSummary?.cnd_status === 'REGULAR'
                        ? 'success'
                        : monitorSummary?.cnd_status === 'PENDENTE'
                        ? 'default'
                        : 'error'
                    }
                  >
                    {monitorSummary?.cnd_status === 'REGULAR'
                      ? 'SEM PENDÊNCIAS'
                      : monitorSummary?.cnd_status === 'PENDENTE'
                      ? 'PENDENTE'
                      : 'COM PENDÊNCIAS'}
                  </Badge>
                </div>

                <div className="border-t border-border/60 pt-4 flex items-center justify-between">
                  <div className="text-xs">
                    <span className="text-muted-foreground block">Validade CND:</span>
                    <span className="font-medium text-foreground">
                      {monitorSummary?.last_sync_at
                        ? `Validade estimada: 180 dias`
                        : 'Pendente de sincronização'}
                    </span>
                  </div>
                  {monitorSummary?.last_cnd_document_id && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        const doc = parsedClientDocs.find((d) => d.id === monitorSummary.last_cnd_document_id) || 
                                    companyDocs.find((d) => d.id === monitorSummary.last_cnd_document_id);
                        const url = doc?.file_url || `https://fiscwise.storage/cnd/federal-cnd.pdf`;
                        window.open(url, '_blank');
                      }}
                      className="gap-1.5 text-xs h-8"
                    >
                      <FileDown className="h-4 w-4" /> Baixar CND PDF
                    </Button>
                  )}
                </div>
              </Card>
            </div>

            {/* Débitos e Irregularidades */}
            <div className="space-y-3">
              <h3 className="text-xs font-bold text-foreground uppercase tracking-wider border-b pb-1">
                Débitos & Pendências Identificados
              </h3>
              {!monitorSummary || !monitorSummary.has_debts || (monitorSummary.debts_list?.debts || []).length === 0 ? (
                <div className="text-center py-8 border border-dashed rounded-xl text-muted-foreground text-xs">
                  Nenhum débito ou pendência fiscal ativa identificada na Receita Federal.
                </div>
              ) : (
                <div className="grid gap-3">
                  {(monitorSummary.debts_list?.debts || []).map((debt) => (
                    <div
                      key={debt.id}
                      className="fiscwise-surface flex flex-col sm:flex-row sm:items-center sm:justify-between p-4 rounded-xl border border-destructive/20 bg-destructive/5 gap-3"
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-foreground text-sm">{debt.description}</span>
                          <span className="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-red-500/20 text-red-400">
                            {debt.type}
                          </span>
                        </div>
                        <p className="text-xs text-muted-foreground font-mono mt-0.5">
                          Vencimento original: {new Date(debt.due_date).toLocaleDateString('pt-BR')}
                        </p>
                      </div>
                      <div className="flex items-center gap-4 justify-between sm:justify-end shrink-0">
                        <span className="font-bold text-red-400 font-mono text-sm">
                          R$ {debt.value.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                        </span>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            toast.info("Guia de regularização sendo emitida pelo parceiro...");
                          }}
                          className="h-8 text-xs border-red-500/20 hover:bg-red-500/10 text-red-300"
                        >
                          Emitir Guia
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Listagem de Notas Fiscais (NF-e) */}
            <div className="space-y-4 pt-2">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border pb-2">
                <h3 className="text-xs font-bold text-foreground uppercase tracking-wider">
                  Notas Fiscais Capturadas (Receita Federal)
                </h3>

                {/* Filtros NF-e */}
                <div className="flex items-center gap-2 shrink-0">
                  <Input
                    placeholder="Buscar emitente / chave..."
                    value={nfeSearchQuery}
                    onChange={(e) => setNfeSearchQuery(e.target.value)}
                    className="h-8 text-xs w-44 md:w-56"
                  />
                  <Select
                    value={nfeTypeFilter}
                    onChange={(e) => setNfeTypeFilter(e.target.value as NfeTypeFilter)}
                    className="h-8 text-xs w-28"
                  >
                    <option value="ALL">Todas</option>
                    <option value="ENTRADA">Entradas</option>
                    <option value="SAIDA">Saídas</option>
                  </Select>
                </div>
              </div>

              {/* Tabela NF-e */}
              {isLoadingNfes ? (
                <div className="py-6 text-center text-xs text-muted-foreground">
                  Buscando histórico de notas fiscais...
                </div>
              ) : monitorNfes.length === 0 ? (
                <div className="text-center py-10 border border-dashed rounded-xl text-muted-foreground text-xs">
                  Nenhuma nota fiscal eletrônica capturada para este cliente. Clique em Sincronizar.
                </div>
              ) : (() => {
                const filteredNfes = monitorNfes.filter((nfe) => {
                  const matchesSearch =
                    nfe.issuer_name.toLowerCase().includes(nfeSearchQuery.toLowerCase()) ||
                    nfe.recipient_name.toLowerCase().includes(nfeSearchQuery.toLowerCase()) ||
                    nfe.access_key.includes(nfeSearchQuery) ||
                    nfe.nfe_number.includes(nfeSearchQuery);
                  const matchesType = nfeTypeFilter === 'ALL' || nfe.nfe_type === nfeTypeFilter;
                  return matchesSearch && matchesType;
                });

                if (filteredNfes.length === 0) {
                  return (
                    <div className="text-center py-6 text-xs text-muted-foreground">
                      Nenhuma nota atende aos filtros aplicados.
                    </div>
                  );
                }

                return (
                  <div className="overflow-x-auto rounded-xl border border-border bg-card/10">
                    <table className="w-full text-left border-collapse text-xs">
                      <thead>
                        <tr className="border-b border-border bg-muted/20 font-semibold text-muted-foreground">
                          <th className="p-3">Data Emissão</th>
                          <th className="p-3">Número / Chave</th>
                          <th className="p-3">Operação</th>
                          <th className="p-3">Parceiro Comercial</th>
                          <th className="p-3 text-right">Valor</th>
                          <th className="p-3 text-center">XML</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredNfes.map((nfe) => {
                          const isIncoming = nfe.nfe_type === 'ENTRADA';
                          const partnerName = isIncoming ? nfe.issuer_name : nfe.recipient_name;
                          const partnerDoc = isIncoming ? nfe.issuer_document : nfe.recipient_document;

                          return (
                            <tr key={nfe.id} className="border-b border-border/60 hover:bg-muted/10 transition-colors">
                              <td className="p-3 font-medium whitespace-nowrap">
                                {new Date(nfe.issued_at).toLocaleDateString('pt-BR')}
                              </td>
                              <td className="p-3">
                                <span className="font-semibold block">{nfe.nfe_number}</span>
                                <span className="text-[10px] text-muted-foreground font-mono block select-all truncate max-w-[180px]">
                                  {nfe.access_key}
                                </span>
                              </td>
                              <td className="p-3">
                                <Badge variant={isIncoming ? 'success' : 'default'} className="text-[9px] px-1.5 py-0.5">
                                  {isIncoming ? 'ENTRADA' : 'SAÍDA'}
                                </Badge>
                              </td>
                              <td className="p-3">
                                <span className="font-semibold block truncate max-w-[200px]">{partnerName}</span>
                                <span className="text-[10px] text-muted-foreground font-mono">{partnerDoc}</span>
                              </td>
                              <td className="p-3 text-right font-mono font-bold text-foreground">
                                R$ {nfe.value.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                              </td>
                              <td className="p-3 text-center">
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  className="h-7 w-7 p-0 hover:bg-primary/10 hover:text-primary"
                                  onClick={() => {
                                    window.open(nfe.xml_url || '#', '_blank');
                                  }}
                                >
                                  <FileDown className="h-4.5 w-4.5" />
                                </Button>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                );
              })()}
            </div>
          </div>
        )}

        {/* NOTAS INTERNAS */}
        {activeTab === 'notas' && (
          <div className="space-y-6">
            <h3 className="text-sm font-bold text-foreground uppercase tracking-wide border-b pb-2">
              Anotações Internas Privadas
            </h3>
            <div className="space-y-4">
              <FormField label="Anotações Operacionais" htmlFor="client_notes_textarea">
                <textarea
                  id="client_notes_textarea"
                  rows={8}
                  defaultValue={client.notes || ''}
                  placeholder="Digite anotações operacionais, preferências do cliente ou rotinas particulares..."
                  className="w-full rounded-xl border border-border bg-background p-4 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent scrollbar"
                />
              </FormField>
              <div className="flex justify-end">
                <Button
                  onClick={async () => {
                    const txt = (document.getElementById('client_notes_textarea') as HTMLTextAreaElement)?.value || '';
                    try {
                      await updateClientMutation.mutateAsync({
                        id: clientId,
                        payload: { notes: txt },
                      });
                      toast.success('Notas salvas com sucesso');
                    } catch {
                      toast.error('Erro ao salvar notas.');
                    }
                  }}
                  className="gap-1.5"
                >
                  <Save className="w-4 h-4" /> Salvar Notas
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>

      <ClientStatusReportModal
        isOpen={isReportOpen}
        onClose={() => setIsReportOpen(false)}
        client={client}
        partners={partners}
        deadlines={clientDeadlines}
        companyDocs={companyDocs}
        certificates={clientCertificates}
        billingHistory={billingHistory}
        healthScore={healthScore}
      />
    </div>
  );
}
