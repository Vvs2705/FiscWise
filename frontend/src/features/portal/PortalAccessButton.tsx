import { useState } from 'react';
import { toast } from 'sonner';
import { Copy, KeyRound, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { Input } from '@/components/ui/Input';
import { getApiErrorMessage } from '@/lib/api';
import { describePortalAccessResult, useRequestPortalAccess } from './api';

interface PortalAccessButtonProps {
  clientId: string;
  clientName: string;
  clientEmail?: string | null;
  size?: 'sm' | 'md';
}

/**
 * "Enviar link de acesso ao portal": garante o acesso do cliente (sem senha)
 * e manda o link de uso único por e-mail. Sem e-mail configurado no servidor,
 * mostra o link para o escritório copiar.
 */
export function PortalAccessButton({ clientId, clientName, clientEmail, size = 'sm' }: PortalAccessButtonProps) {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState(clientEmail ?? '');
  const [manualLink, setManualLink] = useState<string | null>(null);
  const mutation = useRequestPortalAccess();

  const openDialog = () => {
    setEmail(clientEmail ?? '');
    setManualLink(null);
    setOpen(true);
  };

  const send = async () => {
    const trimmed = email.trim();
    if (!trimmed) {
      toast.error('Informe o e-mail do cliente.');
      return;
    }
    try {
      const result = await mutation.mutateAsync({ clientId, email: trimmed });
      const outcome = describePortalAccessResult(result);
      if (outcome.kind === 'sent') {
        toast.success(outcome.message);
        setOpen(false);
      } else if (outcome.kind === 'manual') {
        toast.warning(outcome.message);
        setManualLink(outcome.link);
      } else {
        toast.error(outcome.message);
      }
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Não foi possível gerar o link de acesso.'));
    }
  };

  const copy = async () => {
    if (!manualLink) return;
    try {
      await navigator.clipboard.writeText(manualLink);
      toast.success('Link copiado.');
    } catch {
      toast.error('Não foi possível copiar. Selecione o link e copie manualmente.');
    }
  };

  return (
    <>
      <Button variant="outline" size={size} className="gap-1.5" onClick={openDialog}>
        <KeyRound className="h-4 w-4" />
        Enviar link de acesso ao portal
      </Button>

      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        title="Acesso ao portal do cliente"
        footer={
          manualLink ? (
            <Button variant="outline" onClick={() => setOpen(false)}>Fechar</Button>
          ) : (
            <>
              <Button variant="outline" onClick={() => setOpen(false)}>Cancelar</Button>
              <Button onClick={() => void send()} disabled={mutation.isPending} className="gap-1.5">
                {mutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                Enviar link
              </Button>
            </>
          )
        }
      >
        {manualLink ? (
          <div className="space-y-3 text-sm">
            <p className="rounded-lg border border-warning/30 bg-warning/5 p-3 text-warning">
              O envio de e-mail não está configurado neste servidor. Copie o link abaixo e envie
              ao cliente por um canal seguro. Ele vale por 24 horas e só funciona uma vez.
            </p>
            <div className="flex gap-2">
              <Input readOnly value={manualLink} aria-label="Link de acesso ao portal" onFocus={e => e.target.select()} />
              <Button variant="outline" onClick={() => void copy()} className="shrink-0 gap-1.5">
                <Copy className="h-4 w-4" />
                Copiar
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-3 text-sm">
            <p className="text-muted-foreground">
              {clientName} receberá um link de uso único (válido por 24 horas) para entrar no
              portal sem senha.
            </p>
            <label className="block space-y-1">
              <span className="text-xs font-medium text-foreground">E-mail do cliente</span>
              <Input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="cliente@empresa.com.br"
                autoFocus
              />
            </label>
          </div>
        )}
      </Dialog>
    </>
  );
}
