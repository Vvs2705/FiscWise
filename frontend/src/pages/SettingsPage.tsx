'use client';
import { useState, useEffect, useRef } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import {
  User,
  Building2,
  CreditCard,
  ShieldCheck,
  Sparkles,
  Check,
  Lock,
  Phone,
  Mail,
  Globe,
  MapPin,
  FileText,
  Eye,
  EyeOff,
  Star,
  Bell,
  Send,
  CheckCircle2,
  XCircle,
  SkipForward,
  Smartphone,
  MailCheck,
  Shield,
  QrCode,
  Plus,
  Trash2,
  Edit3,
  Search,
  HelpCircle,
  BookOpen,
  Code2,
  Key,
  Copy,
  CheckCheck,
  RefreshCw,
  AlertCircle,
  Activity,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { getApiErrorMessage } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { FormField } from '@/components/ui/FormField';
import { useAuthStore } from '@/stores/authStore';
import {
  fetchTenant,
  updateProfile,
  updateTenant,
  changePassword,
  get2FAStatus,
  setup2FA,
  enableTOTP2FA,
  initiateEmail2FA,
  confirmEmail2FA,
  disable2FA,
  type TenantData,
  type TwoFAStatus,
  type Setup2FAResponse,
} from '@/lib/auth';
import { useSubscriptionUsage, useAvailablePlans, type Plan } from '@/lib/hooks/useSubscription';
import { useSubscription } from '@/lib/hooks/useBilling';
import { UpgradePlanoModal } from '@/features/subscription/components/UpgradePlanoModal';
import {
  useNotificationMessages,
  useNotificationStats,
  useTriggerPendingDocNotifications,
} from '@/lib/hooks/useNotifications';
import {
  useRagDocuments,
  useCreateRagDocument,
  useUpdateRagDocument,
  useDeleteRagDocument,
  type RagDocument,
} from '@/lib/hooks/useRagFiscal';
import {
  useApiKeys,
  useCreateApiKey,
  useRevokeApiKey,
  useWebhooks,
  useCreateWebhook,
  useUpdateWebhook,
  useDeleteWebhook,
  useWebhookDeliveryLogs,
  useAvailableWebhookEvents,
  type ApiKeyCreated,
  type WebhookSubscriptionCreated,
} from '@/lib/hooks/useDeveloper';

// ─── Schemas ────────────────────────────────────────────────────────────────

const profileSchema = z.object({
  full_name: z.string().min(2, 'Nome deve ter ao menos 2 caracteres'),
  phone: z.string().optional(),
});

const tenantSchema = z.object({
  name: z.string().min(2, 'Nome deve ter ao menos 2 caracteres'),
  document: z.string().optional(),
  phone: z.string().optional(),
  address: z.string().optional(),
  website: z.string().optional(),
});

const passwordSchema = z
  .object({
    current_password: z.string().min(1, 'Informe a senha atual'),
    new_password: z.string().min(8, 'Nova senha deve ter ao menos 8 caracteres'),
    confirm_password: z.string().min(1, 'Confirme a nova senha'),
  })
  .refine((d) => d.new_password === d.confirm_password, {
    message: 'As senhas não coincidem',
    path: ['confirm_password'],
  });

type ProfileValues = z.infer<typeof profileSchema>;
type TenantValues = z.infer<typeof tenantSchema>;
type PasswordValues = z.infer<typeof passwordSchema>;

// ─── Plans config ───────────────────────────────────────────────────────────

const PLANS = [
  {
    slug: 'free',
    label: 'Gratuito',
    price: 'Grátis',
    color: 'text-muted-foreground',
    features: ['Até 10 clientes', '2 usuários', 'Calculadora fiscal', 'Documentos e prazos', 'Suporte por e-mail'],
  },
  {
    slug: 'intermediario',
    label: 'Intermediário',
    price: 'R$ 149/mês',
    color: 'text-primary',
    popular: true,
    features: ['Até 80 clientes', '5 usuários', 'IA Fiscal (20 msgs/mês)', 'Motor de obrigações', 'Portal do cliente', 'Suporte prioritário'],
  },
  {
    slug: 'premium',
    label: 'Premium',
    price: 'R$ 299/mês',
    color: 'text-warning',
    features: ['Clientes ilimitados', 'Usuários ilimitados', 'IA Fiscal ilimitada', 'Export PDF', 'Todas as funcionalidades', 'Suporte dedicado'],
  },
];

// ─── Tab config ──────────────────────────────────────────────────────────────

const TABS = [
  { id: 'perfil',            label: 'Perfil',              icon: User },
  { id: 'escritorio',        label: 'Escritório',           icon: Building2 },
  { id: 'plano',             label: 'Plano',                icon: Sparkles },
  { id: 'base_conhecimento', label: 'Base de Conhecimento', icon: FileText },
  { id: 'seguranca',         label: 'Segurança',            icon: ShieldCheck },
  { id: 'pagamento',         label: 'Pagamento',            icon: CreditCard },
  { id: 'notificacoes',      label: 'Notificações',         icon: Bell },
  { id: 'desenvolvedor',     label: 'Desenvolvedor',        icon: Code2 },
] as const;

type TabId = (typeof TABS)[number]['id'];

// ─── Main component ──────────────────────────────────────────────────────────

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabId>('perfil');
  const { user, updateUser } = useAuthStore();
  const [tenant, setTenant] = useState<TenantData | null>(null);
  const [loadingTenant, setLoadingTenant] = useState(true);

  useEffect(() => {
    fetchTenant()
      .then(setTenant)
      .catch((err) => toast.error(getApiErrorMessage(err, 'Erro ao carregar dados da empresa.')))
      .finally(() => setLoadingTenant(false));
  }, []);

  const currentPlan = PLANS.find((p) => p.slug === (tenant?.plan_slug ?? 'free')) ?? PLANS[0];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold md:text-3xl">Configurações</h1>
        <p className="text-muted-foreground">
          Gerencie perfil, escritório, plano e preferências.
        </p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 overflow-x-auto rounded-xl border bg-muted/40 p-1">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setActiveTab(id)}
            className={cn(
              'flex flex-shrink-0 items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-150',
              activeTab === id
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            <Icon className="h-4 w-4" />
            <span className="hidden sm:inline">{label}</span>
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="animate-fade-in">
        {activeTab === 'perfil' && (
          <ProfileTab user={user} onSave={(data) => {
            updateUser({ full_name: data.full_name, phone: data.phone });
          }} />
        )}
        {activeTab === 'escritorio' && (
          <TenantTab
            tenant={tenant}
            loading={loadingTenant}
            onSave={setTenant}
          />
        )}
        {activeTab === 'plano' && (
          <PlanoTab currentPlan={currentPlan} tenant={tenant} />
        )}
        {activeTab === 'seguranca' && <SegurancaTab />}
        {activeTab === 'base_conhecimento' && (
          <BaseConhecimentoTab
            tenant={tenant}
            onNavigateToPlans={() => setActiveTab('plano')}
          />
        )}
        {activeTab === 'pagamento' && <PagamentoTab onNavigateToPlans={() => setActiveTab('plano')} />}
        {activeTab === 'notificacoes' && <NotificacoesTab />}
        {activeTab === 'desenvolvedor' && <DesenvolvedorTab />}
      </div>
    </div>
  );
}

// ─── Perfil tab ───────────────────────────────────────────────────────────────

function ProfileTab({
  user,
  onSave,
}: {
  user: { id: string; email: string; full_name: string; phone?: string; role: string } | null;
  onSave: (data: ProfileValues) => void;
}) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting, isDirty },
    reset,
  } = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: { full_name: user?.full_name ?? '', phone: user?.phone ?? '' },
  });

  async function onSubmit(values: ProfileValues) {
    try {
      const updated = await updateProfile(values);
      onSave(values);
      reset(values);
      toast.success('Perfil atualizado');
      return updated;
    } catch {
      toast.error('Erro ao atualizar perfil');
    }
  }

  const initials = user?.full_name
    ? user.full_name.split(' ').slice(0, 2).map((n) => n[0]).join('').toUpperCase()
    : '??';

  return (
    <div className="space-y-6">
      {/* Avatar + identity */}
      <Card>
        <CardContent className="flex items-center gap-5 pt-6">
          <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-primary/10 text-2xl font-bold text-primary">
            {initials}
          </div>
          <div>
            <p className="text-lg font-semibold">{user?.full_name || '—'}</p>
            <p className="text-sm text-muted-foreground">{user?.email}</p>
            <Badge className="mt-1">{user?.role}</Badge>
          </div>
        </CardContent>
      </Card>

      {/* Edit form */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Dados pessoais</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
            <FormField label="Nome completo" htmlFor="full_name" error={errors.full_name?.message} required>
              <div className="relative">
                <User className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input id="full_name" className="pl-9" placeholder="João Silva" {...register('full_name')} />
              </div>
            </FormField>

            <FormField label="E-mail" htmlFor="email_display">
              <div className="relative">
                <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="email_display"
                  className="pl-9 cursor-not-allowed opacity-60"
                  value={user?.email ?? ''}
                  readOnly
                  tabIndex={-1}
                />
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                O e-mail não pode ser alterado por aqui. Entre em contato com o suporte.
              </p>
            </FormField>

            <FormField label="Telefone" htmlFor="phone" error={errors.phone?.message}>
              <div className="relative">
                <Phone className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input id="phone" className="pl-9" placeholder="(11) 99999-9999" {...register('phone')} />
              </div>
            </FormField>

            <div className="flex justify-end pt-2">
              <Button type="submit" disabled={isSubmitting || !isDirty}>
                {isSubmitting ? 'Salvando...' : 'Salvar alterações'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Escritório tab ───────────────────────────────────────────────────────────

function TenantTab({
  tenant,
  loading,
  onSave,
}: {
  tenant: TenantData | null;
  loading: boolean;
  onSave: (t: TenantData) => void;
}) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting, isDirty },
    reset,
  } = useForm<TenantValues>({
    resolver: zodResolver(tenantSchema),
    defaultValues: {
      name: tenant?.name ?? '',
      document: tenant?.document ?? '',
      phone: tenant?.phone ?? '',
      address: tenant?.address ?? '',
      website: tenant?.website ?? '',
    },
  });

  // Reset form when tenant loads
  useEffect(() => {
    if (tenant) {
      reset({
        name: tenant.name ?? '',
        document: tenant.document ?? '',
        phone: tenant.phone ?? '',
        address: tenant.address ?? '',
        website: tenant.website ?? '',
      });
    }
  }, [tenant, reset]);

  async function onSubmit(values: TenantValues) {
    try {
      const updated = await updateTenant(values);
      onSave(updated);
      reset(values);
      toast.success('Dados do escritório atualizados');
    } catch {
      toast.error('Erro ao atualizar escritório');
    }
  }

  if (loading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="skeleton h-10 w-full rounded-md" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Dados do escritório</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <FormField label="Razão social / Nome" htmlFor="t_name" error={errors.name?.message} required>
            <div className="relative">
              <Building2 className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input id="t_name" className="pl-9" placeholder="Contabilidade Silva & Associados" {...register('name')} />
            </div>
          </FormField>

          <FormField label="CNPJ / CPF" htmlFor="t_document" error={errors.document?.message}>
            <div className="relative">
              <FileText className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input id="t_document" className="pl-9" placeholder="12.345.678/0001-90" {...register('document')} />
            </div>
          </FormField>

          <div className="grid gap-4 sm:grid-cols-2">
            <FormField label="Telefone comercial" htmlFor="t_phone" error={errors.phone?.message}>
              <div className="relative">
                <Phone className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input id="t_phone" className="pl-9" placeholder="(11) 3333-3333" {...register('phone')} />
              </div>
            </FormField>

            <FormField label="Site" htmlFor="t_website" error={errors.website?.message}>
              <div className="relative">
                <Globe className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input id="t_website" className="pl-9" placeholder="www.escritorio.com.br" {...register('website')} />
              </div>
            </FormField>
          </div>

          <FormField label="Endereço" htmlFor="t_address" error={errors.address?.message}>
            <div className="relative">
              <MapPin className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input id="t_address" className="pl-9" placeholder="Rua das Flores, 123 — São Paulo, SP" {...register('address')} />
            </div>
          </FormField>

          <div className="flex justify-end pt-2">
            <Button type="submit" disabled={isSubmitting || !isDirty}>
              {isSubmitting ? 'Salvando...' : 'Salvar alterações'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

// ─── Plano tab ────────────────────────────────────────────────────────────────

function UsageBar({ label, used, limit }: { label: string; used: number; limit: number | null }) {
  const pct = limit ? Math.min((used / limit) * 100, 100) : 0;
  const isNearLimit = limit && pct >= 80;
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className={isNearLimit ? 'font-semibold text-warning' : 'text-muted-foreground'}>
          {used} / {limit === null ? '∞' : limit}
        </span>
      </div>
      {limit !== null && (
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
          <div
            className={`h-full rounded-full transition-all duration-500 ${pct >= 90 ? 'bg-destructive' : pct >= 70 ? 'bg-warning' : 'bg-primary'}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      )}
    </div>
  );
}

function PlanoTab({
  currentPlan,
  tenant,
}: {
  currentPlan: (typeof PLANS)[number];
  tenant: TenantData | null;
}) {
  const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null);
  const { data: usage } = useSubscriptionUsage();
  const { data: dbPlans, isLoading: loadingPlans } = useAvailablePlans();

  const statusLabel: Record<string, string> = {
    trial: 'Trial',
    active: 'Ativo',
    suspended: 'Suspenso',
    cancelled: 'Cancelado',
    expired: 'Expirado',
  };

  const statusTone: Record<string, 'warning' | 'success' | 'error' | 'default'> = {
    trial: 'warning',
    active: 'success',
    suspended: 'error',
    cancelled: 'default',
    expired: 'default',
  };

  const planMeta: Record<string, { color: string; popular?: boolean; features: string[] }> = {
    free: {
      color: 'text-muted-foreground',
      features: ['Até 10 clientes', '2 usuários', 'Calculadora fiscal', 'Documentos e prazos', 'Suporte por e-mail'],
    },
    intermediario: {
      color: 'text-primary',
      popular: true,
      features: ['Até 80 clientes', '5 usuários', 'IA Fiscal (20 msgs/mês)', 'Motor de obrigações', 'Portal do cliente', 'Suporte prioritário'],
    },
    premium: {
      color: 'text-warning',
      features: ['Clientes ilimitados', 'Usuários ilimitados', 'IA Fiscal ilimitada', 'Export PDF', 'Todas as funcionalidades', 'Suporte dedicado'],
    },
  };

  const activeDbPlan = dbPlans?.find((plan) => plan.slug === currentPlan.slug) ?? null;

  function getPlanFeatures(plan: Plan) {
    const meta = planMeta[plan.slug];
    if (meta) return meta.features;
    return [
      plan.max_clients ? `Até ${plan.max_clients} clientes` : 'Clientes ilimitados',
      plan.max_users ? `Até ${plan.max_users} usuários` : 'Usuários ilimitados',
      plan.max_ai_calls_month ? `${plan.max_ai_calls_month} mensagens IA/mês` : 'IA conforme configuração do plano',
    ];
  }

  function getPlanPrice(plan: Plan) {
    return plan.price_monthly === 0 || plan.price_monthly === null
      ? 'Grátis'
      : `R$ ${Number(plan.price_monthly).toLocaleString('pt-BR')}/mês`;
  }

  function getPlanIntent(plan: Plan) {
    if (plan.slug === currentPlan.slug) return 'current';
    if (plan.price_monthly === null || activeDbPlan === null || activeDbPlan.price_monthly === null) {
      return 'change';
    }
    return plan.price_monthly > activeDbPlan.price_monthly ? 'upgrade' : 'downgrade';
  }

  const planCtas: Record<string, string> = {
    current: 'Plano atual',
    upgrade: 'Fazer upgrade',
    downgrade: 'Migrar para este plano',
    change: 'Selecionar plano',
  };

  const nearLimitItems = usage
    ? [
        usage.clients.limit !== null && usage.clients.percent !== null && usage.clients.percent >= 80
          ? `Clientes ativos em ${Math.round(usage.clients.percent)}% da capacidade`
          : null,
        usage.users.limit !== null && usage.users.percent !== null && usage.users.percent >= 80
          ? `Usuários em ${Math.round(usage.users.percent)}% da capacidade`
          : null,
        usage.ai_calls_this_month.limit !== null && usage.ai_calls_this_month.percent !== null && usage.ai_calls_this_month.percent >= 80
          ? `Mensagens de IA em ${Math.round(usage.ai_calls_this_month.percent)}% da capacidade`
          : null,
      ].filter(Boolean)
    : [];

  if (loadingPlans) {
    return (
      <div className="flex h-48 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Current plan summary */}
      <Card className="border-primary/30 bg-primary/5">
        <CardContent className="flex items-center justify-between gap-4 pt-6">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Plano atual</p>
            <p className="mt-0.5 text-2xl font-bold">{currentPlan.label}</p>
            <p className="text-sm text-muted-foreground">{currentPlan.price}</p>
          </div>
          <div className="text-right">
            <Badge variant={statusTone[tenant?.subscription_status ?? 'trial'] ?? 'warning'}>
              {statusLabel[tenant?.subscription_status ?? 'trial'] ?? 'Trial'}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Usage metrics */}
      {usage && (
        <Card className="border-border/60 bg-card">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold">Uso do plano este mês</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <UsageBar label="Clientes ativos" used={usage.clients.used} limit={usage.clients.limit} />
            <UsageBar label="Usuários" used={usage.users.used} limit={usage.users.limit} />
            {usage.ai_calls_this_month.limit !== 0 && (
              <UsageBar label="Mensagens IA" used={usage.ai_calls_this_month.used} limit={usage.ai_calls_this_month.limit} />
            )}
          </CardContent>
        </Card>
      )}

      <Card className="border-border/60">
        <CardContent className="grid gap-4 pt-6 lg:grid-cols-[1.4fr,0.8fr]">
          <div className="space-y-2">
            <p className="text-sm font-semibold text-foreground">Próximo passo recomendado</p>
            <p className="text-sm text-muted-foreground">
              {currentPlan.slug === 'free'
                ? 'Ative um plano pago para liberar faturamento recorrente, automações e operação comercial completa.'
                : 'Compare os planos abaixo para ampliar capacidade, liberar mais IA e ajustar o nível de suporte do escritório.'}
            </p>
            {nearLimitItems.length > 0 && (
              <div className="rounded-lg border border-warning/20 bg-warning/5 p-3 text-sm text-warning">
                {nearLimitItems.map((item) => (
                  <p key={item}>{item}</p>
                ))}
              </div>
            )}
          </div>
          <div className="rounded-xl border bg-muted/30 p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Fluxo do upgrade</p>
            <div className="mt-3 space-y-3 text-sm text-muted-foreground">
              <p>1. Escolha o plano com base em capacidade e recursos.</p>
              <p>2. Revise o impacto comercial antes de confirmar.</p>
              <p>3. A assinatura é provisionada e o plano do tenant é atualizado.</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* All plans */}
      <div className="grid gap-4 md:grid-cols-3">
        {(dbPlans || []).map((plan) => {
          const isActive = plan.slug === currentPlan.slug;
          const meta = planMeta[plan.slug] || { color: 'text-foreground', features: getPlanFeatures(plan) };
          const priceDisplay = getPlanPrice(plan);
          const intent = getPlanIntent(plan);
          const aiLabel = plan.max_ai_calls_month === null
            ? 'IA sem limite explícito'
            : plan.max_ai_calls_month === 0
            ? 'Sem franquia de IA'
            : `${plan.max_ai_calls_month} mensagens IA/mês`;

          return (
            <Card
              key={plan.slug}
              className={cn(
                'relative transition-all duration-200',
                isActive ? 'border-primary shadow-token-sm' : 'hover:border-primary/50',
              )}
            >
              {meta.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="flex items-center gap-1 rounded-full bg-primary px-3 py-0.5 text-xs font-semibold text-primary-foreground">
                    <Star className="h-3 w-3" />
                    Popular
                  </span>
                </div>
              )}
              <CardHeader className="pb-3 pt-5">
                <CardTitle className={cn('text-xl', meta.color)}>{plan.name}</CardTitle>
                <p className="text-2xl font-bold">{priceDisplay}</p>
                {plan.description && (
                  <p className="text-sm text-muted-foreground">{plan.description}</p>
                )}
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="rounded-lg bg-muted/40 p-2">
                    <p className="text-muted-foreground">Clientes</p>
                    <p className="mt-1 font-semibold text-foreground">
                      {plan.max_clients === null ? 'Ilimitado' : plan.max_clients}
                    </p>
                  </div>
                  <div className="rounded-lg bg-muted/40 p-2">
                    <p className="text-muted-foreground">Usuários</p>
                    <p className="mt-1 font-semibold text-foreground">
                      {plan.max_users === null ? 'Ilimitado' : plan.max_users}
                    </p>
                  </div>
                </div>
                <div className="rounded-lg border border-dashed px-3 py-2 text-xs text-muted-foreground">
                  {aiLabel}
                </div>
                <ul className="space-y-2">
                  {getPlanFeatures(plan).map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm">
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-success" />
                      {f}
                    </li>
                  ))}
                </ul>
                <Button
                  className="w-full"
                  variant={isActive ? 'outline' : 'default'}
                  disabled={isActive}
                  onClick={() => setSelectedPlan(plan)}
                >
                  {isActive ? 'Plano atual' : planCtas[intent]}
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <p className="text-center text-xs text-muted-foreground">
        Precisa de algo personalizado?{' '}
        <a href="mailto:contato@vstack-solutions.com.br" className="text-primary hover:underline">
          Entre em contato
        </a>
      </p>

      <UpgradePlanoModal
        open={selectedPlan !== null}
        onClose={() => setSelectedPlan(null)}
        selectedPlan={selectedPlan}
      />
    </div>
  );
}

// ─── 2FA OTP Input ────────────────────────────────────────────────────────────
function OtpInput6({ value, onChange, disabled }: {
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
}) {
  const inputs = useRef<(HTMLInputElement | null)[]>([]);
  const digits = (value + '      ').slice(0, 6).split('');

  const handleKey = (idx: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace') {
      e.preventDefault();
      const next = digits.map((d, i) => (i === idx ? ' ' : d)).join('').trimEnd();
      onChange(next.trim());
      if (idx > 0) inputs.current[idx - 1]?.focus();
    }
  };
  const handleChange = (idx: number, e: React.ChangeEvent<HTMLInputElement>) => {
    const ch = e.target.value.replace(/\D/g, '').slice(-1);
    if (!ch) return;
    const next = digits.map((d, i) => (i === idx ? ch : d)).join('').replace(/ /g, '');
    onChange(next.padEnd(6, ' ').trim());
    if (idx < 5) inputs.current[idx + 1]?.focus();
  };
  const handlePaste = (e: React.ClipboardEvent) => {
    const text = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (text.length > 0) { onChange(text); inputs.current[Math.min(text.length, 5)]?.focus(); }
    e.preventDefault();
  };

  return (
    <div className="flex gap-2 justify-center" onPaste={handlePaste}>
      {Array.from({ length: 6 }).map((_, idx) => (
        <input
          key={idx}
          ref={(el) => { inputs.current[idx] = el; }}
          type="text" inputMode="numeric" maxLength={1}
          value={digits[idx]?.trim() ?? ''}
          onChange={(e) => handleChange(idx, e)}
          onKeyDown={(e) => handleKey(idx, e)}
          disabled={disabled}
          className={cn(
            'h-12 w-10 rounded-lg border-2 bg-background text-center text-lg font-bold',
            'text-foreground transition-all outline-none',
            'border-border focus:border-primary focus:ring-2 focus:ring-primary/20',
            disabled && 'cursor-not-allowed opacity-50',
          )}
          aria-label={`Dígito ${idx + 1}`}
        />
      ))}
    </div>
  );
}

// ─── 2FA Card ─────────────────────────────────────────────────────────────────
function TwoFactorCard() {
  const [status, setStatus] = useState<TwoFAStatus | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [mode, setMode] = useState<'idle' | 'choose' | 'setup-totp' | 'setup-email' | 'confirm-email' | 'disable'>('idle');
  const [setupData, setSetupData] = useState<Setup2FAResponse | null>(null);
  const [otpCode, setOtpCode] = useState('');
  const [disablePassword, setDisablePassword] = useState('');
  const [showDisablePass, setShowDisablePass] = useState(false);
  const [busy, setBusy] = useState(false);

  // Load 2FA status on mount
  useEffect(() => {
    get2FAStatus()
      .then(setStatus)
      .catch((err) => toast.error(getApiErrorMessage(err, 'Erro ao carregar status 2FA.')))
      .finally(() => setLoadingStatus(false));
  }, []);

  const refresh = () => {
    setLoadingStatus(true);
    get2FAStatus()
      .then(setStatus)
      .catch((err) => toast.error(getApiErrorMessage(err, 'Erro ao carregar status 2FA.')))
      .finally(() => setLoadingStatus(false));
  };

  const startSetupTotp = async () => {
    setBusy(true);
    try {
      const data = await setup2FA();
      setSetupData(data);
      setOtpCode('');
      setMode('setup-totp');
    } catch { toast.error('Erro ao iniciar configuração 2FA'); }
    finally { setBusy(false); }
  };

  const startSetupEmail = async () => {
    setBusy(true);
    try {
      await initiateEmail2FA();
      setOtpCode('');
      setMode('confirm-email');
      toast('Código enviado para seu e-mail', { icon: '📧' });
    } catch { toast.error('Erro ao enviar código'); }
    finally { setBusy(false); }
  };

  const confirmTotp = async () => {
    if (!setupData) return;
    setBusy(true);
    try {
      await enableTOTP2FA(setupData.secret, otpCode.replace(/\s/g, ''));
      toast.success('2FA ativado! Sua conta está mais segura.');
      setMode('idle'); setOtpCode(''); setSetupData(null);
      refresh();
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } }).response?.data?.detail;
      toast.error(msg ?? 'Código inválido');
    } finally { setBusy(false); }
  };

  const confirmEmail = async () => {
    setBusy(true);
    try {
      await confirmEmail2FA(otpCode.replace(/\s/g, ''));
      toast.success('2FA por e-mail ativado!');
      setMode('idle'); setOtpCode('');
      refresh();
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } }).response?.data?.detail;
      toast.error(msg ?? 'Código inválido ou expirado');
    } finally { setBusy(false); }
  };

  const handleDisable = async () => {
    setBusy(true);
    try {
      await disable2FA(disablePassword);
      toast.success('2FA desativado.');
      setMode('idle'); setDisablePassword('');
      refresh();
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } }).response?.data?.detail;
      toast.error(msg ?? 'Erro ao desativar 2FA');
    } finally { setBusy(false); }
  };

  const cancel = () => { setMode('idle'); setOtpCode(''); setSetupData(null); setDisablePassword(''); };

  if (loadingStatus) return null;

  const enabled = status?.two_factor_enabled ?? false;
  const method = status?.two_factor_method ?? 'none';

  return (
    <Card className={cn(enabled && 'ring-1 ring-success/30')}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className={cn('h-5 w-5', enabled ? 'text-success' : 'text-muted-foreground')} />
            <CardTitle className="text-base">Autenticação de Dois Fatores (2FA)</CardTitle>
          </div>
          {enabled && (
            <Badge className="bg-success/15 text-success border-success/30">
              ✓ Ativo · {method === 'totp' ? 'App Autenticador' : 'E-mail'}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Idle state */}
        {mode === 'idle' && (
          <>
            <p className="text-sm text-muted-foreground">
              {enabled
                ? 'Sua conta está protegida por verificação em duas etapas. A cada login, você precisará confirmar sua identidade com um código adicional.'
                : 'Adicione uma camada extra de segurança. Além da senha, você precisará confirmar um código gerado pelo app ou enviado por e-mail.'}
            </p>
            {enabled ? (
              <Button
                variant="outline"
                size="sm"
                className="text-destructive border-destructive/40 hover:bg-destructive/5"
                onClick={() => setMode('disable')}
              >
                Desativar 2FA
              </Button>
            ) : (
              <Button size="sm" onClick={() => setMode('choose')}>
                Ativar verificação em 2 etapas
              </Button>
            )}
          </>
        )}

        {/* Choose method */}
        {mode === 'choose' && (
          <div className="space-y-3">
            <p className="text-sm font-medium">Escolha o método de verificação:</p>
            <div className="grid gap-3 sm:grid-cols-2">
              <button
                type="button"
                onClick={startSetupTotp}
                disabled={busy}
                className="group flex flex-col gap-2 rounded-xl border-2 border-border p-4 text-left transition-all hover:border-primary hover:bg-primary/5 disabled:opacity-60"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 group-hover:bg-primary/20">
                  <Smartphone className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <p className="font-semibold text-sm">App Autenticador</p>
                  <p className="text-xs text-muted-foreground mt-0.5">Google Authenticator, Microsoft Authenticator, Authy</p>
                </div>
                <Badge variant="success" className="w-fit text-xs">Recomendado</Badge>
              </button>

              <button
                type="button"
                onClick={startSetupEmail}
                disabled={busy}
                className="group flex flex-col gap-2 rounded-xl border-2 border-border p-4 text-left transition-all hover:border-primary hover:bg-primary/5 disabled:opacity-60"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-info/10 group-hover:bg-info/20">
                  <MailCheck className="h-5 w-5 text-info" />
                </div>
                <div>
                  <p className="font-semibold text-sm">E-mail</p>
                  <p className="text-xs text-muted-foreground mt-0.5">Código enviado para seu e-mail a cada login</p>
                </div>
              </button>
            </div>
            <button type="button" onClick={cancel} className="text-xs text-muted-foreground hover:text-foreground">
              Cancelar
            </button>
          </div>
        )}

        {/* TOTP setup */}
        {mode === 'setup-totp' && setupData && (
          <div className="space-y-4">
            <div className="rounded-xl bg-muted/40 p-4 space-y-3">
              <p className="text-sm font-medium flex items-center gap-2"><QrCode className="h-4 w-4" /> Escaneie o QR Code</p>
              <div className="flex justify-center">
                <img
                  src={`data:image/png;base64,${setupData.qr_code_base64}`}
                  alt="QR Code 2FA"
                  className="h-40 w-40 rounded-lg border border-border"
                />
              </div>
              <p className="text-xs text-muted-foreground text-center">
                Ou insira o código manualmente no app:
              </p>
              <div className="flex items-center gap-2 justify-center">
                <code className="rounded bg-muted px-2 py-1 text-xs font-mono tracking-widest">
                  {setupData.secret}
                </code>
              </div>
            </div>
            <div className="space-y-2">
              <p className="text-sm font-medium">Digite o primeiro código gerado pelo app:</p>
              <OtpInput6 value={otpCode} onChange={setOtpCode} disabled={busy} />
            </div>
            <div className="flex gap-2">
              <Button onClick={confirmTotp} disabled={busy || otpCode.replace(/\s/g, '').length !== 6}>
                {busy ? 'Ativando...' : 'Confirmar e ativar'}
              </Button>
              <Button variant="outline" onClick={cancel} disabled={busy}>Cancelar</Button>
            </div>
          </div>
        )}

        {/* Email confirm */}
        {mode === 'confirm-email' && (
          <div className="space-y-4">
            <div className="rounded-xl bg-info/10 border border-info/20 p-4">
              <p className="text-sm text-info">
                📧 Código enviado para seu e-mail. Verifique a caixa de entrada e insira o código abaixo.
              </p>
            </div>
            <div className="space-y-2">
              <p className="text-sm font-medium">Código de verificação:</p>
              <OtpInput6 value={otpCode} onChange={setOtpCode} disabled={busy} />
            </div>
            <div className="flex gap-2">
              <Button onClick={confirmEmail} disabled={busy || otpCode.replace(/\s/g, '').length !== 6}>
                {busy ? 'Confirmando...' : 'Confirmar e ativar'}
              </Button>
              <Button variant="outline" onClick={cancel} disabled={busy}>Cancelar</Button>
            </div>
          </div>
        )}

        {/* Disable 2FA */}
        {mode === 'disable' && (
          <div className="space-y-4">
            <div className="rounded-xl bg-destructive/10 border border-destructive/20 p-4">
              <p className="text-sm text-destructive">
                ⚠️ Ao desativar o 2FA, sua conta ficará protegida apenas pela senha.
              </p>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Confirme sua senha atual:</label>
              <div className="relative max-w-sm">
                <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  type={showDisablePass ? 'text' : 'password'}
                  placeholder="••••••••"
                  value={disablePassword}
                  onChange={(e) => setDisablePassword(e.target.value)}
                  className="pl-9 pr-10"
                  disabled={busy}
                />
                <button
                  type="button"
                  tabIndex={-1}
                  onClick={() => setShowDisablePass(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showDisablePass ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                className="border-destructive/40 text-destructive hover:bg-destructive/5"
                onClick={handleDisable}
                disabled={busy || !disablePassword}
              >
                {busy ? 'Desativando...' : 'Desativar 2FA'}
              </Button>
              <Button variant="outline" onClick={cancel} disabled={busy}>Cancelar</Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Segurança tab ────────────────────────────────────────────────────────────

function SegurancaTab() {
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    reset,
  } = useForm<PasswordValues>({
    resolver: zodResolver(passwordSchema),
  });

  async function onSubmit(values: PasswordValues) {
    try {
      await changePassword({
        current_password: values.current_password,
        new_password: values.new_password,
      });
      toast.success('Senha alterada com sucesso');
      reset();
    } catch (err: unknown) {
      const msg =
        typeof err === 'object' && err !== null && 'response' in err
          ? (err as { response?: { data?: { detail?: unknown } } }).response?.data?.detail
          : undefined;
      toast.error(typeof msg === 'string' ? msg : 'Erro ao alterar senha');
    }
  }

  return (
    <div className="space-y-6">
      {/* 2FA Card — NEW */}
      <TwoFactorCard />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Alterar senha</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 max-w-md" noValidate>
            <FormField label="Senha atual" htmlFor="current_password" error={errors.current_password?.message} required>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="current_password"
                  type={showCurrent ? 'text' : 'password'}
                  className="pl-9 pr-10"
                  placeholder="••••••••"
                  {...register('current_password')}
                />
                <button
                  type="button"
                  tabIndex={-1}
                  onClick={() => setShowCurrent((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  aria-label={showCurrent ? 'Ocultar senha' : 'Mostrar senha'}
                >
                  {showCurrent ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </FormField>

            <FormField label="Nova senha" htmlFor="new_password" error={errors.new_password?.message} required>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="new_password"
                  type={showNew ? 'text' : 'password'}
                  className="pl-9 pr-10"
                  placeholder="••••••••"
                  {...register('new_password')}
                />
                <button
                  type="button"
                  tabIndex={-1}
                  onClick={() => setShowNew((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  aria-label={showNew ? 'Ocultar senha' : 'Mostrar senha'}
                >
                  {showNew ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </FormField>

            <FormField label="Confirmar nova senha" htmlFor="confirm_password" error={errors.confirm_password?.message} required>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="confirm_password"
                  type="password"
                  className="pl-9"
                  placeholder="••••••••"
                  {...register('confirm_password')}
                />
              </div>
            </FormField>

            <div className="flex justify-end pt-2">
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Salvando...' : 'Alterar senha'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Security info cards */}
      <div className="grid gap-4 sm:grid-cols-2">
        <Card className="border-dashed">
          <CardContent className="pt-5">
            <div className="flex items-start gap-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-success/10">
                <ShieldCheck className="h-5 w-5 text-success" />
              </div>
              <div>
                <p className="font-medium">Sessão protegida</p>
                <p className="mt-0.5 text-sm text-muted-foreground">
                  Sua conta usa tokens JWT com expiração automática.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-dashed">
          <CardContent className="pt-5">
            <div className="flex items-start gap-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                <Lock className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="font-medium">Senha criptografada</p>
                <p className="mt-0.5 text-sm text-muted-foreground">
                  Armazenada com bcrypt — nunca em texto simples.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ─── Pagamento tab ────────────────────────────────────────────────────────────

function PagamentoTab({ onNavigateToPlans }: { onNavigateToPlans: () => void }) {
  const { data: subscription, isLoading } = useSubscription();
  const { user } = useAuthStore();

  if (isLoading) {
    return (
      <div className="flex h-48 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  const isOwner = user?.role === 'owner';
  
  const statusColors: Record<string, string> = {
    trialing: 'bg-warning/10 text-warning hover:bg-warning/20',
    active: 'bg-success/10 text-success hover:bg-success/20',
    past_due: 'bg-destructive/10 text-destructive hover:bg-destructive/20',
    suspended: 'bg-destructive/10 text-destructive hover:bg-destructive/20',
    cancelled: 'bg-muted text-muted-foreground hover:bg-muted/80',
  };

  const statusLabel: Record<string, string> = {
    trialing: 'Período de Teste (Trial)',
    active: 'Assinatura Ativa',
    past_due: 'Fatura em Atraso',
    suspended: 'Acesso Suspenso',
    cancelled: 'Cancelada',
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleDateString('pt-BR');
  };

  const amountFormatted = subscription?.amount 
    ? Number(subscription.amount).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
    : '—';

  return (
    <div className="space-y-6">
      {subscription ? (
        <>
          {/* Subscription Status Card */}
          <Card className="border-primary/20 bg-card">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base font-semibold">Assinatura Ativa</CardTitle>
                <Badge className={statusColors[subscription.status] || 'bg-primary/10 text-primary'}>
                  {statusLabel[subscription.status] || subscription.status}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="rounded-lg bg-muted/40 p-3">
                  <p className="text-xs text-muted-foreground">Valor Mensal</p>
                  <p className="mt-1 text-lg font-bold text-foreground">{amountFormatted}</p>
                </div>
                <div className="rounded-lg bg-muted/40 p-3">
                  <p className="text-xs text-muted-foreground">Provedor de Pagamento</p>
                  <p className="mt-1 text-sm font-semibold uppercase text-foreground">
                    {subscription.billing_provider || 'Manual'}
                  </p>
                </div>
                <div className="rounded-lg bg-muted/40 p-3">
                  <p className="text-xs text-muted-foreground">
                    {subscription.status === 'trialing' ? 'Fim do Período de Teste' : 'Próxima Renovação'}
                  </p>
                  <p className="mt-1 text-sm font-semibold text-foreground">
                    {formatDate(subscription.status === 'trialing' ? subscription.trial_ends_at : subscription.current_period_end)}
                  </p>
                </div>
              </div>

              {isOwner && (
                <div className="flex justify-end pt-2">
                  <a
                    href="https://www.asaas.com"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center justify-center rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow transition hover:bg-primary/90"
                  >
                    Gerenciar no Asaas
                  </a>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Formas de pagamento associadas */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Método de Cobrança</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between rounded-lg border border-dashed p-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-md bg-muted">
                    <CreditCard className="h-5 w-5 text-muted-foreground" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-foreground">Cobrança Direta (Asaas)</p>
                    <p className="text-xs text-muted-foreground">As faturas são emitidas via Boleto/Pix direto para o seu e-mail cadastrado.</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </>
      ) : (
        /* Free state view */
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-12 text-center space-y-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
              <Sparkles className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-foreground">Faturamento Desativado (Plano Gratuito)</h3>
              <p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">
                Sua conta atual está no plano Gratuito de testes. Para liberar o faturamento recorrente e outras ferramentas avançadas, faça o upgrade de plano.
              </p>
            </div>
            <p className="text-xs text-muted-foreground">
              Você pode alterar seu plano a qualquer momento na aba de planos.
            </p>
            <Button onClick={onNavigateToPlans}>Comparar planos</Button>
          </CardContent>
        </Card>
      )}

      {/* Histórico de faturas */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Histórico de faturas</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <FileText className="mb-3 h-10 w-10 text-muted-foreground/40" />
            <p className="text-sm font-medium text-muted-foreground">Nenhuma fatura disponível</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Seu histórico de cobranças aparecerá aqui quando as faturas do Asaas forem geradas.
            </p>
          </div>
        </CardContent>
      </Card>

      <p className="text-center text-xs text-muted-foreground">
        Dúvidas sobre cobrança?{' '}
        <a href="mailto:contato@vstack-solutions.com.br" className="text-primary hover:underline">
          faturamento@vstack-solutions.com.br
        </a>
      </p>
    </div>
  );
}

// ─── Notificações tab ─────────────────────────────────────────────────────────

function statusIcon(status: string) {
  if (status === 'sent' || status === 'delivered') return <CheckCircle2 className="h-3.5 w-3.5 text-success" />;
  if (status === 'failed') return <XCircle className="h-3.5 w-3.5 text-destructive" />;
  if (status === 'skipped') return <SkipForward className="h-3.5 w-3.5 text-warning" />;
  return <Send className="h-3.5 w-3.5 text-muted-foreground" />;
}

function statusLabel(status: string) {
  if (status === 'sent') return 'Enviado';
  if (status === 'delivered') return 'Entregue';
  if (status === 'failed') return 'Falha';
  if (status === 'skipped') return 'Ignorado';
  return 'Pendente';
}

function NotificacoesTab() {
  const { data: stats, isLoading: loadingStats } = useNotificationStats();
  const { data: messages, isLoading: loadingMessages } = useNotificationMessages(30);
  const trigger = useTriggerPendingDocNotifications();
  const [result, setResult] = useState<null | { sent: number; skipped: number; failed: number; clients_notified: number; competence_month: string }>(null);

  async function handleTrigger() {
    try {
      const res = await trigger.mutateAsync(undefined);
      setResult(res);
      toast.success(`Notificações disparadas — ${res.clients_notified} cliente(s) processados`);
    } catch {
      toast.error('Não foi possível disparar as notificações. Tente novamente.');
    }
  }

  return (
    <div className="space-y-6">
      {/* Stats */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Estatísticas (últimos 30 dias)</CardTitle>
        </CardHeader>
        <CardContent>
          {loadingStats ? (
            <p className="text-sm text-muted-foreground">Carregando...</p>
          ) : (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {[
                { label: 'Enviados', value: stats?.sent ?? 0, color: 'text-success' },
                { label: 'Ignorados', value: stats?.skipped ?? 0, color: 'text-warning' },
                { label: 'Falhas', value: stats?.failed ?? 0, color: 'text-destructive' },
                { label: 'Total', value: stats?.total ?? 0, color: 'text-foreground' },
              ].map((s) => (
                <div key={s.label} className="rounded-lg border p-3 text-center">
                  <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">{s.label}</p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Manual trigger */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Disparar notificação manual</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Envia e-mails de cobrança de documentos pendentes para todos os clientes do mês atual.
            O sistema dispara automaticamente toda segunda-feira às 09h.
          </p>

          {result && (
            <div className="rounded-lg border border-success/20 bg-success/5 p-3 text-sm">
              <p className="font-medium text-success">
                Resultado: {result.clients_notified} cliente(s) processados
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Enviados: {result.sent} · Ignorados: {result.skipped} · Falhas: {result.failed}
              </p>
              {result.sent === 0 && result.skipped > 0 && (
                <p className="mt-1 text-xs text-warning">
                  Mensagens registradas como "ignoradas" — configure EMAIL_PROVIDER no servidor para envio real.
                </p>
              )}
            </div>
          )}

          <Button
            onClick={handleTrigger}
            disabled={trigger.isPending}
            className="gap-2"
          >
            <Send className="h-4 w-4" />
            {trigger.isPending ? 'Disparando...' : 'Disparar agora'}
          </Button>
        </CardContent>
      </Card>

      {/* Recent messages */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Mensagens recentes</CardTitle>
        </CardHeader>
        <CardContent>
          {loadingMessages ? (
            <p className="text-sm text-muted-foreground">Carregando...</p>
          ) : !messages || messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <Bell className="mb-3 h-10 w-10 text-muted-foreground/40" />
              <p className="text-sm font-medium text-muted-foreground">Nenhuma notificação enviada ainda</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Use o botão acima ou aguarde o disparo automático de segunda-feira.
              </p>
            </div>
          ) : (
            <div className="divide-y">
              {messages.map((msg) => (
                <div key={msg.id} className="flex items-start gap-3 py-3">
                  <div className="mt-0.5 shrink-0">{statusIcon(msg.status)}</div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{msg.recipient}</p>
                    {msg.subject && (
                      <p className="truncate text-xs text-muted-foreground">{msg.subject}</p>
                    )}
                  </div>
                  <div className="shrink-0 text-right">
                    <span className="text-xs text-muted-foreground">{statusLabel(msg.status)}</span>
                    <p className="text-[10px] text-muted-foreground/60">
                      {new Date(msg.created_at).toLocaleDateString('pt-BR')}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Base de Conhecimento Tab (RAG Fiscal) ────────────────────────────────────

function BaseConhecimentoTab({
  tenant,
  onNavigateToPlans,
}: {
  tenant: TenantData | null;
  onNavigateToPlans: () => void;
}) {
  const isFree = tenant?.plan_slug === 'free' || !tenant?.plan_slug;

  const { data: documents, isLoading } = useRagDocuments();
  const createMutation = useCreateRagDocument();
  const updateMutation = useUpdateRagDocument();
  const deleteMutation = useDeleteRagDocument();

  // Search & Filter state
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('todos');

  // Form state
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingDoc, setEditingDoc] = useState<RagDocument | null>(null);

  // Form Fields
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [source, setSource] = useState('');
  const [category, setCategory] = useState('procedimento');
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Expanded document IDs
  const [expandedIds, setExpandedIds] = useState<Record<string, boolean>>({});

  // Setup form for editing
  const handleEditClick = (doc: RagDocument) => {
    setEditingDoc(doc);
    setTitle(doc.title);
    setContent(doc.content);
    setSource(doc.source);
    setCategory(doc.category);
    setErrors({});
    setIsFormOpen(true);
  };

  // Reset form
  const handleCancel = () => {
    setIsFormOpen(false);
    setEditingDoc(null);
    setTitle('');
    setContent('');
    setSource('');
    setCategory('procedimento');
    setErrors({});
  };

  const handleOpenCreate = () => {
    setEditingDoc(null);
    setTitle('');
    setContent('');
    setSource('Procedimento Interno');
    setCategory('procedimento');
    setErrors({});
    setIsFormOpen(true);
  };

  // Form validation
  const validateForm = () => {
    const newErrors: Record<string, string> = {};
    if (!title.trim() || title.length < 2) {
      newErrors.title = 'O título deve ter no mínimo 2 caracteres.';
    }
    if (title.length > 255) {
      newErrors.title = 'O título não pode exceder 255 caracteres.';
    }
    if (!content.trim() || content.length < 10) {
      newErrors.content = 'O conteúdo deve descrever a regra/faq com no mínimo 10 caracteres.';
    }
    if (source.length > 255) {
      newErrors.source = 'A fonte não pode exceder 255 caracteres.';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Form submit
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;

    const payload = {
      title: title.trim(),
      content: content.trim(),
      source: source.trim() || 'Procedimento Interno',
      category,
    };

    try {
      if (editingDoc) {
        await updateMutation.mutateAsync({ id: editingDoc.id, payload });
        toast.success('Documento atualizado com sucesso');
      } else {
        await createMutation.mutateAsync(payload);
        toast.success('Documento adicionado à base RAG');
      }
      handleCancel();
    } catch {
      toast.error('Erro ao salvar documento na base RAG');
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Deseja realmente excluir permanentemente esta regra da base de conhecimento? A IA do escritório deixará de usá-la.')) {
      return;
    }
    try {
      await deleteMutation.mutateAsync(id);
      toast.success('Documento excluído da base');
    } catch {
      toast.error('Erro ao excluir documento');
    }
  };

  const toggleExpand = (id: string) => {
    setExpandedIds(prev => ({ ...prev, [id]: !prev[id] }));
  };

  if (isFree) {
    return (
      <Card className="border-primary/20 bg-gradient-to-br from-primary/5 via-background to-background p-8 text-center">
        <CardContent className="flex flex-col items-center justify-center space-y-4 py-8">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Lock className="h-8 w-8" />
          </div>
          <h2 className="text-xl font-bold">Base de Conhecimento RAG com IA</h2>
          <p className="max-w-md text-sm text-muted-foreground">
            Alimente o cérebro da IA fiscal do seu escritório com regras, FAQs e procedimentos próprios. Quando você fizer perguntas na calculadora com IA, ela responderá baseada prioritariamente nas diretrizes do seu escritório, citando fontes e confiança!
          </p>
          <div className="rounded-lg border border-warning/20 bg-warning/5 p-3 text-xs text-warning">
            Esta funcionalidade premium está disponível a partir do Plano Intermediário.
          </div>
          <Button onClick={onNavigateToPlans} className="mt-2">
            Fazer Upgrade de Plano
          </Button>
        </CardContent>
      </Card>
    );
  }

  // Filter documents locally
  const filteredDocs = (documents || []).filter((doc) => {
    const matchesSearch =
      doc.title.toLowerCase().includes(search.toLowerCase()) ||
      doc.content.toLowerCase().includes(search.toLowerCase()) ||
      doc.source.toLowerCase().includes(search.toLowerCase());
    
    const matchesCategory = selectedCategory === 'todos' || doc.category === selectedCategory;

    return matchesSearch && matchesCategory;
  });

  const getCategoryLabel = (cat: string) => {
    switch (cat) {
      case 'procedimento': return 'Procedimento';
      case 'faq': return 'FAQ / Dúvida';
      case 'regulamento': return 'Regulamento';
      default: return 'Outros';
    }
  };

  const getCategoryBadgeColor = (cat: string) => {
    switch (cat) {
      case 'procedimento': return 'bg-success/10 text-success border-success/20';
      case 'faq': return 'bg-info/10 text-info border-info/20';
      case 'regulamento': return 'bg-info/10 text-info border-info/20';
      default: return 'bg-muted text-muted-foreground';
    }
  };

  return (
    <div className="space-y-6">
      {/* Intro info */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <BookOpen className="h-6 w-6" />
            </div>
            <div>
              <h2 className="text-lg font-bold">Base de Conhecimento RAG do Escritório</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Cadastre procedimentos operacionais, circulares estaduais e entendimentos internos.
                O FiscWise (GPT-4o Mini) consultará estes documentos e aplicará as diretrizes
                automaticamente ao responder perguntas na calculadora tributária.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Form Card */}
      {isFormOpen && (
        <Card className="border-primary/40 bg-muted/20 animate-slide-up">
          <CardHeader>
            <CardTitle className="text-base">
              {editingDoc ? 'Editar Diretriz de Conhecimento' : 'Adicionar Diretriz à Base RAG'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <FormField label="Título do Documento" error={errors.title} required>
                  <Input
                    placeholder="Ex: Isenção de ICMS Simples Nacional SP Art. X"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                  />
                </FormField>

                <FormField label="Categoria" required>
                  <select
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                  >
                    <option value="procedimento">Procedimento Interno</option>
                    <option value="faq">FAQ / Respostas Frequentes</option>
                    <option value="regulamento">Regulamento / Decreto</option>
                    <option value="outro">Outros</option>
                  </select>
                </FormField>
              </div>

              <FormField label="Fonte / Origem do Conhecimento" error={errors.source}>
                <Input
                  placeholder="Ex: Decreto 45.123/2024 SP ou Manual de Integração do Cliente"
                  value={source}
                  onChange={(e) => setSource(e.target.value)}
                />
              </FormField>

              <FormField label="Conteúdo / Regra de Aplicação (Instruções detalhadas)" error={errors.content} required>
                <textarea
                  className="flex min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                  placeholder="Descreva aqui o procedimento, FAQ ou regulamento. Seja específico, pois a IA interpretará este texto literalmente para responder às perguntas."
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                />
              </FormField>

              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={handleCancel}>
                  Cancelar
                </Button>
                <Button type="submit" disabled={createMutation.isPending || updateMutation.isPending}>
                  {createMutation.isPending || updateMutation.isPending ? 'Salvando...' : 'Salvar na Base RAG'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Main List Management */}
      {!isFormOpen && (
        <div className="space-y-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            {/* Search Input */}
            <div className="relative flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Buscar regras e manuais..."
                className="pl-9"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>

            {/* Create Trigger Button */}
            <Button onClick={handleOpenCreate} className="gap-2 shrink-0">
              <Plus className="h-4 w-4" />
              Nova Diretriz
            </Button>
          </div>

          {/* Category Tabs */}
          <div className="flex flex-wrap gap-1.5 border-b pb-2">
            {[
              { id: 'todos', label: 'Todos' },
              { id: 'procedimento', label: 'Procedimentos' },
              { id: 'faq', label: 'FAQs / Dúvidas' },
              { id: 'regulamento', label: 'Regulamentos' },
              { id: 'outro', label: 'Outros' },
            ].map((cat) => (
              <button
                key={cat.id}
                type="button"
                onClick={() => setSelectedCategory(cat.id)}
                className={cn(
                  'rounded-lg px-3 py-1.5 text-xs font-semibold transition-all',
                  selectedCategory === cat.id
                    ? 'bg-primary/10 text-primary border border-primary/20'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted/40'
                )}
              >
                {cat.label}
              </button>
            ))}
          </div>

          {/* Documents Grid / List */}
          {isLoading ? (
            <div className="flex h-32 items-center justify-center">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            </div>
          ) : filteredDocs.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-dashed p-8 text-center">
              <HelpCircle className="mb-2 h-10 w-10 text-muted-foreground/30" />
              <p className="text-sm font-medium text-muted-foreground">Nenhuma regra fiscal encontrada</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {search ? 'Tente ajustar os termos de pesquisa ou o filtro de categoria.' : 'Clique no botão acima para adicionar a primeira regra fiscal.'}
              </p>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {filteredDocs.map((doc) => {
                const isExpanded = expandedIds[doc.id] || false;
                const truncated = doc.content.length > 180 ? `${doc.content.slice(0, 180)}...` : doc.content;

                return (
                  <Card key={doc.id} className="flex flex-col justify-between hover:border-primary/30 transition-all duration-200">
                    <CardHeader className="pb-2">
                      <div className="flex items-start justify-between gap-2">
                        <Badge variant="regular" className={getCategoryBadgeColor(doc.category)}>
                          {getCategoryLabel(doc.category)}
                        </Badge>
                        <div className="flex gap-1">
                          <button
                            onClick={() => handleEditClick(doc)}
                            className="rounded-lg p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                            title="Editar diretriz"
                          >
                            <Edit3 className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => handleDelete(doc.id)}
                            className="rounded-lg p-1 text-muted-foreground hover:bg-muted hover:text-destructive"
                            title="Excluir diretriz"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                      <CardTitle className="mt-2 text-sm font-bold line-clamp-1">{doc.title}</CardTitle>
                    </CardHeader>
                    <CardContent className="pb-3 text-xs flex-1 flex flex-col justify-between">
                      <div className="space-y-2">
                        <p className="text-muted-foreground leading-relaxed whitespace-pre-line">
                          {isExpanded ? doc.content : truncated}
                        </p>
                        {doc.content.length > 180 && (
                          <button
                            onClick={() => toggleExpand(doc.id)}
                            className="text-primary hover:underline font-semibold"
                          >
                            {isExpanded ? 'Ver menos' : 'Ver mais'}
                          </button>
                        )}
                      </div>
                      <div className="mt-4 pt-2 border-t text-[10px] text-muted-foreground/80 flex items-center justify-between">
                        <span>Fonte: <strong className="text-foreground/80">{doc.source}</strong></span>
                        <span>Atualizado em: {new Date(doc.updated_at).toLocaleDateString('pt-BR')}</span>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Desenvolvedor tab ────────────────────────────────────────────────────────

function DesenvolvedorTab() {
  const { data: apiKeys = [], isLoading: loadingKeys } = useApiKeys();
  const { data: webhooks = [], isLoading: loadingWebhooks } = useWebhooks();
  const { data: logs = [] } = useWebhookDeliveryLogs();
  const { data: availableEvents = [] } = useAvailableWebhookEvents();

  const createApiKey = useCreateApiKey();
  const revokeApiKey = useRevokeApiKey();
  const createWebhook = useCreateWebhook();
  const updateWebhook = useUpdateWebhook();
  const deleteWebhook = useDeleteWebhook();

  const [newKeyName, setNewKeyName] = useState('');
  const [createdKey, setCreatedKey] = useState<ApiKeyCreated | null>(null);
  const [copiedKeyId, setCopiedKeyId] = useState<string | null>(null);

  const [newWebhookUrl, setNewWebhookUrl] = useState('');
  const [selectedEvents, setSelectedEvents] = useState<string[]>([]);
  const [createdWebhook, setCreatedWebhook] = useState<WebhookSubscriptionCreated | null>(null);
  const [copiedSecret, setCopiedSecret] = useState(false);

  async function handleCreateKey() {
    if (!newKeyName.trim()) return;
    try {
      const result = await createApiKey.mutateAsync({ name: newKeyName.trim() });
      setCreatedKey(result);
      setNewKeyName('');
      toast.success('Chave criada com sucesso!');
    } catch {
      toast.error('Erro ao criar chave de API');
    }
  }

  async function handleRevoke(keyId: string) {
    try {
      await revokeApiKey.mutateAsync(keyId);
      toast.success('Chave revogada');
    } catch {
      toast.error('Erro ao revogar chave');
    }
  }

  function handleCopyKey(text: string, id: string) {
    navigator.clipboard.writeText(text);
    setCopiedKeyId(id);
    setTimeout(() => setCopiedKeyId(null), 2000);
  }

  async function handleCreateWebhook() {
    if (!newWebhookUrl.trim() || selectedEvents.length === 0) {
      toast.error('Informe a URL e selecione ao menos um evento');
      return;
    }
    try {
      const result = await createWebhook.mutateAsync({ url: newWebhookUrl.trim(), events: selectedEvents });
      setCreatedWebhook(result);
      setNewWebhookUrl('');
      setSelectedEvents([]);
      toast.success('Webhook criado!');
    } catch {
      toast.error('Erro ao criar webhook');
    }
  }

  function toggleEvent(event: string) {
    setSelectedEvents((prev) =>
      prev.includes(event) ? prev.filter((e) => e !== event) : [...prev, event]
    );
  }

  function handleCopySecret() {
    if (createdWebhook) {
      navigator.clipboard.writeText(createdWebhook.signing_secret);
      setCopiedSecret(true);
      setTimeout(() => setCopiedSecret(false), 2000);
    }
  }

  return (
    <div className="space-y-8">
      {/* Header Banner */}
      <Card className="border-primary/20 bg-gradient-to-r from-primary/5 to-primary/10">
        <CardContent className="flex items-center gap-4 pt-6">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary/10">
            <Code2 className="h-6 w-6 text-primary" />
          </div>
          <div>
            <p className="font-semibold text-foreground">API Pública & Webhooks</p>
            <p className="text-sm text-muted-foreground">
              Integre o FiscWise com ERPs, CRMs e sistemas externos usando chaves de API seguras e notificações em tempo real.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* ── API Keys Section ── */}
      <section className="space-y-4">
        <div className="flex items-center gap-2">
          <Key className="h-5 w-5 text-primary" />
          <h2 className="text-lg font-semibold">Chaves de API</h2>
        </div>

        {/* New Key Revealed Banner */}
        {createdKey && (
          <div className="rounded-xl border border-success/30 bg-success/5 p-4 space-y-2">
            <div className="flex items-center gap-2 text-success">
              <CheckCircle2 className="h-4 w-4" />
              <p className="text-sm font-semibold">Chave criada! Copie agora — não será exibida novamente.</p>
            </div>
            <div className="flex items-center gap-2 rounded-lg bg-background border px-3 py-2">
              <code className="flex-1 text-xs font-mono text-foreground break-all">{createdKey.raw_key}</code>
              <button
                onClick={() => handleCopyKey(createdKey.raw_key, createdKey.id)}
                className="shrink-0 rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
                title="Copiar chave"
              >
                {copiedKeyId === createdKey.id ? <CheckCheck className="h-4 w-4 text-success" /> : <Copy className="h-4 w-4" />}
              </button>
            </div>
            <button
              onClick={() => setCreatedKey(null)}
              className="text-xs text-muted-foreground hover:text-foreground hover:underline"
            >
              Já copiei — fechar
            </button>
          </div>
        )}

        {/* Create new key */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex gap-2">
              <Input
                id="new-api-key-name"
                placeholder="Nome da chave (ex: Integração ERP Totvs)"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleCreateKey()}
                className="flex-1"
              />
              <Button
                onClick={handleCreateKey}
                disabled={!newKeyName.trim() || createApiKey.isPending}
                className="shrink-0"
              >
                <Plus className="mr-2 h-4 w-4" />
                {createApiKey.isPending ? 'Criando...' : 'Criar chave'}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Keys list */}
        <Card>
          <CardContent className="pt-6">
            {loadingKeys ? (
              <div className="space-y-3">
                {[1, 2].map((i) => <div key={i} className="skeleton h-14 rounded-lg" />)}
              </div>
            ) : apiKeys.length === 0 ? (
              <div className="py-8 text-center text-muted-foreground">
                <Key className="mx-auto mb-2 h-8 w-8 opacity-30" />
                <p className="text-sm">Nenhuma chave de API criada ainda.</p>
              </div>
            ) : (
              <div className="divide-y">
                {apiKeys.map((key) => (
                  <div key={key.id} className="flex items-center gap-3 py-3 first:pt-0 last:pb-0">
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm truncate">{key.name}</p>
                      <p className="text-xs text-muted-foreground font-mono">{key.prefix}••••••••</p>
                      <p className="text-[10px] text-muted-foreground mt-0.5">
                        Criado em {new Date(key.created_at).toLocaleDateString('pt-BR')}
                        {key.last_used_at && ` · Último uso: ${new Date(key.last_used_at).toLocaleDateString('pt-BR')}`}
                      </p>
                    </div>
                    <Badge variant={key.is_active ? 'success' : 'default'}>
                      {key.is_active ? 'Ativa' : 'Revogada'}
                    </Badge>
                    {key.is_active && (
                      <button
                        onClick={() => handleRevoke(key.id)}
                        className="shrink-0 rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-destructive"
                        title="Revogar chave"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </section>

      {/* ── Webhooks Section ── */}
      <section className="space-y-4">
        <div className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-primary" />
          <h2 className="text-lg font-semibold">Webhooks</h2>
        </div>

        {/* Signing secret revealed banner */}
        {createdWebhook && (
          <div className="rounded-xl border border-warning/30 bg-warning/5 p-4 space-y-2">
            <div className="flex items-center gap-2 text-warning">
              <AlertCircle className="h-4 w-4" />
              <p className="text-sm font-semibold">Segredo de assinatura gerado! Copie agora — não será exibido novamente.</p>
            </div>
            <div className="flex items-center gap-2 rounded-lg bg-background border px-3 py-2">
              <code className="flex-1 text-xs font-mono text-foreground break-all">{createdWebhook.signing_secret}</code>
              <button
                onClick={handleCopySecret}
                className="shrink-0 rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
                title="Copiar segredo"
              >
                {copiedSecret ? <CheckCheck className="h-4 w-4 text-warning" /> : <Copy className="h-4 w-4" />}
              </button>
            </div>
            <p className="text-xs text-muted-foreground">
              Use o header <code className="font-mono bg-muted px-1 rounded">X-FiscWise-Signature</code> para verificar payloads com HMAC-SHA256.
            </p>
            <button
              onClick={() => setCreatedWebhook(null)}
              className="text-xs text-muted-foreground hover:text-foreground hover:underline"
            >
              Já copiei — fechar
            </button>
          </div>
        )}

        {/* Create webhook */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Novo webhook</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1.5">URL do endpoint</label>
              <Input
                id="webhook-url"
                placeholder="https://app.example.com/webhooks/fiscwise"
                value={newWebhookUrl}
                onChange={(e) => setNewWebhookUrl(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Eventos para assinar</label>
              <div className="flex flex-wrap gap-2">
                {availableEvents.map((event) => (
                  <button
                    key={event}
                    type="button"
                    onClick={() => toggleEvent(event)}
                    className={cn(
                      'rounded-full border px-3 py-1 text-xs font-medium transition-all',
                      selectedEvents.includes(event)
                        ? 'border-primary bg-primary/10 text-primary'
                        : 'border-border text-muted-foreground hover:border-primary/50',
                    )}
                  >
                    {selectedEvents.includes(event) && <span className="mr-1">✓</span>}
                    {event}
                  </button>
                ))}
              </div>
            </div>
            <Button
              onClick={handleCreateWebhook}
              disabled={!newWebhookUrl.trim() || selectedEvents.length === 0 || createWebhook.isPending}
            >
              <Plus className="mr-2 h-4 w-4" />
              {createWebhook.isPending ? 'Criando...' : 'Criar webhook'}
            </Button>
          </CardContent>
        </Card>

        {/* Webhooks list */}
        <Card>
          <CardContent className="pt-6">
            {loadingWebhooks ? (
              <div className="space-y-3">
                {[1, 2].map((i) => <div key={i} className="skeleton h-14 rounded-lg" />)}
              </div>
            ) : webhooks.length === 0 ? (
              <div className="py-8 text-center text-muted-foreground">
                <Activity className="mx-auto mb-2 h-8 w-8 opacity-30" />
                <p className="text-sm">Nenhum webhook configurado ainda.</p>
              </div>
            ) : (
              <div className="divide-y">
                {webhooks.map((wh) => (
                  <div key={wh.id} className="py-3 first:pt-0 last:pb-0 space-y-1">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-medium font-mono truncate flex-1">{wh.url}</p>
                      <div className="flex items-center gap-2 shrink-0">
                        <Badge variant={wh.is_active ? 'success' : 'default'}>
                          {wh.is_active ? 'Ativo' : 'Inativo'}
                        </Badge>
                        <button
                          onClick={() => updateWebhook.mutate({ id: wh.id, payload: { is_active: !wh.is_active } })}
                          className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
                          title={wh.is_active ? 'Desativar' : 'Ativar'}
                        >
                          <RefreshCw className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => deleteWebhook.mutate(wh.id)}
                          className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-destructive"
                          title="Excluir webhook"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {wh.events.map((ev) => (
                        <span key={ev} className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-mono text-primary">
                          {ev}
                        </span>
                      ))}
                    </div>
                    <p className="text-[10px] text-muted-foreground">
                      Criado em {new Date(wh.created_at).toLocaleDateString('pt-BR')}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </section>

      {/* ── Delivery Logs Section ── */}
      {logs.length > 0 && (
        <section className="space-y-4">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-muted-foreground" />
            <h2 className="text-lg font-semibold">Logs de Entrega</h2>
            <Badge variant="default" className="ml-auto">{logs.length}</Badge>
          </div>
          <Card>
            <CardContent className="pt-4">
              <div className="divide-y">
                {logs.slice(0, 20).map((log) => (
                  <div key={log.id} className="py-2.5 first:pt-0 last:pb-0 flex items-center gap-3">
                    <div className={cn(
                      'h-2 w-2 shrink-0 rounded-full',
                      log.success ? 'bg-success' : 'bg-destructive'
                    )} />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-mono truncate">{log.event}</p>
                      <p className="text-[10px] text-muted-foreground truncate">{log.url}</p>
                    </div>
                    <div className="text-right shrink-0">
                      {log.status_code && (
                        <Badge variant={log.success ? 'success' : 'error'} className="text-[10px]">
                          {log.status_code}
                        </Badge>
                      )}
                      <p className="text-[10px] text-muted-foreground mt-0.5">{log.duration_ms}ms</p>
                    </div>
                    <p className="text-[10px] text-muted-foreground shrink-0">
                      {new Date(log.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                    </p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </section>
      )}

      {/* Docs Reference */}
      <Card className="border-dashed">
        <CardContent className="flex items-center gap-3 pt-6">
          <HelpCircle className="h-5 w-5 shrink-0 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            Consulte a{' '}
            <a href="/docs" target="_blank" rel="noopener" className="text-primary hover:underline font-medium">
              documentação da API
            </a>{' '}
            para exemplos de integração, verificação de assinatura HMAC, e referência de todos os campos disponíveis.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
