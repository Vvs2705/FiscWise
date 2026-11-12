import gravacoes from './minicursoGravacoes.json';

/**
 * Aulas do Minicurso FiscWise.
 *
 * Os vídeos ficam em public/minicurso/<id>.mp4 (capa em <id>.jpg) e são
 * gravados com Playwright sobre dados de demonstração:
 *   npm run minicurso:gravar
 * A gravação também escreve minicursoGravacoes.json com a duração, o
 * instante de cada capítulo e as legendas da narração, então capítulos e
 * legendas sempre batem com o vídeo.
 */

export interface LessonChapter {
  /** segundo do vídeo em que o passo começa */
  t: number;
  label: string;
}

/** Trecho da narração, mostrado como legenda por cima do vídeo. */
export interface LessonCue {
  start: number;
  end: number;
  text: string;
}

export interface Lesson {
  id: string;
  title: string;
  description: string;
  /** o que a pessoa sabe fazer ao final da aula */
  outcomes: string[];
  /** página do app onde a tarefa é feita */
  path: string;
  video: string;
  poster: string;
  /** duração em segundos (vem da gravação) */
  duration: number;
  chapters: LessonChapter[];
  cues: LessonCue[];
}

type Gravacoes = Record<string, { duration: number; chapters: LessonChapter[]; cues?: LessonCue[] }>;
const recorded = gravacoes as Gravacoes;

const BASE: Array<Omit<Lesson, 'video' | 'poster' | 'duration' | 'chapters' | 'cues'>> = [
  {
    id: 'primeiros-passos',
    title: 'Primeiros passos no FiscWise',
    description: 'O tour de boas-vindas, o painel do dia e onde fica cada coisa no menu.',
    outcomes: ['Entender o painel e o Foco de hoje', 'Achar cada área no menu', 'Abrir a ajuda de qualquer página'],
    path: '/painel',
  },
  {
    id: 'cadastrar-cliente',
    title: 'Cadastrar clientes',
    description: 'Pelo CNPJ, com os dados da Receita, ou vários de uma vez com planilha Excel ou CSV.',
    outcomes: [
      'Preencher o cadastro só com o CNPJ',
      'Escolher o regime tributário',
      'Importar vários clientes de uma planilha Excel ou CSV',
    ],
    path: '/clientes',
  },
  {
    id: 'obrigacoes',
    title: 'Acompanhar as obrigações do mês',
    description: 'Filtrar por cliente e prioridade, iniciar e dar baixa em uma obrigação entregue.',
    outcomes: ['Ver o que vence na competência', 'Filtrar por cliente e status', 'Marcar uma obrigação como entregue'],
    path: '/obrigacoes',
  },
  {
    id: 'fechamento-mensal',
    title: 'Fazer o fechamento mensal',
    description: 'Abrir o fechamento de um cliente, concluir o checklist e gerar o dossiê em PDF.',
    outcomes: ['Ler o score do fechamento', 'Concluir etapas do checklist', 'Gerar o dossiê do mês'],
    path: '/fechamento',
  },
  {
    id: 'certificados',
    title: 'Cadastrar um certificado digital',
    description: 'Registrar o certificado A1 de um cliente e acompanhar o alerta de vencimento.',
    outcomes: ['Cadastrar certificado com validade', 'Ver quais estão vencendo', 'Avisar o cliente da renovação'],
    path: '/certificados',
  },
  {
    id: 'portal-cliente',
    title: 'Dar acesso ao portal do cliente',
    description: 'Ver o portal como o cliente vê e enviar o link de acesso por e-mail.',
    outcomes: ['Escolher o cliente e ver o portal', 'Conferir guias e pendências', 'Enviar o link de acesso'],
    path: '/portal',
  },
];

export const LESSONS: Lesson[] = BASE.map((lesson) => ({
  ...lesson,
  video: `/minicurso/${lesson.id}.mp4`,
  poster: `/minicurso/${lesson.id}.jpg`,
  duration: recorded[lesson.id]?.duration ?? 0,
  chapters: recorded[lesson.id]?.chapters ?? [],
  cues: recorded[lesson.id]?.cues ?? [],
}));

/** Legenda ativa no instante `t` (a mais recente que já começou e não terminou). */
export function cueAt(cues: LessonCue[], t: number): LessonCue | undefined {
  let found: LessonCue | undefined;
  for (const c of cues) {
    if (c.start > t) break;
    if (t < c.end) found = c;
  }
  return found;
}

export function getLesson(id: string): Lesson | undefined {
  return LESSONS.find((l) => l.id === id);
}

export function formatDuration(seconds: number): string {
  const s = Math.max(0, Math.round(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}
