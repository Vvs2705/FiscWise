import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useInvoices, useIssuers } from '../hooks/useInvoices';
import { InvoiceStatusBadge } from '../components/InvoiceStatusBadge';
import { IssuerProfileForm } from '../components/IssuerProfileForm';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { Dialog } from '@/components/ui/Dialog';
import { PageSpinner, EmptyState } from '@/components/ui/StateViews';
import { 
  Plus, 
  Settings, 
  FileText, 
  Download, 
  Eye,
  DollarSign,
  AlertCircle,
  FileCheck
} from 'lucide-react';
import { useClients } from '@/lib/hooks/useOperations';
import { invoicesService } from '../services/invoices.service';
import { toast } from 'sonner';

export function InvoicesListPage() {
  const navigate = useNavigate();
  const [selectedClient, setSelectedClient] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [openIssuerModal, setOpenIssuerModal] = useState(false);

  const { data: clients } = useClients();
  const { data: issuers, isLoading: issuersLoading } = useIssuers();
  
  const { data: invoices, isLoading: invoicesLoading } = useInvoices({
    client_id: selectedClient || undefined,
    status: selectedStatus || undefined,
  });

  const handleDownloadPdf = async (id: string) => {
    try {
      const res = await invoicesService.getPdfUrl(id);
      window.open(res.url, '_blank');
    } catch {
      toast.error('Erro ao gerar URL do PDF');
    }
  };

  const handleDownloadXml = async (id: string) => {
    try {
      const res = await invoicesService.getXmlUrl(id);
      window.open(res.url, '_blank');
    } catch {
      toast.error('Erro ao gerar URL do XML');
    }
  };

  const totalInvoicesValue = invoices?.reduce((acc, inv) => acc + inv.valor_servico, 0) || 0;
  const issuedCount = invoices?.filter(inv => inv.status === 'issued').length || 0;
  const draftCount = invoices?.filter(inv => inv.status === 'draft').length || 0;

  if (issuersLoading || invoicesLoading) {
    return <PageSpinner />;
  }

  const hasIssuer = issuers && issuers.length > 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Notas Fiscais de Serviço (NFS-e)
          </h1>
          <p className="text-sm text-muted-foreground">
            Emita e gerencie NFS-e nacionais diretamente integradas
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            onClick={() => setOpenIssuerModal(true)}
            className="flex items-center gap-2"
          >
            <Settings className="h-4 w-4" />
            Configurar Emissor
          </Button>

          <Button className="flex items-center gap-2" onClick={() => navigate('/notas-fiscais/nova')}>
            <Plus className="h-4 w-4" />
            Nova NFS-e
          </Button>
        </div>
      </div>

      {/* Summary stats */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="border-border/60 bg-card">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Total Faturado (NFS-e)
            </CardTitle>
            <DollarSign className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-foreground">
              {totalInvoicesValue.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
            </p>
            <p className="text-[10px] text-muted-foreground mt-1">
              Soma total dos serviços de todas as notas
            </p>
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Notas Emitidas
            </CardTitle>
            <FileCheck className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-foreground">{issuedCount}</p>
            <p className="text-[10px] text-muted-foreground mt-1">
              Notas autorizadas pela Prefeitura/RFB
            </p>
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Rascunhos pendentes
            </CardTitle>
            <AlertCircle className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-foreground">{draftCount}</p>
            <p className="text-[10px] text-muted-foreground mt-1">
              Rascunhos aguardando revisão e transmissão
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Filters row */}
      <Card className="border-border/60 bg-card">
        <CardContent className="p-4">
          <div className="flex flex-wrap items-center gap-4">
            <div className="min-w-[220px] flex-1">
              <label className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-1 block">
                Filtrar por Cliente
              </label>
              <Select
                value={selectedClient}
                onChange={(e) => setSelectedClient(e.target.value)}
                className="w-full"
              >
                <option value="">Todos os clientes</option>
                {clients?.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </Select>
            </div>

            <div className="min-w-[150px]">
              <label className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-1 block">
                Filtrar por Status
              </label>
              <Select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                className="w-full"
              >
                <option value="">Todos os status</option>
                <option value="draft">Rascunho</option>
                <option value="processing">Processando</option>
                <option value="issued">Emitida</option>
                <option value="cancelled">Cancelada</option>
                <option value="rejected">Rejeitada</option>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Invoices List table */}
      {!hasIssuer && (
        <Card className="border-yellow-500/20 bg-yellow-500/5 text-yellow-800 dark:text-yellow-400">
          <CardContent className="flex flex-col items-center justify-center p-8 text-center space-y-3">
            <AlertCircle className="h-8 w-8 text-yellow-500 animate-pulse" />
            <div>
              <h3 className="font-semibold text-sm">Nenhum emissor configurado</h3>
              <p className="text-xs text-muted-foreground max-w-md mt-1">
                Você precisa configurar o CNPJ e perfil fiscal da sua firma contábil antes de criar rascunhos de notas fiscais.
              </p>
            </div>
            <Button size="sm" onClick={() => setOpenIssuerModal(true)}>
              Configurar Agora
            </Button>
          </CardContent>
        </Card>
      )}

      {hasIssuer && (!invoices || invoices.length === 0) ? (
        <EmptyState
          title="Nenhuma nota fiscal encontrada"
          description="Você ainda não gerou nenhuma NFS-e ou nenhum rascunho com os filtros selecionados."
        />
      ) : hasIssuer ? (
        <Card className="border-border/60 bg-card overflow-hidden">
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-border/80 bg-muted/30 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    <th className="px-5 py-3">Número / Série</th>
                    <th className="px-5 py-3">Cliente / Tomador</th>
                    <th className="px-5 py-3 text-right">Valor do Serviço</th>
                    <th className="px-5 py-3">Status</th>
                    <th className="px-5 py-3">Emitida Em</th>
                    <th className="px-5 py-3 text-right">Ações</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/40">
                  {invoices?.map((inv) => (
                    <tr key={inv.id} className="hover:bg-muted/10 transition-colors duration-150">
                      <td className="px-5 py-4 font-semibold text-foreground">
                        {inv.numero ? `${inv.numero} - Série ${inv.serie || '1'}` : 'Rascunho'}
                      </td>
                      <td className="px-5 py-4">
                        <p className="font-medium text-foreground">{inv.tomador_nome}</p>
                        <p className="text-xs text-muted-foreground">{inv.tomador_cpf_cnpj}</p>
                      </td>
                      <td className="px-5 py-4 text-right font-bold text-foreground">
                        {inv.valor_servico.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                      </td>
                      <td className="px-5 py-4">
                        <InvoiceStatusBadge status={inv.status} />
                      </td>
                      <td className="px-5 py-4 text-muted-foreground">
                        {inv.issued_at ? new Date(inv.issued_at).toLocaleDateString('pt-BR') : '—'}
                      </td>
                      <td className="px-5 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button variant="ghost" size="sm" onClick={() => navigate(`/notas-fiscais/${inv.id}`)}>
                            <Eye className="h-4 w-4" />
                          </Button>
                          
                          {inv.status === 'issued' && (
                            <>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleDownloadPdf(inv.id)}
                                title="Baixar PDF"
                              >
                                <FileText className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleDownloadXml(inv.id)}
                                title="Baixar XML"
                              >
                                <Download className="h-4 w-4" />
                              </Button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      ) : null}

      <Dialog
        open={openIssuerModal}
        onClose={() => setOpenIssuerModal(false)}
        title="Perfil Fiscal do Emissor (Firma)"
      >
        <IssuerProfileForm onSuccess={() => setOpenIssuerModal(false)} />
      </Dialog>
    </div>
  );
}
export default InvoicesListPage;
