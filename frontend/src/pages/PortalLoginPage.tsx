'use client';

import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import { Loader2, ShieldCheck, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { useAuthStore } from '@/stores/authStore';
import { api } from '@/lib/api';

// ---------------------------------------------------------------------------
// Portal Login — handles magic link token verification from URL
// ---------------------------------------------------------------------------

export function PortalLoginPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const login = useAuthStore((state) => state.setUser);

  const [phase, setPhase] = useState<'verifying' | 'success' | 'error'>('verifying');
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    const token = searchParams.get('token');
    if (!token) {
      setPhase('error');
      setErrorMessage('Link inválido — nenhum token encontrado na URL.');
      return;
    }

    verifyToken(token);
  }, [searchParams]);

  async function verifyToken(token: string) {
    try {
      const res = await api.post('/api/v1/portal/magic-link/verify', { token });
      const { access_token, tenant_id, email } = res.data;

      // Store auth credentials in localStorage (same pattern as regular login)
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('tenant_id', tenant_id);
      const portalUser = { id: '', email, full_name: '', phone: undefined, role: 'client' };
      localStorage.setItem('user', JSON.stringify(portalUser));
      login(portalUser);

      setPhase('success');
      toast.success('Bem-vindo ao portal!');

      // Brief pause so the user sees the success state
      setTimeout(() => {
        navigate('/portal/dashboard', { replace: true });
      }, 1500);
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' &&
        err !== null &&
        'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      setPhase('error');
      setErrorMessage(detail ?? 'Não foi possível verificar o link. Tente novamente.');
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm space-y-6 text-center">
        {/* Logo / Brand */}
        <div className="flex justify-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
            <ShieldCheck className="h-7 w-7" />
          </div>
        </div>
        <div>
          <h1 className="text-2xl font-bold">Portal do Cliente</h1>
          <p className="mt-1 text-sm text-muted-foreground">FiscWise</p>
        </div>

        {/* States */}
        {phase === 'verifying' && (
          <div className="rounded-xl border border-border bg-card p-8 shadow-sm">
            <Loader2 className="mx-auto mb-4 h-8 w-8 animate-spin text-primary" />
            <p className="font-medium">Verificando seu link de acesso...</p>
            <p className="mt-1 text-sm text-muted-foreground">Aguarde um momento.</p>
          </div>
        )}

        {phase === 'success' && (
          <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-8 shadow-sm">
            <CheckCircle2 className="mx-auto mb-4 h-8 w-8 text-emerald-500" />
            <p className="font-semibold text-emerald-600">Acesso verificado!</p>
            <p className="mt-1 text-sm text-muted-foreground">Redirecionando para o portal...</p>
          </div>
        )}

        {phase === 'error' && (
          <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-8 shadow-sm">
            <div className="mx-auto mb-4 flex h-8 w-8 items-center justify-center rounded-full bg-destructive/10 text-destructive">
              <span className="text-lg font-bold">!</span>
            </div>
            <p className="font-semibold text-destructive">Link inválido ou expirado</p>
            <p className="mt-2 text-sm text-muted-foreground">{errorMessage}</p>
            <p className="mt-3 text-xs text-muted-foreground">
              Entre em contato com seu escritório contábil para solicitar um novo link de acesso.
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-4"
              onClick={() => window.location.reload()}
            >
              Tentar novamente
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
