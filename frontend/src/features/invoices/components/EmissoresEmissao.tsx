/** Emissores de NFS-e com a situação da emissão real e o painel "Como emitir". */
import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { CheckCircle2, KeyRound, XCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { useConfigEmissao } from '@/lib/hooks/useCertificados';
import { useClients } from '@/lib/hooks/useOperations';
import { MODO_LABEL, formatarDocumentoCertificado } from '@/lib/certificados';
import type { InvoiceIssuerResponse } from '../services/invoices.service';
import { EmissaoConfigPanel } from './EmissaoConfigPanel';

/** Parâmetro de URL que abre a configuração de um emissor (`?configurar=<issuer_id>`). */
export const PARAM_CONFIGURAR_EMISSOR = 'configurar';

function SituacaoEmissao({ issuerId }: { issuerId: string }) {
  const { data, isLoading, isError } = useConfigEmissao(issuerId);
  if (isLoading) return <span className="text-xs text-muted-foreground">Verificando...</span>;
  if (isError || !data) return <Badge variant="neutral">Indisponível</Badge>;
  return (
    <div className="flex flex-wrap items-center gap-2">
      {data.emissao_liberada ? (
        <Badge variant="success" className="gap-1">
          <CheckCircle2 className="h-3.5 w-3.5" /> Emissão liberada
        </Badge>
      ) : (
        <Badge variant="warning" className="gap-1">
          <XCircle className="h-3.5 w-3.5" /> {data.pendencias.length || 1}{' '}
          {data.pendencias.length === 1 ? 'pendência' : 'pendências'}
        </Badge>
      )}
      {data.modo_certificado && (
        <span className="text-xs text-muted-foreground">{MODO_LABEL[data.modo_certificado]}</span>
      )}
    </div>
  );
}

export function EmissoresEmissao({ issuers }: { issuers: InvoiceIssuerResponse[] }) {
  const { data: clients } = useClients();
  const [params, setParams] = useSearchParams();
  const [aberto, setAberto] = useState<string | null>(null);

  // Link vindo da tela de emissão: abre direto a configuração do emissor.
  useEffect(() => {
    const id = params.get(PARAM_CONFIGURAR_EMISSOR);
    if (id && issuers.some((i) => i.id === id)) setAberto(id);
  }, [params, issuers]);

  const nomes = useMemo(() => new Map((clients ?? []).map((c) => [c.id, c.name])), [clients]);
  const emissorAberto = issuers.find((i) => i.id === aberto) ?? null;

  function fechar() {
    setAberto(null);
    if (params.has(PARAM_CONFIGURAR_EMISSOR)) {
      const novo = new URLSearchParams(params);
      novo.delete(PARAM_CONFIGURAR_EMISSOR);
      setParams(novo, { replace: true });
    }
  }

  function nomeEmissor(i: InvoiceIssuerResponse) {
    const cliente = i.client_id ? nomes.get(i.client_id) : undefined;
    return cliente ?? `CNPJ ${formatarDocumentoCertificado(i.cnpj)}`;
  }

  return (
    <Card className="border-border/60 bg-card">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm font-semibold text-muted-foreground">
          <KeyRound className="h-4 w-4" aria-hidden="true" />
          Emissores e certificado para emissão
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {issuers.map((i) => (
          <div
            key={i.id}
            className="flex flex-col gap-2 rounded-lg border border-border/60 p-3 sm:flex-row sm:items-center sm:justify-between"
          >
            <div className="min-w-0">
              <p className="font-medium text-foreground">{nomeEmissor(i)}</p>
              <p className="text-xs text-muted-foreground">
                CNPJ {formatarDocumentoCertificado(i.cnpj)} · IBGE {i.municipio_ibge}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <SituacaoEmissao issuerId={i.id} />
              <Button size="sm" variant="outline" onClick={() => setAberto(i.id)}>
                Como emitir
              </Button>
            </div>
          </div>
        ))}
      </CardContent>

      <Dialog
        open={!!emissorAberto}
        onClose={fechar}
        title={emissorAberto ? `Emissão de notas · ${nomeEmissor(emissorAberto)}` : 'Emissão de notas'}
        className="max-w-2xl"
      >
        {emissorAberto && (
          <EmissaoConfigPanel
            issuerId={emissorAberto.id}
            issuerCnpj={emissorAberto.cnpj}
            clientId={emissorAberto.client_id ?? null}
          />
        )}
      </Dialog>
    </Card>
  );
}
