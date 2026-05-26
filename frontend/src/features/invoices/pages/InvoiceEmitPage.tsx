import { useParams, useNavigate } from 'react-router-dom';
import { useInvoice } from '../hooks/useInvoices';
import { useInvoiceEmission } from '../hooks/useInvoiceEmission';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { PageSpinner, EmptyState } from '@/components/ui/StateViews';
import { ArrowLeft, Send, CheckCircle2, ShieldCheck } from 'lucide-react';
import toast from 'react-hot-toast';

export function InvoiceEmitPage() {
  const { id = '' } = useParams();
  const navigate = useNavigate();
  const { data: invoice, isLoading } = useInvoice(id);
  const emitInvoice = useInvoiceEmission();

  const handleEmit = async () => {
    try {
      await emitInvoice.mutateAsync(id);
      toast.success('Nota enviada para a fila de processamento!');
      navigate(`/notas-fiscais/${id}`);
    } catch {
      toast.error('Erro ao solicitar emissão da NFS-e.');
    }
  };

  if (isLoading) {
    return <PageSpinner />;
  }

  if (!invoice) {
    return (
      <EmptyState
        title="Nota não encontrada"
        description="O rascunho solicitado não pôde ser carregado."
      />
    );
  }

  const validations = [
    { name: 'CNPJ/CPF do Tomador válido', status: (invoice.tomador_cpf_cnpj || '').length >= 11 },
    { name: 'IBGE do município preenchido', status: !!invoice.tomador_municipio_ibge },
    { name: 'Valor do serviço maior que zero', status: invoice.valor_servico > 0 },
    { name: 'Descrição do serviço inserida', status: invoice.descricao_servico.length > 5 },
  ];

  const canEmit = validations.every((v) => v.status);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" onClick={() => navigate(`/notas-fiscais/${id}`)}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Voltar para o Detalhe
        </Button>
      </div>

      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Revisar e Transmitir NFS-e
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Confirme os dados antes de assinar e transmitir a nota fiscal ao Portal Nacional
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <div className="space-y-6 md:col-span-2">
          {/* Review Card */}
          <Card className="border-border/60 bg-card">
            <CardHeader>
              <CardTitle className="text-sm font-semibold tracking-wider uppercase text-muted-foreground">
                Resumo da NFS-e
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="text-xs text-muted-foreground block">Tomador (Cliente)</span>
                  <span className="font-semibold text-foreground">{invoice.tomador_nome}</span>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground block">CPF / CNPJ</span>
                  <span className="font-semibold text-foreground">{invoice.tomador_cpf_cnpj}</span>
                </div>
              </div>

              <div className="border-t border-border/40 pt-3">
                <span className="text-xs text-muted-foreground block">Descrição dos Serviços</span>
                <p className="text-foreground mt-1 leading-relaxed">{invoice.descricao_servico}</p>
              </div>

              <div className="border-t border-border/40 pt-3 grid grid-cols-3 gap-4">
                <div>
                  <span className="text-xs text-muted-foreground block">Valor Total</span>
                  <span className="text-lg font-bold text-foreground block mt-0.5">
                    {invoice.valor_servico.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                  </span>
                </div>

                <div>
                  <span className="text-xs text-muted-foreground block">Deduções</span>
                  <span className="text-sm font-semibold text-foreground block mt-0.5">
                    {(invoice.valor_deducoes || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                  </span>
                </div>

                <div>
                  <span className="text-xs text-muted-foreground block">Alíquota ISS Estimada</span>
                  <span className="text-sm font-semibold text-foreground block mt-0.5">
                    {(invoice.valor_iss || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Validation Column */}
        <div className="space-y-6">
          <Card className="border-border/60 bg-card">
            <CardHeader>
              <CardTitle className="text-sm font-semibold tracking-wider uppercase text-muted-foreground">
                Lista de Validações
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <ul className="space-y-3">
                {validations.map((v, i) => (
                  <li key={i} className="flex items-center gap-3 text-sm">
                    {v.status ? (
                      <CheckCircle2 className="h-5 w-5 text-emerald-500 shrink-0" />
                    ) : (
                      <ShieldCheck className="h-5 w-5 text-red-500 shrink-0" />
                    )}
                    <span className={v.status ? 'text-foreground' : 'text-red-500'}>
                      {v.name}
                    </span>
                  </li>
                ))}
              </ul>

              <div className="border-t border-border/40 pt-4 mt-4">
                <Button
                  onClick={handleEmit}
                  disabled={!canEmit || emitInvoice.isPending}
                  className="w-full flex items-center justify-center gap-2"
                >
                  <Send className="h-4 w-4" />
                  {emitInvoice.isPending ? 'Transmitindo...' : 'Transmitir NFS-e'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
export default InvoiceEmitPage;
