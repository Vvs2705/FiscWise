import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { GoogleLogin } from '@react-oauth/google';
import { motion } from 'framer-motion';
import { useAuth } from '@/lib/hooks/useAuth';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import {
  Eye,
  EyeOff,
  Lock,
  Mail,
  ShieldCheck,
  Smartphone,
  MailOpen,
  ArrowLeft,
  RefreshCcw,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { api, getApiErrorMessage } from '@/lib/api';
import { Logo } from '@/components/Logo';
import { LoginBrandPanel } from '@/features/auth/components/LoginBrandPanel';
import { OtpInput } from '@/features/auth/components/OtpInput';

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
  onVerify: (code: string) => void;
  onBack: () => void;
  isLoading: boolean;
}) {
  const [code, setCode] = useState('');
  const [countdown, setCountdown] = useState(method === 'email' ? 60 : 0);
  const [resending, setResending] = useState(false);

  const handleResend = async () => {
    setResending(true);
    try {
      await api.post('/api/v1/auth/login/resend-2fa', { mfa_token: mfaToken });
      setCountdown(60);
      // toast is imported at page level via useAuth — show inline feedback
    } catch (err) {
      console.error(getApiErrorMessage(err, 'Erro ao reenviar código.'));
    } finally {
      setResending(false);
    }
  };

  // Countdown timer for email resend
  useEffect(() => {
    if (method !== 'email' || countdown <= 0) return;
    const t = setInterval(() => setCountdown((c) => c - 1), 1000);
    return () => clearInterval(t);
  }, [method, countdown]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = code.replace(/\s/g, '');
    if (trimmed.length === 6) onVerify(trimmed);
  };

  const Icon = method === 'totp' ? Smartphone : MailOpen;
  const title = method === 'totp' ? 'Autenticador' : 'Código por e-mail';
  const hint =
    method === 'totp'
      ? 'Abra o Google Authenticator (ou similar) e insira o código de 6 dígitos.'
      : message;

  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
      className="w-full max-w-md rounded-[28px] border border-border bg-card/90 p-6 shadow-token backdrop-blur-xl sm:p-8"
    >
      {/* Header */}
      <div className="flex flex-col items-center gap-3 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-card bg-primary/10 ring-2 ring-primary/20">
          <Icon className="h-8 w-8 text-primary" />
        </div>
        <div>
          <h2 className="text-2xl font-bold text-foreground">Verificação em 2 etapas</h2>
          <p className="text-sm text-muted-foreground mt-1">{title}</p>
        </div>
      </div>

      {/* Hint */}
      <div className="rounded-xl border border-border bg-muted/30 px-4 py-3">
        <p className="text-sm text-muted-foreground text-center">{hint}</p>
      </div>

      {/* OTP input */}
      <form onSubmit={handleSubmit} className="space-y-4">
        <OtpInput value={code} onChange={setCode} disabled={isLoading} />

        <Button
          type="submit"
          className="w-full"
          size="md"
          disabled={isLoading || code.replace(/\s/g, '').length !== 6}
        >
          {isLoading ? (
            <span className="flex items-center gap-2">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
              Verificando...
            </span>
          ) : (
            'Verificar código'
          )}
        </Button>
      </form>

      {/* Resend for email method */}
      {method === 'email' && (
        <div className="text-center">
          {countdown > 0 ? (
            <p className="text-xs text-muted-foreground">
              Reenviar em <span className="font-semibold text-foreground">{countdown}s</span>
            </p>
          ) : (
            <button
              type="button"
              onClick={handleResend}
              disabled={resending}
              className="flex items-center gap-1.5 mx-auto text-xs font-medium text-primary hover:text-primary/80 transition-colors disabled:opacity-50"
            >
              <RefreshCcw className={cn("h-3.5 w-3.5", resending && "animate-spin")} />
              {resending ? 'Enviando...' : 'Reenviar código'}
            </button>
          )}
        </div>
      )}

      {/* Back */}
      <button
        type="button"
        onClick={onBack}
        className="flex items-center gap-1.5 mx-auto text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Voltar para o login
      </button>
    </motion.div>
  );
}

