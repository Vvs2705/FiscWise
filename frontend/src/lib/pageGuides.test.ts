import { describe, expect, it } from 'vitest';
import { PAGE_GUIDES, getPageGuide } from './pageGuides';
import { LESSONS, getLesson } from './minicurso';

// Rotas do menu do escritório: toda página precisa de guia no botão Ajuda.
const APP_ROUTES = [
  '/painel', '/foco', '/clientes', '/fechamento', '/obrigacoes', '/documentos', '/notas-fiscais', '/ecac',
  '/guias', '/caixa-postal-fiscal', '/procuracoes', '/certificados', '/financeiro', '/whatsapp', '/portal',
  '/relatorios', '/aprender', '/minicurso', '/configuracoes', '/sincronizacao', '/calculadora',
];

describe('guias por página', () => {
  it('cobre todas as rotas do menu, inclusive subrotas', () => {
    for (const route of APP_ROUTES) expect(getPageGuide(route)?.path, route).toBe(route);
    expect(getPageGuide('/clientes/abc')?.path).toBe('/clientes');
    expect(getPageGuide('/fechamento/123')?.path).toBe('/fechamento');
  });

  it('não confunde rotas com o mesmo começo', () => {
    expect(getPageGuide('/portal')?.path).toBe('/portal');
    expect(getPageGuide('/guiasx')).toBeUndefined();
  });

  it('cada guia tem tarefas com passos e só aponta para aulas que existem', () => {
    for (const g of PAGE_GUIDES) {
      expect(g.tasks.length, g.path).toBeGreaterThan(0);
      for (const t of g.tasks) expect(t.steps.length, `${g.path}: ${t.title}`).toBeGreaterThan(0);
      if (g.lessonId) expect(getLesson(g.lessonId), g.lessonId).toBeDefined();
    }
  });

  it('cada aula aponta para vídeo e capa em /minicurso', () => {
    for (const l of LESSONS) {
      expect(l.video).toBe(`/minicurso/${l.id}.mp4`);
      expect(l.poster).toBe(`/minicurso/${l.id}.jpg`);
    }
  });
});
