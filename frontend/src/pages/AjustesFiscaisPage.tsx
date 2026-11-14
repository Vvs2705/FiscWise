import { useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { CalendarClock, FileUp, MapPin, Paperclip, Scale, Undo2 } from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { FormField } from '@/components/ui/FormField';
import { Badge } from '@/components/ui/Badge';
import { Dialog } from '@/components/ui/Dialog';
import { EmptyState } from '@/components/ui/EmptyState';
import { getApiErrorMessage } from '@/lib/api';
import {
  ARQUIVO_ACEITO,
  STATUS_TONE,
  TIPO_LABEL,
  UFS,
  ajusteEstruturado,
  regiaoLabel,
  statusLabel,
  tipoLabel,
  validarAjuste,
  validarArquivo,
  type AjusteAtivo,
  type AjusteFiscal,
  type ErrosAjuste,
  type TipoAjuste,
} from '@/lib/ajustesFiscais';
import {
  useAjustesAtivos,
  useAjustesFiscais,
  useCriarAjusteFiscal,
  useDesfazerAjusteFiscal,
  useObrigacoesAjustaveis,
} from '@/lib/hooks/useAjustesFiscais';
import { useRagDocuments, useUploadRagDocument } from '@/lib/hooks/useRagFiscal';

const textareaClasses =
  'flex min-h-[96px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2';

function formatarData(iso: string | null | undefined): string {
  if (!iso) return '';
  const [y, m, d] = iso.slice(0, 10).split('-');
  return d && m && y ? `${d}/${m}/${y}` : iso;
}

function resumoAjuste(a: Pick<AjusteFiscal, 'tipo' | 'data' | 'recorrente_anual' | 'obrigacao_code' | 'due_day'>): string {
  if (a.tipo === 'feriado' && a.data) {
    return `Feriado em ${formatarData(a.data)}${a.recorrente_anual ? ' (todo ano)' : ''}`;
  }
  if (a.tipo === 'prazo' && a.obrigacao_code) {
    return `${a.obrigacao_code} vence no dia ${a.due_day ?? '?'}`;
  }
  return tipoLabel(a.tipo);
}

export function AjustesFiscaisPage() {
  const { data: ajustes, isLoading } = useAjustesFiscais();
  const { data: ativos } = useAjustesAtivos();
  const { data: obrigacoes } = useObrigacoesAjustaveis();
  const { data: documentos } = useRagDocuments();
  const criar = useCriarAjusteFiscal();
  const desfazer = useDesfazerAjusteFiscal();
  const upload = useUploadRagDocument();

  const [tipo, setTipo] = useState<TipoAjuste>('feriado');
  const [uf, setUf] = useState('');
  const [municipioNome, setMunicipioNome] = useState('');
  const [municipioIbge, setMunicipioIbge] = useState('');
  const [data, setData] = useState('');
  const [recorrente, setRecorrente] = useState(true);
  const [obrigacao, setObrigacao] = useState('');
  const [diaVencimento, setDiaVencimento] = useState('');
  const [descricao, setDescricao] = useState('');
  const [fonte, setFonte] = useState('');
  const [docId, setDocId] = useState('');
  const [erros, setErros] = useState<ErrosAjuste>({});
  const [paraDesfazer, setParaDesfazer] = useState<AjusteFiscal | null>(null);
  const arquivoRef = useRef<HTMLInputElement>(null);

  const limpar = () => {
    setMunicipioNome('');
    setMunicipioIbge('');
    setData('');
    setRecorrente(true);
    setObrigacao('');
    setDiaVencimento('');
    setDescricao('');
    setFonte('');
    setDocId('');
    setErros({});
  };

  const enviar = async (e: React.FormEvent) => {
    e.preventDefault();
    const input = {
      tipo,
      uf,
      municipio_ibge: municipioIbge,
      municipio_nome: municipioNome,
      data,
      recorrente_anual: recorrente,
      obrigacao_code: obrigacao,
      due_day: diaVencimento ? Number(diaVencimento) : undefined,
      descricao,
      fonte,
      knowledge_doc_id: docId || undefined,
    };
    const encontrados = validarAjuste(input);
    setErros(encontrados);
    if (Object.keys(encontrados).length > 0) return;
    try {
      const criado = await criar.mutateAsync(input);
      if (ajusteEstruturado(tipo)) {
        const n = criado.recalculadas;
        toast.success(
          typeof n === 'number'
            ? `Aplicado no seu escritório: ${n} ${n === 1 ? 'obrigação recalculada' : 'obrigações recalculadas'}.`
            : 'Aplicado no seu escritório. Nossa equipe vai analisar.',
        );
      } else {
        toast.success('Solicitação enviada. Nossa equipe vai analisar.');
      }
      limpar();
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Não foi possível enviar a solicitação.'));
    }
  };

  const enviarArquivo = async (file: File | undefined) => {
    if (!file) return;
    const problema = validarArquivo(file);
    if (problema) {
      toast.error(problema);
      return;
    }
    try {
      const titulo = file.name.replace(/\.[^.]+$/, '');
      const doc = await upload.mutateAsync({ file, title: titulo, category: 'regulamento' });
      setDocId(doc.id);
      toast.success('Arquivo enviado para a base de conhecimento e anexado.');
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Não foi possível enviar o arquivo.'));
    } finally {
      if (arquivoRef.current) arquivoRef.current.value = '';
    }
  };

  const confirmarDesfazer = async () => {
    if (!paraDesfazer) return;
    try {
      await desfazer.mutateAsync(paraDesfazer.id);
      toast.success('Ajuste desfeito no seu escritório.');
      setParaDesfazer(null);
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Não foi possível desfazer.'));
    }
  };

  const ordenados = useMemo(
    () => [...(ajustes ?? [])].sort((a, b) => b.created_at.localeCompare(a.created_at)),
    [ajustes],
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Ajustes fiscais"
        subtitle="Feriados e prazos do seu estado e município"
        icon={<Scale className="h-5 w-5" />}
      />

      <Card>
        <CardContent className="pt-6 text-sm text-muted-foreground">
          Falta um feriado do seu município ou um prazo do seu estado está diferente? Peça o ajuste: ele
          vale na hora para o seu escritório e nossa equipe analisa para incluir para todos que atendem a
          mesma região. Quem atende outros estados não é afetado.
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Nova solicitação</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={enviar} className="space-y-4" noValidate>
            <div className="grid gap-4 sm:grid-cols-3">
              <FormField label="Tipo" htmlFor="ajuste-tipo" required>
                <Select id="ajuste-tipo" value={tipo} onChange={(e) => setTipo(e.target.value as TipoAjuste)}>
                  {(Object.keys(TIPO_LABEL) as TipoAjuste[]).map((t) => (
                    <option key={t} value={t}>{TIPO_LABEL[t]}</option>
                  ))}
                </Select>
              </FormField>
              <FormField label="Estado (UF)" htmlFor="ajuste-uf" error={erros.uf} required>
                <Select id="ajuste-uf" value={uf} onChange={(e) => setUf(e.target.value)} invalid={!!erros.uf}>
                  <option value="">Escolha</option>
                  {UFS.map((u) => (
                    <option key={u} value={u}>{u}</option>
                  ))}
                </Select>
              </FormField>
              <FormField label="Município" htmlFor="ajuste-municipio">
                <Input
                  id="ajuste-municipio"
                  placeholder="Ex.: Campinas"
                  value={municipioNome}
                  onChange={(e) => setMunicipioNome(e.target.value)}
                />
              </FormField>
            </div>

            <FormField
              label="Código IBGE do município"
              htmlFor="ajuste-ibge"
              error={erros.municipio_ibge}
              hint="Código IBGE de 7 dígitos, opcional. Sem ele, o ajuste vale para o estado todo."
            >
              <Input
                id="ajuste-ibge"
                inputMode="numeric"
                maxLength={7}
                placeholder="Ex.: 3509502"
                value={municipioIbge}
                onChange={(e) => setMunicipioIbge(e.target.value.replace(/\D/g, ''))}
              />
            </FormField>

            {tipo === 'feriado' && (
              <div className="grid gap-4 sm:grid-cols-2">
                <FormField label="Data do feriado" htmlFor="ajuste-data" error={erros.data} required>
                  <Input id="ajuste-data" type="date" value={data} onChange={(e) => setData(e.target.value)} />
                </FormField>
                <label className="flex items-center gap-2 self-end pb-2 text-sm">
                  <input
                    type="checkbox"
                    checked={recorrente}
                    onChange={(e) => setRecorrente(e.target.checked)}
                    className="h-4 w-4 rounded border-input"
                  />
                  Repete todo ano
                </label>
              </div>
            )}

            {tipo === 'prazo' && (
              <div className="grid gap-4 sm:grid-cols-2">
                <FormField label="Obrigação" htmlFor="ajuste-obrigacao" error={erros.obrigacao_code} required>
                  <Select
                    id="ajuste-obrigacao"
                    value={obrigacao}
                    onChange={(e) => setObrigacao(e.target.value)}
                    invalid={!!erros.obrigacao_code}
                  >
                    <option value="">Escolha</option>
                    {(obrigacoes ?? []).map((o) => (
                      <option key={o.code} value={o.code}>{o.code} — {o.name}</option>
                    ))}
                  </Select>
                </FormField>
                <FormField label="Dia do vencimento" htmlFor="ajuste-dia" error={erros.due_day} required>
                  <Input
                    id="ajuste-dia"
                    type="number"
                    min={1}
                    max={31}
                    value={diaVencimento}
                    onChange={(e) => setDiaVencimento(e.target.value)}
                  />
                </FormField>
              </div>
            )}

            <FormField label="Descrição" htmlFor="ajuste-descricao" error={erros.descricao} required>
              <textarea
                id="ajuste-descricao"
                className={textareaClasses}
                placeholder={
                  tipo === 'feriado'
                    ? 'Ex.: Aniversário da cidade, feriado municipal pela Lei 1.234/1990.'
                    : tipo === 'prazo'
                      ? 'Ex.: Em SP a GIA vence no dia 20 para o meu caso, conforme portaria.'
                      : 'Explique o ajuste que você precisa.'
                }
                value={descricao}
                onChange={(e) => setDescricao(e.target.value)}
              />
            </FormField>

            <FormField label="Fonte (lei, decreto ou link)" htmlFor="ajuste-fonte" error={erros.fonte}>
              <Input
                id="ajuste-fonte"
                placeholder="Ex.: Decreto 12.345/2026 ou https://..."
                value={fonte}
                onChange={(e) => setFonte(e.target.value)}
              />
            </FormField>

            <FormField
              label="Anexar documento da base de conhecimento"
              htmlFor="ajuste-doc"
              hint="O arquivo continua só do seu escritório; nossa equipe consegue ler para analisar este pedido."
            >
              <div className="flex flex-col gap-2 sm:flex-row">
                <Select id="ajuste-doc" value={docId} onChange={(e) => setDocId(e.target.value)} className="flex-1">
                  <option value="">Nenhum</option>
                  {(documentos ?? []).map((d) => (
                    <option key={d.id} value={d.id}>{d.title}</option>
                  ))}
                </Select>
                <input
                  ref={arquivoRef}
                  type="file"
                  accept={ARQUIVO_ACEITO}
                  className="hidden"
                  onChange={(e) => void enviarArquivo(e.target.files?.[0])}
                />
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => arquivoRef.current?.click()}
                  loading={upload.isPending}
                  className="gap-2"
                >
                  <FileUp className="h-4 w-4" />
                  Enviar arquivo
                </Button>
              </div>
            </FormField>

            <div className="flex flex-col gap-3 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-xs text-muted-foreground">
                {ajusteEstruturado(tipo)
                  ? 'Vale na hora para os clientes do seu escritório nessa região.'
                  : 'Vai para a análise da nossa equipe; não muda prazos sozinho.'}
              </p>
              <Button type="submit" loading={criar.isPending}>
                Enviar solicitação
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <section className="space-y-3">
        <h2 className="text-base font-semibold">Suas solicitações</h2>
        {isLoading ? (
          <div className="h-20 animate-pulse rounded-lg bg-muted" />
        ) : ordenados.length === 0 ? (
          <EmptyState
            title="Nenhuma solicitação ainda"
            description="Quando você pedir um ajuste, ele aparece aqui com o andamento da análise."
            icon={CalendarClock}
          />
        ) : (
          <div className="space-y-3">
            {ordenados.map((a) => (
              <Card key={a.id}>
                <CardContent className="space-y-2 pt-5">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={STATUS_TONE[a.status] ?? 'neutral'}>{statusLabel(a.status)}</Badge>
                    <span className="text-sm font-medium">{resumoAjuste(a)}</span>
                    <span className="flex items-center gap-1 text-xs text-muted-foreground">
                      <MapPin className="h-3.5 w-3.5" />
                      {regiaoLabel(a)}
                    </span>
                  </div>
                  <p className="whitespace-pre-line text-sm text-muted-foreground">{a.descricao}</p>
                  {(a.fonte || a.knowledge_doc_title) && (
                    <p className="flex flex-wrap gap-3 text-xs text-muted-foreground">
                      {a.fonte && <span>Fonte: {a.fonte}</span>}
                      {a.knowledge_doc_title && (
                        <span className="flex items-center gap-1">
                          <Paperclip className="h-3.5 w-3.5" />
                          {a.knowledge_doc_title}
                        </span>
                      )}
                    </p>
                  )}
                  {a.resposta_equipe && (
                    <div className="rounded-md border bg-muted/40 p-3 text-xs">
                      <strong>Resposta da equipe FiscWise:</strong> {a.resposta_equipe}
                    </div>
                  )}
                  <div className="flex items-center justify-between pt-1 text-xs text-muted-foreground">
                    <span>Enviada em {formatarData(a.created_at)}</span>
                    {a.status !== 'regra_geral' && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="gap-1"
                        onClick={() => setParaDesfazer(a)}
                      >
                        <Undo2 className="h-3.5 w-3.5" />
                        Desfazer
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold">Ajustes que valem para você</h2>
        <div className="grid gap-4 md:grid-cols-2">
          <ListaAtivos
            titulo="Do seu escritório"
            vazio="Nenhum ajuste próprio ativo."
            itens={ativos?.escritorio ?? []}
          />
          <ListaAtivos
            titulo="Gerais (regras da região)"
            vazio="Nenhuma regra geral extra para as regiões que você atende."
            itens={ativos?.gerais ?? []}
          />
        </div>
        <p className="text-xs text-muted-foreground">
          Precisa de uma lei ou norma por perto? Guarde na{' '}
          <Link to="/configuracoes?aba=base_conhecimento" className="text-primary hover:underline">
            base de conhecimento
          </Link>
          .
        </p>
      </section>

      <Dialog
        open={!!paraDesfazer}
        onClose={() => setParaDesfazer(null)}
        title="Desfazer ajuste?"
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setParaDesfazer(null)}>Cancelar</Button>
            <Button variant="destructive" loading={desfazer.isPending} onClick={() => void confirmarDesfazer()}>
              Desfazer
            </Button>
          </div>
        }
      >
        <p className="text-sm text-muted-foreground">
          O ajuste deixa de valer para o seu escritório e os prazos voltam à regra padrão. A solicitação sai da
          fila de análise.
        </p>
      </Dialog>
    </div>
  );
}

function ListaAtivos({ titulo, vazio, itens }: { titulo: string; vazio: string; itens: AjusteAtivo[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">{titulo}</CardTitle>
      </CardHeader>
      <CardContent>
        {itens.length === 0 ? (
          <p className="text-xs text-muted-foreground">{vazio}</p>
        ) : (
          <ul className="space-y-2 text-sm">
            {itens.map((i) => (
              <li key={i.id} className="flex flex-col">
                <span className="font-medium">{resumoAjuste(i)}</span>
                <span className="text-xs text-muted-foreground">{regiaoLabel(i)} · {i.descricao}</span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

export default AjustesFiscaisPage;
