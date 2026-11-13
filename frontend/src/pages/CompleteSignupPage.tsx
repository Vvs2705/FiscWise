import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { Building2 } from 'lucide-react';
import { Logo } from '@/components/Logo';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { FormField } from '@/components/ui/FormField';
import { api, getApiErrorMessage } from '@/lib/api';
import { completeSignup, fetchTenant } from '@/lib/auth';
import { useAuthStore } from '@/stores/authStore';

const schema = z.object({
  company_name: z.string().min(2, 'Nome deve ter ao menos 2 caracteres'),
  document: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

/**
 * Escritório sem cadastro concluído (p.ex. criado pelo antigo login Google
 * automático): o servidor recusa todo o sistema com 403 SIGNUP_INCOMPLETE até
 * o responsável informar o escritório e aceitar os Termos. A conta começa
 * com 14 dias de teste grátis do Premium (backend: onboarding.complete-signup).
 */
export function CompleteSignupPage() {
  const navigate = useNavigate();
  const { user, isAuthenticated, updateUser, logout } = useAuthStore();
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const isOwner = user?.role === 'owner';

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { company_name: '', document: '' },
  });

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login', { replace: true });
      return;
    }
    // Já concluído (ou concluído em outra aba): segue para o sistema.
    void api
      .get<{ signup_complete?: boolean }>('/api/v1/auth/me')
      .then(({ data }) => {
        if (data.signup_complete !== false) {
          updateUser({ signup_complete: true });
          navigate('/painel', { replace: true });
        }
      })
      .catch(() => undefined);
    void fetchTenant()
      .then((t) => form.reset({ company_name: t.name ?? '', document: t.document ?? '' }))
      .catch(() => undefined);
  }, [isAuthenticated, navigate, updateUser, form]);

  const onSubmit = async (values: FormValues) => {
    if (!termsAccepted) {
      setError('Você deve aceitar os Termos de Uso e a Política de Privacidade para continuar.');
      return;
    }
    setError(null);
    setSaving(true);
    try {
      await completeSignup({
        company_name: values.company_name,
        document: values.document || undefined,
        terms_accepted: true,
      });
      updateUser({ signup_complete: true });
      toast.success('Cadastro concluído!');
      navigate('/painel', { replace: true });
    } catch (err) {
      setError(getApiErrorMessage(err, 'Não foi possível concluir o cadastro. Tente novamente.'));
    } finally {
      setSaving(false);
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
            <h1 className="text-2xl font-bold tracking-[-0.02em]">Concluir cadastro</h1>
            <p className="text-sm text-muted-foreground">
              Antes de usar o FiscWise, informe o seu escritório e aceite os Termos de Uso. A conta
              começa com 14 dias de teste grátis do Premium, sem cartão; depois, assine o plano que
              preferir.
            </p>
          </div>

          {!isOwner ? (
            <div role="alert" className="space-y-4 text-sm">
              <p>
                O cadastro deste escritório ainda não foi concluído. Peça ao responsável pela conta
                para entrar e concluir o cadastro.
              </p>
              <Button type="button" variant="outline" className="w-full" onClick={() => logout('/login')}>
                Sair
              </Button>
            </div>
          ) : (
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4" noValidate>
              <FormField
                label="Nome do escritório / empresa"
                htmlFor="company_name"
                error={form.formState.errors.company_name?.message}
                required
              >
                <div className="relative">
                  <Building2 className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="company_name"
                    className="pl-9"
                    placeholder="Seu nome profissional ou marca contábil"
                    {...form.register('company_name')}
                  />
                </div>
              </FormField>

              <FormField label="CNPJ / CPF (opcional)" htmlFor="document">
                <Input id="document" placeholder="12.345.678/0001-90" {...form.register('document')} />
              </FormField>

              <label className="flex cursor-pointer items-start gap-3">
                <input
                  type="checkbox"
                  checked={termsAccepted}
                  onChange={(e) => {
                    setTermsAccepted(e.target.checked);
                    if (e.target.checked) setError(null);
                  }}
                  className="mt-0.5 h-4 w-4 shrink-0 cursor-pointer accent-primary"
                />
                <span className="text-xs leading-relaxed text-muted-foreground">
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

              {error && (
                <p role="alert" className="text-xs text-destructive">
                  {error}
                </p>
              )}

              <Button type="submit" className="w-full" disabled={saving}>
                {saving ? 'Salvando...' : 'Concluir cadastro'}
              </Button>
              <button
                type="button"
                onClick={() => logout('/login')}
                className="w-full text-center text-sm text-muted-foreground hover:text-foreground"
              >
                Sair
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
