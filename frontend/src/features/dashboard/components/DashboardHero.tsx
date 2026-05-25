import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, AlertTriangle, BookOpen } from 'lucide-react';
import { startTour } from '@/lib/tours';

interface DashboardHeroProps {
  isError?: boolean;
  onStartFocusMode: () => void;
}

export function DashboardHero({ isError, onStartFocusMode }: DashboardHeroProps) {
  const navigate = useNavigate();

  return (
    <div className="grid gap-8 p-6 md:grid-cols-[1.55fr_0.95fr] md:p-8">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-cyan-700 dark:text-cyan-200/90">
          Painel
        </p>
        <h1
          id="tour-welcome"
          className="mt-3 max-w-3xl text-3xl font-semibold tracking-tight text-slate-950 dark:text-white md:text-[2.8rem]"
        >
          Veja o que precisa da sua atenção hoje
        </h1>
        <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-600 dark:text-slate-300 md:text-base">
          Mantenha seus clientes em dia acompanhando obrigações, documentos pendentes e prazos fiscais em um só lugar.
        </p>

        <div className="mt-6 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => startTour('dashboard', navigate, '/dashboard')}
            className="inline-flex items-center gap-2 rounded-full border border-teal-500/25 bg-teal-500/10 px-5 py-3 text-sm font-semibold text-teal-700 transition hover:-translate-y-0.5 hover:bg-teal-500/20 dark:text-teal-300"
          >
            <BookOpen className="h-4 w-4" />
            Iniciar Guia
          </button>
          <button
            type="button"
            onClick={onStartFocusMode}
            className="inline-flex items-center gap-2 rounded-full bg-cyan-300 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:-translate-y-0.5 hover:bg-cyan-200"
          >
            Resolver agora
            <ArrowRight className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => navigate('/agenda-prazos')}
            className="inline-flex items-center gap-2 rounded-full border border-slate-300/70 bg-white/70 px-5 py-3 text-sm font-semibold text-slate-700 transition hover:-translate-y-0.5 hover:bg-white dark:border-white/15 dark:bg-white/5 dark:text-white dark:hover:bg-white/10"
          >
            Ver agenda fiscal
          </button>
          <button
            type="button"
            onClick={() => navigate('/clientes', { state: { openCreate: true } })}
            className="inline-flex items-center gap-2 rounded-full border border-slate-300/70 bg-transparent px-5 py-3 text-sm font-semibold text-slate-600 transition hover:-translate-y-0.5 hover:border-cyan-500/30 hover:text-slate-900 dark:border-white/15 dark:text-slate-200 dark:hover:border-cyan-300/30 dark:hover:text-white"
          >
            Novo cliente
          </button>
        </div>

        {isError && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-6 flex items-center gap-3 rounded-2xl border border-amber-400/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-800 dark:border-amber-400/20 dark:text-amber-100"
          >
            <AlertTriangle className="h-4 w-4 shrink-0" />
            Não foi possível atualizar todo o painel agora. Os blocos abaixo usam os dados
            mais recentes disponíveis.
          </motion.div>
        )}
      </div>
    </div>
  );
}
