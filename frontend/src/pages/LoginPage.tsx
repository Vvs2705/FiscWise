import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { GoogleLogin } from '@react-oauth/google';
import { ArrowLeft, Eye, EyeOff, LockKeyhole, MailOpen, RefreshCcw, Smartphone } from 'lucide-react';
import { useAuth } from '@/lib/hooks/useAuth';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { cn } from '@/lib/utils';
import { api, getApiErrorMessage } from '@/lib/api';
import { passwordResetAvailable } from '@/lib/auth';
import { LoginHowItWorks } from '@/features/auth/components/LoginHowItWorks';
import { LoginFooter, LoginTopBar } from '@/features/auth/components/LoginShell';
import { OtpInput } from '@/features/auth/components/OtpInput';

/* Coluna do formulário: sem cartão, direto sobre o fundo. Entrada de 200 ms. */
const FORM_COLUMN_CLASS = 'w-full animate-fade-in-up [animation-duration:200ms]';

function Spinner() {
  return (
    <span
      aria-hidden="true"
      className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
    />
  );
}

/* ─── Tela de verificação 2FA ───────────────────────────────────────────── */
function TwoFAScreen({
  method,
  message,
  mfaToken,
  onVerify,
  onBack,
  isLoading,
}: {
  method: 'totp' | 'email';
  message: string;
  mfaToken: string;
  onVerify: (code: string) => Promise<void>;
  onBack: () => void;
  isLoading: boolean;
}) {
  const [code, setCode] = useState('');
  const [countdown, setCountdown] = useState(method === 'email' ? 60 : 0);
  const [resending, setResending] = useState(false);
  const [error, setError] = useState('');

  const handleResend = async () => {
    setResending(true);
    setError('');
    try {
      const { data } = await api.post<{ sent?: boolean; message?: string }>(
        '/api/v1/auth/login/resend-2fa',
        { mfa_token: mfaToken },
      );
      if (data?.sent === false) {
        setError(data.message || 'Não foi possível reenviar o código agora.');
      } else {
        setCountdown(60);
      }
    } catch (err) {
      const msg = getApiErrorMessage(err, 'Erro ao reenviar código.');
      console.error(msg);
      setError(msg);
    } finally {
      setResending(false);
    }
  };

  // Contagem regressiva para reenvio por e-mail
  useEffect(() => {
    if (method !== 'email' || countdown <= 0) return;
    const t = setInterval(() => setCountdown((c) => c - 1), 1000);
    return () => clearInterval(t);
  }, [method, countdown]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = code.replace(/\s/g, '');
    if (trimmed.length !== 6) return;
    setError('');
    try {
      await onVerify(trimmed);
    } catch {
      // A mensagem detalhada já sai no toast do useAuth.
      setError('Código inválido ou expirado. Tente novamente.');
    }
  };

  const Icon = method === 'totp' ? Smartphone : MailOpen;
  const subtitle = method === 'totp' ? 'Aplicativo autenticador' : 'Código por e-mail';
  const hint =
    method === 'totp'
      ? 'Abra o Google Authenticator (ou similar) e digite o código de 6 dígitos.'
      : message;

  return (
    <div className={FORM_COLUMN_CLASS}>
      <span className="flex h-11 w-11 items-center justify-center rounded-lg border border-primary/20 bg-accent text-primary">
        <Icon className="h-5 w-5" aria-hidden="true" />
      </span>
      <p className="mt-6 text-sm font-medium text-primary">{subtitle}</p>
      <h1 className="mt-1 text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
        Verificação em 2 etapas
      </h1>
      <p className="mt-2 text-sm text-muted-foreground">{hint}</p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <OtpInput value={code} onChange={setCode} disabled={isLoading} />

        <p
          aria-live="polite"
          role="status"
          className={cn('text-center text-sm text-destructive', !error && '-mt-4')}
        >
          {error}
        </p>

        <Button
          type="submit"
          size="lg"
          className="h-11 w-full"
          disabled={isLoading || code.replace(/\s/g, '').length !== 6}
        >
          {isLoading ? (
            <>
              <Spinner />
              Verificando...
            </>
          ) : (
            'Verificar código'
          )}
        </Button>
      </form>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <Button type="button" variant="ghost" size="md" onClick={onBack} className="-ml-3">
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Voltar para o login
        </Button>

        {method === 'email' &&
          (countdown > 0 ? (
            <p className="text-sm text-muted-foreground">
              Reenviar código em{' '}
              <span className="font-medium tabular-nums text-foreground">{countdown}s</span>
            </p>
          ) : (
            <Button
              type="button"
              variant="ghost"
              size="md"
              onClick={handleResend}
              disabled={resending}
              className="text-primary"
            >
              <RefreshCcw className={cn('h-4 w-4', resending && 'animate-spin')} aria-hidden="true" />
              {resending ? 'Enviando...' : 'Reenviar código'}
            </Button>
          ))}
      </div>
    </div>
  );
}

/* ─── Formulário de login ──────────────────────────────────────────────── */
type AuthApi = ReturnType<typeof useAuth>;

