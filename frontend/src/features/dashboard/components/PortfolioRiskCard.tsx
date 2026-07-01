import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Shield,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Info,
  Sparkles,
  ArrowRight,
  CheckCircle,
} from 'lucide-react';
import { fadeIn } from '../../../lib/motion';

interface RiskFactor {
  label: string;
  impact: number;
  status: 'good' | 'warning' | 'critical';
}

interface PortfolioRiskCardProps {
  score: number;
  factors: RiskFactor[];
  isLoading?: boolean;
  onStartFocusMode?: () => void;
}

export function PortfolioRiskCard({
  score,
  factors,
  isLoading,
  onStartFocusMode,
}: PortfolioRiskCardProps) {
  const [showCalculation, setShowCalculation] = useState(false);

  if (isLoading) {
    return (
      <div className="bg-card border border-border rounded-card shadow-token-sm p-6">
        <div className="h-6 w-48 bg-muted animate-pulse rounded mb-4" />
        <div className="h-40 bg-muted animate-pulse rounded-lg" />
      </div>
    );
  }

  const getScoreConfig = (score: number) => {
    if (score >= 90) {
      return {
        label: 'Excelente',
        color: 'text-success',
        bg: 'bg-success',
        gradient: 'from-success to-success/80',
        icon: TrendingUp,
      };
    }
    if (score >= 75) {
      return {
        label: 'Boa',
        color: 'text-info',
        bg: 'bg-info',
        gradient: 'from-info to-info/80',
        icon: TrendingUp,
      };
    }
    if (score >= 55) {
      return {
        label: 'Atenção',
        color: 'text-warning',
        bg: 'bg-warning',
        gradient: 'from-warning to-warning/80',
        icon: AlertTriangle,
      };
    }
    return {
      label: 'Crítica',
      color: 'text-destructive',
      bg: 'bg-destructive',
      gradient: 'from-destructive to-destructive/80',
      icon: TrendingDown,
    };
  };

  const config = getScoreConfig(score);
  const Icon = config.icon;

  const factorStatusConfig = {
    good: {
      color: 'text-success',
      bg: 'bg-success/10',
      border: 'border-success/30',
    },
    warning: {
      color: 'text-warning',
      bg: 'bg-warning/10',
      border: 'border-warning/30',
    },
    critical: {
      color: 'text-destructive',
      bg: 'bg-destructive/10',
      border: 'border-destructive/30',
    },
  };

  // Recommendations builder based on risk factors
  const recommendations = factors.map((factor) => {
    if (factor.label.toLowerCase().includes('obrigaç')) {
      return {
        tip: 'Resolver obrigações fiscais vencidas no Modo Foco.',
        recovery: `+${Math.abs(factor.impact)} pts`,
        action: onStartFocusMode,
      };
    }
    if (factor.label.toLowerCase().includes('documento')) {
      return {
        tip: 'Conferir e aprovar documentos pendentes.',
        recovery: `+${Math.abs(factor.impact)} pts`,
        link: '/documentos',
      };
    }
    if (factor.label.toLowerCase().includes('certificado')) {
      return {
        tip: 'Contatar clientes com certificados expirando.',
        recovery: `+${Math.abs(factor.impact)} pts`,
        link: '/certificados',
      };
    }
    if (factor.label.toLowerCase().includes('recebível') || factor.label.toLowerCase().includes('atraso')) {
      return {
        tip: 'Cobrar honorários contábeis vencidos.',
        recovery: `+${Math.abs(factor.impact)} pts`,
        link: '/financeiro',
      };
    }
    return {
      tip: `Resolver pendência de ${factor.label}.`,
      recovery: `+${Math.abs(factor.impact)} pts`,
    };
  });

  return (
    <motion.div
      variants={fadeIn}
      className="bg-card border border-border rounded-card shadow-token-sm p-6 space-y-5"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
          <Shield className="w-5 h-5 text-primary" />
          Saúde da Carteira
        </h2>
        <button
          onClick={() => setShowCalculation(!showCalculation)}
          className="text-xs text-primary hover:underline flex items-center gap-1 font-medium"
        >
          <Info className="w-3.5 h-3.5" />
          {showCalculation ? 'Ocultar regras' : 'Ver regras de cálculo'}
        </button>
      </div>

      {/* Score Display */}
      <div className="relative">
        <div className="flex items-center justify-center">
          <div className="relative">
            {/* Circular Progress */}
            <svg className="w-40 h-40 transform -rotate-90">
              <circle
                cx="80"
                cy="80"
                r="70"
                stroke="currentColor"
                strokeWidth="12"
                fill="none"
                className="text-muted"
              />
              <motion.circle
                cx="80"
                cy="80"
                r="70"
                stroke="currentColor"
                strokeWidth="12"
                fill="none"
                strokeLinecap="round"
                className={config.color}
                initial={{ strokeDasharray: '0 440' }}
                animate={{
                  strokeDasharray: `${(score / 100) * 440} 440`,
                }}
                transition={{ duration: 1.5, ease: 'easeOut' }}
              />
            </svg>

            {/* Score Text */}
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <Icon className={`w-8 h-8 ${config.color} mb-1`} />
              <span className={`text-4xl font-bold ${config.color}`}>
                {score}
              </span>
              <span className="text-sm text-muted-foreground">de 100</span>
            </div>
          </div>
        </div>

        <div className="text-center mt-4">
          <span
            className={`inline-block px-4 py-1.5 rounded-full text-xs font-bold ${config.color} ${
              factorStatusConfig[
                score >= 75 ? 'good' : score >= 55 ? 'warning' : 'critical'
              ].bg
            } border ${
              factorStatusConfig[
                score >= 75 ? 'good' : score >= 55 ? 'warning' : 'critical'
              ].border
            }`}
          >
            Carteira {config.label}
          </span>
        </div>
      </div>

      {/* Rules Breakdown Section */}
      <AnimatePresence>
        {showCalculation && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden bg-muted border border-border rounded-card p-4 text-xs space-y-2 text-muted-foreground"
          >
            <p className="font-bold text-foreground mb-2 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-primary" />
              Fórmula de Dedução de Pontos:
            </p>
            <div className="grid grid-cols-2 gap-2 font-mono">
              <div className="flex items-center justify-between p-1.5 bg-muted rounded">
                <span>DAS Atrasado</span>
                <span className="text-destructive font-bold">-15 pts</span>
              </div>
              <div className="flex items-center justify-between p-1.5 bg-muted rounded">
                <span>Prazo Atrasado</span>
                <span className="text-destructive font-bold">-5 pts</span>
              </div>
              <div className="flex items-center justify-between p-1.5 bg-muted rounded">
                <span>Certificado Exp.</span>
                <span className="text-warning font-bold">-3 pts</span>
              </div>
              <div className="flex items-center justify-between p-1.5 bg-muted rounded">
                <span>Fatura Atrasada</span>
                <span className="text-destructive font-bold">-4 pts</span>
              </div>
              <div className="flex items-center justify-between p-1.5 bg-muted rounded col-span-2">
                <span>Doc. Pendente conferência</span>
                <span className="text-info font-bold">-2 pts</span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Risk Factors Breakdown */}
      {factors.length > 0 ? (
        <div className="space-y-2.5">
          <h3 className="text-sm font-semibold text-foreground flex items-center gap-1">
            Fatores que reduziram a saúde:
          </h3>
          <div className="space-y-2">
            {factors.map((factor, index) => {
              const factorConfig = factorStatusConfig[factor.status];
              return (
                <div
                  key={index}
                  className={`${factorConfig.bg} border ${factorConfig.border} rounded-lg p-3 flex items-center justify-between text-xs`}
                >
                  <span className="font-medium text-foreground">
                    {factor.label}
                  </span>
                  <span className={`font-mono font-bold ${factorConfig.color}`}>
                    {factor.impact} pts
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="rounded-card border border-success/20 bg-success/5 p-4 flex items-start gap-2.5 text-xs text-success">
          <CheckCircle className="w-5 h-5 shrink-0 text-success" />
          <div>
            <p className="font-bold">Nenhum fator de risco ativo!</p>
            <p className="text-muted-foreground mt-0.5">Sua carteira está operando em compliance máximo.</p>
          </div>
        </div>
      )}

      {/* Actionable recommendations tips */}
      {recommendations.length > 0 && (
        <div className="border-t border-border pt-4 space-y-2.5">
          <h3 className="text-xs uppercase tracking-wider text-muted-foreground font-bold">
            Como melhorar o score:
          </h3>
          <div className="space-y-2">
            {recommendations.slice(0, 2).map((rec, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between gap-3 text-xs bg-muted border border-border p-3 rounded-lg"
              >
                <div className="space-y-0.5 text-foreground">
                  <p>{rec.tip}</p>
                  <p className="text-[10px] text-success font-bold">
                    Recupera {rec.recovery}
                  </p>
                </div>
                {rec.action ? (
                  <button
                    onClick={rec.action}
                    className="shrink-0 flex items-center gap-1 text-[10px] bg-primary text-primary-foreground font-bold px-2 py-1.5 rounded-md hover:bg-primary/90 transition"
                  >
                    Focar
                    <ArrowRight className="w-3 h-3" />
                  </button>
                ) : rec.link ? (
                  <a
                    href={rec.link}
                    className="shrink-0 flex items-center gap-1 text-[10px] border border-primary/35 bg-primary/10 text-primary font-bold px-2 py-1.5 rounded-md hover:bg-primary/20 transition"
                  >
                    Acessar
                  </a>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}
