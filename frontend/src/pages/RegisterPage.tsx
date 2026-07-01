import { useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { GoogleLogin } from '@react-oauth/google';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Building2,
  User,
  Mail,
  Phone,
  Lock,
  Eye,
  EyeOff,
  Check,
  ChevronRight,
  Star,
  ArrowLeft,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Logo } from '@/components/Logo';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { FormField } from '@/components/ui/FormField';
import { useAuth } from '@/lib/hooks/useAuth';

// ─── Plans ────────────────────────────────────────────────────────────────────

const PLANS = [
  {
    slug: 'free',
    label: 'Free',
    price: 'Grátis',
    description: 'Para organizar sua carteira desde o primeiro cliente',
    features: ['Até 5 clientes', '1 usuário', 'Documentos básicos', 'Calculadora fiscal básica'],
  },
  {
    slug: 'intermediario',
    label: 'Intermediário',
    price: 'R$ 49/mês',
    description: 'Para contadores autônomos com carteira em expansão',
    popular: true,
    features: ['Até 50 clientes', '3 usuários', 'Agenda e prazos', 'Certificados digitais', 'Chat IA (20 msgs/mês)', 'Recomendações IA'],
  },
  {
    slug: 'premium',
    label: 'Premium',
    price: 'R$ 149/mês',
    description: 'Para uma operação fiscal mais completa e previsível',
    features: ['Clientes ilimitados', '10 usuários', 'Relatórios avançados', 'Chat IA ilimitado', 'Exportação PDF', 'API access'],
  },
];

// ─── Schemas ──────────────────────────────────────────────────────────────────

const step1Schema = z.object({
  company_name: z.string().min(2, 'Nome deve ter ao menos 2 caracteres'),
  document: z.string().optional(),
});

const step2Schema = z
  .object({
    owner_full_name: z.string().min(2, 'Nome deve ter ao menos 2 caracteres'),
    owner_email: z.string().email('E-mail inválido'),
    owner_phone: z.string().optional(),
    owner_password: z.string().min(8, 'Senha deve ter ao menos 8 caracteres'),
    confirm_password: z.string().min(1, 'Confirme a senha'),
  })
  .refine((d) => d.owner_password === d.confirm_password, {
    message: 'As senhas não coincidem',
    path: ['confirm_password'],
  });

type Step1Values = z.infer<typeof step1Schema>;
type Step2Values = z.infer<typeof step2Schema>;

// ─── Step indicator ───────────────────────────────────────────────────────────

function StepIndicator({ current, total }: { current: number; total: number }) {
  return (
    <div className="flex items-center gap-2">
      {Array.from({ length: total }, (_, i) => i + 1).map((s) => (
        <div key={s} className="flex items-center">
          <div
            className={cn(
              'flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold transition-all duration-300',
              s < current
                ? 'bg-primary text-primary-foreground'
                : s === current
                ? 'border-2 border-primary bg-primary/10 text-primary'
                : 'border border-border text-muted-foreground',
            )}
          >
            {s < current ? <Check className="h-3.5 w-3.5" /> : s}
          </div>
          {s < total && (
            <div
              className={cn(
                'mx-1.5 h-px w-8 transition-all duration-300',
                s < current ? 'bg-primary' : 'bg-border',
              )}
            />
          )}
        </div>
      ))}
    </div>
  );
}

// ─── Brand Panel ──────────────────────────────────────────────────────────────

