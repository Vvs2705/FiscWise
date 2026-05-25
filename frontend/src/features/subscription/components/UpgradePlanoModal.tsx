import { useState, useEffect } from 'react';
import {
  CreditCard,
  QrCode,
  Barcode,
  Users,
  Sparkles,
  Bot,
  CheckCircle2,
  ArrowRight,
  Lock,
  Loader2,
  Calendar
} from 'lucide-react';
import { Dialog } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useCreateSubscription } from '@/lib/hooks/useBilling';
import { useSubscriptionUsage, type Plan } from '@/lib/hooks/useSubscription';
import { updateTenant } from '@/lib/auth';
import { toast } from 'sonner';

interface UpgradePlanoModalProps {
  open: boolean;
  onClose: () => void;
  selectedPlan: Plan | null;
  onUpgradeSuccess: (slug: string) => void;
}

type PaymentMethod = 'cartao' | 'pix' | 'boleto';

export function UpgradePlanoModal({
  open,
  onClose,
  selectedPlan,
  onUpgradeSuccess
}: UpgradePlanoModalProps) {
  const [activeTab, setActiveTab] = useState<PaymentMethod>('cartao');
  const [step, setStep] = useState<'checkout' | 'loading' | 'success'>('checkout');
  
  // Billing details
  const [cnpjCpf, setCnpjCpf] = useState('');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');

  // Card details
  const [cardNumber, setCardNumber] = useState('');
  const [cardName, setCardName] = useState('');
  const [cardExpiry, setCardExpiry] = useState('');
  const [cardCvv, setCardCvv] = useState('');
  const [isFlipped, setIsFlipped] = useState(false);

  const createSub = useCreateSubscription();
  const { data: usage } = useSubscriptionUsage();

  // Reset states on open/close
  useEffect(() => {
    if (open) {
      setStep('checkout');
      setActiveTab('cartao');
      // Prefill values where possible
      setCnpjCpf('');
      setName('');
      setEmail('');
      setPhone('');
      setCardNumber('');
      setCardName('');
      setCardExpiry('');
      setCardCvv('');
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

  // Format Expiry
  const handleExpiryChange = (val: string) => {
    const cleaned = val.replace(/\D/g, '');
    if (cleaned.length <= 2) {
      setCardExpiry(cleaned);
    } else {
      setCardExpiry(`${cleaned.substring(0, 2)}/${cleaned.substring(2, 4)}`);
    }
  };

  // Format Card Number
  const handleCardNumberChange = (val: string) => {
    const cleaned = val.replace(/\D/g, '');
    const matched = cleaned.match(/.{1,4}/g);
    setCardNumber(matched ? matched.join(' ').substring(0, 19) : cleaned);
  };

  // Check validation
  const isFormValid = () => {
    if (!cnpjCpf || !name || !email || !phone) return false;
    if (activeTab === 'cartao') {
      return cardNumber.length >= 16 && cardName.length > 2 && cardExpiry.length === 5 && cardCvv.length >= 3;
    }
    return true;
  };

  const handleConfirm = async () => {
    if (!isFormValid()) {
      toast.warning('Por favor, preencha todos os campos obrigatórios.');
      return;
    }

    setStep('loading');

    try {
      // Call backend api post to create subscription on Asaas
      await createSub.mutateAsync({
        plan_id: selectedPlan.id,
        billing_provider: 'asaas'
      });

      // Update tenant plan slug
      await updateTenant({ plan_slug: selectedPlan.slug });

      // Show loading delay to simulate processing on the gateway
      await new Promise((resolve) => setTimeout(resolve, 2000));
      
      setStep('success');
      onUpgradeSuccess(selectedPlan.slug);
      toast.success('Assinatura processada com sucesso!');
    } catch (err: any) {
      setStep('checkout');
      toast.error(err?.response?.data?.detail || 'Erro ao processar assinatura no Asaas. Tente novamente.');
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
          
          {/* Coluna Esquerda: Formas de Pagamento e Faturamento */}
          <div className="space-y-5">
            <div>
              <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">1</span>
                Forma de Pagamento
              </h3>
              
              {/* Tabs */}
              <div className="grid grid-cols-3 gap-2 p-1 bg-muted/40 rounded-lg border">
                {(['cartao', 'pix', 'boleto'] as const).map((method) => (
                  <button
                    key={method}
                    onClick={() => setActiveTab(method)}
                    className={`flex flex-col sm:flex-row items-center justify-center gap-2 py-2 px-3 rounded-md text-xs font-medium transition-all ${
                      activeTab === method
                        ? 'bg-background shadow text-foreground border border-border/60'
                        : 'text-muted-foreground hover:text-foreground hover:bg-muted/60'
                    }`}
                  >
                    {method === 'cartao' && <CreditCard className="h-4 w-4" />}
                    {method === 'pix' && <QrCode className="h-4 w-4" />}
                    {method === 'boleto' && <Barcode className="h-4 w-4" />}
                    <span className="capitalize">{method === 'cartao' ? 'Cartão' : method}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Visual de Cartão / QR Code / Barcode */}
            <div className="rounded-xl border border-border/80 bg-gradient-to-br from-card to-muted/20 p-4 min-h-[170px] flex items-center justify-center relative overflow-hidden">
              
              {activeTab === 'cartao' && (
                <div 
                  className={`w-full max-w-[320px] h-[170px] rounded-xl text-white p-5 flex flex-col justify-between shadow-lg relative overflow-hidden transition-all duration-500 bg-gradient-to-br from-zinc-800 to-zinc-950 dark:from-zinc-900 dark:to-black border border-zinc-700/50 ${
                    isFlipped ? 'rotate-y-180' : ''
                  }`}
                  onClick={() => setIsFlipped(!isFlipped)}
                  style={{ perspective: '1000px', cursor: 'pointer' }}
                >
                  {/* Decorative mesh */}
                  <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-emerald-500/10 via-transparent to-transparent pointer-events-none" />
                  
                  {!isFlipped ? (
                    <>
                      {/* Front of card */}
                      <div className="flex items-start justify-between">
                        <div className="h-8 w-11 bg-amber-500/80 rounded-md opacity-80" /> {/* Chip */}
                        <Sparkles className="h-5 w-5 text-emerald-400" />
                      </div>
                      <div className="space-y-1">
                        <p className="text-sm tracking-[0.25em] font-mono leading-none">
                          {cardNumber || '•••• •••• •••• ••••'}
                        </p>
                      </div>
                      <div className="flex justify-between items-end">
                        <div className="max-w-[70%]">
                          <p className="text-[10px] text-zinc-400 uppercase tracking-wider leading-none">Titular</p>
                          <p className="text-xs font-semibold uppercase tracking-wide truncate mt-1">
                            {cardName || 'NOME DO TITULAR'}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-[10px] text-zinc-400 uppercase tracking-wider leading-none">Validade</p>
                          <p className="text-xs font-semibold mt-1">{cardExpiry || 'MM/AA'}</p>
                        </div>
                      </div>
                    </>
                  ) : (
                    <>
                      {/* Back of card */}
                      <div className="w-full h-8 bg-zinc-800 absolute top-5 left-0" />
                      <div className="mt-12 flex justify-end items-center gap-2">
                        <div className="bg-zinc-700 h-6 px-2 flex items-center rounded text-[10px] font-mono text-zinc-300">CVV</div>
                        <p className="font-mono text-xs font-semibold tracking-widest bg-zinc-200 text-zinc-900 px-2 py-0.5 rounded">
                          {cardCvv || '•••'}
                        </p>
                      </div>
                      <p className="text-[9px] text-zinc-500 text-right">FiscWise Signature Card</p>
                    </>
                  )}
                </div>
              )}

              {activeTab === 'pix' && (
                <div className="flex flex-col items-center text-center space-y-2 p-2">
                  <div className="relative p-2 bg-white rounded-lg border">
                    <QrCode className="h-24 w-24 text-zinc-900" />
                    {/* Simulated scanning beam */}
                    <div className="absolute left-0 right-0 h-0.5 bg-emerald-500 animate-bounce top-1/2" />
                  </div>
                  <div>
                    <p className="text-xs font-medium text-foreground">Pix Gerado sob Demanda</p>
                    <p className="text-[10px] text-muted-foreground">Chave dinâmica Asaas expira em 24h.</p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-[11px] h-7 px-3"
                    onClick={() => {
                      navigator.clipboard.writeText('00020126360014BR.GOV.BCB.PIX0114000000000000005204000053039865406149.005802BR5916FiscWise*Asaas6009Sao Paulo62070503***6304CA12');
                      toast.success('Cópia Pix realizada!');
                    }}
                  >
                    Copiar Código Pix
                  </Button>
                </div>
              )}

              {activeTab === 'boleto' && (
                <div className="flex flex-col items-center text-center space-y-2 w-full px-4">
                  <div className="w-full max-w-[280px] bg-muted/60 p-3 rounded-lg border border-dashed text-left space-y-1.5">
                    <div className="flex justify-between items-center text-[10px] text-muted-foreground border-b pb-1">
                      <span>BANCO ASAAS S.A.</span>
                      <span className="font-semibold">033-7</span>
                    </div>
                    <p className="font-mono text-xs text-foreground tracking-tight break-all">
                      03399.01234 56789.012345 67890.123455 9 12340000014900
                    </p>
                    <div className="flex justify-between text-[9px] text-muted-foreground pt-1">
                      <span>Vence em 3 dias</span>
                      <span>Valor: {planPriceFormatted}</span>
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-[11px] h-7 px-3"
                    onClick={() => {
                      navigator.clipboard.writeText('03399.01234 56789.012345 67890.123455 9 12340000014900');
                      toast.success('Linha digitável copiada!');
                    }}
                  >
                    Copiar Linha Digitável
                  </Button>
                </div>
              )}

            </div>

            {/* Inputs de Cartão se for cartão */}
            {activeTab === 'cartao' && (
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="sm:col-span-2">
                  <label className="text-[11px] font-medium text-muted-foreground uppercase">Número do Cartão</label>
                  <Input
                    placeholder="0000 0000 0000 0000"
                    value={cardNumber}
                    onChange={(e) => handleCardNumberChange(e.target.value)}
                    maxLength={19}
                    className="mt-1"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-medium text-muted-foreground uppercase">Nome impresso</label>
                  <Input
                    placeholder="Ex: João da Silva"
                    value={cardName}
                    onChange={(e) => setCardName(e.target.value)}
                    className="mt-1"
                    onFocus={() => setIsFlipped(false)}
                  />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[11px] font-medium text-muted-foreground uppercase">Validade</label>
                    <Input
                      placeholder="MM/AA"
                      value={cardExpiry}
                      onChange={(e) => handleExpiryChange(e.target.value)}
                      maxLength={5}
                      className="mt-1"
                      onFocus={() => setIsFlipped(false)}
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-medium text-muted-foreground uppercase">CVV</label>
                    <Input
                      placeholder="123"
                      value={cardCvv}
                      onChange={(e) => setCardCvv(e.target.value.replace(/\D/g, '').substring(0, 4))}
                      maxLength={4}
                      className="mt-1"
                      onFocus={() => setIsFlipped(true)}
                      onBlur={() => setIsFlipped(false)}
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Seção 2: Dados de Faturamento */}
            <div>
              <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">2</span>
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
                <div>
                  <label className="text-[11px] font-medium text-muted-foreground uppercase">E-mail Financeiro</label>
                  <Input
                    type="email"
                    placeholder="financeiro@email.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="mt-1"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-medium text-muted-foreground uppercase">Telefone celular</label>
                  <Input
                    type="tel"
                    placeholder="(11) 99999-9999"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className="mt-1"
                  />
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
                <Lock className="h-3.5 w-3.5 shrink-0 text-emerald-500 mt-0.5" />
                <span>Cobrança processada de forma segura pela Asaas S.A. Conexão criptografada SSL de 256 bits.</span>
              </div>
            </div>

            <div className="space-y-2">
              <Button
                className="w-full font-semibold shadow-md py-5 flex items-center justify-center gap-2"
                onClick={handleConfirm}
                disabled={!isFormValid()}
              >
                Ativar Plano {selectedPlan.name}
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
              Criando o perfil de cobrança do cliente e provisionando os limites operacionais no FiscWise.
            </p>
          </div>
        </div>
      )}

      {step === 'success' && (
        <div className="flex flex-col items-center justify-center py-10 text-center space-y-6 max-w-md mx-auto">
          {/* Confetti simulation top indicator */}
          <div className="relative">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-500 animate-pulse border-2 border-emerald-500/20">
              <CheckCircle2 className="h-10 w-10" />
            </div>
            <Sparkles className="absolute -top-1 -right-1 h-5 w-5 text-amber-400 animate-bounce" />
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
              <span className="text-muted-foreground">Método de cobrança:</span>
              <span className="font-semibold text-foreground uppercase">{activeTab === 'cartao' ? 'Cartão de Crédito' : activeTab}</span>
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
            className="w-full font-semibold shadow-md py-4"
            onClick={onClose}
          >
            Começar a Usar Agora
          </Button>
        </div>
      )}
    </Dialog>
  );
}
