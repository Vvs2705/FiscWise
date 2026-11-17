/**
 * Cofre de certificados A1 usados na emissão de NFS-e.
 *
 * O escritório envia o .pfx/.p12 e a senha; o backend confere (senha, ICP-Brasil,
 * validade, CNPJ do cliente), guarda criptografado e devolve só os metadados.
 */
import { useMemo, useRef, useState, type FormEvent } from 'react';
import { toast } from 'sonner';
import { Ban, KeyRound, Lock, ShieldCheck, Trash2, Unlock, Upload } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { FormField } from '@/components/ui/FormField';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { EmptyState, LoadingCards } from '@/components/ui/StateViews';
import { WarningPanel } from '@/components/ui/OperationalStates';
import { getApiErrorMessage } from '@/lib/api';
import { useClients } from '@/lib/hooks/useOperations';
import { usePermission } from '@/lib/hooks/usePermission';
import {
  useBloquearCertificado,
  useCertificadosCofre,
  useDesbloquearCertificado,
  useEnviarCertificado,
  useRemoverCertificado,
} from '@/lib/hooks/useCertificados';
import {
  AJUDA_A1_A3,
  AVISO_SEGURANCA,
  type CertificadoCofre,
  type EscopoCertificado,
  dataBR,
  dataHoraBR,
  formatarDocumentoCertificado,
  seloCertificado,
  validarEnvioCertificado,
} from '@/lib/certificados';

interface EnviarCertificadoDialogProps {
  open: boolean;
  onClose: () => void;
  /** Fixa o dono do certificado (ex.: dentro da configuração de um cliente). */
  escopoFixo?: EscopoCertificado;
  clientIdFixo?: string | null;
  onEnviado?: (cert: CertificadoCofre) => void;
}

