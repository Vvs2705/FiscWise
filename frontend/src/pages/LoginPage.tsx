import { useState, useRef, useEffect } from 'react';
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
import { Logo } from '@/components/Logo';
import { LoginBrandPanel } from '@/features/auth/components/LoginBrandPanel';

/* ─── OTP Input — 6 boxes ───────────────────────────────────────────────── */
function OtpInput({ value, onChange, disabled }: {
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
    if (text.length > 0) {
      onChange(text);
      inputs.current[Math.min(text.length, 5)]?.focus();
    }
    e.preventDefault();
  };

  return (
    <div className="flex gap-2 justify-center" onPaste={handlePaste}>
      {Array.from({ length: 6 }).map((_, idx) => (
        <input
          key={idx}
          ref={(el) => { inputs.current[idx] = el; }}
          id={`otp-${idx}`}
          type="text"
          inputMode="numeric"
          maxLength={1}
          value={digits[idx]?.trim() ?? ''}
          onChange={(e) => handleChange(idx, e)}
          onKeyDown={(e) => handleKey(idx, e)}
          disabled={disabled}
          className={cn(
            'h-14 w-12 rounded-xl border-2 bg-background text-center text-xl font-bold',
            'text-foreground transition-all duration-150 outline-none',
            'border-border focus:border-primary focus:ring-2 focus:ring-primary/20',
            disabled && 'cursor-not-allowed opacity-50',
          )}
          autoComplete="one-time-code"
          aria-label={`Dígito ${idx + 1} do código OTP`}
        />
      ))}
    </div>
  );
}

