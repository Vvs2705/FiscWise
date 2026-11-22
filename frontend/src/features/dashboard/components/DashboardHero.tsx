import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  AlertTriangle,
  BookOpen,
  UserPlus,
  Calendar,
  Upload,
  Shield,
  Receipt,
  Calculator,
  type LucideIcon,
} from 'lucide-react';
import { startTour } from '@/lib/tours';
import { cn } from '@/lib/utils';

interface DashboardHeroProps {
  isError?: boolean;
  isLoading?: boolean;
  /** Frase-resumo do dia (já montada com os dados que a página busca). */
  summary: string;
  /** Há algo para resolver? Controla o botão primário. */
  hasPending: boolean;
  onStartFocusMode: () => void;
}

const FOCUS_RING =
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background';

/** Topo do painel: responde "o que faço agora?" antes de qualquer número. */
export function DashboardHero({ isError, isLoading, summary, hasPending, onStartFocusMode }: DashboardHeroProps) {
  const navigate = useNavigate();
  const today = new Date().toLocaleDateString('pt-BR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  });

  return (
    <div>
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="min-w-0">
          <p className="font-mono text-xs font-medium uppercase tracking-wide text-muted-foreground">
            <span className="first-letter:uppercase">{today}</span>
          </p>
          <h1
            id="tour-welcome"
            className="mt-1 text-2xl font-semibold tracking-tight text-foreground md:text-3xl"
          >
            Hoje
          </h1>
          <p className="mt-1 text-sm text-muted-foreground md:text-base" aria-live="polite">
            {isLoading ? 'Carregando o resumo do dia...' : summary}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => startTour('dashboard', navigate, '/painel')}
            className={cn(
              'inline-flex h-10 items-center gap-2 rounded-md px-3 text-sm font-medium text-muted-foreground transition-colors duration-100 hover:bg-muted hover:text-foreground',
              FOCUS_RING,
            )}
          >
            <BookOpen className="h-4 w-4" aria-hidden="true" />
            Iniciar guia
          </button>
          {hasPending && (
            <button
              type="button"
              onClick={onStartFocusMode}
              className={cn(
                'inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground shadow-sm transition-[background-color,transform] duration-100 hover:bg-primary/90 active:scale-[0.98]',
                FOCUS_RING,
              )}
            >
              Resolver agora
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </button>
          )}
        </div>
      </div>

      {isError && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          role="status"
          className="mt-4 flex items-center gap-3 rounded-card border border-warning/30 bg-warning/10 px-4 py-3 text-sm text-warning"
        >
          <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden="true" />
          Não foi possível atualizar todo o painel agora. Os blocos abaixo usam os dados
          mais recentes disponíveis.
        </motion.div>
      )}
    </div>
  );
}

type QuickAction = {
  label: string;
  icon: LucideIcon;
  to: string;
  openCreate?: boolean;
};

const QUICK_ACTIONS: QuickAction[] = [
  { label: 'Ver agenda fiscal', icon: Calendar, to: '/obrigacoes' },
  { label: 'Nova obrigação', icon: Calendar, to: '/obrigacoes', openCreate: true },
  { label: 'Enviar documento', icon: Upload, to: '/documentos', openCreate: true },
  { label: 'Registrar guia', icon: Receipt, to: '/guias' },
  { label: 'Novo cliente', icon: UserPlus, to: '/clientes', openCreate: true },
  { label: 'Cadastrar certificado', icon: Shield, to: '/certificados', openCreate: true },
  { label: 'Calculadora', icon: Calculator, to: '/calculadora' },
];

/** Atalhos de criação/consulta, logo abaixo do que é urgente. */
export function QuickActions() {
  const navigate = useNavigate();
  return (
    <section aria-labelledby="quick-actions-title">
      <h2 id="quick-actions-title" className="text-sm font-semibold text-foreground">
        Ações rápidas
      </h2>
      <div className="mt-3 flex flex-wrap gap-2">
        {QUICK_ACTIONS.map(({ label, icon: Icon, to, openCreate }) => (
          <button
            key={label}
            type="button"
            onClick={() => navigate(to, openCreate ? { state: { openCreate: true } } : undefined)}
            className={cn(
              'inline-flex h-10 items-center gap-2 rounded-md border border-border bg-card px-3 text-sm font-medium text-foreground transition-colors duration-100 hover:bg-muted',
              FOCUS_RING,
            )}
          >
            <Icon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            {label}
          </button>
        ))}
      </div>
    </section>
  );
}