/* ─── Página de login ────────────────────────────────────────────── */
export function LoginPage() {
  const { login, loginWithGoogle, verify2FA, cancelMfa, mfaChallenge, isLoading } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPass, setShowPass] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await login({ email, password });
  };

  return (
    <div className="min-h-screen bg-muted text-foreground lg:grid lg:grid-cols-[46%_54%] lg:h-screen lg:max-h-screen lg:overflow-hidden">
      <style>{`
        @media (min-width: 1024px) {
          body {
            overflow: hidden !important;
            height: 100vh !important;
          }
        }
      `}</style>
      <LoginBrandPanel />

      <section
        className="relative flex min-h-screen lg:min-h-0 flex-1 flex-col items-center justify-center lg:justify-end lg:h-screen lg:max-h-screen lg:overflow-hidden px-5 py-8 lg:py-0 lg:pl-[clamp(32px,5vw,80px)] lg:pr-[clamp(72px,8vw,150px)]"
        style={{
          background:
            'radial-gradient(circle at 70% 20%, hsl(var(--primary) / 0.12), transparent 28%), radial-gradient(circle at 20% 80%, hsl(var(--info) / 0.10), transparent 26%), linear-gradient(135deg, hsl(var(--muted)) 0%, hsl(var(--muted)) 100%)',
        }}
      >
        <div className="pointer-events-none absolute right-10 top-10 h-48 w-48 rounded-full bg-primary/15 blur-3xl" />
        <div className="pointer-events-none absolute bottom-0 left-10 h-56 w-56 rounded-full bg-info/25 blur-3xl" />

        <div className="relative z-10 flex w-full max-w-[480px] flex-col items-center gap-[22px]">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, ease: 'easeOut' }}
            className="mb-8 flex items-center justify-between lg:hidden"
          >
            <Logo variant="full" theme="light" size={34} />
            <span className="rounded-full border border-border bg-card/80 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground shadow-sm">
              Login seguro
            </span>
          </motion.div>

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
            <motion.div
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, ease: 'easeOut' }}
              className="w-full rounded-[30px] border border-border bg-card/90 p-6 shadow-token backdrop-blur-xl sm:p-8"
            >
              <div className="mb-6 space-y-3">
                <div className="inline-flex items-center gap-2 rounded-full border border-success/40 bg-success/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-success">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  Seus dados seguem protegidos
                </div>

                <div className="space-y-1.5">
                  <h2 className="text-2xl font-bold tracking-[-0.02em] text-foreground">
                    Bem-vindo de volta
                  </h2>
                  <p className="text-sm leading-normal text-muted-foreground">
                    Acesse sua central para acompanhar clientes, pendências e tudo o que precisa da sua atenção hoje.
                  </p>
                </div>
              </div>

              {import.meta.env.VITE_GOOGLE_CLIENT_ID && (
                <div
                  className={cn(
                    'mb-4 rounded-card border border-border bg-muted/80 p-2',
                    isLoading && 'pointer-events-none opacity-60',
                  )}
                >
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
              )}

              <div className="relative mb-4 flex items-center gap-3">
                <div className="h-px flex-1 bg-border" />
                <span className="text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                  ou continue com e-mail
                </span>
                <div className="h-px flex-1 bg-border" />
              </div>

              <form onSubmit={handleSubmit} className="space-y-4" noValidate>
                <div className="space-y-1.5">
                  <label htmlFor="email" className="text-sm font-medium text-foreground">
                    E-mail
                  </label>
                  <div className="relative">
                    <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      id="email"
                      type="email"
                      placeholder="voce@seudominio.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      disabled={isLoading}
                      className="h-11 rounded-xl border-border bg-background pl-10 text-foreground shadow-sm"
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <label htmlFor="password" className="text-sm font-medium text-foreground">
                      Senha
                    </label>
                    <Link
                      to="/forgot-password"
                      className="text-xs font-medium text-muted-foreground transition-colors hover:text-primary"
                    >
                      Esqueci minha senha
                    </Link>
                  </div>
                  <div className="relative">
                    <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      id="password"
                      type={showPass ? 'text' : 'password'}
                      placeholder="••••••••"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      disabled={isLoading}
                      className="h-11 rounded-xl border-border bg-background pl-10 pr-12 text-foreground shadow-sm"
                    />
                    <button
                      type="button"
                      tabIndex={-1}
                      onClick={() => setShowPass((s) => !s)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full p-1 text-muted-foreground transition-colors hover:text-foreground"
                      aria-label={showPass ? 'Ocultar senha' : 'Exibir senha'}
                    >
                      {showPass ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>

                <Button
                  type="submit"
                  className="h-11 w-full rounded-xl bg-[linear-gradient(135deg,hsl(var(--primary))_0%,hsl(var(--primary))_60%,hsl(var(--primary)/0.82)_100%)] text-primary-foreground shadow-token hover:shadow-token"
                  size="md"
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <span className="flex items-center gap-2">
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                      Entrando...
                    </span>
                  ) : (
                    'Entrar na conta'
                  )}
                </Button>
              </form>

              <div className="mt-4 rounded-card border border-border bg-muted/80 px-3 py-2.5">
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 rounded-full bg-primary/10 p-2 text-primary">
                    <ShieldCheck className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-foreground">Acesso com verificação reforçada</p>
                    <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">
                      Login por Google, senha e fluxos de 2FA permanecem ativos para manter sua conta protegida.
                    </p>
                  </div>
                </div>
              </div>

              <p className="mt-4 text-center text-sm text-muted-foreground">
                Não tem uma conta?{' '}
                <Link
                  to="/register"
                  className="font-semibold text-primary transition-colors hover:text-primary/80 hover:underline"
                >
                  Criar conta grátis
                </Link>
              </p>
            </motion.div>
          )}

          <footer className="text-center">
            <p className="text-xs text-muted-foreground/80">
              Desenvolvido por{' '}
              <a
                href="https://vstack-solutions.com.br"
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium text-muted-foreground transition-colors hover:text-primary"
              >
                Vstack Solutions
              </a>
              {' '}· © {new Date().getFullYear()} FiscWise
            </p>
          </footer>
        </div>
      </section>
    </div>
  );
}
