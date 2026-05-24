'use client';
import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
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
  ChevronRight,
  Star,
} from 'lucide-react';
import { cn } from '@/lib/utils';
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
  type TenantData,
} from '@/lib/auth';
import { useSubscriptionUsage } from '@/lib/hooks/useSubscription';

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
    color: 'text-amber-500',
    features: ['Clientes ilimitados', 'Usuários ilimitados', 'IA Fiscal ilimitada', 'Export PDF', 'Todas as funcionalidades', 'Suporte dedicado'],
  },
];

// ─── Tab config ──────────────────────────────────────────────────────────────

const TABS = [
  { id: 'perfil',     label: 'Perfil',        icon: User },
  { id: 'escritorio', label: 'Escritório',     icon: Building2 },
  { id: 'plano',      label: 'Plano',          icon: Sparkles },
  { id: 'seguranca',  label: 'Segurança',      icon: ShieldCheck },
  { id: 'pagamento',  label: 'Pagamento',      icon: CreditCard },
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
      .catch(() => {/* tenant fetch fails silently if backend not yet updated */})
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
          <PlanoTab currentPlan={currentPlan} tenant={tenant} onPlanChange={(slug) => {
            setTenant((t) => t ? { ...t, plan_slug: slug } : t);
          }} />
        )}
        {activeTab === 'seguranca' && <SegurancaTab />}
        {activeTab === 'pagamento' && <PagamentoTab currentPlan={currentPlan} />}
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
        <span className={isNearLimit ? 'font-semibold text-amber-500' : 'text-muted-foreground'}>
          {used} / {limit === null ? '∞' : limit}
        </span>
      </div>
      {limit !== null && (
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
          <div
            className={`h-full rounded-full transition-all duration-500 ${pct >= 90 ? 'bg-red-500' : pct >= 70 ? 'bg-amber-500' : 'bg-primary'}`}
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
  onPlanChange,
}: {
  currentPlan: (typeof PLANS)[number];
  tenant: TenantData | null;
  onPlanChange: (slug: string) => void;
}) {
  const [changing, setChanging] = useState<string | null>(null);
  const { data: usage } = useSubscriptionUsage();

  async function handleChangePlan(slug: string) {
    if (slug === currentPlan.slug) return;
    setChanging(slug);
    try {
      await updateTenant({ plan_slug: slug });
      onPlanChange(slug);
      toast.success('Plano atualizado');
    } catch {
      toast.error('Erro ao alterar plano');
    } finally {
      setChanging(null);
    }
  }

  const statusLabel: Record<string, string> = {
    trial: 'Trial',
    active: 'Ativo',
    suspended: 'Suspenso',
    cancelled: 'Cancelado',
    expired: 'Expirado',
  };

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
            <Badge variant={tenant?.subscription_status === 'trial' ? 'warning' : 'success'}>
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

      {/* All plans */}
      <div className="grid gap-4 md:grid-cols-3">
        {PLANS.map((plan) => {
          const isActive = plan.slug === currentPlan.slug;
          return (
            <Card
              key={plan.slug}
              className={cn(
                'relative transition-all duration-200',
                isActive ? 'border-primary shadow-md' : 'hover:border-primary/50',
              )}
            >
              {plan.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="flex items-center gap-1 rounded-full bg-primary px-3 py-0.5 text-xs font-semibold text-primary-foreground">
                    <Star className="h-3 w-3" />
                    Popular
                  </span>
                </div>
              )}
              <CardHeader className="pb-3 pt-5">
                <CardTitle className={cn('text-xl', plan.color)}>{plan.label}</CardTitle>
                <p className="text-2xl font-bold">{plan.price}</p>
              </CardHeader>
              <CardContent className="space-y-4">
                <ul className="space-y-2">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm">
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
                      {f}
                    </li>
                  ))}
                </ul>
                <Button
                  className="w-full"
                  variant={isActive ? 'outline' : 'default'}
                  disabled={isActive || changing !== null}
                  onClick={() => handleChangePlan(plan.slug)}
                >
                  {changing === plan.slug
                    ? 'Alterando...'
                    : isActive
                    ? 'Plano atual'
                    : 'Selecionar plano'}
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
    </div>
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
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-emerald-500/10">
                <ShieldCheck className="h-5 w-5 text-emerald-500" />
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

function PagamentoTab({ currentPlan }: { currentPlan: (typeof PLANS)[number] }) {
  return (
    <div className="space-y-6">
      {/* Coming soon banner */}
      <Card className="overflow-hidden border-amber-200 bg-amber-50 dark:border-amber-800/40 dark:bg-amber-900/10">
        <CardContent className="flex items-center gap-4 pt-6">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-amber-100 dark:bg-amber-900/30">
            <Sparkles className="h-5 w-5 text-amber-500" />
          </div>
          <div>
            <p className="font-semibold text-amber-800 dark:text-amber-300">Em breve</p>
            <p className="text-sm text-amber-700 dark:text-amber-400">
              Gerenciamento de pagamentos estará disponível na próxima versão.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Payment method placeholder */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Forma de pagamento</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between rounded-lg border border-dashed p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-md bg-muted">
                <CreditCard className="h-5 w-5 text-muted-foreground" />
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Nenhum cartão cadastrado</p>
                <p className="text-xs text-muted-foreground">Adicione um cartão para gerenciar sua assinatura</p>
              </div>
            </div>
            <Button variant="outline" size="sm" disabled>
              Adicionar
            </Button>
          </div>

          <div className="rounded-lg border p-4">
            <p className="text-sm font-medium">Assinatura atual</p>
            <div className="mt-3 flex items-center justify-between">
              <div>
                <p className="font-semibold">Plano {currentPlan.label}</p>
                <p className="text-sm text-muted-foreground">{currentPlan.price}</p>
              </div>
              <Button variant="outline" size="sm" disabled className="gap-1">
                Gerenciar
                <ChevronRight className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Billing history placeholder */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Histórico de faturas</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <FileText className="mb-3 h-10 w-10 text-muted-foreground/40" />
            <p className="text-sm font-medium text-muted-foreground">Nenhuma fatura disponível</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Seu histórico de cobranças aparecerá aqui quando disponível.
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
