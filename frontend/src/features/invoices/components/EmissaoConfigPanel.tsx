/**
 * "Como emitir as notas deste cliente": escolhe o certificado (da própria
 * empresa ou do escritório com procuração), testa contra o governo e mostra
 * se a emissão está liberada ou o que falta.
 */
import { useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import { CheckCircle2, ExternalLink, FlaskConical, Upload, XCircle } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { FormField } from '@/components/ui/FormField';
import { Select } from '@/components/ui/Select';
import { PageSpinner } from '@/components/ui/StateViews';
import { WarningPanel } from '@/components/ui/OperationalStates';
import { getApiErrorMessage } from '@/lib/api';
import { usePermission } from '@/lib/hooks/usePermission';
import {
  useCertificadosCofre,
  useConfigEmissao,
  useSalvarConfigEmissao,
  useTestarEmissao,
} from '@/lib/hooks/useCertificados';
import {
  MODO_LABEL,
  RECEITA_PROCURACAO_URL,
  type ModoCertificado,
  certificadoUtilizavel,
  dataBR,
  dataHoraBR,
  formatarDocumentoCertificado,
} from '@/lib/certificados';
import { somenteDigitos } from '@/lib/auth';
import { EnviarCertificadoDialog, SeloCertificado } from './CofreCertificados';

interface EmissaoConfigPanelProps {
  issuerId: string;
  /** CNPJ do emissor (para achar o certificado da própria empresa). */
  issuerCnpj?: string | null;
  /** Cliente do FiscWise ligado ao emissor, quando houver. */
  clientId?: string | null;
}

export function EmissaoConfigPanel({ issuerId, issuerCnpj, clientId }: EmissaoConfigPanelProps) {
  const { hasRole } = usePermission();
  const podeConfigurar = hasRole('admin');
  const { data: config, isLoading, isError, error } = useConfigEmissao(issuerId);
  const { data: certificados } = useCertificadosCofre();
  const salvar = useSalvarConfigEmissao(issuerId);
  const testar = useTestarEmissao(issuerId);

  const [modo, setModo] = useState<ModoCertificado | ''>('');
  const [certificadoId, setCertificadoId] = useState('');
  const [procuracao, setProcuracao] = useState(false);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    if (!config) return;
    setModo(config.modo_certificado ?? '');
    setCertificadoId(config.certificado_id ?? '');
    setProcuracao(!!config.procuracao_confirmada_em);
  }, [config]);

  const cnpj = somenteDigitos(issuerCnpj ?? '');
  const certificadosDaEmpresa = useMemo(
    () =>
      (certificados ?? []).filter(
        (c) =>
          c.escopo === 'cliente' &&
          ((clientId && c.client_id === clientId) || (cnpj && somenteDigitos(c.documento ?? '') === cnpj)),
      ),
    [certificados, clientId, cnpj],
  );
  const certificadoEscritorio = (certificados ?? []).find((c) => c.escopo === 'escritorio' && certificadoUtilizavel(c))
    ?? (certificados ?? []).find((c) => c.escopo === 'escritorio');

  const alterado =
    !!config &&
    (modo !== (config.modo_certificado ?? '') ||
      (modo === 'proprio' && certificadoId !== (config.certificado_id ?? '')) ||
      (modo === 'procuracao' && procuracao !== !!config.procuracao_confirmada_em));

  async function onSalvar() {
    if (!modo) {
      toast.error('Escolha como as notas deste cliente serão emitidas.');
      return;
    }
    if (modo === 'proprio' && !certificadoId) {
      toast.error('Escolha o certificado da empresa ou envie um.');
      return;
    }
    try {
      await salvar.mutateAsync({
        modo_certificado: modo,
        certificado_id: modo === 'proprio' ? certificadoId : certificadoEscritorio?.id ?? null,
        procuracao_confirmada: modo === 'procuracao' ? procuracao : undefined,
      });
      toast.success('Configuração salva. Rode o teste de emissão para liberar.');
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Não foi possível salvar a configuração.'));
    }
  }

  async function onTestar() {
    try {
      const r = await testar.mutateAsync();
      if (r.emissao_liberada) toast.success('Teste aprovado: emissão liberada.');
      else toast.error(r.ultimo_teste_mensagem || 'O teste não passou. Veja as pendências.');
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Não foi possível testar a emissão agora.'));
    }
  }

  if (isLoading) return <PageSpinner />;
  if (isError || !config) {
    const status = (error as { response?: { status?: number } })?.response?.status;
    return (
      <WarningPanel
        variant={status === 503 ? 'info' : 'danger'}
        title={status === 503 ? 'Emissão real ainda não disponível' : 'Não foi possível carregar a configuração'}
        description={getApiErrorMessage(error, 'Tente novamente em instantes.')}
      />
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2">
        {config.emissao_liberada ? (
          <Badge variant="success" className="gap-1">
            <CheckCircle2 className="h-3.5 w-3.5" /> Emissão liberada
          </Badge>
        ) : (
          <Badge variant="warning" className="gap-1">
            <XCircle className="h-3.5 w-3.5" /> Emissão bloqueada
          </Badge>
        )}
        {config.ultimo_teste_em && (
          <span className="text-xs text-muted-foreground">
            Último teste: {dataHoraBR(config.ultimo_teste_em)} —{' '}
            {config.ultimo_teste_ok ? 'aprovado' : 'não passou'}
          </span>
        )}
      </div>

      {!config.emissao_liberada && config.pendencias.length > 0 && (
        <WarningPanel variant="warning" title="O que falta para liberar a emissão">
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-foreground/80">
            {config.pendencias.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        </WarningPanel>
      )}

      {config.ultimo_teste_ok === false && config.ultimo_teste_mensagem && (
        <WarningPanel variant="danger" title="Resposta do último teste" description={config.ultimo_teste_mensagem} />
      )}

      <fieldset className="space-y-3" disabled={!podeConfigurar}>
        <legend className="text-sm font-semibold text-foreground">Como emitir as notas deste cliente</legend>

        <label className="flex cursor-pointer gap-3 rounded-lg border border-border/60 p-3 has-[:checked]:border-primary/50 has-[:checked]:bg-primary/5">
          <input
            type="radio"
            name={`modo-${issuerId}`}
            className="mt-1"
            checked={modo === 'proprio'}
            onChange={() => setModo('proprio')}
          />
          <div className="flex-1 space-y-2">
            <span className="block text-sm font-medium text-foreground">{MODO_LABEL.proprio}</span>
            <span className="block text-xs text-muted-foreground">
              Usa o A1 da empresa que emite a nota. O CNPJ do certificado precisa ser o mesmo do emissor.
            </span>
            {modo === 'proprio' && (
              <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
                <FormField label="Certificado" htmlFor={`cert-${issuerId}`} className="flex-1">
                  <Select
                    id={`cert-${issuerId}`}
                    value={certificadoId}
                    onChange={(e) => setCertificadoId(e.target.value)}
                  >
                    <option value="">Selecione</option>
                    {certificadosDaEmpresa.map((c) => (
                      <option key={c.id} value={c.id}>
                        {(c.titular_nome || 'Certificado')} · {formatarDocumentoCertificado(c.documento)} · até{' '}
                        {dataBR(c.valido_ate)}
                      </option>
                    ))}
                  </Select>
                </FormField>
                <Button type="button" size="sm" variant="outline" className="gap-1.5" onClick={() => setEnviando(true)}>
                  <Upload className="h-3.5 w-3.5" /> Enviar certificado
                </Button>
              </div>
            )}
            {modo === 'proprio' && certificadosDaEmpresa.length === 0 && (
              <p className="text-xs text-warning">Nenhum certificado desta empresa no cofre ainda.</p>
            )}
          </div>
        </label>

        <label className="flex cursor-pointer gap-3 rounded-lg border border-border/60 p-3 has-[:checked]:border-primary/50 has-[:checked]:bg-primary/5">
          <input
            type="radio"
            name={`modo-${issuerId}`}
            className="mt-1"
            checked={modo === 'procuracao'}
            onChange={() => setModo('procuracao')}
          />
          <div className="flex-1 space-y-2">
            <span className="block text-sm font-medium text-foreground">{MODO_LABEL.procuracao}</span>
            <span className="block text-xs text-muted-foreground">
              O escritório emite com o próprio A1, em nome do cliente, depois que o cliente cadastra uma procuração
              eletrônica na Receita.
            </span>
            {modo === 'procuracao' && (
              <div className="space-y-3">
                {certificadoEscritorio ? (
                  <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <span>
                      Certificado do escritório: <strong className="text-foreground">{certificadoEscritorio.titular_nome}</strong>{' '}
                      ({formatarDocumentoCertificado(certificadoEscritorio.documento)})
                    </span>
                    <SeloCertificado cert={certificadoEscritorio} />
                  </div>
                ) : (
                  <p className="text-xs text-warning">
                    O escritório ainda não enviou o certificado dele. Envie em Certificados.
                  </p>
                )}
                <ol className="list-decimal space-y-1 pl-5 text-xs text-foreground/80">
                  <li>
                    O cliente entra em{' '}
                    <a
                      href={RECEITA_PROCURACAO_URL}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-primary hover:underline"
                    >
                      servicos.receitafederal.gov.br <ExternalLink className="h-3 w-3" />
                    </a>{' '}
                    com a conta gov.br ou o certificado da empresa.
                  </li>
                  <li>Abre "Nova Autorização" e escolhe o serviço NFS-e.</li>
                  <li>
                    Informa o CNPJ/CPF do escritório
                    {certificadoEscritorio?.documento
                      ? ` (${formatarDocumentoCertificado(certificadoEscritorio.documento)})`
                      : ''}{' '}
                    e confirma.
                  </li>
                </ol>
                <label className="flex items-center gap-2 text-sm text-foreground">
                  <input
                    type="checkbox"
                    checked={procuracao}
                    onChange={(e) => setProcuracao(e.target.checked)}
                    className="h-4 w-4 rounded border-border"
                  />
                  O cliente já cadastrou a procuração
                  {config.procuracao_confirmada_em && (
                    <span className="text-xs text-muted-foreground">
                      (marcado em {dataBR(config.procuracao_confirmada_em)})
                    </span>
                  )}
                </label>
              </div>
            )}
          </div>
        </label>
      </fieldset>

      {podeConfigurar ? (
        <div className="flex flex-col gap-2 border-t border-border/40 pt-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-muted-foreground">
            Qualquer mudança aqui exige um novo teste de emissão antes de liberar.
          </p>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={!alterado || salvar.isPending}
              onClick={() => void onSalvar()}
            >
              {salvar.isPending ? 'Salvando...' : 'Salvar'}
            </Button>
            <Button
              type="button"
              size="sm"
              className="gap-1.5"
              disabled={alterado || !config.modo_certificado || testar.isPending}
              onClick={() => void onTestar()}
              title={alterado ? 'Salve a configuração antes de testar' : undefined}
            >
              <FlaskConical className="h-4 w-4" />
              {testar.isPending ? 'Testando...' : 'Testar emissão'}
            </Button>
          </div>
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">
          Só o responsável ou um administrador do escritório altera a forma de emissão.
        </p>
      )}

      <EnviarCertificadoDialog
        open={enviando}
        onClose={() => setEnviando(false)}
        escopoFixo="cliente"
        clientIdFixo={clientId ?? undefined}
        onEnviado={(cert) => setCertificadoId(cert.id)}
      />
    </div>
  );
}
