import { Drawer, DrawerContent, DrawerHeader, DrawerTitle } from '@/components/ui/Drawer';
import { Button } from '@/components/ui/Button';
import { Download, ExternalLink, FileText, Sparkles } from 'lucide-react';
import { buildDocumentAiView } from '@/lib/aiDocuments';
import { Badge } from '@/components/ui/Badge';
import { dateBR, type ClientDocument } from '@/lib/hooks/useOperations';

interface DocumentPreviewDrawerProps {
  document: ClientDocument | null;
  isOpen: boolean;
  onClose: () => void;
}

export function DocumentPreviewDrawer({ document, isOpen, onClose }: DocumentPreviewDrawerProps) {
  if (!document) return null;

  const isPdf = document.file_url?.toLowerCase().endsWith('.pdf');
  const isImage =
    document.file_url?.toLowerCase().endsWith('.png') ||
    document.file_url?.toLowerCase().endsWith('.jpg') ||
    document.file_url?.toLowerCase().endsWith('.jpeg') ||
    document.file_url?.toLowerCase().endsWith('.gif') ||
    document.file_url?.toLowerCase().endsWith('.webp');

  const aiView = buildDocumentAiView(document);

  return (
    <Drawer open={isOpen} onOpenChange={(open) => !open && onClose()} direction="right">
      <DrawerContent className="fixed inset-y-0 right-0 bottom-0 top-0 mt-0 h-full w-full max-w-4xl rounded-t-none border-l border-border bg-card shadow-2xl flex flex-col">
        <DrawerHeader className="border-b border-border/80 px-6 py-5 flex items-center justify-between shrink-0">
          <div>
            <DrawerTitle className="text-xl font-bold text-foreground flex items-center gap-2">
              {document.name}
            </DrawerTitle>
            <p className="text-xs text-muted-foreground mt-1">
              Tipo: <span className="font-semibold text-foreground">{document.document_type}</span> · 
              Emissão: <span className="font-semibold text-foreground">{dateBR(document.issued_at)}</span>
            </p>
          </div>
          <div className="flex items-center gap-2">
            {document.file_url && (
              <>
                <a href={document.file_url} target="_blank" rel="noopener noreferrer">
                  <Button variant="outline" size="sm" className="gap-1.5 h-8">
                    <ExternalLink className="h-4 w-4" />
                    Abrir em nova aba
                  </Button>
                </a>
                <a href={document.file_url} download>
                  <Button variant="outline" size="sm" className="gap-1.5 h-8">
                    <Download className="h-4 w-4" />
                    Baixar
                  </Button>
                </a>
              </>
            )}
            <Button variant="outline" size="sm" onClick={onClose} className="h-8">
              Fechar
            </Button>
          </div>
        </DrawerHeader>

        {/* Content Area split into Preview and Details panel */}
        <div className="flex-1 min-h-0 flex flex-col md:flex-row bg-muted/5">
          {/* File Preview */}
          <div className="flex-1 p-6 flex flex-col justify-center items-center border-r border-border/60 min-h-0">
            {document.file_url ? (
              isPdf ? (
                <iframe
                  src={document.file_url}
                  className="w-full h-full min-h-[60vh] rounded-xl border border-border bg-background shadow-sm"
                  title={document.name}
                />
              ) : isImage ? (
                <div className="w-full h-full flex items-center justify-center bg-black/5 rounded-xl border p-4 max-h-[65vh] overflow-hidden">
                  <img
                    src={document.file_url}
                    className="max-h-full max-w-full object-contain rounded shadow-sm"
                    alt={document.name}
                  />
                </div>
              ) : (
                <div className="text-center py-16 px-6 max-w-md border border-dashed rounded-2xl bg-card">
                  <FileText className="h-16 w-16 text-muted-foreground/60 mx-auto mb-4" />
                  <h4 className="font-bold text-foreground mb-1">Pré-visualização não disponível</h4>
                  <p className="text-sm text-muted-foreground mb-6">
                    O formato deste arquivo não suporta visualização direta no navegador. Faça o download para abrir localmente.
                  </p>
                  <a href={document.file_url} download>
                    <Button className="gap-1.5 shadow-glow-sm">
                      <Download className="h-4 w-4" />
                      Baixar Arquivo
                    </Button>
                  </a>
                </div>
              )
            ) : (
              <div className="text-center py-16 px-6 max-w-md border border-dashed rounded-2xl bg-card">
                <FileText className="h-16 w-16 text-muted-foreground/60 mx-auto mb-4" />
                <h4 className="font-bold text-foreground mb-1">Nenhum arquivo anexado</h4>
                <p className="text-sm text-muted-foreground">
                  Este registro de documento não possui um arquivo PDF/imagem vinculado.
                </p>
              </div>
            )}
          </div>

          {/* AI Info & Details Panel */}
          <div className="w-full md:w-80 shrink-0 p-6 overflow-y-auto space-y-6 scrollbar">
            {/* AI Insights Card */}
            <div className="rounded-xl border border-primary/20 bg-primary/5 p-4 space-y-4 shadow-glow-sm">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <Sparkles className="h-4 w-4 text-primary" />
                  <span className="text-xs font-bold text-foreground uppercase tracking-wider">Extração IA</span>
                </div>
                <Badge variant={aiView.parseStatusVariant}>{aiView.parseStatusLabel}</Badge>
              </div>

              {aiView.classification ? (
                <div className="space-y-4">
                  <div>
                    <h5 className="text-xs font-bold text-foreground uppercase">Classificação</h5>
                    <p className="text-sm text-foreground/90 font-medium mt-1">
                      {aiView.classification.documentType}
                    </p>
                    {aiView.classification.confidenceLabel && (
                      <span className="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded mt-1 inline-block">
                        Confiança: {aiView.classification.confidenceLabel}
                      </span>
                    )}
                  </div>

                  {aiView.classification.fields.length > 0 && (
                    <div className="space-y-2 border-t pt-3 border-border/50">
                      <h5 className="text-xs font-bold text-foreground uppercase">Campos Extraídos</h5>
                      <div className="space-y-1.5 mt-1.5">
                        {aiView.classification.fields.map((f) => (
                          <div key={f.label} className="text-xs flex justify-between gap-2">
                            <span className="text-muted-foreground">{f.label}:</span>
                            <span className="font-semibold text-foreground text-right">{f.value}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {aiView.classification.summary && (
                    <div className="border-t pt-3 border-border/50">
                      <h5 className="text-xs font-bold text-foreground uppercase">Resumo do Conteúdo</h5>
                      <p className="text-xs text-muted-foreground leading-relaxed mt-1.5">
                        {aiView.classification.summary}
                      </p>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {aiView.parseError || 'Aguardando processamento de inteligência artificial ou documento pendente.'}
                </p>
              )}
            </div>

            {/* Standard Meta Info */}
            <div className="space-y-4 border-t pt-4 border-border/80">
              <h5 className="text-xs font-bold text-foreground uppercase tracking-wide">Ficha do Documento</h5>
              <div className="space-y-3 text-sm">
                <div>
                  <span className="text-xs text-muted-foreground block">Vencimento</span>
                  <span className={`font-semibold ${document.status === 'expired' ? 'text-destructive' : 'text-foreground'}`}>
                    {dateBR(document.expires_at)}
                  </span>
                </div>
                {document.notes && (
                  <div>
                    <span className="text-xs text-muted-foreground block">Observações</span>
                    <p className="text-xs text-foreground/80 mt-1 bg-muted/40 p-2 rounded border border-border/40 leading-normal">
                      {document.notes}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </DrawerContent>
    </Drawer>
  );
}
