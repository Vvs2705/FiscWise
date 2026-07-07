import { useState, useEffect } from 'react';
import {
  Users,
  Sparkles,
  Bot,
  CheckCircle2,
  ArrowRight,
  Lock,
  Loader2,
  Calendar,
  ExternalLink,
  ShieldCheck
} from 'lucide-react';
import { isAxiosError } from 'axios';
import { Dialog } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useCreateSubscription } from '@/lib/hooks/useBilling';
import { useSubscriptionUsage, type Plan } from '@/lib/hooks/useSubscription';
import { updateTenant } from '@/lib/auth';
import { toast } from 'sonner';
import { getApiErrorMessage } from '@/lib/api';

interface UpgradePlanoModalProps {
  open: boolean;
  onClose: () => void;
  selectedPlan: Plan | null;
  onUpgradeSuccess: (slug: string) => void;
}

// PCI: nenhum dado de cartão passa pelo FiscWise — o pagamento acontece no
// checkout hospedado do Asaas (pix/boleto/cartão à escolha do cliente).
export function UpgradePlanoModal({
  open,
  onClose,
  selectedPlan,
  onUpgradeSuccess
}: UpgradePlanoModalProps) {
  const [step, setStep] = useState<'checkout' | 'loading' | 'success'>('checkout');

  // Billing details (perfil de cobrança no Asaas)
  const [cnpjCpf, setCnpjCpf] = useState('');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');

  const createSub = useCreateSubscription();
  const { data: usage } = useSubscriptionUsage();

  // Reset states on open/close
  useEffect(() => {
    if (open) {
      setStep('checkout');
      setCnpjCpf('');
      setName('');
      setEmail('');
    }
  }, [open]);

  if (!selectedPlan) return null;

  // Format CNPJ/CPF
  const handleCnpjCpfChange = (val: string) => {
    const cleaned = val.replace(/\D/g, '');
    if (cleaned.length <= 11) {
      // CPF
      setCnpjCpf(cleaned.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/g, '$1.$2.$3-$4').substring(0, 14) || cleaned);
    } else {
      // CNPJ
      setCnpjCpf(cleaned.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/g, '$1.$2.$3/$4-$5').substring(0, 18) || cleaned);
    }
  };

  const isFormValid = () => {
    const digits = cnpjCpf.replace(/\D/g, '');
    return (digits.length === 11 || digits.length === 14) && name.length > 2 && email.includes('@');
  };

  const handleConfirm = async () => {
    if (!isFormValid()) {
      toast.warning('Por favor, preencha CPF/CNPJ, nome e e-mail.');
      return;
    }

    setStep('loading');

    try {
      const sub = await createSub.mutateAsync({
        plan_id: selectedPlan.id,
        billing_provider: 'asaas',
        cpf_cnpj: cnpjCpf.replace(/\D/g, ''),
        name,
        email
      });

      if (sub.checkout_url) {
        // Checkout hospedado do Asaas — o plano ativa via webhook após o pagamento
        toast.success('Redirecionando para o checkout seguro do Asaas...');
        window.location.href = sub.checkout_url;
        return;
      }

      // Modo dev/manual (sem gateway): ativa direto como antes
      await updateTenant({ plan_slug: selectedPlan.slug });
      setStep('success');
      onUpgradeSuccess(selectedPlan.slug);
      toast.success('Assinatura processada com sucesso!');
    } catch (err: unknown) {
      setStep('checkout');
      if (isAxiosError(err) && err.response?.status === 503) {
        toast.error('Cobrança temporariamente indisponível. Tente novamente em alguns minutos.');
      } else {
        toast.error(
          getApiErrorMessage(err, 'Erro ao processar assinatura no Asaas. Tente novamente.')
        );
      }
    }
  };

  const planPriceFormatted = selectedPlan.price_monthly
    ? Number(selectedPlan.price_monthly).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
    : 'Grátis';

  return (
    <Dialog
      open={open}
      onClose={() => step !== 'loading' && onClose()}
      title={step === 'success' ? 'Upgrade Concluído!' : `Upgrade para Plano ${selectedPlan.name}`}
      className="max-w-4xl"
    >
      {step === 'checkout' && (
        <div className="grid gap-6 lg:grid-cols-[1.4fr,1fr]">

          {/* Coluna Esquerda: Dados de Faturamento */}
          <div className="space-y-5">
            <div>
              <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">1</span>
                Dados de Faturamento (Asaas)
              </h3>
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className="text-[11px] font-medium text-muted-foreground uppercase">CPF / CNPJ do Pagador</label>
                  <Input
                    placeholder="000.000.000-00"
                    value={cnpjCpf}
                    onChange={(e) => handleCnpjCpfChange(e.target.value)}
                    className="mt-1"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-medium text-muted-foreground uppercase">Nome Completo / Razão Social</label>
                  <Input
                    placeholder="Seu nome ou empresa"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="mt-1"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="text-[11px] font-medium text-muted-foreground uppercase">E-mail Financeiro</label>
                  <Input
                    type="email"
                    placeholder="financeiro@email.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="mt-1"
                  />
                </div>
              </div>
            </div>

            {/* Como funciona o pagamento */}
            <div>
              <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">2</span>
                Pagamento no Checkout Seguro
              </h3>
              <div className="rounded-xl border border-border/80 bg-muted/20 p-4 space-y-3">
                <div className="flex items-start gap-3">
                  <ShieldCheck className="h-5 w-5 text-success shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-foreground">Você será redirecionado ao Asaas</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Escolha entre Pix, boleto ou cartão de crédito diretamente na página segura do Asaas.
                      Nenhum dado de cartão passa pelo FiscWise.
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <CheckCircle2 className="h-5 w-5 text-success shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-foreground">Ativação automática</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Assim que o pagamento for confirmado, seu plano é ativado automaticamente.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Coluna Direita: Resumo do Upgrade */}
          <div className="rounded-xl border bg-muted/20 p-5 flex flex-col justify-between space-y-6 h-fit border-border/80">
            <div className="space-y-4">
              <div>
                <p className="text-xs uppercase font-medium tracking-wide text-muted-foreground">Upgrade Escolhido</p>
                <h4 className="text-lg font-bold text-foreground mt-0.5">{selectedPlan.name}</h4>
                <p className="text-sm text-muted-foreground mt-1">{selectedPlan.description}</p>
              </div>

              {/* Price box */}
              <div className="bg-card rounded-lg border p-3 flex justify-between items-center">
                <span className="text-xs text-muted-foreground font-medium">Preço Mensal</span>
                <span className="text-lg font-extrabold text-foreground">{planPriceFormatted}</span>
              </div>

              {/* Comparison of features limits */}
              <div className="space-y-3 pt-2">
                <p className="text-[11px] uppercase font-bold text-muted-foreground tracking-wider">Capacidade Expandida</p>

                {/* Clientes */}
                <div className="space-y-1">
                  <div className="flex justify-between text-xs font-medium">
                    <span className="text-muted-foreground flex items-center gap-1.5">
                      <Users className="h-3.5 w-3.5" /> Clientes Ativos
                    </span>
                    <span className="text-foreground font-semibold">
                      {usage?.clients?.limit ?? '10'} <ArrowRight className="inline h-3 w-3 mx-1 text-muted-foreground" /> {selectedPlan.max_clients ?? 'Ilimitado'}
                    </span>
                  </div>
                </div>

                {/* Usuarios */}
                <div className="space-y-1">
                  <div className="flex justify-between text-xs font-medium">
                    <span className="text-muted-foreground flex items-center gap-1.5">
                      <Users className="h-3.5 w-3.5" /> Usuários
                    </span>
                    <span className="text-foreground font-semibold">
                      {usage?.users?.limit ?? '2'} <ArrowRight className="inline h-3 w-3 mx-1 text-muted-foreground" /> {selectedPlan.max_users ?? 'Ilimitado'}
                    </span>
                  </div>
                </div>

                {/* IA */}
                <div className="space-y-1">
                  <div className="flex justify-between text-xs font-medium">
                    <span className="text-muted-foreground flex items-center gap-1.5">
                      <Bot className="h-3.5 w-3.5" /> Consultas IA
                    </span>
                    <span className="text-foreground font-semibold">
                      {usage?.ai_calls_this_month?.limit ?? '0'} <ArrowRight className="inline h-3 w-3 mx-1 text-muted-foreground" /> {selectedPlan.max_ai_calls_month ?? 'Sem limite'}
                    </span>
                  </div>
                </div>

              </div>

              {/* Security info */}
              <div className="pt-2 border-t border-border/80 flex items-start gap-2 text-[10px] text-muted-foreground">
                <Lock className="h-3.5 w-3.5 shrink-0 text-success mt-0.5" />
                <span>Cobrança processada de forma segura pela Asaas S.A. Conexão criptografada SSL de 256 bits.</span>
              </div>
            </div>

            <div className="space-y-2">
              <Button
                className="w-full font-semibold shadow-token-sm py-5 flex items-center justify-center gap-2"
                onClick={handleConfirm}
                disabled={!isFormValid() || createSub.isPending}
              >
                Ir para o Pagamento <ExternalLink className="h-4 w-4" />
              </Button>

              <Button
                variant="ghost"
                className="w-full text-xs text-muted-foreground"
                onClick={onClose}
              >
                Cancelar e voltar
              </Button>
            </div>

          </div>

        </div>
      )}

      {step === 'loading' && (
        <div className="flex flex-col items-center justify-center py-16 text-center space-y-4">
          <Loader2 className="h-10 w-10 text-primary animate-spin" />
          <div className="space-y-1">
            <h4 className="text-base font-bold text-foreground">Conectando ao gateway Asaas...</h4>
            <p className="text-sm text-muted-foreground max-w-xs">
              Criando o perfil de cobrança e preparando o checkout seguro. Você será redirecionado em instantes.
            </p>
          </div>
        </div>
      )}

      {step === 'success' && (
        <div className="flex flex-col items-center justify-center py-10 text-center space-y-6 max-w-md mx-auto">
          <div className="relative">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-success/10 text-success animate-pulse border-2 border-success/20">
              <CheckCircle2 className="h-10 w-10" />
            </div>
            <Sparkles className="absolute -top-1 -right-1 h-5 w-5 text-warning animate-bounce" />
          </div>

          <div className="space-y-2">
            <h3 className="text-xl font-extrabold text-foreground">Assinatura confirmada! 🎉</h3>
            <p className="text-sm text-muted-foreground">
              Seu escritório foi atualizado com sucesso para o plano <span className="font-semibold text-foreground">{selectedPlan.name}</span>.
            </p>
          </div>

          {/* Details invoice box */}
          <div className="w-full bg-muted/30 border rounded-lg p-4 text-left text-xs space-y-2.5">
            <div className="flex justify-between border-b border-border/80 pb-2">
              <span className="text-muted-foreground">Novo Plano:</span>
              <span className="font-semibold text-foreground uppercase">{selectedPlan.name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Valor mensal:</span>
              <span className="font-semibold text-foreground">{planPriceFormatted}</span>
            </div>
            <div className="flex justify-between border-t border-border/80 pt-2 text-[10px] text-muted-foreground">
              <span className="flex items-center gap-1"><Calendar className="h-3 w-3" /> Primeira fatura gerada em:</span>
              <span>{new Date().toLocaleDateString('pt-BR')}</span>
            </div>
          </div>

          <Button
            className="w-full font-semibold shadow-token-sm py-4"
            onClick={onClose}
          >
            Começar a Usar Agora
          </Button>
        </div>
      )}
    </Dialog>
  );
}
