import { Clock3 } from 'lucide-react';

interface FocusItem {
  id: string;
  label: string;
  value: number;
  tone: 'danger' | 'warning' | 'info' | 'success';
}

interface DailyFocusCardProps {
  focusItems: FocusItem[];
  totalCount: number;
  isLoading?: boolean;
  onStartFocusMode: () => void;
}

function toneClasses(tone: FocusItem['tone']) {
  if (tone === 'danger') {
    return 'border-destructive/30 bg-destructive/10 text-destructive';
  }

  if (tone === 'warning') {
    return 'border-warning/30 bg-warning/10 text-warning';
  }

  if (tone === 'success') {
    return 'border-success/30 bg-success/10 text-success';
  }

  return 'border-info/30 bg-info/10 text-info';
}

export function DailyFocusCard({ focusItems, totalCount, isLoading, onStartFocusMode }: DailyFocusCardProps) {
  return (
    <div className="rounded-card border border-border bg-card/90 p-5 backdrop-blur">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-primary/80">
            Foco de hoje
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-foreground">
            {isLoading ? 'Carregando...' : `${totalCount} itens pedem ação`}
          </h2>
        </div>
        <div className="rounded-card border border-primary/20 bg-primary/10 p-3 text-primary">
          <Clock3 className="h-5 w-5" />
        </div>
      </div>

      <div className="mt-5 space-y-3">
        {focusItems.length === 0 ? (
          <div className="rounded-card border border-success/20 bg-success/10 px-4 py-4 text-sm text-success">
            Nenhuma urgência crítica agora. O painel segue limpo para acompanhar a semana.
          </div>
        ) : (
          focusItems.map((item) => (
            <div
              key={item.id}
              className={`rounded-card border px-4 py-3 ${toneClasses(item.tone)}`}
            >
              <div className="flex items-center justify-between gap-4">
                <p className="text-sm font-medium text-inherit">{item.label}</p>
                <span className="text-lg font-semibold text-foreground">{item.value}</span>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="mt-5 rounded-card border border-border bg-muted px-4 py-4">
        <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Próximo passo</p>
        <p className="mt-2 text-sm leading-6 text-foreground">
          Comece o Modo Foco para resolver as pendências críticas ordenadamente, ou acesse a agenda fiscal.
        </p>
        {totalCount > 0 && (
          <button
            type="button"
            onClick={onStartFocusMode}
            className="mt-3 w-full inline-flex items-center justify-center gap-2 rounded-md bg-primary py-2.5 text-xs font-bold text-primary-foreground transition hover:bg-primary/90 hover:-translate-y-0.5 active:translate-y-0"
          >
            Iniciar Modo Foco ({totalCount} pendências)
          </button>
        )}
      </div>
    </div>
  );
}
