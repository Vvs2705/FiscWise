'use client';

import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { toast } from 'sonner';
import { Loader2, ShieldCheck, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { api, getApiErrorMessage } from '@/lib/api';

// ---------------------------------------------------------------------------
// Portal Invite - client accepts an invitation and creates the portal account
// ---------------------------------------------------------------------------

export function PortalInvitePage() {
  const { inviteId } = useParams<{ inviteId: string }>();
  const navigate = useNavigate();

  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [phase, setPhase] = useState<'form' | 'success' | 'error'>('form');
  const [errorMessage, setErrorMessage] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 8) {
      toast.error('A senha precisa ter pelo menos 8 caracteres.');
      return;
    }
    if (password !== confirm) {
      toast.error('As senhas nao coincidem.');
      return;
    }
    setSubmitting(true);
    try {
      await api.post(`/api/v1/portal/invites/${inviteId}/accept`, {
        invite_id: inviteId,
        password,
        full_name: fullName,
      });
      setPhase('success');
      toast.success('Conta criada com sucesso!');
    } catch (err: unknown) {
      setPhase('error');
      setErrorMessage(
        getApiErrorMessage(err, 'Nao foi possivel aceitar o convite. Tente novamente.')
      );
    } finally {
      setSubmitting(false);
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
          <p className="mt-1 text-sm text-muted-foreground">
            Voce foi convidado pelo seu escritorio contabil
          </p>
        </div>

        {phase === 'form' && (
          <form
            onSubmit={handleSubmit}
            className="space-y-4 rounded-xl border border-border bg-card p-6 text-left shadow-sm"
          >
            <div className="space-y-1.5">
              <label htmlFor="full_name" className="text-sm font-medium">Seu nome completo</label>
              <Input
                id="full_name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
                maxLength={255}
                autoComplete="name"
              />
            </div>
            <div className="space-y-1.5">
              <label htmlFor="password" className="text-sm font-medium">Crie uma senha</label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                autoComplete="new-password"
              />
              <p className="text-xs text-muted-foreground">Minimo de 8 caracteres.</p>
            </div>
            <div className="space-y-1.5">
              <label htmlFor="confirm" className="text-sm font-medium">Confirme a senha</label>
              <Input
                id="confirm"
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
                minLength={8}
                autoComplete="new-password"
              />
            </div>
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              Criar minha conta
            </Button>
          </form>
        )}

        {phase === 'success' && (
          <div className="rounded-xl border border-success/20 bg-success/5 p-8 shadow-sm">
            <CheckCircle2 className="mx-auto mb-4 h-8 w-8 text-success" />
            <p className="font-semibold text-success">Conta criada!</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Entre com seu e-mail e a senha que acabou de criar.
            </p>
            <Button className="mt-4 w-full" onClick={() => navigate('/login', { replace: true })}>
              Ir para o login
            </Button>
          </div>
        )}

        {phase === 'error' && (
          <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-8 shadow-sm">
            <p className="font-semibold text-destructive">Convite invalido ou expirado</p>
            <p className="mt-2 text-sm text-muted-foreground">{errorMessage}</p>
            <p className="mt-3 text-xs text-muted-foreground">
              Peca ao seu escritorio contabil para enviar um novo convite.
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-4"
              onClick={() => setPhase('form')}
            >
              Tentar novamente
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

export default PortalInvitePage;
