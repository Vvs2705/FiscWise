import { X, Printer, Shield, Key, DollarSign, Calendar, FileText, Users } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { dateBR, moneyBRL, type AccountingClient, type CompanyPartner, type DeadlineItem, type CompanyDocument, type DigitalCertificate, type ClientBillingHistoryItem } from '@/lib/hooks/useOperations';

interface ClientStatusReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  client: AccountingClient;
  partners: CompanyPartner[];
  deadlines: DeadlineItem[];
  companyDocs: CompanyDocument[];
  certificates: DigitalCertificate[];
  billingHistory: ClientBillingHistoryItem[];
  healthScore: number;
}

export function ClientStatusReportModal({
  isOpen,
  onClose,
  client,
  partners,
  deadlines,
  companyDocs,
  certificates,
  billingHistory,
  healthScore,
}: ClientStatusReportModalProps) {
  if (!isOpen) return null;

  const handlePrint = () => {
    window.print();
  };

  const getScoreLabel = (s: number) => {
    if (s >= 90) return 'Excelente';
    if (s >= 75) return 'Boa';
    if (s >= 55) return 'Atenção';
    return 'Crítica';
  };

  const getScoreColor = (s: number) => {
    if (s >= 90) return 'text-success';
    if (s >= 75) return 'text-primary';
    if (s >= 55) return 'text-warning';
    return 'text-destructive';
  };

  const docTypeLabel = (val: string) => {
    const types: Record<string, string> = {
      cnpj: 'CNPJ',
      contrato_social: 'Contrato Social',
      inscricao_municipal: 'Inscrição Municipal',
      inscricao_estadual: 'Inscrição Estadual',
      alvara_funcionamento: 'Alvará de Funcionamento',
      licenca_sanitaria: 'Licença Sanitária',
      cnes: 'CNES',
      alvara_bombeiros: 'Alvará do Corpo de Bombeiros',
      cro_juridico: 'CRO Jurídico',
    };
    return types[val] || val.toUpperCase();
  };

  const isExpired = (expDateStr?: string | null) => {
    if (!expDateStr) return false;
    return new Date(expDateStr) < new Date();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/85 p-4 backdrop-blur-sm overflow-y-auto">
      {/* Dynamic CSS styles for clean printing of the modal container only */}
      <style>{`
        @media print {
          body * {
            visibility: hidden;
          }
          #print-report-modal, #print-report-modal * {
            visibility: visible;
          }
          #print-report-modal {
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
            background: white !important;
            color: black !important;
            padding: 0 !important;
            border: none !important;
            box-shadow: none !important;
          }
          .no-print {
            display: none !important;
          }
          .print-border {
            border: 1px solid #e2e8f0 !important;
          }
        }
      `}</style>

      <div
        id="print-report-modal"
        className="w-full max-w-4xl rounded-panel border border-border bg-card text-foreground shadow-token p-6 md:p-8 space-y-6 relative max-h-[90vh] overflow-y-auto scrollbar"
      >
        {/* Floating print actions */}
        <div className="no-print flex items-center justify-between border-b border-border pb-4">
          <div className="flex items-center gap-2">
            <Printer className="h-5 w-5 text-primary" />
            <span className="text-xs uppercase font-bold text-muted-foreground tracking-wider">Ficha de Status do Cliente</span>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="default" size="sm" onClick={handlePrint} className="gap-1.5 bg-primary text-background hover:bg-primary/90">
              <Printer className="h-4 w-4" />
              Imprimir / PDF
            </Button>
            <Button variant="outline" size="sm" onClick={onClose} className="border-border bg-muted text-muted-foreground hover:bg-muted">
              <X className="h-4 w-4" />
              Fechar
            </Button>
          </div>
        </div>

        {/* PRINT HEADER */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-border pb-6 print-border-b">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-primary print:text-slate-800">
              <Shield className="h-6 w-6 shrink-0" />
              <h1 className="text-2xl font-extrabold tracking-tight">FiscWise</h1>
            </div>
            <p className="text-xs text-muted-foreground font-medium">Relatório de Diagnóstico & Status Operacional</p>
          </div>
          <div className="text-left sm:text-right text-xs text-muted-foreground space-y-1 font-mono">
            <p>Gerado em: {new Date().toLocaleDateString('pt-BR')} às {new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</p>
            <p>Cliente Código: #{client.client_code}</p>
          </div>
        </div>

        {/* GENERAL PROFILE */}
        <div className="grid gap-6 md:grid-cols-[1.5fr_0.5fr]">
          <div className="space-y-4">
            <h2 className="text-sm font-extrabold uppercase text-primary print:text-slate-800 flex items-center gap-1.5 border-b border-border pb-1">
              <Users className="w-4.5 h-4.5 text-inherit" />
              Dados Cadastrais
            </h2>
            <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
              <div>
                <span className="text-muted-foreground block font-medium">Razão Social:</span>
                <span className="font-bold text-foreground print:text-slate-900">{client.name}</span>
              </div>
              <div>
                <span className="text-muted-foreground block font-medium">CNPJ/CPF:</span>
                <span className="font-bold text-foreground print:text-slate-900">{client.document || 'Não informado'}</span>
              </div>
              <div>
                <span className="text-muted-foreground block font-medium">Regime Tributário:</span>
                <span className="font-bold text-foreground print:text-slate-900">{client.tax_regime || 'Não informado'}</span>
              </div>
              <div>
                <span className="text-muted-foreground block font-medium">E-mail:</span>
                <span className="font-bold text-foreground print:text-slate-900">{client.email || 'Não informado'}</span>
              </div>
              <div>
                <span className="text-muted-foreground block font-medium">Telefone:</span>
                <span className="font-bold text-foreground print:text-slate-900">{client.phone || 'Não informado'}</span>
              </div>
              <div>
                <span className="text-muted-foreground block font-medium">Responsável Legal:</span>
                <span className="font-bold text-foreground print:text-slate-900">{client.responsible_name || 'Não informado'}</span>
              </div>
            </div>
          </div>

          {/* HEALTH SCORE CARD */}
          <div className="bg-muted border border-border print:border print:bg-slate-50 rounded-card p-4 flex flex-col items-center justify-center text-center space-y-2">
            <span className="text-[10px] uppercase font-extrabold text-muted-foreground tracking-wider">Saúde da Carteira</span>
            <div className={`text-4xl font-extrabold ${getScoreColor(healthScore)}`}>
              {healthScore}
            </div>
            <span className={`text-xs font-bold px-2 py-0.5 rounded bg-muted border border-border ${getScoreColor(healthScore)}`}>
              {getScoreLabel(healthScore)}
            </span>
          </div>
        </div>

        {/* PARTNERS (QSA) */}
        {partners.length > 0 && (
          <div className="space-y-3">
            <h2 className="text-sm font-extrabold uppercase text-primary print:text-slate-800 flex items-center gap-1.5 border-b border-border pb-1">
              <Users className="w-4.5 h-4.5 text-inherit" />
              Quadro de Sócios (QSA)
            </h2>
            <div className="overflow-hidden border border-border rounded-xl">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-muted border-b border-border text-muted-foreground font-semibold print:bg-slate-100">
                    <th className="p-3">Nome do Sócio</th>
                    <th className="p-3">CPF</th>
                    <th className="p-3 text-right">Participação</th>
                    <th className="p-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {partners.map((partner) => (
                    <tr key={partner.id} className="text-foreground print:text-slate-800">
                      <td className="p-3 font-semibold">{partner.name}</td>
                      <td className="p-3 font-mono">{partner.cpf}</td>
                      <td className="p-3 text-right font-bold">{partner.participation_percentage}%</td>
                      <td className="p-3 capitalize">{partner.status === 'active' ? 'Ativo' : 'Inativo'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* PENDING DEADLINES & TASKS */}
        <div className="space-y-3">
          <h2 className="text-sm font-extrabold uppercase text-primary print:text-slate-800 flex items-center gap-1.5 border-b border-border pb-1">
            <Calendar className="w-4.5 h-4.5 text-inherit" />
            Compromissos & Prazos Ativos
          </h2>
          {deadlines.length === 0 ? (
            <p className="text-xs text-muted-foreground italic">Nenhum compromisso pendente cadastrado.</p>
          ) : (
            <div className="overflow-hidden border border-border rounded-xl">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-muted border-b border-border text-muted-foreground font-semibold print:bg-slate-100">
                    <th className="p-3">Título / Categoria</th>
                    <th className="p-3">Vencimento</th>
                    <th className="p-3">Prioridade</th>
                    <th className="p-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {deadlines.map((dl) => (
                    <tr key={dl.id} className="text-foreground print:text-slate-800">
                      <td className="p-3">
                        <span className="font-semibold block">{dl.title}</span>
                        <span className="text-[10px] text-muted-foreground">{dl.category}</span>
                      </td>
                      <td className="p-3 font-mono">{dateBR(dl.due_date)}</td>
                      <td className="p-3 capitalize">{dl.priority}</td>
                      <td className="p-3 font-semibold">
                        {dl.status === 'completed' ? (
                          <span className="text-success">Concluído</span>
                        ) : dl.status === 'overdue' ? (
                          <span className="text-destructive">Atrasado</span>
                        ) : (
                          <span className="text-warning">Pendente</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* OFFICIAL DOCUMENTS */}
        <div className="space-y-3">
          <h2 className="text-sm font-extrabold uppercase text-primary print:text-slate-800 flex items-center gap-1.5 border-b border-border pb-1">
            <FileText className="w-4.5 h-4.5 text-inherit" />
            Documentos Arquivados & Alvarás
          </h2>
          {companyDocs.length === 0 ? (
            <p className="text-xs text-muted-foreground italic">Nenhum documento arquivado.</p>
          ) : (
            <div className="overflow-hidden border border-border rounded-xl">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-muted border-b border-border text-muted-foreground font-semibold print:bg-slate-100">
                    <th className="p-3">Tipo do Documento</th>
                    <th className="p-3">Data de Upload</th>
                    <th className="p-3">Vencimento</th>
                    <th className="p-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {companyDocs.map((doc) => (
                    <tr key={doc.id} className="text-foreground print:text-slate-800">
                      <td className="p-3 font-semibold">{docTypeLabel(doc.document_type)}</td>
                      <td className="p-3 font-mono">{new Date(doc.upload_date).toLocaleDateString('pt-BR')}</td>
                      <td className="p-3 font-mono">{doc.expiration_date ? dateBR(doc.expiration_date) : 'Inexistente'}</td>
                      <td className="p-3">
                        {isExpired(doc.expiration_date) ? (
                          <span className="text-destructive font-bold">Expirado</span>
                        ) : (
                          <span className="text-success">Regular</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* DIGITAL CERTIFICATES */}
        {certificates.length > 0 && (
          <div className="space-y-3">
            <h2 className="text-sm font-extrabold uppercase text-primary print:text-slate-800 flex items-center gap-1.5 border-b border-border pb-1">
              <Key className="w-4.5 h-4.5 text-inherit" />
              Certificados Digitais
            </h2>
            <div className="overflow-hidden border border-border rounded-xl">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-muted border-b border-border text-muted-foreground font-semibold print:bg-slate-100">
                    <th className="p-3">Identificador / Apelido</th>
                    <th className="p-3">Tipo</th>
                    <th className="p-3">Vencimento</th>
                    <th className="p-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {certificates.map((cert) => (
                    <tr key={cert.id} className="text-foreground print:text-slate-800">
                      <td className="p-3 font-semibold">{cert.label}</td>
                      <td className="p-3 uppercase font-mono">{cert.certificate_type}</td>
                      <td className="p-3 font-mono">{dateBR(cert.valid_until)}</td>
                      <td className="p-3">
                        {cert.status === 'expired' ? (
                          <span className="text-destructive font-bold">Vencido</span>
                        ) : cert.status === 'expiring' ? (
                          <span className="text-warning font-bold">Vencendo</span>
                        ) : (
                          <span className="text-success">Válido</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* RECENT INVOICES */}
        {billingHistory.length > 0 && (
          <div className="space-y-3">
            <h2 className="text-sm font-extrabold uppercase text-primary print:text-slate-800 flex items-center gap-1.5 border-b border-border pb-1">
              <DollarSign className="w-4.5 h-4.5 text-inherit" />
              Faturamento e Honorários Recorrentes
            </h2>
            <div className="overflow-hidden border border-border rounded-xl">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-muted border-b border-border text-muted-foreground font-semibold print:bg-slate-100">
                    <th className="p-3">Descrição da Fatura</th>
                    <th className="p-3">Vencimento</th>
                    <th className="p-3 text-right">Valor</th>
                    <th className="p-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {billingHistory.slice(0, 5).map((invoice) => (
                    <tr key={invoice.id} className="text-foreground print:text-slate-800">
                      <td className="p-3">{invoice.description}</td>
                      <td className="p-3 font-mono">{dateBR(invoice.due_date)}</td>
                      <td className="p-3 text-right font-bold">{moneyBRL(invoice.amount)}</td>
                      <td className="p-3 uppercase font-semibold">
                        {invoice.status === 'paid' ? (
                          <span className="text-success">Pago</span>
                        ) : invoice.status === 'overdue' ? (
                          <span className="text-destructive">Atrasado</span>
                        ) : (
                          <span className="text-warning">Pendente</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* REPORT FOOTER */}
        <div className="border-t border-border pt-4 text-center text-[10px] text-muted-foreground font-medium font-mono uppercase">
          Diagnóstico Confidencial — Gerado automaticamente pelo sistema de gestão fiscal FiscWise.
        </div>

      </div>
    </div>
  );
}
