import { useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { ExternalLink, MapPin, Paperclip, ShieldAlert, UsersRound } from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { FormField } from '@/components/ui/FormField';
import { Badge } from '@/components/ui/Badge';
import { Dialog } from '@/components/ui/Dialog';
import { EmptyState } from '@/components/ui/EmptyState';
import { getApiErrorMessage } from '@/lib/api';
import {
  STATUS_LABEL,
  STATUS_LABEL_EQUIPE,
  STATUS_TONE,
  TIPO_LABEL,
  UFS,
  regiaoLabel,
  statusLabel,
  tipoLabel,
  type AjusteFiscalEquipe,
  type StatusAjuste,
  type TipoAjuste,
} from '@/lib/ajustesFiscais';
import {
  useAcaoEquipeAjuste,
  useEquipeAjusteDetalhe,
  useEquipeAjustes,
  type AcaoEquipe,
} from '@/lib/hooks/useAjustesFiscais';

const textareaClasses =
  'flex min-h-[96px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2';

function dataBr(iso: string | null | undefined): string {
  if (!iso) return '';
  const [y, m, d] = iso.slice(0, 10).split('-');
  return d && m && y ? `${d}/${m}/${y}` : iso;
}

function detalheRegra(a: AjusteFiscalEquipe): string {
  if (a.tipo === 'feriado' && a.data) return `Feriado em ${dataBr(a.data)}${a.recorrente_anual ? ' (todo ano)' : ''}`;
  if (a.tipo === 'prazo' && a.obrigacao_code) return `${a.obrigacao_code} vence no dia ${a.due_day ?? '?'}`;
  return tipoLabel(a.tipo);
}

export function EquipeAjustesPage() {
  const [status, setStatus] = useState('');
  const [uf, setUf] = useState('');
  const [tipo, setTipo] = useState('');
  const [aberto, setAberto] = useState<string | null>(null);
  const [confirmarGeral, setConfirmarGeral] = useState<AjusteFiscalEquipe | null>(null);
  const [recusando, setRecusando] = useState<AjusteFiscalEquipe | null>(null);
  const [resposta, setResposta] = useState('');

  const { data: itens, isLoading, error } = useEquipeAjustes({ status, uf, tipo });
  const detalhe = useEquipeAjusteDetalhe(aberto);
  const acao = useAcaoEquipeAjuste();

  const semAcesso = axios.isAxiosError(error) && error.response?.status === 403;

  const executar = async (item: AjusteFiscalEquipe, qual: AcaoEquipe, texto?: string) => {
    try {
      await acao.mutateAsync({ id: item.id, acao: qual, resposta: texto });
      toast.success(
        qual === 'regra-geral'
          ? 'Virou regra geral para a região.'
          : qual === 'recusar'
            ? 'Solicitação recusada.'
            : 'Marcada como em análise.',
      );
      setConfirmarGeral(null);
      setRecusando(null);
      setResposta('');
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Não foi possível concluir a ação.'));
    }
  };

  if (semAcesso) {
    return (
      <EmptyState
        title="Acesso só da equipe FiscWise"
        description="Esta tela é usada pela equipe FiscWise para analisar os pedidos de ajuste fiscal."
        icon={ShieldAlert}
      />
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Solicitações de ajuste fiscal"
        subtitle="Equipe FiscWise: analise e transforme em regra geral da região"
        icon={<UsersRound className="h-5 w-5" />}
      />

      <div className="grid gap-3 sm:grid-cols-3">
        <FormField label="Status" htmlFor="eq-status">
          <Select id="eq-status" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">Todos</option>
            {(Object.keys(STATUS_LABEL) as StatusAjuste[]).map((s) => (
              <option key={s} value={s}>{STATUS_LABEL_EQUIPE[s]}</option>
            ))}
          </Select>
        </FormField>
        <FormField label="Estado" htmlFor="eq-uf">
          <Select id="eq-uf" value={uf} onChange={(e) => setUf(e.target.value)}>
            <option value="">Todos</option>
            {UFS.map((u) => (
              <option key={u} value={u}>{u}</option>
            ))}
          </Select>
        </FormField>
        <FormField label="Tipo" htmlFor="eq-tipo">
          <Select id="eq-tipo" value={tipo} onChange={(e) => setTipo(e.target.value)}>
            <option value="">Todos</option>
            {(Object.keys(TIPO_LABEL) as TipoAjuste[]).map((t) => (
              <option key={t} value={t}>{TIPO_LABEL[t]}</option>
            ))}
          </Select>
        </FormField>
      </div>

      {isLoading ? (
        <div className="h-24 animate-pulse rounded-lg bg-muted" />
      ) : !itens || itens.length === 0 ? (
        <EmptyState title="Nenhuma solicitação com esses filtros" icon={UsersRound} />
      ) : (
        <div className="space-y-3">
          {itens.map((a) => {
            const expandido = aberto === a.id;
            const doc = expandido ? detalhe.data?.knowledge_doc : null;
            return (
              <Card key={a.id}>
                <CardContent className="space-y-2 pt-5">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={STATUS_TONE[a.status] ?? 'neutral'}>{statusLabel(a.status, 'equipe')}</Badge>
                    <span className="text-sm font-medium">{detalheRegra(a)}</span>
                    <span className="flex items-center gap-1 text-xs text-muted-foreground">
                      <MapPin className="h-3.5 w-3.5" />
                      {regiaoLabel(a)}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {a.tenant_name} · enviada em {dataBr(a.created_at)}
                  </p>
                  <p className="whitespace-pre-line text-sm">{a.descricao}</p>
                  {a.fonte && <p className="text-xs text-muted-foreground">Fonte: {a.fonte}</p>}
                  {a.knowledge_doc_title && (
                    <button
                      type="button"
                      className="flex items-center gap-1 text-xs text-primary hover:underline"
                      onClick={() => setAberto(expandido ? null : a.id)}
                    >
                      <Paperclip className="h-3.5 w-3.5" />
                      {expandido ? 'Esconder documento' : `Ver documento: ${a.knowledge_doc_title}`}
                    </button>
                  )}
                  {expandido && (
                    <div className="rounded-md border bg-muted/40 p-3 text-xs">
                      {detalhe.isLoading ? (
                        'Carregando...'
                      ) : doc ? (
                        <>
                          <p className="font-medium">{doc.title}</p>
                          <p className="mt-1 whitespace-pre-line text-muted-foreground">{doc.content_preview}</p>
                          {doc.download_url && (
                            <a
                              href={doc.download_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="mt-2 inline-flex items-center gap-1 text-primary hover:underline"
                            >
                              <ExternalLink className="h-3.5 w-3.5" />
                              Abrir arquivo
                            </a>
                          )}
                        </>
                      ) : (
                        'Documento indisponível.'
                      )}
                    </div>
                  )}
                  {a.resposta_equipe && (
                    <p className="text-xs text-muted-foreground">Resposta: {a.resposta_equipe}</p>
                  )}
                  {a.status !== 'regra_geral' && a.status !== 'recusada' && (
                    <div className="flex flex-wrap justify-end gap-2 pt-1">
                      {a.status !== 'em_analise' && (
                        <Button size="sm" variant="outline" onClick={() => void executar(a, 'em-analise')}>
                          Em análise
                        </Button>
                      )}
                      <Button size="sm" variant="outline" onClick={() => { setRecusando(a); setResposta(''); }}>
                        Recusar
                      </Button>
                      <Button size="sm" onClick={() => setConfirmarGeral(a)}>
                        Virar regra geral
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      <Dialog
        open={!!confirmarGeral}
        onClose={() => setConfirmarGeral(null)}
        title="Virar regra geral?"
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setConfirmarGeral(null)}>Cancelar</Button>
            <Button
              loading={acao.isPending}
              onClick={() => confirmarGeral && void executar(confirmarGeral, 'regra-geral')}
            >
              Confirmar
            </Button>
          </div>
        }
      >
        {confirmarGeral && (
          <p className="text-sm text-muted-foreground">
            {detalheRegra(confirmarGeral)} passa a valer para todos os escritórios com clientes em{' '}
            <strong>{regiaoLabel(confirmarGeral)}</strong>. Escritórios que atendem outras regiões não são afetados.
          </p>
        )}
      </Dialog>

      <Dialog
        open={!!recusando}
        onClose={() => setRecusando(null)}
        title="Recusar solicitação"
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setRecusando(null)}>Cancelar</Button>
            <Button
              variant="destructive"
              loading={acao.isPending}
              disabled={resposta.trim().length < 5}
              onClick={() => recusando && void executar(recusando, 'recusar', resposta.trim())}
            >
              Recusar
            </Button>
          </div>
        }
      >
        <FormField
          label="Resposta para o escritório"
          htmlFor="eq-resposta"
          hint="Explique o motivo. O escritório vê esta resposta na tela dele."
          required
        >
          <textarea
            id="eq-resposta"
            className={textareaClasses}
            value={resposta}
            onChange={(e) => setResposta(e.target.value)}
          />
        </FormField>
      </Dialog>
    </div>
  );
}

export default EquipeAjustesPage;
