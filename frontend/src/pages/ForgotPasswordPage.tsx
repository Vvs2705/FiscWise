import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Mail, MailCheck, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Logo } from '@/components/Logo';
import { requestPasswordReset, getApiErrorMessage } from '@/lib/api';

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    try {
      await requestPasswordReset(email);
      setSent(true);
    } catch (err) {
      setError(getApiErrorMessage(err, 'Não foi possível enviar a solicitação. Tente novamente.'));
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
        {sent ? (
          <div className="flex flex-col items-center gap-4 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-card bg-primary/10 ring-2 ring-primary/20">
              <MailCheck className="h-8 w-8 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">Verifique seu e-mail</h1>
              <p className="mt-2 text-sm text-muted-foreground">
                Se o e-mail existir em nossa base, enviaremos instruções para redefinir sua senha.
              </p>
            </div>
            <Link to="/login" className="w-full">
              <Button variant="outline" className="w-full gap-1.5">
                <ArrowLeft className="h-4 w-4" />
                Voltar para o login
              </Button>
            </Link>
          </div>
        ) : (
          <>
            <div className="mb-6 space-y-1.5">
              <h1 className="text-2xl font-bold tracking-[-0.02em] text-foreground">
                Esqueceu sua senha?
              </h1>
              <p className="text-sm leading-normal text-muted-foreground">
                Informe o e-mail da sua conta e enviaremos um link para criar uma nova senha.
              </p>
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

              {error && <p className="text-sm text-destructive">{error}</p>}

              <Button type="submit" className="h-11 w-full rounded-xl" disabled={isLoading || !email}>
                {isLoading ? (
                  <span className="flex items-center gap-2">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                    Enviando...
                  </span>
                ) : (
                  'Enviar instruções'
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
