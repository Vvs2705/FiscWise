/**
 * Solicitações de ajuste fiscal: tipos, rótulos e validação (sem React).
 *
 * Um ajuste estruturado (feriado ou prazo) vale na hora só para o escritório
 * que pediu, no estado/município informado, e vai para a análise da equipe
 * FiscWise, que pode transformá-lo em regra geral daquela região.
 */

export type TipoAjuste = 'feriado' | 'prazo' | 'nova_obrigacao' | 'outro';

export type StatusAjuste = 'aplicada_no_escritorio' | 'em_analise' | 'regra_geral' | 'recusada';

export interface AjusteFiscal {
  id: string;
  tipo: TipoAjuste;
  uf: string;
  municipio_ibge: string | null;
  municipio_nome: string | null;
  data: string | null;
  recorrente_anual: boolean | null;
  obrigacao_code: string | null;
  due_day: number | null;
  descricao: string;
  fonte: string | null;
  knowledge_doc_id: string | null;
  knowledge_doc_title: string | null;
  status: StatusAjuste;
  resposta_equipe: string | null;
  created_at: string;
  reviewed_at: string | null;
  /** Só na resposta da criação: obrigações recalculadas no escritório. */
  recalculadas?: number;
}

export interface AjusteFiscalInput {
  tipo: TipoAjuste;
  uf: string;
  municipio_ibge?: string;
  municipio_nome?: string;
  data?: string;
  recorrente_anual?: boolean;
  obrigacao_code?: string;
  due_day?: number;
  descricao: string;
  fonte?: string;
  knowledge_doc_id?: string;
}

/** Item da fila da equipe FiscWise. */
export interface AjusteFiscalEquipe extends AjusteFiscal {
  tenant_id: string;
  tenant_name: string;
}

export interface AjusteFiscalEquipeDetalhe extends AjusteFiscalEquipe {
  knowledge_doc: { title: string; content_preview: string; download_url: string | null } | null;
}

export interface ObrigacaoOpcao {
  code: string;
  name: string;
}

/** Feriado ou prazo que vale para o escritório (do próprio escritório ou geral). */
export interface AjusteAtivo {
  id: string;
  tipo: TipoAjuste;
  uf: string;
  municipio_ibge: string | null;
  municipio_nome: string | null;
  data: string | null;
  recorrente_anual: boolean | null;
  obrigacao_code: string | null;
  due_day: number | null;
  descricao: string;
  /** 'escritorio' = só para o escritório; 'geral' = regra da região para todos. */
  escopo: 'escritorio' | 'geral';
}

export interface AjustesAtivosResposta {
  escritorio: AjusteAtivo[];
  gerais: AjusteAtivo[];
}

export const UFS = [
  'AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MG', 'MS', 'MT', 'PA',
  'PB', 'PE', 'PI', 'PR', 'RJ', 'RN', 'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO',
] as const;

export const TIPO_LABEL: Record<TipoAjuste, string> = {
  feriado: 'Feriado',
  prazo: 'Prazo de obrigação',
  nova_obrigacao: 'Nova obrigação',
  outro: 'Outro',
};

export const STATUS_LABEL: Record<StatusAjuste, string> = {
  aplicada_no_escritorio: 'Vale no seu escritório',
  em_analise: 'Em análise',
  regra_geral: 'Virou regra geral',
  recusada: 'Recusada',
};

export type StatusTone = 'success' | 'warning' | 'primary' | 'danger';

export const STATUS_TONE: Record<StatusAjuste, StatusTone> = {
  aplicada_no_escritorio: 'success',
  em_analise: 'warning',
  regra_geral: 'primary',
  recusada: 'danger',
};

/** Na tela da equipe FiscWise quem lê não é o escritório que pediu. */
export const STATUS_LABEL_EQUIPE: Record<StatusAjuste, string> = {
  ...STATUS_LABEL,
  aplicada_no_escritorio: 'Vale no escritório que pediu',
};

export function statusLabel(status: string, visao: 'escritorio' | 'equipe' = 'escritorio'): string {
  const rotulos = visao === 'equipe' ? STATUS_LABEL_EQUIPE : STATUS_LABEL;
  return rotulos[status as StatusAjuste] ?? status;
}

export function tipoLabel(tipo: string): string {
  return TIPO_LABEL[tipo as TipoAjuste] ?? tipo;
}

