import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useInvoice, useInvoiceEvents, useInvoiceRejections, useCancelInvoice } from '../hooks/useInvoices';
import { useInvoiceEmission } from '../hooks/useInvoiceEmission';
import { InvoiceStatusBadge } from '../components/InvoiceStatusBadge';
import { InvoiceTimeline } from '../components/InvoiceTimeline';
import { InvoiceRejectionAlert } from '../components/InvoiceRejectionAlert';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { FormField } from '@/components/ui/FormField';
import { PageSpinner, EmptyState } from '@/components/ui/StateViews';
import { 
  ArrowLeft, 
  Send, 
  XOctagon, 
  FileText, 
  Download,
  AlertTriangle
} from 'lucide-react';
import { downloadErrorMessage, invoicesService } from '../services/invoices.service';
import { getApiErrorMessage } from '@/lib/api';
import { SimulationNotice } from '@/components/ui/OperationalStates';
import { toast } from 'sonner';
import { WarningPanel } from '@/components/ui/OperationalStates';
import {
  OFFLINE_CANCEL_NOTICE,
  OFFLINE_EMISSION_NOTICE,
  isNetworkError,
  useOfflineEmission,
} from '../hooks/useOfflineEmission';

export function InvoiceDetailPage() {
  const { id = '' } = useParams();
  const navigate = useNavigate();
  const [openCancelModal, setOpenCancelModal] = useState(false);
  const [cancelReason, setCancelReason] = useState('');

  const { data: invoice, isLoading: invoiceLoading } = useInvoice(id);
  const { data: events, isLoading: eventsLoading } = useInvoiceEvents(id);
  const { data: rejections } = useInvoiceRejections(id);

  const emitInvoice = useInvoiceEmission();
  const cancelInvoice = useCancelInvoice();
  const offline = useOfflineEmission(invoice);

  const queueEmission = async () => {
    try {
      await offline.enqueueEmission();
      toast.success('Nota marcada como Pendente de transmissão. Será enviada quando a conexão voltar.');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Não foi possível enfileirar a nota.');
    }
  };

  const handleEmit = async () => {
    if (offline.isOffline) {
      await queueEmission();
      return;
    }
    try {
      await emitInvoice.mutateAsync(id);
      toast.success('Transmissão da NFS-e iniciada!');
    } catch (err) {
      if (isNetworkError(err) && offline.canQueue) {
        await queueEmission();
        return;
      }
      toast.error(getApiErrorMessage(err, 'Falha ao iniciar transmissão da nota.'));
    }
  };

  const emitLabel = (online: string, pending: string) =>
    offline.isOffline ? 'Enfileirar para transmissão' : emitInvoice.isPending ? pending : online;

  const handleCancelSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (offline.isOffline) {
      toast.error(OFFLINE_CANCEL_NOTICE);
      return;
    }
    if (!cancelReason.trim()) {
      toast.error('Insira a justificativa do cancelamento.');
      return;
    }

    try {
      await cancelInvoice.mutateAsync({ id, reason: cancelReason });
      toast.success('Nota fiscal cancelada com sucesso!');
      setOpenCancelModal(false);
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Erro ao solicitar cancelamento da nota.'));
    }
  };

  const handleDownloadPdf = async () => {
    try {
      await invoicesService.downloadPdf(id, invoice?.numero);
    } catch (err) {
      toast.error(await downloadErrorMessage(err, 'Erro ao obter PDF'));
    }
  };

  const handleDownloadXml = async () => {
    try {
      await invoicesService.downloadXml(id, invoice?.numero);
    } catch (err) {
      toast.error(await downloadErrorMessage(err, 'Erro ao obter XML'));
    }
  };

  if (invoiceLoading || eventsLoading) {
    return <PageSpinner />;
  }

  if (!invoice) {
    return (
      <EmptyState
        title="Nota não encontrada"
        description="A NFS-e solicitada não existe ou pertence a outro tenant."
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" onClick={() => navigate('/notas-fiscais')}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Voltar para a Lista
        </Button>
      </div>

      {invoice.simulated && (
        <SimulationNotice>
          Esta nota foi processada por um emissor simulado: não foi transmitida à prefeitura e não
          tem valor fiscal.
        </SimulationNotice>
      )}

      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              {invoice.numero ? `NFS-e Nº ${invoice.numero}` : 'Rascunho de NFS-e'}
            </h1>
            <InvoiceStatusBadge status={offline.displayStatus ?? invoice.status} issuedAt={invoice.issued_at ?? null} />
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Competência: {new Date(invoice.competencia + 'T00:00:00').toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {invoice.status === 'draft' && !offline.pendingTransmission && (
            <Button onClick={handleEmit} disabled={emitInvoice.isPending} className="flex items-center gap-2">
              <Send className="h-4 w-4" />
              {emitLabel('Transmitir NFS-e', 'Emitindo...')}
            </Button>
          )}

          {invoice.status === 'issued' && (
            <>
              <Button onClick={handleDownloadPdf} variant="outline" className="flex items-center gap-2">
                <FileText className="h-4 w-4" />
                Baixar PDF
              </Button>
              <Button onClick={handleDownloadXml} variant="outline" className="flex items-center gap-2">
                <Download className="h-4 w-4" />
                Baixar XML
              </Button>
              <Button
                onClick={() => setOpenCancelModal(true)}
                disabled={offline.isOffline}
                title={offline.isOffline ? OFFLINE_CANCEL_NOTICE : undefined}
                variant="ghost"
                className="text-destructive hover:bg-destructive/10 hover:text-destructive flex items-center gap-2"
              >
                <XOctagon className="h-4 w-4" />
                Solicitar Cancelamento
              </Button>
            </>
          )}
        </div>
      </div>

      {offline.isOffline && (invoice.status === 'draft' || invoice.status === 'rejected') && !offline.pendingTransmission && (
        <WarningPanel title="Sem conexão com a internet" description={OFFLINE_EMISSION_NOTICE} />
      )}
      {offline.isOffline && invoice.status === 'issued' && (
        <WarningPanel title="Cancelamento indisponível sem internet" description={OFFLINE_CANCEL_NOTICE} />
      )}
      {offline.pendingTransmission && (
        <WarningPanel
          variant="info"
          title="Pendente de transmissão"
          description="A nota ainda não foi emitida. O pedido está guardado neste dispositivo e será enviado quando a conexão voltar."
        />
      )}

      {rejections && rejections.length > 0 && (
        <InvoiceRejectionAlert rejections={rejections} />
      )}

      <div className="grid gap-6 md:grid-cols-3">
        {/* Core details column */}
        <div className="space-y-6 md:col-span-2">
          <Card className="border-border/60 bg-card">
            <CardHeader>
              <CardTitle className="text-sm font-semibold text-muted-foreground">
                Dados do Tomador (Cliente)
              </CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2 text-sm">
              <div>
                <p className="text-xs text-muted-foreground">Razão Social / Nome</p>
                <p className="font-medium text-foreground mt-0.5">{invoice.tomador_nome}</p>
              </div>

              <div>
                <p className="text-xs text-muted-foreground">CPF / CNPJ</p>
                <p className="font-medium text-foreground mt-0.5">{invoice.tomador_cpf_cnpj}</p>
              </div>

              <div>
                <p className="text-xs text-muted-foreground">E-mail</p>
                <p className="font-medium text-foreground mt-0.5">{invoice.tomador_email || '—'}</p>
              </div>

              <div>
                <p className="text-xs text-muted-foreground">IBGE Município</p>
                <p className="font-medium text-foreground mt-0.5">{invoice.tomador_municipio_ibge}</p>
              </div>
            </CardContent>
          </Card>

          <Card className="border-border/60 bg-card">
            <CardHeader>
              <CardTitle className="text-sm font-semibold text-muted-foreground">
                Discriminação dos Serviços
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm space-y-4">
              <div className="whitespace-pre-line text-foreground leading-relaxed bg-muted/20 p-4 rounded-lg border border-border/30">
                {invoice.descricao_servico}
              </div>
            </CardContent>
          </Card>

          <Card className="border-border/60 bg-card">
            <CardHeader>
              <CardTitle className="text-sm font-semibold text-muted-foreground">
                Valores e Alíquotas
              </CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-3 text-sm">
              <div className="bg-muted/10 p-3 rounded-lg border border-border/30">
                <p className="text-xs text-muted-foreground">Valor do Serviço</p>
                <p className="text-lg font-bold text-foreground mt-0.5">
                  {invoice.valor_servico.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                </p>
              </div>

              <div className="bg-muted/10 p-3 rounded-lg border border-border/30">
                <p className="text-xs text-muted-foreground">Deduções permitidas</p>
                <p className="text-lg font-semibold text-foreground mt-0.5">
                  {(invoice.valor_deducoes || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                </p>
              </div>

              <div className="bg-muted/10 p-3 rounded-lg border border-border/30">
                <p className="text-xs text-muted-foreground">Valor do ISS estimado</p>
                <p className="text-lg font-semibold text-foreground mt-0.5">
                  {(invoice.valor_iss || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Timeline/Audit column */}
        <div>
          <Card className="border-border/60 bg-card">
            <CardContent className="p-5">
              <InvoiceTimeline events={events || []} />
            </CardContent>
          </Card>
        </div>
      </div>

      <Dialog
        open={openCancelModal}
        onClose={() => setOpenCancelModal(false)}
        title="Cancelar Nota Fiscal de Serviço"
      >
        <form onSubmit={handleCancelSubmit} className="space-y-4">
          <div className="bg-warning/5 text-warning border border-warning/20 p-3 rounded-lg flex gap-3 text-xs">
            <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold block">Atenção: Ação Irreversível</span>
              Esta ação enviará uma solicitação de cancelamento da nota fiscal diretamente ao provedor da NFS-e.
            </div>
          </div>

          <FormField label="Justificativa do Cancelamento" htmlFor="reason">
            <textarea
              id="reason"
              rows={3}
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
              className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
              placeholder="Ex: Serviço cancelado pelo cliente antes do faturamento."
              required
            />
          </FormField>

          <div className="flex justify-end gap-3 pt-2">
            <Button type="button" variant="outline" onClick={() => setOpenCancelModal(false)}>
              Voltar
            </Button>
            <Button
              type="submit"
              variant="destructive"
              disabled={cancelInvoice.isPending || offline.isOffline}
              title={offline.isOffline ? OFFLINE_CANCEL_NOTICE : undefined}
            >
              {cancelInvoice.isPending ? 'Cancelando...' : 'Confirmar Cancelamento'}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
export default InvoiceDetailPage;