/* ─── Tela de verificação 2FA ───────────────────────────────────────────── */
function TwoFAScreen({
  method,
  message,
  onVerify,
  onBack,
  isLoading,
}: {
  method: 'totp' | 'email';
  message: string;
  onVerify: (code: string) => void;
  onBack: () => void;
  isLoading: boolean;
}) {
  const [code, setCode] = useState('');
  const [countdown, setCountdown] = useState(method === 'email' ? 60 : 0);

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
      className="w-full max-w-md rounded-[28px] border border-slate-200 bg-white/90 p-6 shadow-[0_24px_80px_rgba(15,23,42,0.18)] backdrop-blur-xl sm:p-8"
    >
      {/* Header */}
      <div className="flex flex-col items-center gap-3 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 ring-2 ring-primary/20">
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
              onClick={() => setCountdown(60)}
              className="flex items-center gap-1.5 mx-auto text-xs font-medium text-primary hover:text-primary/80 transition-colors"
            >
              <RefreshCcw className="h-3.5 w-3.5" />
              Reenviar código
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
    <div className="min-h-screen bg-slate-50 text-foreground lg:flex">
      <LoginBrandPanel />

      <section className="relative flex min-h-screen flex-1 items-center justify-center overflow-hidden px-5 py-8 sm:px-8 lg:px-10">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              'radial-gradient(circle at top, rgba(45,212,191,0.10), transparent 28%), linear-gradient(180deg, rgba(241,245,249,0.95) 0%, rgba(248,250,252,1) 100%)',
          }}
        />
        <div className="pointer-events-none absolute right-10 top-10 h-48 w-48 rounded-full bg-cyan-300/15 blur-3xl" />
        <div className="pointer-events-none absolute bottom-0 left-10 h-56 w-56 rounded-full bg-sky-200/25 blur-3xl" />

        <div className="relative z-10 flex w-full max-w-[480px] flex-col">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, ease: 'easeOut' }}
            className="mb-8 flex items-center justify-between lg:hidden"
          >
            <Logo variant="full" theme="light" size={34} />
            <span className="rounded-full border border-slate-200 bg-white/80 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500 shadow-sm">
              Login seguro
            </span>
          </motion.div>

          {mfaChallenge ? (
            <TwoFAScreen
              method={mfaChallenge.two_factor_method}
              message={mfaChallenge.message}
              onVerify={verify2FA}
              onBack={cancelMfa}
              isLoading={isLoading}
            />
          ) : (
            <motion.div
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, ease: 'easeOut' }}
              className="rounded-[30px] border border-white/70 bg-white/90 p-6 shadow-[0_28px_100px_rgba(15,23,42,0.14)] backdrop-blur-xl sm:p-8"
            >
              <div className="mb-8 space-y-4">
                <div className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-emerald-700">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  Seus dados seguem protegidos
                </div>

                <div className="space-y-2">
                  <h2 className="text-3xl font-semibold tracking-[-0.03em] text-slate-950">
                    Bem-vindo de volta
                  </h2>
                  <p className="text-sm leading-6 text-slate-600">
                    Acesse sua central para acompanhar clientes, pendências e tudo o que precisa da sua atenção hoje.
                  </p>
                </div>
              </div>

              {import.meta.env.VITE_GOOGLE_CLIENT_ID && (
                <div
                  className={cn(
                    'mb-5 rounded-2xl border border-slate-200/80 bg-slate-50/80 p-2',
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

              <div className="relative mb-5 flex items-center gap-3">
                <div className="h-px flex-1 bg-slate-200" />
                <span className="text-[11px] font-medium uppercase tracking-[0.18em] text-slate-400">
                  ou continue com e-mail
                </span>
                <div className="h-px flex-1 bg-slate-200" />
              </div>

              <form onSubmit={handleSubmit} className="space-y-4" noValidate>
                <div className="space-y-1.5">
                  <label htmlFor="email" className="text-sm font-medium text-slate-800">
                    E-mail
                  </label>
                  <div className="relative">
                    <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                    <Input
                      id="email"
                      type="email"
                      placeholder="voce@seudominio.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      disabled={isLoading}
                      className="h-12 rounded-xl border-slate-200 bg-white pl-10 text-slate-900 shadow-sm"
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label htmlFor="password" className="text-sm font-medium text-slate-800">
                    Senha
                  </label>
                  <div className="relative">
                    <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                    <Input
                      id="password"
                      type={showPass ? 'text' : 'password'}
                      placeholder="••••••••"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      disabled={isLoading}
                      className="h-12 rounded-xl border-slate-200 bg-white pl-10 pr-12 text-slate-900 shadow-sm"
                    />
                    <button
                      type="button"
                      tabIndex={-1}
                      onClick={() => setShowPass((s) => !s)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full p-1 text-slate-400 transition-colors hover:text-slate-700"
                      aria-label={showPass ? 'Ocultar senha' : 'Exibir senha'}
                    >
                      {showPass ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>

                <Button
                  type="submit"
                  className="h-12 w-full rounded-xl bg-[linear-gradient(135deg,#14b8a6_0%,#0f766e_45%,#0f172a_100%)] text-white shadow-[0_18px_40px_rgba(20,184,166,0.28)] hover:shadow-[0_22px_50px_rgba(20,184,166,0.32)]"
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

              <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50/80 px-4 py-3">
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 rounded-full bg-cyan-100 p-2 text-cyan-700">
                    <ShieldCheck className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-800">Acesso com verificacao reforcada</p>
                    <p className="mt-1 text-sm leading-6 text-slate-600">
                      Login por Google, senha e fluxos de 2FA permanecem ativos para manter sua conta protegida.
                    </p>
                  </div>
                </div>
              </div>

              <p className="mt-6 text-center text-sm text-slate-500">
                Nao tem uma conta?{' '}
                <Link
                  to="/register"
                  className="font-semibold text-primary transition-colors hover:text-primary/80 hover:underline"
                >
                  Criar conta gratis
                </Link>
              </p>
            </motion.div>
          )}

          <footer className="mt-8 text-center">
            <p className="text-xs text-slate-500/80">
              Desenvolvido por{' '}
              <a
                href="https://vstack-solutions.com.br"
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium text-slate-600 transition-colors hover:text-primary"
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
