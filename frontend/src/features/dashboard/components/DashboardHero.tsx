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
} from 'lucide-react';
import { startTour } from '@/lib/tours';

interface DashboardHeroProps {
  isError?: boolean;
  onStartFocusMode: () => void;
}

export function DashboardHero({ isError, onStartFocusMode }: DashboardHeroProps) {
  const navigate = useNavigate();

  return (
    <div className="p-6 md:p-8">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-primary">
          Painel
        </p>
        <h1
          id="tour-welcome"
          className="mt-3 text-3xl font-semibold tracking-tight text-foreground md:text-[2.8rem]"
        >
          Veja o que precisa da sua atenção hoje
        </h1>
        <p className="mt-4 text-sm leading-7 text-muted-foreground md:text-base">
          Mantenha seus clientes em dia acompanhando obrigações, documentos pendentes e prazos fiscais em um só lugar.
        </p>

        <div className="mt-6 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => startTour('dashboard', navigate, '/painel')}
            className="inline-flex items-center gap-2 rounded-full border border-primary/25 bg-primary/10 px-5 py-3 text-sm font-semibold text-primary transition hover:-translate-y-0.5 hover:bg-primary/20"
          >
            <BookOpen className="h-4 w-4" />
            Iniciar Guia
          </button>

          <button
            type="button"
            onClick={onStartFocusMode}
            className="inline-flex items-center gap-2 rounded-full bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground transition hover:-translate-y-0.5 hover:bg-primary/90"
          >
            Resolver agora
            <ArrowRight className="h-4 w-4" />
          </button>

          <button
            type="button"
            onClick={() => navigate('/obrigacoes')}
            className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-5 py-3 text-sm font-semibold text-foreground transition hover:-translate-y-0.5 hover:bg-muted"
          >
            <Calendar className="h-4 w-4" />
            Ver agenda fiscal
          </button>

          <button
            type="button"
            onClick={() => navigate('/clientes', { state: { openCreate: true } })}
            className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-5 py-3 text-sm font-semibold text-foreground transition hover:-translate-y-0.5 hover:bg-muted"
          >
            <UserPlus className="h-4 w-4" />
            Novo cliente
          </button>

          <button
            type="button"
            onClick={() => navigate('/obrigacoes', { state: { openCreate: true } })}
            className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-5 py-3 text-sm font-semibold text-foreground transition hover:-translate-y-0.5 hover:bg-muted"
          >
            <Calendar className="h-4 w-4" />
            Nova obrigação
          </button>

          <button
            type="button"
            onClick={() => navigate('/documentos', { state: { openCreate: true } })}
            className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-5 py-3 text-sm font-semibold text-foreground transition hover:-translate-y-0.5 hover:bg-muted"
          >
            <Upload className="h-4 w-4" />
            Enviar documento
          </button>

          <button
            type="button"
            onClick={() => navigate('/certificados', { state: { openCreate: true } })}
            className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-5 py-3 text-sm font-semibold text-foreground transition hover:-translate-y-0.5 hover:bg-muted"
          >
            <Shield className="h-4 w-4" />
            Cadastrar certificado
          </button>

          <button
            type="button"
            onClick={() => navigate('/guias')}
            className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-5 py-3 text-sm font-semibold text-foreground transition hover:-translate-y-0.5 hover:bg-muted"
          >
            <Receipt className="h-4 w-4" />
            Registrar guia
          </button>

          <button
            type="button"
            onClick={() => navigate('/calculadora')}
            className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-5 py-3 text-sm font-semibold text-foreground transition hover:-translate-y-0.5 hover:bg-muted"
          >
            <Calculator className="h-4 w-4" />
            Calculadora
          </button>
        </div>

        {isError && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-6 flex items-center gap-3 rounded-card border border-warning/30 bg-warning/10 px-4 py-3 text-sm text-warning"
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
