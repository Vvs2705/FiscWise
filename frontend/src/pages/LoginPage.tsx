import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { GoogleLogin } from '@react-oauth/google';
import { ArrowLeft, Eye, EyeOff, MailOpen, RefreshCcw, Smartphone } from 'lucide-react';
import { useAuth } from '@/lib/hooks/useAuth';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Logo } from '@/components/Logo';
import { cn } from '@/lib/utils';
import { api, getApiErrorMessage } from '@/lib/api';
import { passwordResetAvailable } from '@/lib/auth';
import { LoginBrandPanel, LoginValueSummary } from '@/features/auth/components/LoginBrandPanel';
import { OtpInput } from '@/features/auth/components/OtpInput';

const CARD_CLASS =
  'w-full max-w-md rounded-lg border border-border bg-card p-6 shadow-lg sm:p-8 animate-fade-in-up';

function Spinner() {
  return (
    <span
      aria-hidden="true"
      className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
    />
  );
}

/** Logo do card: wordmark navy no claro, claro no escuro. */
function CardLogo() {
  return (
    <>
      <Logo variant="full" theme="light" size={28} className="dark:hidden" />
      <Logo variant="full" theme="dark" size={28} className="hidden dark:block" />
    </>
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
      await api.post('/api/v1/auth/login/resend-2fa', { mfa_token: mfaToken });
      setCountdown(60);
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
    <div className={CARD_CLASS}>
      <CardLogo />

      <div className="mt-8 flex items-start gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent text-primary">
          <Icon className="h-5 w-5" aria-hidden="true" />
        </span>
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-foreground">
            Verificação em 2 etapas
          </h1>
          <p className="text-sm text-muted-foreground">{subtitle}</p>
        </div>
      </div>

      <p className="mt-4 text-sm text-muted-foreground">{hint}</p>

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

      <div className="mt-4 flex flex-col items-center gap-3">
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

        <Button type="button" variant="ghost" size="md" onClick={onBack}>
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Voltar para o login
        </Button>
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
    <div className={CARD_CLASS}>
      <CardLogo />
      <h1 className="mt-8 text-xl font-semibold tracking-tight text-foreground">Entrar</h1>

      {import.meta.env.VITE_GOOGLE_CLIENT_ID && (
        <>
          <div className={cn('mt-6', isLoading && 'pointer-events-none opacity-50')}>
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
            <span className="text-xs text-muted-foreground">ou</span>
            <div className="h-px flex-1 bg-border" />
          </div>
        </>
      )}

      <form onSubmit={handleSubmit} className="mt-6 space-y-4" noValidate>
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
          <div className="flex items-center justify-between">
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

      <div className="mt-4 border-t border-border pt-4 text-center">
        <p className="text-sm text-muted-foreground">Ainda não tem conta?</p>
        <Link
          to="/register"
          className="mt-1 inline-block rounded-md text-sm font-semibold text-primary transition-colors duration-150 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          Criar conta grátis — sem cartão
        </Link>
      </div>
    </div>
  );
}

/* ─── Página de login ──────────────────────────────────────────────────── */
export function LoginPage() {
  // Uma única instância do hook: o desafio de MFA vive no estado dele.
  const { login, loginWithGoogle, verify2FA, cancelMfa, mfaChallenge, isLoading } = useAuth();

  return (
    <div className="min-h-screen bg-background text-foreground lg:grid lg:grid-cols-[45fr_55fr]">
      <LoginBrandPanel />

      <main className="flex min-h-screen flex-col items-center px-4 py-8 sm:px-6 lg:justify-center lg:py-10">
        <div className="flex w-full flex-1 flex-col items-center justify-center gap-10 lg:flex-none">
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

          <LoginValueSummary />
        </div>

        <footer className="mt-10 text-center text-xs text-muted-foreground">
          <a
            href="https://vstack-solutions.com.br"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-foreground"
          >
            Vstack Solutions
          </a>
          {' · '}© {new Date().getFullYear()}
          {' · '}
          <Link to="/termos" className="hover:text-foreground">
            Termos
          </Link>
          {' · '}
          <Link to="/privacidade" className="hover:text-foreground">
            Privacidade
          </Link>
        </footer>
      </main>
    </div>
  );
}
