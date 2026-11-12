import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { AlertTriangle, ArrowLeft, Mail, MailCheck } from 'lucide-react';
import { Logo } from '@/components/Logo';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { FormField } from '@/components/ui/FormField';
import { getApiErrorMessage } from '@/lib/api';
import { passwordResetAvailable, requestPasswordReset } from '@/lib/auth';

const schema = z.object({
  email: z.string().trim().email('E-mail inválido'),
});
type FormValues = z.infer<typeof schema>;

export function ForgotPasswordPage() {
  // null = ainda verificando (ou não deu para saber): não mostra aviso.
  const [available, setAvailable] = useState<boolean | null>(null);
  const [sentMessage, setSentMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const form = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { email: '' } });

  useEffect(() => {
    let active = true;
    passwordResetAvailable()
      .then((ok) => active && setAvailable(ok))
      .catch(() => active && setAvailable(null));
    return () => {
      active = false;
    };
  }, []);

  const onSubmit = async ({ email }: FormValues) => {
    setError(null);
    try {
      const { message } = await requestPasswordReset(email);
      setSentMessage(message);
    } catch (err) {
      setError(getApiErrorMessage(err, 'Não foi possível enviar o pedido. Tente novamente.'));
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted px-4 py-10 text-foreground">
      <div className="w-full max-w-[440px] space-y-6">
        <div className="flex justify-center">
          <Logo variant="full" theme="auto" size={32} />
        </div>

        <div className="rounded-[24px] border border-border bg-card p-6 text-card-foreground shadow-token sm:p-8">
          <div className="mb-6 space-y-1.5">
            <h1 className="text-2xl font-bold tracking-[-0.02em]">Esqueci minha senha</h1>
            <p className="text-sm text-muted-foreground">
              Informe o e-mail da sua conta. Enviaremos um link para criar uma nova senha.
            </p>
          </div>

          {available === false && (
            <div
              role="alert"
              className="mb-5 flex gap-2.5 rounded-xl border border-warning/40 bg-warning/10 p-3 text-sm"
            >
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
              <p>
                A recuperação de senha por e-mail está indisponível nesta instalação. Fale com o suporte
                para redefinir o seu acesso.
              </p>
            </div>
          )}

          {sentMessage ? (
            <div role="status" className="space-y-4">
              <div className="flex gap-2.5 rounded-xl border border-success/40 bg-success/10 p-3 text-sm">
                <MailCheck className="mt-0.5 h-4 w-4 shrink-0 text-success" />
                <p>{sentMessage} Confira também a caixa de spam. O link vale por 1 hora.</p>
              </div>
              <Button variant="outline" className="w-full" onClick={() => setSentMessage(null)}>
                Enviar para outro e-mail
              </Button>
            </div>
          ) : (
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4" noValidate>
              <FormField label="E-mail" htmlFor="email" error={form.formState.errors.email?.message} required>
                <div className="relative">
                  <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="email"
                    type="email"
                    autoComplete="email"
                    placeholder="voce@escritorio.com.br"
                    className="pl-9"
                    {...form.register('email')}
                  />
                </div>
              </FormField>

              {error && (
                <p role="alert" className="text-sm text-destructive">
                  {error}
                </p>
              )}

              <Button type="submit" className="w-full" disabled={form.formState.isSubmitting}>
                {form.formState.isSubmitting ? 'Enviando...' : 'Enviar link de redefinição'}
              </Button>
            </form>
          )}
        </div>

        <Link
          to="/login"
          className="mx-auto flex w-fit items-center gap-1.5 text-sm font-medium text-primary hover:text-primary/80"
        >
          <ArrowLeft className="h-4 w-4" />
          Voltar para o login
        </Link>
      </div>
    </div>
  );
}
