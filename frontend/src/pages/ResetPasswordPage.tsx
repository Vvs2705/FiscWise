import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { ArrowLeft, Eye, EyeOff, Lock } from 'lucide-react';
import { Logo } from '@/components/Logo';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { FormField } from '@/components/ui/FormField';
import { getApiErrorMessage } from '@/lib/api';
import { confirmPasswordReset, newPasswordError } from '@/lib/auth';

const schema = z
  .object({
    new_password: z.string(),
    confirm_password: z.string().min(1, 'Confirme a senha'),
  })
  .superRefine((d, ctx) => {
    const problem = newPasswordError(d.new_password);
    if (problem) ctx.addIssue({ code: z.ZodIssueCode.custom, message: problem, path: ['new_password'] });
    if (d.new_password !== d.confirm_password) {
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: 'As senhas não coincidem', path: ['confirm_password'] });
    }
  });
type FormValues = z.infer<typeof schema>;

export function ResetPasswordPage() {
  const [params] = useSearchParams();
  const token = params.get('token') ?? '';
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { new_password: '', confirm_password: '' },
  });

  const onSubmit = async ({ new_password }: FormValues) => {
    setError(null);
    try {
      await confirmPasswordReset(token, new_password);
      toast.success('Senha redefinida. Entre com a nova senha.');
      navigate('/login', { replace: true });
    } catch (err) {
      setError(getApiErrorMessage(err, 'Não foi possível redefinir a senha. Solicite um novo link.'));
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted px-4 py-10 text-foreground">
      <div className="w-full max-w-[440px] space-y-6">
        <div className="flex justify-center">
          <Logo variant="full" theme="light" size={32} />
        </div>

        <div className="rounded-[24px] border border-border bg-white/90 p-6 shadow-token sm:p-8">
          <div className="mb-6 space-y-1.5">
            <h1 className="text-2xl font-bold tracking-[-0.02em]">Criar nova senha</h1>
            <p className="text-sm text-muted-foreground">
              Ao salvar, todas as sessões abertas da sua conta serão encerradas.
            </p>
          </div>

          {!token ? (
            <div role="alert" className="space-y-4 text-sm">
              <p>Este link de redefinição está incompleto. Solicite um novo link pelo e-mail da sua conta.</p>
              <Link to="/esqueci-senha" className="font-medium text-primary hover:text-primary/80">
                Solicitar novo link
              </Link>
            </div>
          ) : (
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4" noValidate>
              <FormField
                label="Nova senha"
                htmlFor="new_password"
                error={form.formState.errors.new_password?.message}
                required
              >
                <div className="relative">
                  <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="new_password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    placeholder="Mínimo de 8 caracteres"
                    className="pl-9 pr-10"
                    {...form.register('new_password')}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </FormField>

              <FormField
                label="Confirmar nova senha"
                htmlFor="confirm_password"
                error={form.formState.errors.confirm_password?.message}
                required
              >
                <div className="relative">
                  <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="confirm_password"
                    type="password"
                    autoComplete="new-password"
                    placeholder="Repita a senha"
                    className="pl-9"
                    {...form.register('confirm_password')}
                  />
                </div>
              </FormField>

              {error && (
                <div role="alert" className="space-y-1 text-sm text-destructive">
                  <p>{error}</p>
                  <Link to="/esqueci-senha" className="font-medium text-primary hover:text-primary/80">
                    Solicitar novo link
                  </Link>
                </div>
              )}

              <Button type="submit" className="w-full" disabled={form.formState.isSubmitting}>
                {form.formState.isSubmitting ? 'Salvando...' : 'Salvar nova senha'}
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