/** Estrutura que muda prazo na hora (o resto só vai para análise). */
export function ajusteEstruturado(tipo: TipoAjuste): boolean {
  return tipo === 'feriado' || tipo === 'prazo';
}

export function regiaoLabel(a: { uf: string; municipio_nome?: string | null; municipio_ibge?: string | null }): string {
  if (a.municipio_nome) return `${a.municipio_nome}/${a.uf}`;
  if (a.municipio_ibge) return `Município ${a.municipio_ibge}/${a.uf}`;
  return `${a.uf} (estado todo)`;
}

export type ErrosAjuste = Partial<Record<keyof AjusteFiscalInput, string>>;

/** Validação do formulário por tipo. Vazio = pode enviar. */
export function validarAjuste(input: AjusteFiscalInput): ErrosAjuste {
  const erros: ErrosAjuste = {};
  if (!UFS.includes(input.uf as (typeof UFS)[number])) {
    erros.uf = 'Escolha o estado.';
  }
  const ibge = (input.municipio_ibge ?? '').trim();
  if (ibge && !/^\d{7}$/.test(ibge)) {
    erros.municipio_ibge = 'O código IBGE tem 7 dígitos.';
  }
  const descricao = input.descricao.trim();
  if (descricao.length < 10) {
    erros.descricao = 'Descreva o ajuste com pelo menos 10 caracteres.';
  } else if (descricao.length > 2000) {
    erros.descricao = 'A descrição pode ter até 2.000 caracteres.';
  }
  if (input.tipo === 'feriado') {
    if (!input.data || !/^\d{4}-\d{2}-\d{2}$/.test(input.data)) {
      erros.data = 'Informe a data do feriado.';
    }
  }
  if (input.tipo === 'prazo') {
    if (!input.obrigacao_code) {
      erros.obrigacao_code = 'Escolha a obrigação.';
    }
    const dia = input.due_day;
    if (dia === undefined || !Number.isInteger(dia) || dia < 1 || dia > 31) {
      erros.due_day = 'O dia do vencimento vai de 1 a 31.';
    }
  }
  if ((input.fonte ?? '').length > 500) {
    erros.fonte = 'A fonte pode ter até 500 caracteres.';
  }
  return erros;
}

/** Monta o corpo do POST só com os campos que valem para o tipo. */
export function montarCorpoAjuste(input: AjusteFiscalInput): AjusteFiscalInput {
  const corpo: AjusteFiscalInput = {
    tipo: input.tipo,
    uf: input.uf,
    descricao: input.descricao.trim(),
  };
  const ibge = (input.municipio_ibge ?? '').trim();
  const nome = (input.municipio_nome ?? '').trim();
  if (ibge) corpo.municipio_ibge = ibge;
  if (nome) corpo.municipio_nome = nome;
  const fonte = (input.fonte ?? '').trim();
  if (fonte) corpo.fonte = fonte;
  if (input.knowledge_doc_id) corpo.knowledge_doc_id = input.knowledge_doc_id;
  if (input.tipo === 'feriado') {
    corpo.data = input.data;
    corpo.recorrente_anual = !!input.recorrente_anual;
  }
  if (input.tipo === 'prazo') {
    corpo.obrigacao_code = input.obrigacao_code;
    corpo.due_day = input.due_day;
  }
  return corpo;
}

/** Arquivos aceitos na base de conhecimento. */
export const ARQUIVO_ACEITO = '.pdf,.docx,.txt,.md';
export const ARQUIVO_MAX_BYTES = 20 * 1024 * 1024;

export function validarArquivo(file: { name: string; size: number }): string | null {
  const ext = file.name.toLowerCase().split('.').pop() ?? '';
  if (!['pdf', 'docx', 'txt', 'md'].includes(ext)) {
    return 'Envie um arquivo PDF, DOCX, TXT ou MD.';
  }
  if (file.size > ARQUIVO_MAX_BYTES) {
    return 'O arquivo pode ter até 20 MB.';
  }
  if (file.size === 0) {
    return 'O arquivo está vazio.';
  }
  return null;
}

export function formatarTamanho(bytes: number | null | undefined): string {
  if (!bytes && bytes !== 0) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1).replace('.', ',')} MB`;
}
