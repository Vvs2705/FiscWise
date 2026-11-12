import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Drawer as VaulDrawer } from 'vaul';
import { CircleHelp, GraduationCap, Lightbulb, Map, PlayCircle, X } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { getPageGuide } from '@/lib/pageGuides';
import { getLesson } from '@/lib/minicurso';
import { startTour } from '@/lib/tours';
import { startWelcomeTour } from '@/lib/welcomeTour';

/**
 * Botão "Ajuda" do topo: abre, à direita, o guia da página atual
 * (para que serve, passo a passo das tarefas, dicas), com atalhos para a aula
 * do Minicurso, o tour da página e o tour de boas-vindas.
 */
export function PageHelp() {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const guide = getPageGuide(location.pathname);
  const lesson = guide?.lessonId ? getLesson(guide.lessonId) : undefined;

  const runPageTour = () => {
    if (!guide?.tour) return;
    setOpen(false);
    // Espera o painel fechar para o tour medir os elementos certos.
    window.setTimeout(() => startTour(guide.tour!, navigate, location.pathname), 250);
  };

  const runWelcome = () => {
    setOpen(false);
    window.setTimeout(() => void startWelcomeTour(), 250);
  };

  return (
    <VaulDrawer.Root open={open} onOpenChange={setOpen} direction="right" shouldScaleBackground={false}>
      <VaulDrawer.Trigger asChild>
        <Button
          variant="ghost"
          size="sm"
          data-tour="ajuda"
          aria-label="Ajuda desta página"
          className="text-muted-foreground hover:text-foreground"
        >
          <CircleHelp className="h-4 w-4" aria-hidden="true" />
          <span className="hidden sm:inline">Ajuda</span>
        </Button>
      </VaulDrawer.Trigger>
      <VaulDrawer.Portal>
        <VaulDrawer.Overlay className="fixed inset-0 z-50 bg-foreground/40" />
        <VaulDrawer.Content
          className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l border-border bg-card text-card-foreground shadow-lg outline-none"
          aria-describedby={undefined}
        >
          <div className="flex items-start justify-between gap-3 border-b border-border px-5 py-4">
            <div className="min-w-0">
              <p className="text-xs font-medium text-muted-foreground">Guia da página</p>
              <VaulDrawer.Title className="truncate text-lg font-semibold text-foreground">
                {guide?.title ?? 'Ajuda'}
              </VaulDrawer.Title>
            </div>
            <VaulDrawer.Close asChild>
              <Button variant="ghost" size="sm" aria-label="Fechar ajuda" className="-mr-2">
                <X className="h-4 w-4" aria-hidden="true" />
              </Button>
            </VaulDrawer.Close>
          </div>

          <div className="flex-1 space-y-6 overflow-y-auto px-5 py-5">
            {guide ? (
              <>
                <p className="text-sm leading-relaxed text-muted-foreground">{guide.summary}</p>

                {(lesson || guide.tour) && (
                  <div className="grid gap-2">
                    {lesson && (
                      <Link
                        to={`/minicurso?aula=${lesson.id}`}
                        onClick={() => setOpen(false)}
                        className="flex items-center gap-3 rounded-lg border border-primary/25 bg-primary/5 p-3 text-sm transition-colors hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      >
                        <PlayCircle className="h-5 w-5 shrink-0 text-primary" aria-hidden="true" />
                        <span className="min-w-0">
                          <span className="block font-medium text-foreground">Assistir à aula em vídeo</span>
                          <span className="block truncate text-xs text-muted-foreground">{lesson.title}</span>
                        </span>
                      </Link>
                    )}
                    {guide.tour && (
                      <button
                        type="button"
                        onClick={runPageTour}
                        className="flex items-center gap-3 rounded-lg border border-border p-3 text-left text-sm transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      >
                        <Map className="h-5 w-5 shrink-0 text-primary" aria-hidden="true" />
                        <span>
                          <span className="block font-medium text-foreground">Fazer o tour desta página</span>
                          <span className="block text-xs text-muted-foreground">Mostra cada parte da tela, passo a passo.</span>
                        </span>
                      </button>
                    )}
                  </div>
                )}

                {guide.tasks.map((task) => (
                  <section key={task.title} aria-label={task.title}>
                    <h3 className="mb-2 text-sm font-semibold text-foreground">{task.title}</h3>
                    <ol className="space-y-2">
                      {task.steps.map((step, i) => (
                        <li key={step} className="flex gap-3 text-sm leading-relaxed text-muted-foreground">
                          <span
                            className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[11px] font-semibold text-primary"
                            aria-hidden="true"
                          >
                            {i + 1}
                          </span>
                          <span>{step}</span>
                        </li>
                      ))}
                    </ol>
                  </section>
                ))}

                {guide.tips && guide.tips.length > 0 && (
                  <div className="rounded-lg bg-muted p-3">
                    {guide.tips.map((tip) => (
                      <p key={tip} className="flex gap-2 text-sm leading-relaxed text-muted-foreground">
                        <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-warning" aria-hidden="true" />
                        <span>{tip}</span>
                      </p>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <p className="text-sm text-muted-foreground">
                Esta tela ainda não tem um guia próprio. Veja as aulas do Minicurso ou refaça o tour de boas-vindas.
              </p>
            )}
          </div>

          <div className="grid gap-2 border-t border-border px-5 py-4 sm:grid-cols-2">
            <Button variant="outline" size="sm" onClick={runWelcome}>
              <Map className="h-4 w-4" aria-hidden="true" />
              Tour de boas-vindas
            </Button>
            <Button variant="outline" size="sm" onClick={() => { setOpen(false); navigate('/minicurso'); }}>
              <GraduationCap className="h-4 w-4" aria-hidden="true" />
              Minicurso FiscWise
            </Button>
          </div>
        </VaulDrawer.Content>
      </VaulDrawer.Portal>
    </VaulDrawer.Root>
  );
}
