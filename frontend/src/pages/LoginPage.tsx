import { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { GoogleLogin } from '@react-oauth/google';
import { useAuth } from '@/lib/hooks/useAuth';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import {
  Eye,
  EyeOff,
  Lock,
  Mail,
  ShieldCheck,
  TrendingUp,
  Zap,
  Smartphone,
  MailOpen,
  ArrowLeft,
  RefreshCcw,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Logo } from '@/components/Logo';

/* ─── Painel esquerdo — branding ────────────────────────────────── */
function BrandPanel() {
  const features = [
    {
      icon: ShieldCheck,
      title: 'Segurança total',
      desc: 'Dados criptografados e isolados por escritório.',
    },
    {
      icon: TrendingUp,
      title: 'Visão em tempo real',
      desc: 'Dashboard com KPIs financeiros e de compliance.',
    },
    {
      icon: Zap,
      title: 'Automatize processos',
      desc: 'Prazos, documentos e certificados em um só lugar.',
    },
  ];

  return (
    <div
      className="relative hidden flex-col justify-between overflow-hidden bg-sidebar px-10 py-12 lg:flex"
      style={{ minWidth: 420 }}
    >
      {/* Fundo decorativo */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0">
        <div className="absolute -top-32 -right-32 h-[480px] w-[480px] rounded-full bg-primary/10 blur-3xl" />
        <div className="absolute -bottom-40 -left-20 h-[360px] w-[360px] rounded-full bg-sidebar-accent/15 blur-3xl" />
      </div>

      {/* Logo */}
      <div className="relative z-10 animate-fade-in-up">
        <Logo variant="full" theme="dark" size={38} />
      </div>

      {/* Headline */}
      <div className="relative z-10 space-y-4 animate-fade-in-up animation-delay-75">
        <h1 className="text-3xl font-bold leading-snug text-sidebar-foreground">
          Controle total da sua<br />
          <span className="text-sidebar-accent">operação contábil</span>
        </h1>
        <p className="text-sm leading-relaxed text-sidebar-muted">
          Gerencie clientes, documentos, certificados digitais e prazos
          fiscais com segurança e eficiência.
        </p>
      </div>

      {/* Features */}
      <div className="relative z-10 space-y-4">
        {features.map((f, i) => (
          <div
            key={f.title}
            className="animate-fade-in-up flex items-start gap-3"
            style={{ animationDelay: `${150 + i * 75}ms` }}
          >
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-sidebar-accent/15 ring-1 ring-sidebar-accent/20">
              <f.icon className="h-4 w-4 text-sidebar-accent" />
            </div>
            <div>
              <p className="text-sm font-semibold text-sidebar-foreground">{f.title}</p>
              <p className="text-xs text-sidebar-muted">{f.desc}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Rodapé */}
      <p className="relative z-10 text-xs text-sidebar-muted animate-fade-in animation-delay-300">
        © {new Date().getFullYear()} FiscWise · fiscwise.com.br
      </p>
    </div>
  );
}

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
    <div className="w-full max-w-sm space-y-6 animate-fade-in-up">
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
    </div>
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
    <div className="flex min-h-screen bg-background">
      <BrandPanel />

      {/* Painel direito — formulário */}
      <div className="flex flex-1 flex-col items-center justify-center px-6 py-12 animate-fade-in-up">
        {/* Logo mobile (esconde em lg) */}
        <div className="mb-8 lg:hidden">
          <Logo variant="full" theme="light" size={36} />
        </div>

        {/* 2FA screen OR normal login form */}
        {mfaChallenge ? (
          <TwoFAScreen
            method={mfaChallenge.two_factor_method}
            message={mfaChallenge.message}
            onVerify={verify2FA}
            onBack={cancelMfa}
            isLoading={isLoading}
          />
        ) : (
          <div className="w-full max-w-sm space-y-6">
            {/* Cabeçalho */}
            <div className="space-y-1 animate-fade-in-up animation-delay-75">
              <h2 className="text-2xl font-bold text-foreground">Bem-vindo de volta</h2>
              <p className="text-sm text-muted-foreground">
                Entre para acessar seu painel contábil.
              </p>
            </div>

            {/* Google login */}
            {import.meta.env.VITE_GOOGLE_CLIENT_ID && (
              <div
                className={cn(
                  'animate-fade-in-up animation-delay-150',
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

            {/* Divider */}
            <div className="animate-fade-in-up animation-delay-150 relative flex items-center gap-3">
              <div className="h-px flex-1 bg-border" />
              <span className="text-xs text-muted-foreground">ou continue com e-mail</span>
              <div className="h-px flex-1 bg-border" />
            </div>

            {/* Form */}
            <form
              onSubmit={handleSubmit}
              className="animate-fade-in-up animation-delay-225 space-y-4"
              noValidate
            >
              {/* E-mail */}
              <div className="space-y-1.5">
                <label htmlFor="email" className="text-sm font-medium text-foreground">
                  E-mail
                </label>
                <div className="relative">
                  <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="seu@email.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    disabled={isLoading}
                    className="pl-9"
                  />
                </div>
              </div>

              {/* Senha */}
              <div className="space-y-1.5">
                <label htmlFor="password" className="text-sm font-medium text-foreground">
                  Senha
                </label>
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
                    className="pl-9 pr-10"
                  />
                  <button
                    type="button"
                    tabIndex={-1}
                    onClick={() => setShowPass((s) => !s)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground"
                    aria-label={showPass ? 'Ocultar senha' : 'Exibir senha'}
                  >
                    {showPass ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              <Button type="submit" className="w-full" size="md" disabled={isLoading}>
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

            {/* Link registro */}
            <p className="animate-fade-in-up animation-delay-300 text-center text-sm text-muted-foreground">
              Não tem uma conta?{' '}
              <Link
                to="/register"
                className="font-semibold text-primary transition-colors hover:text-primary/80 hover:underline"
              >
                Criar conta grátis
              </Link>
            </p>
          </div>
        )}

        {/* Footer */}
        <footer className="animate-fade-in mt-auto pt-10 text-center">
          <p className="text-xs text-muted-foreground/70">
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
    </div>
  );
}
