import { useState } from 'react';
import { CreditCard, ExternalLink, Gift, QrCode } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { getApiErrorMessage } from '@/lib/api';
import {
  dataOferta,
  useBillingConfig,
  useCheckout,
  useOferta,
  type CicloCobranca,
  type MetodoPagamento,
  type OfertaPlano,
} from '@/lib/hooks/useBilling';

const brl = (v: number) => v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

/**
 * Oferta especial para quem não assinou depois do teste grátis
 * (15% no 1º mês do mensal no cartão ou anual com 25%, por 7 dias).
 * O preço mostrado vem do servidor e é recalculado no checkout.
 */
export function OfertaReconquista() {
  const { data: oferta } = useOferta();
  const { data: config } = useBillingConfig();
  const checkout = useCheckout();
  const [escolha, setEscolha] = useState<string | null>(null);

  if (!oferta?.ativa || oferta.planos.length === 0) return null;
  const goLive = config?.go_live === true;
  const validade = dataOferta(oferta.expires_at);

  function assinar(plano: OfertaPlano, ciclo: CicloCobranca, metodo: MetodoPagamento) {
    const chave = `${plano.plan_slug}:${ciclo}:${metodo}`;
    setEscolha(chave);
    checkout.mutate(
      { plan_slug: plano.plan_slug, ciclo, metodo, oferta: true },
      {
        onSuccess: (data) => {
          if (data.init_point) {
            window.location.href = data.init_point;
          } else {
            toast.error('O gateway não retornou o link de pagamento. Tente novamente.');
            setEscolha(null);
          }
        },
        onError: (err) => {
          toast.error(getApiErrorMessage(err, 'Não foi possível abrir a oferta. Tente novamente.'));
          setEscolha(null);
        },
      },
    );
  }

  const ocupado = checkout.isPending || checkout.isSuccess;

  return (
    <Card id="oferta-especial" className="border-success/40 bg-success/5">
      <CardContent className="space-y-4 pt-6">
        <div className="flex items-start gap-3">
          <Gift className="mt-0.5 h-5 w-5 shrink-0 text-success" aria-hidden="true" />
          <div>
            <p className="text-lg font-bold text-foreground">Oferta especial até {validade}</p>
            <p className="text-sm text-muted-foreground">
              Volte a usar o FiscWise com 15% de desconto no 1º mês do plano mensal ou 25% no plano anual.
            </p>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          {oferta.planos.map((p) => (
            <div key={p.plan_slug} className="space-y-3 rounded-lg border bg-background p-4">
              <p className="font-semibold text-foreground">{p.plan_name}</p>

              <div className="space-y-1">
                <p className="text-sm text-foreground">
                  <strong>{brl(p.mensal_promo)}</strong> no 1º mês{' '}
                  <span className="text-xs font-semibold text-success">(−{p.mensal_desconto_pct}%)</span>
                </p>
                <p className="text-xs text-muted-foreground">
                  Depois {brl(p.mensal_cheio)}/mês, no cartão, com renovação automática. Cancele quando quiser.
                </p>
                <Button
                  size="sm"
                  className="w-full"
                  disabled={!goLive || ocupado}
                  loading={escolha === `${p.plan_slug}:mensal:cartao` && ocupado}
                  onClick={() => assinar(p, 'mensal', 'cartao')}
                >
                  <CreditCard className="h-4 w-4" aria-hidden="true" /> Mensal com 15% no 1º mês
                </Button>
              </div>

              <div className="space-y-1 border-t pt-3">
                <p className="text-sm text-foreground">
                  Anual por <strong>{brl(p.anual_promo)}</strong>{' '}
                  <span className="text-xs font-semibold text-success">(−{p.anual_desconto_pct}%)</span>
                </p>
                <p className="text-xs text-muted-foreground">
                  Em vez de {brl(p.anual_cheio)}. No Pix ou em até {p.anual_max_parcelas}x de {brl(p.anual_parcela)} sem juros.
                </p>
                <div className="grid grid-cols-2 gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={!goLive || ocupado}
                    loading={escolha === `${p.plan_slug}:anual:pix` && ocupado}
                    onClick={() => assinar(p, 'anual', 'pix')}
                  >
                    <QrCode className="h-4 w-4" aria-hidden="true" /> Anual no Pix
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={!goLive || ocupado}
                    loading={escolha === `${p.plan_slug}:anual:cartao` && ocupado}
                    onClick={() => assinar(p, 'anual', 'cartao')}
                  >
                    <CreditCard className="h-4 w-4" aria-hidden="true" /> Anual no cartão
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>

        <p className="flex items-start gap-1 text-[11px] text-muted-foreground">
          <ExternalLink className="mt-0.5 h-3 w-3 shrink-0" aria-hidden="true" />
          Pagamento no ambiente seguro do Mercado Pago. Oferta válida até {validade}, uma vez por escritório,
          não soma com outros descontos. Você pode desistir em até 7 dias após o pagamento e receber o valor de volta.
        </p>
      </CardContent>
    </Card>
  );
}
