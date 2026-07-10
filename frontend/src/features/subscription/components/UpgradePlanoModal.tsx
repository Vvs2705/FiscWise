import { useEffect, useState } from 'react';
import { CreditCard, QrCode, Loader2, Lock, AlertTriangle, ExternalLink } from 'lucide-react';
import { Dialog } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import {
  useBillingConfig,
  useCheckout,
  type CicloCobranca,
  type MetodoPagamento,
} from '@/lib/hooks/useBilling';
import type { Plan, LinhaPreco } from '@/lib/hooks/useSubscription';
import { toast } from 'sonner';
import { getApiErrorMessage } from '@/lib/api';

interface UpgradePlanoModalProps {
  open: boolean;
  onClose: () => void;
  selectedPlan: Plan | null;
}

const brl = (v: number) =>
  v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

export function UpgradePlanoModal({ open, onClose, selectedPlan }: UpgradePlanoModalProps) {
  const [ciclo, setCiclo] = useState<CicloCobranca>('mensal');
  const [metodo, setMetodo] = useState<MetodoPagamento>('cartao');

  const { data: config } = useBillingConfig();
  const checkout = useCheckout();

  useEffect(() => {
    if (open) {
      setCiclo('mensal');
      setMetodo('cartao');
      checkout.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  if (!selectedPlan) return null;

  const linhas: LinhaPreco[] = selectedPlan.tabela_precos ?? [];
  const linha = linhas.find((l) => l.ciclo === ciclo) ?? null;

  // Mensal é assinatura recorrente — só cartão.
  const metodoEfetivo: MetodoPagamento = ciclo === 'mensal' ? 'cartao' : metodo;

  const goLive = config?.go_live === true;
  const processando = checkout.isPending || checkout.isSuccess; // isSuccess = redirecionando
  const podeConfirmar = goLive && linha !== null && !processando;

  const handleConfirm = () => {
    if (!linha) return;
    checkout.mutate(
      { plan_slug: selectedPlan.slug, ciclo: linha.ciclo, metodo: metodoEfetivo },
      {
        onSuccess: (data) => {
          if (data.init_point) {
            // Checkout Pro hospedado: o pagamento acontece no Mercado Pago.
            window.location.href = data.init_point;
          } else {
            toast.error('O gateway não retornou o link de pagamento. Tente novamente.');
            checkout.reset();
          }
        },
        onError: (err) => {
          toast.error(getApiErrorMessage(err, 'Erro ao iniciar o checkout. Tente novamente.'));
        },
      }
    );
  };

  return (
    <Dialog
      open={open}
      onClose={() => !processando && onClose()}
      title={`Assinar plano ${selectedPlan.name}`}
      className="max-w-2xl"
    >
      <div className="space-y-5">
        {/* Aviso honesto enquanto pagamentos não estão habilitados */}
        {config && !goLive && (
          <div className="flex items-start gap-2 rounded-lg border border-warning/30 bg-warning/10 p-3 text-sm text-warning">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>
              Pagamentos em ativação — em breve. A cobrança online ainda não está habilitada;
              nenhuma assinatura pode ser contratada neste momento.
            </span>
          </div>
        )}

        {linhas.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Este plano não possui contratação online. Entre em contato com o suporte.
          </p>
        ) : (
          <>
            {/* 1. Ciclo */}
            <div>
              <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-foreground">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">1</span>
                Ciclo de cobrança
              </h3>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {linhas.map((l) => (
                  <button
                    key={l.ciclo}
                    type="button"
                    onClick={() => setCiclo(l.ciclo)}
                    className={`rounded-lg border p-3 text-left transition-all ${
                      ciclo === l.ciclo
                        ? 'border-primary bg-primary/5 shadow-token-sm'
                        : 'border-border/80 hover:border-primary/50'
                    }`}
                  >
                    <p className="text-xs font-semibold text-foreground">{l.label}</p>
                    <p className="mt-1 text-sm font-bold text-foreground">
                      {l.ciclo === 'mensal' ? `${brl(l.preco_cheio)}/mês` : brl(l.pix_total)}
                    </p>
                    {l.desconto_pix_pct > 0 && (
                      <p className="text-[10px] font-medium text-success">
                        −{l.desconto_pix_pct}% no Pix
                      </p>
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* 2. Método */}
            <div>
              <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-foreground">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">2</span>
                Forma de pagamento
              </h3>
              {linha && (
                <div className="grid gap-2 sm:grid-cols-2">
                  {/* Pix */}
                  <button
                    type="button"
                    disabled={ciclo === 'mensal'}
                    onClick={() => setMetodo('pix')}
                    className={`rounded-lg border p-3 text-left transition-all disabled:cursor-not-allowed disabled:opacity-50 ${
                      metodoEfetivo === 'pix'
                        ? 'border-primary bg-primary/5 shadow-token-sm'
                        : 'border-border/80 hover:border-primary/50'
                    }`}
                  >
                    <p className="flex items-center gap-2 text-xs font-semibold text-foreground">
                      <QrCode className="h-4 w-4" /> Pix
                    </p>
                    {ciclo === 'mensal' ? (
                      <p className="mt-1 text-xs text-muted-foreground">
                        Indisponível no mensal — assinatura recorrente é só no cartão.
                      </p>
                    ) : (
                      <p className="mt-1 text-sm font-bold text-foreground">
                        {brl(linha.pix_total)}{' '}
                        {linha.desconto_pix_pct > 0 && (
                          <span className="text-xs font-semibold text-success">
                            (−{linha.desconto_pix_pct}%)
                          </span>
                        )}
                      </p>
                    )}
                  </button>

                  {/* Cartão */}
                  <button
                    type="button"
                    onClick={() => setMetodo('cartao')}
                    className={`rounded-lg border p-3 text-left transition-all ${
                      metodoEfetivo === 'cartao'
                        ? 'border-primary bg-primary/5 shadow-token-sm'
                        : 'border-border/80 hover:border-primary/50'
                    }`}
                  >
                    <p className="flex items-center gap-2 text-xs font-semibold text-foreground">
                      <CreditCard className="h-4 w-4" /> Cartão de crédito
                    </p>
                    {ciclo === 'mensal' ? (
                      <p className="mt-1 text-sm font-bold text-foreground">
                        {brl(linha.cartao_total)}/mês{' '}
                        <span className="text-xs font-normal text-muted-foreground">
                          (assinatura recorrente)
                        </span>
                      </p>
                    ) : (
                      <p className="mt-1 text-sm font-bold text-foreground">
                        {brl(linha.cartao_total)}{' '}
                        <span className="text-xs font-normal text-muted-foreground">
                          em até {linha.cartao_max_parcelas}x de {brl(linha.cartao_parcela)} sem juros
                        </span>
                        {linha.desconto_cartao_pct > 0 && (
                          <span className="ml-1 text-xs font-semibold text-success">
                            (−{linha.desconto_cartao_pct}%)
                          </span>
                        )}
                      </p>
                    )}
                  </button>
                </div>
              )}
            </div>

            {/* Resumo */}
            {linha && (
              <div className="flex items-center justify-between rounded-lg border bg-muted/20 p-3">
                <div>
                  <p className="text-xs text-muted-foreground">
                    {selectedPlan.name} · {linha.label} ·{' '}
                    {metodoEfetivo === 'pix' ? 'Pix' : 'Cartão'}
                  </p>
                  <p className="text-lg font-extrabold text-foreground">
                    {brl(metodoEfetivo === 'pix' ? linha.pix_total : linha.cartao_total)}
                    {ciclo === 'mensal' && <span className="text-sm font-normal">/mês</span>}
                  </p>
                </div>
                <p className="max-w-[45%] text-right text-[11px] text-muted-foreground">{linha.obs}</p>
              </div>
            )}

            {/* Segurança: nenhum dado de cartão é digitado aqui */}
            <div className="flex items-start gap-2 text-[11px] text-muted-foreground">
              <Lock className="mt-0.5 h-3.5 w-3.5 shrink-0 text-success" />
              <span>
                Você será redirecionado para o ambiente seguro do Mercado Pago para concluir o
                pagamento. O FiscWise não coleta nem armazena dados do seu cartão.
              </span>
            </div>

            <div className="space-y-2">
              <Button
                className="flex w-full items-center justify-center gap-2 py-5 font-semibold shadow-token-sm"
                onClick={handleConfirm}
                disabled={!podeConfirmar}
              >
                {processando ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" /> Redirecionando ao Mercado Pago...
                  </>
                ) : (
                  <>
                    Continuar para o Mercado Pago <ExternalLink className="h-4 w-4" />
                  </>
                )}
              </Button>
              <Button
                variant="ghost"
                className="w-full text-xs text-muted-foreground"
                onClick={onClose}
                disabled={processando}
              >
                Cancelar e voltar
              </Button>
            </div>
          </>
        )}
      </div>
    </Dialog>
  );
}
