import { motion } from 'framer-motion';
import { Shield, TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react';
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
}

export function PortfolioRiskCard({
  score,
  factors,
  isLoading,
}: PortfolioRiskCardProps) {
  if (isLoading) {
    return (
      <div className="bg-fw-surface-solid border border-fw-border rounded-xl p-6">
        <div className="h-6 w-48 bg-fw-surface animate-pulse rounded mb-4" />
        <div className="h-40 bg-fw-surface animate-pulse rounded-lg" />
      </div>
    );
  }

  const getScoreConfig = (score: number) => {
    if (score >= 90) {
      return {
        label: 'Excelente',
        color: 'text-fw-success',
        bg: 'bg-fw-success',
        gradient: 'from-fw-success to-fw-success/80',
        icon: TrendingUp,
      };
    }
    if (score >= 75) {
      return {
        label: 'Boa',
        color: 'text-fw-blue',
        bg: 'bg-fw-blue',
        gradient: 'from-fw-blue to-fw-blue/80',
        icon: TrendingUp,
      };
    }
    if (score >= 55) {
      return {
        label: 'Atenção',
        color: 'text-fw-warning',
        bg: 'bg-fw-warning',
        gradient: 'from-fw-warning to-fw-warning/80',
        icon: AlertTriangle,
      };
    }
    return {
      label: 'Crítica',
      color: 'text-fw-danger',
      bg: 'bg-fw-danger',
      gradient: 'from-fw-danger to-fw-danger/80',
      icon: TrendingDown,
    };
  };

  const config = getScoreConfig(score);
  const Icon = config.icon;

  const factorStatusConfig = {
    good: {
      color: 'text-fw-success',
      bg: 'bg-fw-success-soft',
      border: 'border-fw-success/30',
    },
    warning: {
      color: 'text-fw-warning',
      bg: 'bg-fw-warning-soft',
      border: 'border-fw-warning/30',
    },
    critical: {
      color: 'text-fw-danger',
      bg: 'bg-fw-danger-soft',
      border: 'border-fw-danger/30',
    },
  };

  return (
    <motion.div
      variants={fadeIn}
      className="bg-fw-surface-solid border border-fw-border rounded-xl p-6"
    >
      <h2 className="text-lg font-semibold text-fw-text mb-4 flex items-center gap-2">
        <Shield className="w-5 h-5 text-fw-primary" />
        Saúde da Carteira
      </h2>

      {/* Score Display */}
      <div className="relative mb-6">
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
                className="text-fw-surface"
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
              <span className="text-sm text-fw-text-muted">de 100</span>
            </div>
          </div>
        </div>

        <div className="text-center mt-4">
          <span
            className={`inline-block px-4 py-2 rounded-full text-sm font-semibold ${config.color} ${
              factorStatusConfig[
                score >= 75 ? 'good' : score >= 55 ? 'warning' : 'critical'
              ].bg
            } border ${
              factorStatusConfig[
                score >= 75 ? 'good' : score >= 55 ? 'warning' : 'critical'
              ].border
            }`}
          >
            {config.label}
          </span>
        </div>
      </div>

      {/* Risk Factors */}
      {factors.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-fw-text mb-3">
            Fatores de risco
          </h3>
          {factors.map((factor, index) => {
            const factorConfig = factorStatusConfig[factor.status];
            return (
              <div
                key={index}
                className={`${factorConfig.bg} border ${factorConfig.border} rounded-lg p-3`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-fw-text">
                    {factor.label}
                  </span>
                  <span className={`text-sm font-semibold ${factorConfig.color}`}>
                    {factor.impact > 0 ? '+' : ''}
                    {factor.impact}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Info Text */}
      <p className="text-xs text-fw-text-muted mt-4 text-center">
        Score baseado em prazos, documentos, certificados e guias
      </p>
    </motion.div>
  );
}