export function EnviarCertificadoDialog({
  open,
  onClose,
  escopoFixo,
  clientIdFixo,
  onEnviado,
}: EnviarCertificadoDialogProps) {
  const { data: clients } = useClients();
  const enviar = useEnviarCertificado();
  const [escopo, setEscopo] = useState<EscopoCertificado>(escopoFixo ?? 'escritorio');
  const [clientId, setClientId] = useState<string>(clientIdFixo ?? '');
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [senha, setSenha] = useState('');
  const [erro, setErro] = useState<string | null>(null);
  const inputArquivo = useRef<HTMLInputElement>(null);

  function limpar() {
    // A senha nunca fica guardada no navegador: some do estado ao enviar ou fechar.
    setSenha('');
    setArquivo(null);
    setErro(null);
    if (inputArquivo.current) inputArquivo.current.value = '';
  }

  function fechar() {
    limpar();
    onClose();
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const escopoFinal = escopoFixo ?? escopo;
    const clienteFinal = clientIdFixo ?? clientId;
    const problema = validarEnvioCertificado({ arquivo, senha, escopo: escopoFinal, clientId: clienteFinal });
    if (problema) {
      setErro(problema);
      return;
    }
    setErro(null);
    try {
      const cert = await enviar.mutateAsync({
        arquivo: arquivo as File,
        senha,
        escopo: escopoFinal,
        client_id: escopoFinal === 'cliente' ? clienteFinal : null,
      });
      toast.success('Certificado conferido e guardado com segurança.');
      onEnviado?.(cert);
      fechar();
    } catch (err) {
      setSenha('');
      setErro(getApiErrorMessage(err, 'Não foi possível conferir o certificado.'));
    }
  }

  return (
    <Dialog open={open} onClose={fechar} title="Enviar certificado A1">
      <form onSubmit={onSubmit} className="space-y-4" noValidate autoComplete="off">
        <p className="text-sm text-muted-foreground">{AVISO_SEGURANCA}</p>

        {!escopoFixo && (
          <FormField label="De quem é o certificado" htmlFor="cert-escopo" required>
            <Select
              id="cert-escopo"
              value={escopo}
              onChange={(e) => setEscopo(e.target.value as EscopoCertificado)}
            >
              <option value="escritorio">Do escritório (para emitir com procuração)</option>
              <option value="cliente">De um cliente (a empresa que emite a nota)</option>
            </Select>
          </FormField>
        )}

        {!clientIdFixo && (escopoFixo ?? escopo) === 'cliente' && (
          <FormField label="Cliente" htmlFor="cert-cliente" required>
            <Select id="cert-cliente" value={clientId} onChange={(e) => setClientId(e.target.value)}>
              <option value="">Selecione o cliente</option>
              {(clients ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
          </FormField>
        )}

        <FormField label="Arquivo do certificado (.pfx ou .p12)" htmlFor="cert-arquivo" required>
          <Input
            ref={inputArquivo}
            id="cert-arquivo"
            type="file"
            accept=".pfx,.p12,application/x-pkcs12"
            onChange={(e) => setArquivo(e.target.files?.[0] ?? null)}
          />
        </FormField>

        <FormField label="Senha do certificado" htmlFor="cert-senha" required>
          <Input
            id="cert-senha"
            type="password"
            autoComplete="new-password"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
          />
        </FormField>

        <p className="text-xs text-muted-foreground">{AJUDA_A1_A3}</p>

        {erro && <WarningPanel variant="danger" title="Certificado não aceito" description={erro} />}

        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="outline" onClick={fechar}>
            Cancelar
          </Button>
          <Button type="submit" disabled={enviar.isPending} className="gap-2">
            <Upload className="h-4 w-4" />
            {enviar.isPending ? 'Conferindo...' : 'Enviar e conferir'}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

const TOM_BADGE = { success: 'success', warning: 'warning', danger: 'danger', neutral: 'neutral' } as const;

export function SeloCertificado({ cert }: { cert: CertificadoCofre }) {
  const selo = seloCertificado(cert);
  return <Badge variant={TOM_BADGE[selo.tom]}>{selo.label}</Badge>;
}

function LinhaCertificado({
  cert,
  nomeCliente,
  podeGerenciar,
}: {
  cert: CertificadoCofre;
  nomeCliente?: string;
  podeGerenciar: boolean;
}) {
  const bloquear = useBloquearCertificado();
  const desbloquear = useDesbloquearCertificado();
  const remover = useRemoverCertificado();
  const bloqueado = cert.status === 'bloqueado';

  async function acao(fn: () => Promise<unknown>, ok: string, falha: string) {
    try {
      await fn();
      toast.success(ok);
    } catch (err) {
      toast.error(getApiErrorMessage(err, falha));
    }
  }

  function onRemover() {
    if (
      !confirm(
        'Remover este certificado do cofre? A emissão dos clientes que usam ele fica bloqueada até enviar outro.',
      )
    )
      return;
    void acao(() => remover.mutateAsync(cert.id), 'Certificado removido.', 'Não foi possível remover.');
  }

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border/60 bg-card p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <KeyRound className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
          <span className="font-semibold text-foreground">{cert.titular_nome || 'Titular não informado'}</span>
          <SeloCertificado cert={cert} />
        </div>
        <p className="text-xs text-muted-foreground">
          {(cert.tipo_documento || '').toUpperCase() || 'Documento'}{' '}
          {formatarDocumentoCertificado(cert.documento)}
          {nomeCliente ? ` · Cliente: ${nomeCliente}` : ''}
          {cert.emissor ? ` · Certificadora: ${cert.emissor}` : ''}
        </p>
        <p className="text-xs text-muted-foreground">
          Válido até {dataBR(cert.valido_ate)} · Último uso: {cert.ultimo_uso ? dataHoraBR(cert.ultimo_uso) : 'nunca'}
        </p>
      </div>
      {podeGerenciar && (
        <div className="flex shrink-0 items-center gap-2">
          {bloqueado ? (
            <Button
              size="sm"
              variant="outline"
              className="gap-1.5"
              disabled={desbloquear.isPending}
              onClick={() =>
                void acao(() => desbloquear.mutateAsync(cert.id), 'Certificado desbloqueado.', 'Não foi possível desbloquear.')
              }
            >
              <Unlock className="h-3.5 w-3.5" /> Desbloquear
            </Button>
          ) : (
            <Button
              size="sm"
              variant="outline"
              className="gap-1.5"
              disabled={bloquear.isPending}
              onClick={() =>
                void acao(() => bloquear.mutateAsync(cert.id), 'Certificado bloqueado para uso.', 'Não foi possível bloquear.')
              }
            >
              <Ban className="h-3.5 w-3.5" /> Bloquear
            </Button>
          )}
          <Button
            size="sm"
            variant="ghost"
            className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
            disabled={remover.isPending}
            onClick={onRemover}
            aria-label="Remover certificado"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      )}
    </div>
  );
}

/** Seção do cofre na página de Certificados. */
export function CofreCertificados() {
  const { hasRole } = usePermission();
  const podeGerenciar = hasRole('admin');
  const { data: certificados, isLoading, isError, error } = useCertificadosCofre();
  const { data: clients } = useClients();
  const [aberto, setAberto] = useState(false);

  const nomes = useMemo(() => new Map((clients ?? []).map((c) => [c.id, c.name])), [clients]);
  const doEscritorio = (certificados ?? []).filter((c) => c.escopo === 'escritorio');
  const deClientes = (certificados ?? []).filter((c) => c.escopo === 'cliente');
  const cofreIndisponivel =
    isError && (error as { response?: { status?: number } })?.response?.status === 503;

  return (
    <Card className="border-primary/20">
      <CardHeader className="flex flex-col gap-3 space-y-0 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldCheck className="h-5 w-5 text-primary" aria-hidden="true" />
            Cofre de certificados para emissão de NFS-e
          </CardTitle>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Envie o certificado A1 do escritório (para emitir com procuração) ou o de cada cliente. O sistema
            confere senha, validade e CNPJ e libera a emissão. <Lock className="inline h-3.5 w-3.5" aria-hidden="true" />{' '}
            {AVISO_SEGURANCA}
          </p>
        </div>
        {podeGerenciar && (
          <Button size="sm" onClick={() => setAberto(true)} className="gap-1.5 self-start">
            <Upload className="h-4 w-4" /> Enviar certificado A1
          </Button>
        )}
      </CardHeader>
      <CardContent className="space-y-5">
        {!podeGerenciar && (
          <p className="text-xs text-muted-foreground">
            Só o responsável ou um administrador do escritório envia, bloqueia ou remove certificados.
          </p>
        )}
        {cofreIndisponivel ? (
          <WarningPanel
            variant="info"
            title="Cofre de certificados ainda não disponível"
            description="O armazenamento seguro dos certificados não está configurado neste ambiente."
          />
        ) : isError ? (
          <WarningPanel
            variant="danger"
            title="Não foi possível carregar os certificados"
            description={getApiErrorMessage(error, 'Tente novamente em instantes.')}
          />
        ) : isLoading ? (
          <div className="grid gap-3 sm:grid-cols-2">
            <LoadingCards count={2} />
          </div>
        ) : (
          <>
            <section className="space-y-2">
              <h3 className="text-sm font-semibold text-foreground">Certificado do escritório</h3>
              {doEscritorio.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  Nenhum. Com ele e uma procuração eletrônica de cada cliente, o escritório emite pelos clientes sem
                  guardar um certificado por empresa.
                </p>
              ) : (
                doEscritorio.map((c) => <LinhaCertificado key={c.id} cert={c} podeGerenciar={podeGerenciar} />)
              )}
            </section>
            <section className="space-y-2">
              <h3 className="text-sm font-semibold text-foreground">Certificados dos clientes</h3>
              {deClientes.length === 0 ? (
                <EmptyState
                  title="Nenhum certificado de cliente"
                  description="Envie o A1 da empresa que vai emitir as notas, ou use o certificado do escritório com procuração."
                />
              ) : (
                deClientes.map((c) => (
                  <LinhaCertificado
                    key={c.id}
                    cert={c}
                    nomeCliente={c.client_id ? nomes.get(c.client_id) : undefined}
                    podeGerenciar={podeGerenciar}
                  />
                ))
              )}
            </section>
          </>
        )}
      </CardContent>
      <EnviarCertificadoDialog open={aberto} onClose={() => setAberto(false)} />
    </Card>
  );
}