function BrandPanel() {
  return (
    <div
      className={cn(
        'relative hidden overflow-hidden lg:flex lg:w-[420px] lg:shrink-0 lg:flex-col',
        'bg-sidebar',
      )}
    >
      {/* Decorative blobs */}
      <div className="pointer-events-none absolute -left-16 -top-16 h-64 w-64 rounded-full bg-white/5 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-16 -right-16 h-64 w-64 rounded-full bg-white/5 blur-3xl" />

      <div className="relative flex flex-1 flex-col justify-between p-10">
        <Logo variant="full" theme="dark" size={36} />

        <div className="space-y-6">
          <div>
            <h2 className="text-2xl font-bold text-white">
              Estruture sua rotina desde o início
            </h2>
            <p className="mt-2 text-sm text-white/60">
              Monte sua central fiscal, organize clientes e comece a trabalhar com mais previsibilidade.
            </p>
          </div>

          <div className="space-y-3">
            {[
              { icon: '📁', text: 'Organize documentos e certificados por cliente' },
              { icon: '📅', text: 'Acompanhe vencimentos e obrigações em um só lugar' },
              { icon: '💰', text: 'Controle honorários, recebíveis e pendências da carteira' },
            ].map(({ icon, text }) => (
              <div key={text} className="flex items-start gap-3 text-sm text-white/70">
                <span className="mt-0.5 text-base leading-none">{icon}</span>
                <span>{text}</span>
              </div>
            ))}
          </div>
        </div>

        <p className="text-xs text-white/30">
          Desenvolvido por{' '}
          <a
            href="https://vstack-solutions.com.br"
            target="_blank"
            rel="noopener noreferrer"
            className="underline underline-offset-2 hover:text-white/60"
          >
            Vstack Solutions
          </a>
        </p>
      </div>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function RegisterPage() {
  const { register: registerUser, loginWithGoogle, isLoading } = useAuth();
  const [step, setStep] = useState(1);
  const [showPassword, setShowPassword] = useState(false);
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [termsError, setTermsError] = useState('');

  // Accumulated form data across steps
  const [step1Data, setStep1Data] = useState<Step1Values | null>(null);

  // ── Step 1 form ──
  const form1 = useForm<Step1Values>({
    resolver: zodResolver(step1Schema),
    defaultValues: { company_name: '', document: '' },
  });

  // ── Step 2 form ──
  const form2 = useForm<Step2Values>({
    resolver: zodResolver(step2Schema),
    defaultValues: { owner_full_name: '', owner_email: '', owner_phone: '', owner_password: '', confirm_password: '' },
  });

  // ── Step 3 plan state ──
  const [selectedPlan, setSelectedPlan] = useState('free');

  // ── Handlers ──
  function handleStep1(values: Step1Values) {
    setStep1Data(values);
    setStep(2);
  }

  function handleStep2() {
    // Values stay in form2 state; final submit reads them in handleFinish
    setStep(3);
  }

  async function handleFinish() {
    if (!step1Data) return;
    if (!termsAccepted) {
      setTermsError('Você deve aceitar os Termos de Uso e a Política de Privacidade para continuar.');
      return;
    }
    setTermsError('');
    const step2Values = form2.getValues();
    await registerUser({
      company_name: step1Data.company_name,
      document: step1Data.document,
      owner_full_name: step2Values.owner_full_name,
      owner_email: step2Values.owner_email,
      owner_phone: step2Values.owner_phone,
      owner_password: step2Values.owner_password,
      plan_slug: selectedPlan,
      terms_accepted: true,
    });
  }

  const handleGoogleSuccess = useCallback(
    async (credentialResponse: { credential?: string }) => {
      if (credentialResponse.credential) {
        await loginWithGoogle(credentialResponse.credential);
      }
    },
    [loginWithGoogle],
  );

  const stepLabel = ['Seu ambiente', 'Seus dados', 'Escolha o plano'][step - 1];

  return (
    <div className="flex min-h-screen bg-background">
      <BrandPanel />

      {/* Form side */}
      <div className="flex flex-1 flex-col items-center justify-center px-4 py-12 sm:px-8">
        {/* Mobile logo */}
        <div className="mb-8 lg:hidden">
          <Logo variant="full" theme="light" size={32} />
        </div>

        <div className="w-full max-w-md animate-fade-in-up">
          {/* Header */}
          <div className="mb-8 space-y-1">
            <div className="flex items-center justify-between">
              <h1 className="text-2xl font-bold">Criar conta</h1>
              <StepIndicator current={step} total={3} />
            </div>
            <p className="text-sm text-muted-foreground">
              Passo {step} de 3 — <span className="font-medium text-foreground">{stepLabel}</span>
            </p>
          </div>

          {/* ── Step 1: Company ── */}
          {step === 1 && (
            <form onSubmit={form1.handleSubmit(handleStep1)} className="space-y-5 animation-delay-75 animate-fade-in-up" noValidate>
              <FormField label="Nome do escritório / empresa" htmlFor="company_name" error={form1.formState.errors.company_name?.message} required>
                <div className="relative">
                  <Building2 className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="company_name"
                    className="pl-9"
                    placeholder="Seu nome profissional ou marca contábil"
                    {...form1.register('company_name')}
                  />
                </div>
              </FormField>

              <FormField label="CNPJ / CPF (opcional)" htmlFor="document" error={form1.formState.errors.document?.message}>
                <Input
                  id="document"
                  placeholder="12.345.678/0001-90"
                  {...form1.register('document')}
                />
              </FormField>

              <Button type="submit" className="w-full gap-1">
                Continuar <ChevronRight className="h-4 w-4" />
              </Button>

              <p className="text-center text-sm text-muted-foreground">
                Já tem conta?{' '}
                <Link to="/login" className="font-medium text-primary hover:underline">
                  Fazer login
                </Link>
              </p>
            </form>
          )}

          {/* ── Step 2: Personal data ── */}
          {step === 2 && (
            <div className="space-y-5 animation-delay-75 animate-fade-in-up">
              {/* Google shortcut */}
              {import.meta.env.VITE_GOOGLE_CLIENT_ID && (
                <div className="space-y-3">
                  <div className="flex justify-center">
                    <GoogleLogin
                      onSuccess={handleGoogleSuccess}
                      onError={() => {}}
                      text="signup_with"
                      shape="pill"
                      width="100%"
                    />
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="h-px flex-1 bg-border" />
                    <span className="text-xs text-muted-foreground">ou preencha abaixo</span>
                    <div className="h-px flex-1 bg-border" />
                  </div>
                </div>
              )}

              <form onSubmit={form2.handleSubmit(handleStep2)} className="space-y-4" noValidate>
                <FormField label="Nome completo" htmlFor="owner_full_name" error={form2.formState.errors.owner_full_name?.message} required>
                  <div className="relative">
                    <User className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input id="owner_full_name" className="pl-9" placeholder="João Silva" {...form2.register('owner_full_name')} />
                  </div>
                </FormField>

                <FormField label="E-mail" htmlFor="owner_email" error={form2.formState.errors.owner_email?.message} required>
                  <div className="relative">
                    <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input id="owner_email" type="email" className="pl-9" placeholder="voce@seudominio.com" {...form2.register('owner_email')} />
                  </div>
                </FormField>

                <FormField label="Telefone (opcional)" htmlFor="owner_phone" error={form2.formState.errors.owner_phone?.message}>
                  <div className="relative">
                    <Phone className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input id="owner_phone" className="pl-9" placeholder="(11) 99999-9999" {...form2.register('owner_phone')} />
                  </div>
                </FormField>

                <FormField label="Senha" htmlFor="owner_password" error={form2.formState.errors.owner_password?.message} required>
                  <div className="relative">
                    <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      id="owner_password"
                      type={showPassword ? 'text' : 'password'}
                      className="pl-9 pr-10"
                      placeholder="Mínimo 8 caracteres"
                      {...form2.register('owner_password')}
                    />
                    <button
                      type="button"
                      tabIndex={-1}
                      onClick={() => setShowPassword((v) => !v)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                      aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'}
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </FormField>

                <FormField label="Confirmar senha" htmlFor="confirm_password" error={form2.formState.errors.confirm_password?.message} required>
                  <div className="relative">
                    <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      id="confirm_password"
                      type="password"
                      className="pl-9"
                      placeholder="Repita a senha"
                      {...form2.register('confirm_password')}
                    />
                  </div>
                </FormField>

                <div className="flex gap-2 pt-1">
                  <Button type="button" variant="outline" className="gap-1" onClick={() => setStep(1)}>
                    <ArrowLeft className="h-4 w-4" /> Voltar
                  </Button>
                  <Button type="submit" className="flex-1 gap-1">
                    Continuar <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </form>
            </div>
          )}

          {/* ── Step 3: Plan ── */}
          {step === 3 && (
            <div className="space-y-5 animation-delay-75 animate-fade-in-up">
              <div className="space-y-3">
                {PLANS.map((plan) => {
                  const active = selectedPlan === plan.slug;
                  return (
                    <label
                      key={plan.slug}
                      className={cn(
                        'relative flex cursor-pointer items-start gap-4 rounded-xl border p-4 transition-all duration-150',
                        active
                          ? 'border-primary bg-primary/5 shadow-sm'
                          : 'hover:border-primary/40',
                      )}
                    >
                      <input
                        type="radio"
                        name="plan"
                        value={plan.slug}
                        checked={active}
                        onChange={() => setSelectedPlan(plan.slug)}
                        className="sr-only"
                      />
                      {/* Radio indicator */}
                      <div
                        className={cn(
                          'mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border-2 transition-all',
                          active ? 'border-primary bg-primary' : 'border-border',
                        )}
                      >
                        {active && <div className="h-1.5 w-1.5 rounded-full bg-white" />}
                      </div>

                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold">{plan.label}</span>
                          {plan.popular && (
                            <span className="flex items-center gap-0.5 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-bold text-primary">
                              <Star className="h-2.5 w-2.5" />
                              Popular
                            </span>
                          )}
                        </div>
                        <p className="text-sm font-medium text-primary">{plan.price}</p>
                        <p className="mt-0.5 text-xs text-muted-foreground">{plan.description}</p>
                        <div className="mt-2 flex flex-wrap gap-x-3 gap-y-0.5">
                          {plan.features.map((f) => (
                            <span key={f} className="flex items-center gap-1 text-xs text-muted-foreground">
                              <Check className="h-3 w-3 text-success" />
                              {f}
                            </span>
                          ))}
                        </div>
                      </div>
                    </label>
                  );
                })}
              </div>

              {/* LGPD — terms acceptance checkbox */}
              <label className="flex cursor-pointer items-start gap-3">
                <input
                  type="checkbox"
                  checked={termsAccepted}
                  onChange={(e) => {
                    setTermsAccepted(e.target.checked);
                    if (e.target.checked) setTermsError('');
                  }}
                  className="mt-0.5 h-4 w-4 shrink-0 cursor-pointer accent-primary"
                />
                <span className="text-xs text-muted-foreground leading-relaxed">
                  Li e aceito os{' '}
                  <Link to="/termos" target="_blank" className="font-medium text-primary hover:underline">
                    Termos de Uso
                  </Link>{' '}
                  e a{' '}
                  <Link to="/privacidade" target="_blank" className="font-medium text-primary hover:underline">
                    Política de Privacidade
                  </Link>{' '}
                  do FiscWise, conforme exigido pela LGPD.
                </span>
              </label>
              {termsError && (
                <p className="text-xs text-destructive">{termsError}</p>
              )}

              <div className="flex gap-2 pt-1">
                <Button type="button" variant="outline" className="gap-1" onClick={() => setStep(2)}>
                  <ArrowLeft className="h-4 w-4" /> Voltar
                </Button>
                <Button
                  type="button"
                  className="flex-1"
                  disabled={isLoading}
                  onClick={handleFinish}
                >
                  {isLoading ? 'Criando conta...' : 'Criar minha conta'}
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
