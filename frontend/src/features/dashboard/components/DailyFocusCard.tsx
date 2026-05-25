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
    return 'border-red-400/30 bg-red-500/10 text-red-100';
  }

  if (tone === 'warning') {
    return 'border-amber-400/30 bg-amber-500/10 text-amber-100';
  }

  if (tone === 'success') {
    return 'border-emerald-400/30 bg-emerald-500/10 text-emerald-100';
  }

  return 'border-cyan-400/30 bg-cyan-500/10 text-cyan-100';
}

export function DailyFocusCard({ focusItems, totalCount, isLoading, onStartFocusMode }: DailyFocusCardProps) {
  return (
    <div className="rounded-[26px] border border-white/10 bg-[#0b131f]/90 p-5 backdrop-blur">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-cyan-200/80">
            Foco de hoje
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-white">
            {isLoading ? 'Carregando...' : `${totalCount} itens pedem ação`}
          </h2>
        </div>
        <div className="rounded-2xl border border-cyan-300/20 bg-cyan-300/10 p-3 text-cyan-200">
          <Clock3 className="h-5 w-5" />
        </div>
      </div>

      <div className="mt-5 space-y-3">
        {focusItems.length === 0 ? (
          <div className="rounded-2xl border border-emerald-400/20 bg-emerald-500/10 px-4 py-4 text-sm text-emerald-100">
            Nenhuma urgência crítica agora. O painel segue limpo para acompanhar a semana.
          </div>
        ) : (
          focusItems.map((item) => (
            <div
              key={item.id}
              className={`rounded-2xl border px-4 py-3 ${toneClasses(item.tone)}`}
            >
              <div className="flex items-center justify-between gap-4">
                <p className="text-sm font-medium text-inherit">{item.label}</p>
                <span className="text-lg font-semibold text-white">{item.value}</span>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="mt-5 rounded-2xl border border-white/10 bg-white/5 px-4 py-4">
        <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Próximo passo</p>
        <p className="mt-2 text-sm leading-6 text-slate-200">
          Comece o Modo Foco para resolver as pendências críticas ordenadamente, ou acesse a agenda fiscal.
        </p>
        {totalCount > 0 && (
          <button
            type="button"
            onClick={onStartFocusMode}
            className="mt-3 w-full inline-flex items-center justify-center gap-2 rounded-xl bg-cyan-300 py-2.5 text-xs font-bold text-slate-950 transition hover:bg-cyan-200 hover:-translate-y-0.5 active:translate-y-0"
          >
            Iniciar Modo Foco ({totalCount} pendências)
          </button>
        )}
      </div>
    </div>
  );
}
