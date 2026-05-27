import { useParams, useNavigate } from 'react-router-dom';
import { useGuide, useUploadPdf, useMarkPaid } from '../hooks/useGuias';
import { GuiaStatusBadge } from '../components/GuiaStatusBadge';
import { GuiaUploadComprovante } from '../components/GuiaUploadComprovante';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { PageSpinner, EmptyState } from '@/components/ui/StateViews';
import { ArrowLeft, FileText, Download, CheckCircle, Upload } from 'lucide-react';
import { useClients } from '@/lib/hooks/useOperations';
import { guiasService } from '../services/guias.service';
import { toast } from 'sonner';

export function GuiaDetailPage() {
  const { id = '' } = useParams();
  const navigate = useNavigate();
  const { data: guide, isLoading, refetch } = useGuide(id);
  const { data: clients } = useClients();
  const uploadPdf = useUploadPdf();
  const markPaid = useMarkPaid();

  const handlePdfUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      try {
        await uploadPdf.mutateAsync({ id, file: e.target.files[0] });
        toast.success('Guia PDF anexada com sucesso!');
        refetch();
      } catch {
        toast.error('Erro ao enviar arquivo PDF.');
      }
    }
  };

  const handleDownloadPdf = async () => {
    try {
      const res = await guiasService.getPdfUrl(id);
      window.open(res.url, '_blank');
    } catch {
      toast.error('Erro ao buscar link do PDF.');
    }
  };

  const handleDownloadComprovante = async () => {
    try {
      const res = await guiasService.getComprovanteUrl(id);
      window.open(res.url, '_blank');
    } catch {
      toast.error('Erro ao buscar link do comprovante.');
    }
  };

  const handleMarkPaid = async () => {
    try {
      await markPaid.mutateAsync(id);
      toast.success('Guia marcada como paga com sucesso!');
      refetch();
    } catch {
      toast.error('Erro ao atualizar status da guia.');
    }
  };

  if (isLoading) {
    return <PageSpinner />;
  }

  if (!guide) {
    return (
      <EmptyState
        title="Guia não encontrada"
        description="A guia tributária solicitada não pôde ser carregada."
      />
    );
  }

  const clientName = clients?.find((c) => c.id === guide.client_id)?.name || 'Cliente';

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" onClick={() => navigate('/guias')}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Voltar para a Lista
        </Button>
      </div>

      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              Guia {guide.tipo} - {guide.competencia.substring(0, 7)}
            </h1>
            <GuiaStatusBadge status={guide.status || 'pendente'} />
          </div>
          <p className="text-sm text-muted-foreground mt-1">Cliente: {clientName}</p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {guide.status !== 'paga' && (
            <Button onClick={handleMarkPaid} disabled={markPaid.isPending} className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4" />
              Marcar como Paga
            </Button>
          )}

          {guide.pdf_storage_path && (
            <Button onClick={handleDownloadPdf} variant="outline" className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Baixar Guia PDF
            </Button>
          )}

          {guide.comprovante_storage_path && (
            <Button onClick={handleDownloadComprovante} variant="outline" className="flex items-center gap-2">
              <Download className="h-4 w-4" />
              Ver Comprovante
            </Button>
          )}
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="border-border/60 bg-card">
          <CardHeader>
            <CardTitle className="text-sm font-semibold tracking-wider uppercase text-muted-foreground">
              Informações Tributárias
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-xs text-muted-foreground block font-medium">Valor Total da Guia</span>
                <span className="text-lg font-bold text-foreground block mt-0.5">
                  {guide.valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                </span>
              </div>

              <div>
                <span className="text-xs text-muted-foreground block font-medium">Data de Vencimento</span>
                <span className="text-sm font-semibold text-foreground block mt-0.5">
                  {new Date(guide.vencimento + 'T00:00:00').toLocaleDateString('pt-BR')}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 border-t border-border/40 pt-3">
              <div>
                <span className="text-xs text-muted-foreground block font-medium">Data de Envio</span>
                <span className="text-sm text-foreground block mt-0.5">
                  {guide.enviada_em ? new Date(guide.enviada_em).toLocaleString('pt-BR') : 'Ainda não enviada'}
                </span>
              </div>

              <div>
                <span className="text-xs text-muted-foreground block font-medium">Data de Pagamento</span>
                <span className="text-sm text-foreground block mt-0.5">
                  {guide.paga_em ? new Date(guide.paga_em).toLocaleString('pt-BR') : 'Não pago'}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Upload documents card */}
        <Card className="border-border/60 bg-card">
          <CardHeader>
            <CardTitle className="text-sm font-semibold tracking-wider uppercase text-muted-foreground">
              Arquivos & Anexos
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Guide PDF Upload */}
            <div className="flex flex-col gap-2 p-3 bg-muted/10 border border-border/30 rounded-lg">
              <span className="text-xs font-semibold text-muted-foreground uppercase">
                {guide.pdf_storage_path ? 'Substituir Guia de Imposto (PDF)' : 'Anexar Guia de Imposto (PDF)'}
              </span>
              <label className="flex items-center justify-between px-3 py-1.5 bg-background border border-input rounded-md text-xs cursor-pointer hover:bg-muted/10 mt-1">
                <span className="text-muted-foreground">
                  {guide.pdf_storage_path ? 'Alterar arquivo PDF' : 'Selecionar arquivo...'}
                </span>
                <input type="file" className="hidden" accept=".pdf" onChange={handlePdfUpload} />
                <Upload className="h-3.5 w-3.5 text-muted-foreground" />
              </label>
            </div>

            {/* Receipt Upload Component */}
            <GuiaUploadComprovante guideId={id} onSuccess={refetch} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
export default GuiaDetailPage;
