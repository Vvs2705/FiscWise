import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { isAxiosError } from 'axios';
import { Lock, Eye, EyeOff, CheckCircle2, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Logo } from '@/components/Logo';
import { resetPassword, getApiErrorMessage } from '@/lib/api';

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') ?? '';

  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showPass, setShowPass] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState<'form' | 'success' | 'invalid'>(token ? 'form' : 'invalid');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    // Mesmas regras do RegisterPage: mínimo 8 caracteres + confirmação
    if (password.length < 8) {
      setError('Senha deve ter ao menos 8 caracteres');
      return;
    }
    if (password !== confirm) {
      setError('As senhas não coincidem');
      return;
    }
    setError('');
    setIsLoading(true);
    try {
      await resetPassword(token, password);
      setStatus('success');
    } catch (err) {
      if (isAxiosError(err) && err.response?.status === 400) {
        setStatus('invalid');
      } else {
        setError(getApiErrorMessage(err, 'Não foi possível redefinir a senha. Tente novamente.'));
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      className="flex min-h-screen flex-col items-center justify-center bg-muted px-5 py-8 text-foreground"
      style={{
        background:
          'radial-gradient(circle at 70% 20%, hsl(var(--primary) / 0.12), transparent 28%), radial-gradient(circle at 20% 80%, hsl(var(--info) / 0.10), transparent 26%), linear-gradient(135deg, hsl(var(--muted)) 0%, hsl(var(--muted)) 100%)',
      }}
    >
      <div className="mb-8">
        <span className="dark:hidden"><Logo variant="full" theme="light" size={34} /></span>
        <span className="hidden dark:block"><Logo variant="full" theme="dark" size={34} /></span>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: 'easeOut' }}
        className="w-full max-w-md rounded-[28px] border border-border bg-card/95 p-6 shadow-token backdrop-blur-xl sm:p-8"
      >
        {status === 'success' && (
          <div className="flex flex-col items-center gap-4 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-card bg-success/10 ring-2 ring-success/20">
              <CheckCircle2 className="h-8 w-8 text-success" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">Senha redefinida</h1>
              <p className="mt-2 text-sm text-muted-foreground">
                Sua senha foi alterada com sucesso. Faça login com a nova senha.
              </p>
            </div>
            <Link to="/login" className="w-full">
              <Button className="w-full">Ir para o login</Button>
            </Link>
          </div>
        )}

        {status === 'invalid' && (
          <div className="flex flex-col items-center gap-4 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-card bg-destructive/10 ring-2 ring-destructive/20">
              <AlertTriangle className="h-8 w-8 text-destructive" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">Link inválido ou expirado</h1>
              <p className="mt-2 text-sm text-muted-foreground">
                Este link de redefinição não é mais válido. Solicite um novo para continuar.
              </p>
            </div>
            <Link to="/forgot-password" className="w-full">
              <Button className="w-full">Pedir novo link</Button>
            </Link>
            <Link
              to="/login"
              className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              Voltar para o login
            </Link>
          </div>
        )}

        {status === 'form' && (
          <>
            <div className="mb-6 space-y-1.5">
              <h1 className="text-2xl font-bold tracking-[-0.02em] text-foreground">
                Criar nova senha
              </h1>
              <p className="text-sm leading-normal text-muted-foreground">
                Escolha uma nova senha com ao menos 8 caracteres para acessar sua conta.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4" noValidate>
              <div className="space-y-1.5">
                <label htmlFor="new_password" className="text-sm font-medium text-foreground">
                  Nova senha
                </label>
                <div className="relative">
                  <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="new_password"
                    type={showPass ? 'text' : 'password'}
                    placeholder="Mínimo 8 caracteres"
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

              <div className="space-y-1.5">
                <label htmlFor="confirm_password" className="text-sm font-medium text-foreground">
                  Confirmar senha
                </label>
                <div className="relative">
                  <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="confirm_password"
                    type="password"
                    placeholder="Repita a senha"
                    value={confirm}
                    onChange={(e) => setConfirm(e.target.value)}
                    required
                    disabled={isLoading}
                    className="h-11 rounded-xl border-border bg-background pl-10 text-foreground shadow-sm"
                  />
                </div>
              </div>

              {error && <p className="text-sm text-destructive">{error}</p>}

              <Button
                type="submit"
                className="h-11 w-full rounded-xl"
                disabled={isLoading || !password || !confirm}
              >
                {isLoading ? (
                  <span className="flex items-center gap-2">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                    Redefinindo...
                  </span>
                ) : (
                  'Redefinir senha'
                )}
              </Button>
            </form>

            <p className="mt-4 text-center text-sm text-muted-foreground">
              Lembrou a senha?{' '}
              <Link
                to="/login"
                className="font-semibold text-primary transition-colors hover:text-primary/80 hover:underline"
              >
                Fazer login
              </Link>
            </p>
          </>
        )}
      </motion.div>
    </div>
  );
}
