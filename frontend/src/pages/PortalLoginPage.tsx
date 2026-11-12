'use client';

import { useState, useEffect, useCallback, useRef, type FormEvent } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';
import { Loader2, ShieldCheck, CheckCircle2, Mail } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useAuthStore } from '@/stores/authStore';
import { api, getApiErrorMessage } from '@/lib/api';
import { useSelfRequestPortalLink } from '@/features/portal/api';

// ---------------------------------------------------------------------------
// Portal Login — verifica o link mágico da URL ou deixa o cliente pedir um novo
// ---------------------------------------------------------------------------

type Phase = 'verifying' | 'success' | 'error' | 'request' | 'requested';

export function PortalLoginPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const login = useAuthStore((state) => state.setUser);

  const [phase, setPhase] = useState<Phase>('verifying');
  const [errorMessage, setErrorMessage] = useState('');
  const [email, setEmail] = useState('');
  const [requestedMessage, setRequestedMessage] = useState('');
  const selfRequest = useSelfRequestPortalLink();
  // O token é de uso único: nunca verificar o mesmo duas vezes (StrictMode, re-render).
  const verifiedToken = useRef<string | null>(null);

  const verifyToken = useCallback(
    async (token: string) => {
      try {
        const res = await api.post('/api/v1/portal/magic-link/verify', { token });
        const { access_token, tenant_id, email: userEmail } = res.data;

        localStorage.setItem('access_token', access_token);
        localStorage.setItem('tenant_id', tenant_id);
        const portalUser = { id: '', email: userEmail, full_name: '', phone: undefined, role: 'client' };
        localStorage.setItem('user', JSON.stringify(portalUser));
        login(portalUser);

        setPhase('success');
        toast.success('Bem-vindo ao portal!');

        setTimeout(() => {
          navigate('/portal/dashboard', { replace: true });
        }, 1500);
      } catch (err: unknown) {
        setPhase('error');
        setErrorMessage(
          getApiErrorMessage(err, 'Não foi possível verificar o link.')
        );
      }
    },
    [login, navigate]
  );

  useEffect(() => {
    const token = searchParams.get('token');
    if (!token) {
      setPhase(current => (current === 'requested' ? current : 'request'));
      return;
    }
    if (verifiedToken.current === token) return;
    verifiedToken.current = token;
    setPhase('verifying');
    void verifyToken(token);
  }, [searchParams, verifyToken]);

  const askNewLink = () => {
    setErrorMessage('');
    setPhase('request');
    // Tira o token usado da URL para não ser verificado de novo.
    navigate('/portal/login', { replace: true });
  };

  const submitRequest = async (e: FormEvent) => {
    e.preventDefault();
    const trimmed = email.trim();
    if (!trimmed) return;
    try {
      const res = await selfRequest.mutateAsync(trimmed);
      setRequestedMessage(res.message);
      setPhase('requested');
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Não foi possível pedir o link agora. Tente mais tarde.'));
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm space-y-6 text-center">
        <div className="flex justify-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-card bg-primary/10 text-primary">
            <ShieldCheck className="h-7 w-7" />
          </div>
        </div>
        <div>
          <h1 className="text-2xl font-bold">Portal do Cliente</h1>
          <p className="mt-1 text-sm text-muted-foreground">FiscWise</p>
        </div>

        {phase === 'verifying' && (
          <div className="rounded-xl border border-border bg-card p-8 shadow-sm">
            <Loader2 className="mx-auto mb-4 h-8 w-8 animate-spin text-primary" />
            <p className="font-medium">Verificando seu link de acesso...</p>
            <p className="mt-1 text-sm text-muted-foreground">Aguarde um momento.</p>
          </div>
        )}

        {phase === 'success' && (
          <div className="rounded-xl border border-success/20 bg-success/5 p-8 shadow-sm">
            <CheckCircle2 className="mx-auto mb-4 h-8 w-8 text-success" />
            <p className="font-semibold text-success">Acesso verificado!</p>
            <p className="mt-1 text-sm text-muted-foreground">Redirecionando para o portal...</p>
          </div>
        )}

        {phase === 'request' && (
          <form
            onSubmit={e => void submitRequest(e)}
            className="space-y-4 rounded-xl border border-border bg-card p-6 text-left shadow-sm"
          >
            <div>
              <p className="font-semibold text-foreground">Receba seu link de acesso</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Informe o e-mail cadastrado no seu escritório contábil. Enviaremos um link de uso
                único, válido por 24 horas.
              </p>
            </div>
            <label className="block space-y-1">
              <span className="text-xs font-medium text-foreground">E-mail</span>
              <Input
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="voce@empresa.com.br"
              />
            </label>
            <Button type="submit" className="w-full gap-1.5" disabled={selfRequest.isPending}>
              {selfRequest.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Mail className="h-4 w-4" />}
              Enviar link de acesso
            </Button>
          </form>
        )}

        {phase === 'requested' && (
          <div className="rounded-xl border border-border bg-card p-8 shadow-sm">
            <Mail className="mx-auto mb-4 h-8 w-8 text-primary" />
            <p className="font-semibold text-foreground">Verifique seu e-mail</p>
            <p className="mt-2 text-sm text-muted-foreground">{requestedMessage}</p>
            <p className="mt-3 text-xs text-muted-foreground">
              Não chegou? Confira a caixa de spam ou peça ao seu escritório para confirmar o seu
              e-mail cadastrado.
            </p>
            <Button variant="outline" size="sm" className="mt-4" onClick={() => setPhase('request')}>
              Usar outro e-mail
            </Button>
          </div>
        )}

        {phase === 'error' && (
          <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-8 shadow-sm">
            <div className="mx-auto mb-4 flex h-8 w-8 items-center justify-center rounded-full bg-destructive/10 text-destructive">
              <span className="text-lg font-bold">!</span>
            </div>
            <p className="font-semibold text-destructive">Link inválido ou expirado</p>
            <p className="mt-2 text-sm text-muted-foreground">{errorMessage}</p>
            <Button variant="outline" size="sm" className="mt-4" onClick={askNewLink}>
              Pedir novo link
            </Button>
          </div>
        )}

        <p className="text-xs text-muted-foreground">
          Acesso seguro via link mágico de uso único
        </p>
      </div>
    </div>
  );
}

export default PortalLoginPage;
