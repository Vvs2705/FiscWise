import { useState, useCallback, type ChangeEvent } from 'react';
import axios from 'axios';
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
  Gift,
  ArrowLeft,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Logo } from '@/components/Logo';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { FormField } from '@/components/ui/FormField';
import { useAuth } from '@/lib/hooks/useAuth';
import {
  clearGoogleSignup,
  documentoValido,
  formatarDocumento,
  getGoogleSignup,
  isGoogleSignupRequired,
  mensagemErroDocumento,
  somenteDigitos,
  type GoogleSignupRequired,
} from '@/lib/auth';

// ─── Teste grátis ─────────────────────────────────────────────────────────────

// Todo cadastro começa com 14 dias de teste grátis do Premium, sem cartão
// (backend: onboarding.TRIAL_DAYS). Não existe mais plano Gratuito permanente.
const TRIAL_FEATURES = [
  'Clientes e usuários ilimitados',
  'Chat IA ilimitado',
  'Portal do cliente e obrigações',
  'Exportação em PDF',
];

// ─── Schemas ──────────────────────────────────────────────────────────────────

const step1Schema = z.object({
  company_name: z.string().min(2, 'Nome deve ter ao menos 2 caracteres'),
  // Obrigatório: um teste grátis por CNPJ/CPF (backend valida de novo).
  document: z
    .string()
    .min(1, 'Informe o CNPJ ou CPF')
    .refine(documentoValido, 'CNPJ ou CPF inválido. Confira os números.'),
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

// Primeiro acesso com Google: e-mail já confirmado pelo Google, sem senha.
const googleStep2Schema = z.object({
  owner_full_name: z.string().min(2, 'Nome deve ter ao menos 2 caracteres'),
  owner_phone: z.string().optional(),
});

type Step1Values = z.infer<typeof step1Schema>;
type Step2Values = z.infer<typeof step2Schema>;
type GoogleStep2Values = z.infer<typeof googleStep2Schema>;

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
      <div className="relative flex flex-1 flex-col justify-between p-10">
        <Logo variant="full" theme="dark" size={36} />

        <div className="space-y-6">
          <div>
            <h2 className="text-2xl font-bold text-sidebar-foreground">
              Estruture sua rotina desde o início
            </h2>
            <p className="mt-2 text-sm text-sidebar-muted">
              Monte sua central fiscal, organize clientes e comece a trabalhar com mais previsibilidade.
            </p>
          </div>

          <div className="space-y-3">
            {[
              { icon: '📁', text: 'Organize documentos e certificados por cliente' },
              { icon: '📅', text: 'Acompanhe vencimentos e obrigações em um só lugar' },
              { icon: '💰', text: 'Controle honorários, recebíveis e pendências da carteira' },
            ].map(({ icon, text }) => (
              <div key={text} className="flex items-start gap-3 text-sm text-sidebar-foreground/85">
                <span className="mt-0.5 text-base leading-none">{icon}</span>
                <span>{text}</span>
              </div>
            ))}
          </div>
        </div>

        <p className="text-xs text-sidebar-muted">
          Desenvolvido por{' '}
          <a
            href="https://vstack-solutions.com.br"
            target="_blank"
            rel="noopener noreferrer"
            className="underline underline-offset-2 hover:text-sidebar-foreground"
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
  const { register: registerUser, registerWithGoogle, loginWithGoogle, isLoading } = useAuth();
  // Veio do botão do Google com um e-mail ainda sem conta: o cadastro do
  // escritório (termos + plano) é obrigatório antes de entrar no sistema.
  const [googleSignup, setGoogleSignup] = useState<GoogleSignupRequired | null>(() =>
    new URLSearchParams(window.location.search).get('google') === '1' ? getGoogleSignup() : null,
  );
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

  // ── Step 2 (Google) form ──
  const formGoogle = useForm<GoogleStep2Values>({
    resolver: zodResolver(googleStep2Schema),
    defaultValues: { owner_full_name: googleSignup?.full_name ?? '', owner_phone: '' },
  });

  function cancelGoogleSignup() {
    clearGoogleSignup();
    setGoogleSignup(null);
    setStep(step1Data ? 2 : 1);
  }

  // ── Handlers ──
  function handleStep1(values: Step1Values) {
    setStep1Data(values);
    setStep(2);
  }

  function handleStep2() {
    // Values stay in form2 state; final submit reads them in handleFinish
    setStep(3);
  }

  /** Erro de documento vindo do backend: volta ao passo 1 com o aviso no campo. */
  function voltarComErroDeDocumento(error: unknown): boolean {
    if (!axios.isAxiosError(error)) return false;
    const mensagem = mensagemErroDocumento(String(error.response?.headers?.['x-error-code'] ?? ''));
    if (!mensagem) return false;
    setStep(1);
    // Espera o passo 1 montar para o erro aparecer no campo.
    setTimeout(() => form1.setError('document', { type: 'server', message: mensagem }), 0);
    return true;
  }

  async function handleFinish() {
    if (!step1Data) return;
    if (!termsAccepted) {
      setTermsError('Você deve aceitar os Termos de Uso e a Política de Privacidade para continuar.');
      return;
    }
    setTermsError('');
    if (googleSignup) {
      const g = formGoogle.getValues();
      try {
        await registerWithGoogle({
          signup_token: googleSignup.signup_token,
          company_name: step1Data.company_name,
          document: somenteDigitos(step1Data.document),
          owner_full_name: g.owner_full_name,
          owner_phone: g.owner_phone,
          terms_accepted: true,
        });
      } catch (error) {
        if (voltarComErroDeDocumento(error)) return;
        // Token do Google venceu (30 min): pede para clicar no Google de novo.
        if (axios.isAxiosError(error) && error.response?.status === 401) cancelGoogleSignup();
      }
      return;
    }
    const step2Values = form2.getValues();
    try {
      await registerUser({
        company_name: step1Data.company_name,
        document: somenteDigitos(step1Data.document),
        owner_full_name: step2Values.owner_full_name,
        owner_email: step2Values.owner_email,
        owner_phone: step2Values.owner_phone,
        owner_password: step2Values.owner_password,
        terms_accepted: true,
      });
    } catch (error) {
      // O aviso geral já saiu (toast em useAuth); erro de documento volta ao campo.
      voltarComErroDeDocumento(error);
    }
  }

  const handleGoogleSuccess = useCallback(
    async (credentialResponse: { credential?: string }) => {
      if (credentialResponse.credential) {
        const result = await loginWithGoogle(credentialResponse.credential);
        if (result && isGoogleSignupRequired(result)) {
          setGoogleSignup(result);
          formGoogle.reset({ owner_full_name: result.full_name ?? '', owner_phone: '' });
          setStep(step1Data ? 2 : 1);
        }
      }
    },
    [loginWithGoogle, formGoogle, step1Data],
  );

  const stepLabel = ['Seu ambiente', 'Seus dados', 'Seu teste grátis'][step - 1];

  return (
    <div className="flex min-h-screen bg-background">
      <BrandPanel />

      {/* Form side */}
      <div className="flex flex-1 flex-col items-center justify-center px-4 py-12 sm:px-8">
        {/* Mobile logo */}
        <div className="mb-8 lg:hidden">
          <Logo variant="full" theme="auto" size={32} />
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

              <FormField
                label="CNPJ / CPF"
                htmlFor="document"
                error={form1.formState.errors.document?.message}
                hint="O teste grátis vale uma vez por CNPJ ou CPF."
                required
              >
                <Input
                  id="document"
                  inputMode="numeric"
                  autoComplete="off"
                  placeholder="00.000.000/0000-00 ou 000.000.000-00"
                  {...form1.register('document', {
                    onChange: (e: ChangeEvent<HTMLInputElement>) =>
                      form1.setValue('document', formatarDocumento(e.target.value)),
                  })}
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

          {/* Aviso do cadastro com Google */}
          {googleSignup && (
            <div className="mb-5 rounded-xl border border-primary/30 bg-primary/5 p-3 text-sm">
              <p className="font-medium text-foreground">Criando conta com o Google</p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {googleSignup.email} ainda não tem conta no FiscWise. Complete o cadastro do seu
                escritório para entrar.{' '}
                <button type="button" onClick={cancelGoogleSignup} className="font-medium text-primary hover:underline">
                  Usar outro e-mail
                </button>
              </p>
            </div>
          )}

          {/* ── Step 2 (Google): nome e telefone, sem senha ── */}
          {step === 2 && googleSignup && (
            <form
              onSubmit={formGoogle.handleSubmit(() => setStep(3))}
              className="space-y-4 animation-delay-75 animate-fade-in-up"
              noValidate
            >
              <FormField label="E-mail (Google)" htmlFor="google_email">
                <div className="relative">
                  <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input id="google_email" className="pl-9" value={googleSignup.email} readOnly disabled />
                </div>
              </FormField>
              <FormField label="Nome completo" htmlFor="g_owner_full_name" error={formGoogle.formState.errors.owner_full_name?.message} required>
                <div className="relative">
                  <User className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input id="g_owner_full_name" className="pl-9" placeholder="João Silva" {...formGoogle.register('owner_full_name')} />
                </div>
              </FormField>
              <FormField label="Telefone (opcional)" htmlFor="g_owner_phone">
                <div className="relative">
                  <Phone className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input id="g_owner_phone" className="pl-9" placeholder="(11) 99999-9999" {...formGoogle.register('owner_phone')} />
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
          )}

          {/* ── Step 2: Personal data ── */}
          {step === 2 && !googleSignup && (
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
              <div className="rounded-xl border border-primary bg-primary/5 p-4 shadow-sm">
                <div className="flex items-center gap-2">
                  <Gift className="h-4 w-4 text-primary" aria-hidden="true" />
                  <span className="font-semibold">14 dias grátis com tudo do Premium</span>
                </div>
                <p className="mt-1 text-sm font-medium text-primary">Sem cartão de crédito</p>
                <div className="mt-2 flex flex-wrap gap-x-3 gap-y-0.5">
                  {TRIAL_FEATURES.map((f) => (
                    <span key={f} className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Check className="h-3 w-3 text-success" />
                      {f}
                    </span>
                  ))}
                </div>
                <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
                  Antes do fim do teste, escolha o Intermediário ou o Premium para continuar. Sem
                  assinatura, a conta fica só para leitura: você consulta e exporta seus dados, mas
                  não cadastra nem edita.
                </p>
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
                  {isLoading ? 'Criando conta...' : 'Começar teste grátis'}
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
