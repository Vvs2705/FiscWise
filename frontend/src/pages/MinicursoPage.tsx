import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowRight, CheckCircle2, Circle, Clock, GraduationCap, PlayCircle } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';
import { LESSONS, formatDuration, type Lesson } from '@/lib/minicurso';

const WATCHED_KEY = 'fiscwise:minicurso:assistidas';

function readWatched(): string[] {
  try {
    const raw = localStorage.getItem(WATCHED_KEY);
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((v): v is string => typeof v === 'string') : [];
  } catch {
    return [];
  }
}

function saveWatched(ids: string[]) {
  try {
    localStorage.setItem(WATCHED_KEY, JSON.stringify(ids));
  } catch {
    /* sem storage: o progresso vale só nesta visita */
  }
}

export function MinicursoPage() {
  const [params, setParams] = useSearchParams();
  const current: Lesson = LESSONS.find((l) => l.id === params.get('aula')) ?? LESSONS[0];
  const index = LESSONS.indexOf(current);
  const next = LESSONS[index + 1];
  const videoRef = useRef<HTMLVideoElement>(null);
  const [watched, setWatched] = useState<string[]>(readWatched);
  const [time, setTime] = useState(0);
  const [ended, setEnded] = useState(false);

  useEffect(() => {
    setTime(0);
    setEnded(false);
  }, [current.id]);

  const markWatched = useCallback((id: string) => {
    setWatched((prev) => {
      if (prev.includes(id)) return prev;
      const updated = [...prev, id];
      saveWatched(updated);
      return updated;
    });
  }, []);

  const selectLesson = (id: string) => {
    setParams({ aula: id }, { replace: false });
    document.getElementById('minicurso-player')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const seek = (t: number) => {
    const v = videoRef.current;
    if (!v) return;
    v.currentTime = t;
    void v.play().catch(() => undefined);
  };

  const activeChapter = useMemo(() => {
    let active = -1;
    current.chapters.forEach((c, i) => {
      if (time >= c.t) active = i;
    });
    return active;
  }, [current.chapters, time]);

  const totalMinutes = Math.max(1, Math.round(LESSONS.reduce((s, l) => s + l.duration, 0) / 60));
  const doneCount = LESSONS.filter((l) => watched.includes(l.id)).length;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="space-y-2">
          <p className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
            <GraduationCap className="h-4 w-4" aria-hidden="true" />
            {LESSONS.length} aulas · cerca de {totalMinutes} min
          </p>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground md:text-3xl">Minicurso FiscWise</h1>
          <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground">
            Aulas curtas em vídeo mostrando cada tarefa sendo feita na tela: onde clicar, o que preencher e o que
            acontece quando você salva. Os dados dos vídeos são de demonstração.
          </p>
        </div>
        <div className="w-full max-w-xs space-y-1.5 md:w-64" aria-label="Seu progresso no minicurso">
          <p className="text-sm font-medium text-foreground">
            {doneCount} de {LESSONS.length} aulas assistidas
          </p>
          <div className="h-2 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary transition-[width] duration-200"
              style={{ width: `${(doneCount / LESSONS.length) * 100}%` }}
            />
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        {/* Player */}
        <section id="minicurso-player" aria-label="Aula atual" className="min-w-0 space-y-4 scroll-mt-4">
          <div className="overflow-hidden rounded-lg border border-border bg-foreground/5 shadow-token-sm">
            <video
              key={current.id}
              ref={videoRef}
              data-testid="minicurso-video"
              className="aspect-video w-full bg-black"
              controls
              playsInline
              preload="metadata"
              poster={current.poster}
              onTimeUpdate={(e) => {
                const v = e.currentTarget;
                setTime(v.currentTime);
                if (v.duration && v.currentTime / v.duration > 0.9) markWatched(current.id);
              }}
              onEnded={() => {
                setEnded(true);
                markWatched(current.id);
              }}
              onPlay={() => setEnded(false)}
            >
              <source src={current.video} type="video/mp4" />
              Seu navegador não reproduz vídeos. Use a versão mais recente do Chrome, Edge, Firefox ou Safari.
            </video>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0 space-y-1">
              <p className="text-xs font-medium text-muted-foreground">
                Aula {index + 1} de {LESSONS.length}
                {current.duration > 0 && ` · ${formatDuration(current.duration)}`}
              </p>
              <h2 className="text-xl font-semibold text-foreground">{current.title}</h2>
              <p className="text-sm text-muted-foreground">{current.description}</p>
            </div>
            <div className="flex shrink-0 gap-2">
              <Link
                to={current.path}
                className="inline-flex h-8 items-center gap-1.5 rounded-md border border-input bg-card px-3 text-sm font-medium text-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                Fazer agora
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
              {next && (
                <Button size="sm" variant={ended ? 'default' : 'outline'} onClick={() => selectLesson(next.id)}>
                  Próxima aula
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </Button>
              )}
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <Card className="p-4">
              <h3 className="mb-3 text-sm font-semibold text-foreground">Passo a passo da aula</h3>
              {current.chapters.length > 0 ? (
                <ol className="space-y-1">
                  {current.chapters.map((c, i) => (
                    <li key={`${c.t}-${c.label}`}>
                      <button
                        type="button"
                        onClick={() => seek(c.t)}
                        aria-current={i === activeChapter ? 'step' : undefined}
                        className={cn(
                          'flex w-full items-start gap-3 rounded-md px-2 py-1.5 text-left text-sm transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                          i === activeChapter ? 'bg-primary/10 text-foreground' : 'text-muted-foreground',
                        )}
                      >
                        <span className="w-10 shrink-0 font-mono text-xs leading-5 text-primary">{formatDuration(c.t)}</span>
                        <span className="leading-5">{c.label}</span>
                      </button>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="text-sm text-muted-foreground">Os capítulos aparecem depois da gravação da aula.</p>
              )}
            </Card>
            <Card className="p-4">
              <h3 className="mb-3 text-sm font-semibold text-foreground">Ao final você sabe</h3>
              <ul className="space-y-2">
                {current.outcomes.map((o) => (
                  <li key={o} className="flex gap-2 text-sm text-muted-foreground">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-success" aria-hidden="true" />
                    <span>{o}</span>
                  </li>
                ))}
              </ul>
            </Card>
          </div>
        </section>

        {/* Lista de aulas */}
        <nav aria-label="Aulas do minicurso" className="space-y-2">
          {LESSONS.map((lesson, i) => {
            const isCurrent = lesson.id === current.id;
            const isWatched = watched.includes(lesson.id);
            return (
              <button
                key={lesson.id}
                type="button"
                onClick={() => selectLesson(lesson.id)}
                aria-current={isCurrent ? 'true' : undefined}
                className={cn(
                  'flex w-full gap-3 rounded-lg border p-2 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  isCurrent ? 'border-primary/40 bg-primary/5' : 'border-border bg-card hover:bg-muted',
                )}
              >
                <span className="relative aspect-video w-28 shrink-0 overflow-hidden rounded-md bg-muted">
                  <img src={lesson.poster} alt="" loading="lazy" className="h-full w-full object-cover" />
                  <span className="absolute inset-0 flex items-center justify-center bg-foreground/20">
                    <PlayCircle className="h-6 w-6 text-white" aria-hidden="true" />
                  </span>
                </span>
                <span className="min-w-0 flex-1 py-0.5">
                  <span className="flex items-center gap-1.5 text-[11px] font-medium text-muted-foreground">
                    {isWatched ? (
                      <CheckCircle2 className="h-3.5 w-3.5 text-success" aria-label="Assistida" />
                    ) : (
                      <Circle className="h-3.5 w-3.5" aria-hidden="true" />
                    )}
                    Aula {i + 1}
                    {lesson.duration > 0 && (
                      <>
                        <Clock className="ml-1 h-3 w-3" aria-hidden="true" />
                        {formatDuration(lesson.duration)}
                      </>
                    )}
                  </span>
                  <span className="mt-0.5 block text-sm font-medium leading-snug text-foreground">{lesson.title}</span>
                </span>
              </button>
            );
          })}
        </nav>
      </div>
    </div>
  );
}