function LoginForm({
  login,
  loginWithGoogle,
  isLoading,
}: Pick<AuthApi, 'login' | 'loginWithGoogle' | 'isLoading'>) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPass, setShowPass] = useState(false);
  const [error, setError] = useState('');
  // Link "Esqueci minha senha" só aparece quando o backend tem e-mail
  // configurado (GET /auth/password-reset/available); sem isso, nada muda.
  const [resetAvailable, setResetAvailable] = useState(false);
  useEffect(() => {
    let active = true;
    passwordResetAvailable()
      .then((ok) => { if (active) setResetAvailable(ok); })
      .catch(() => {});
    return () => { active = false; };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await login({ email, password });
    } catch {
      // A mensagem detalhada já sai no toast do useAuth.
      setError('Não foi possível entrar. Confira e-mail e senha e tente novamente.');
    }
  };

  return (
    <div className={FORM_COLUMN_CLASS}>
      <h1 className="text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
        Entrar no FiscWise
      </h1>
      <p className="mt-2 text-sm text-muted-foreground">Acesse suas notas, clientes e prazos.</p>

      {import.meta.env.VITE_GOOGLE_CLIENT_ID && (
        <>
          <div className={cn('mt-8', isLoading && 'pointer-events-none opacity-50')}>
            <GoogleLogin
              onSuccess={(res) => {
                if (res.credential) loginWithGoogle(res.credential);
              }}
              onError={() => {}}
              width="100%"
              text="signin_with"
              shape="rectangular"
              logo_alignment="left"
            />
          </div>

          <div className="mt-6 flex items-center gap-3" role="separator">
            <div className="h-px flex-1 bg-border" />
            <span className="text-xs text-muted-foreground">ou com e-mail</span>
            <div className="h-px flex-1 bg-border" />
          </div>
        </>
      )}

      <form
        onSubmit={handleSubmit}
        className={cn('space-y-4', import.meta.env.VITE_GOOGLE_CLIENT_ID ? 'mt-6' : 'mt-8')}
        noValidate
      >
        <div className="space-y-1.5">
          <label htmlFor="email" className="text-sm font-medium text-foreground">
            E-mail
          </label>
          <Input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            placeholder="voce@empresa.com.br"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            disabled={isLoading}
            className="h-11"
          />
        </div>

        <div className="space-y-1.5">
          <div className="flex items-center justify-between gap-3">
            <label htmlFor="password" className="text-sm font-medium text-foreground">
              Senha
            </label>
            {resetAvailable && (
              <Link
                to="/esqueci-senha"
                className="rounded-md text-xs font-medium text-muted-foreground transition-colors duration-150 hover:text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                Esqueci minha senha
              </Link>
            )}
          </div>
          <div className="relative">
            <Input
              id="password"
              name="password"
              type={showPass ? 'text' : 'password'}
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={isLoading}
              className="h-11 pr-11"
            />
            <button
              type="button"
              onClick={() => setShowPass((s) => !s)}
              className="absolute right-1 top-1/2 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-md text-muted-foreground transition-colors duration-150 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label={showPass ? 'Ocultar senha' : 'Mostrar senha'}
              aria-pressed={showPass}
              aria-controls="password"
            >
              {showPass ? (
                <EyeOff className="h-4 w-4" aria-hidden="true" />
              ) : (
                <Eye className="h-4 w-4" aria-hidden="true" />
              )}
            </button>
          </div>
        </div>

        {/* Região viva sempre montada; sem erro, anula o espaçamento do form. */}
        <p
          aria-live="polite"
          role="status"
          className={cn('text-sm text-destructive', !error && '-mt-4')}
        >
          {error}
        </p>

        <Button type="submit" size="lg" className="h-11 w-full" disabled={isLoading}>
          {isLoading ? (
            <>
              <Spinner />
              Entrando...
            </>
          ) : (
            'Entrar'
          )}
        </Button>
      </form>

      <p className="mt-4 flex items-center gap-2 text-xs text-muted-foreground">
        <LockKeyhole className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        Acesso protegido com verificação em 2 etapas
      </p>
    </div>
  );
}

/* ─── Página de login ──────────────────────────────────────────────────── */
export function LoginPage() {
  // Uma única instância do hook: o desafio de MFA vive no estado dele.
  const { login, loginWithGoogle, verify2FA, cancelMfa, mfaChallenge, isLoading } = useAuth();

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <LoginTopBar />

      <main className="mx-auto grid w-full max-w-7xl flex-1 grid-cols-1 content-start gap-10 px-4 pb-6 pt-6 sm:px-6 sm:pt-10 lg:grid-cols-[minmax(0,400px)_minmax(0,1fr)] lg:content-stretch lg:gap-16 lg:px-10 lg:py-5 xl:py-6 xl:grid-cols-[minmax(0,440px)_minmax(0,1fr)] xl:gap-24">
        <div className="w-full max-w-[440px] lg:self-center">
          {mfaChallenge ? (
            <TwoFAScreen
              method={mfaChallenge.two_factor_method}
              message={mfaChallenge.message}
              mfaToken={mfaChallenge.mfa_token}
              onVerify={verify2FA}
              onBack={cancelMfa}
              isLoading={isLoading}
            />
          ) : (
            <LoginForm login={login} loginWithGoogle={loginWithGoogle} isLoading={isLoading} />
          )}
        </div>

        <LoginHowItWorks />
      </main>

      <LoginFooter />
    </div>
  );
}
