import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import {
  UserPlus,
  FileText,
  Calendar,
  Shield,
  Receipt,
  Calculator,
} from 'lucide-react';
import { staggerContainer, fadeIn } from '../../../lib/motion';

interface QuickAction {
  id: string;
  label: string;
  icon: 'client' | 'document' | 'obligation' | 'certificate' | 'guide' | 'calculator';
  onClick: () => void;
  variant?: 'primary' | 'secondary';
}

interface QuickActionsProps {
  actions?: QuickAction[];
}

const iconMap = {
  client: UserPlus,
  document: FileText,
  obligation: Calendar,
  certificate: Shield,
  guide: Receipt,
  calculator: Calculator,
};

export function QuickActions({ actions }: QuickActionsProps) {
  const navigate = useNavigate();

  const defaultActions: QuickAction[] = [
    {
      id: 'new-client',
      label: 'Novo cliente',
      icon: 'client',
      onClick: () => navigate('/clientes', { state: { openCreate: true } }),
      variant: 'primary',
    },
    {
      id: 'new-obligation',
      label: 'Nova obrigação',
      icon: 'obligation',
      onClick: () => navigate('/obrigacoes', { state: { openCreate: true } }),
    },
    {
      id: 'upload-document',
      label: 'Enviar documento',
      icon: 'document',
      onClick: () => navigate('/documentos', { state: { openCreate: true } }),
    },
    {
      id: 'new-certificate',
      label: 'Cadastrar certificado',
      icon: 'certificate',
      onClick: () => navigate('/certificados', { state: { openCreate: true } }),
    },
    {
      id: 'new-guide',
      label: 'Registrar guia',
      icon: 'guide',
      onClick: () => navigate('/das-mensal'),
    },
    {
      id: 'calculator',
      label: 'Calculadora',
      icon: 'calculator',
      onClick: () => navigate('/calculadora'),
    },
  ];

  const currentActions = actions || defaultActions;

  return (
    <motion.div
      variants={staggerContainer}
      initial="initial"
      animate="animate"
      className="bg-fw-surface-solid border border-fw-border rounded-xl p-6"
    >
      <h2 className="text-lg font-semibold text-fw-text mb-4">Ações rápidas</h2>

      <div className="grid grid-cols-2 gap-3">
        {currentActions.map((action) => {
          const Icon = iconMap[action.icon];
          const isPrimary = action.variant === 'primary';

          return (
            <motion.button
              key={action.id}
              variants={fadeIn}
              onClick={action.onClick}
              className={`
                group relative overflow-hidden rounded-lg p-4 text-left transition-all
                ${
                  isPrimary
                    ? 'bg-gradient-to-br from-fw-primary to-fw-blue text-white hover:shadow-fw-shadow-glow'
                    : 'bg-fw-surface border border-fw-border hover:border-fw-primary/30'
                }
              `}
            >
              <div className="relative z-10">
                <div
                  className={`
                  w-10 h-10 rounded-lg flex items-center justify-center mb-3 transition-transform group-hover:scale-110
                  ${
                    isPrimary
                      ? 'bg-white/20'
                      : 'bg-fw-primary-soft border border-fw-primary/30'
                  }
                `}
                >
                  <Icon
                    className={`w-5 h-5 ${
                      isPrimary ? 'text-white' : 'text-fw-primary'
                    }`}
                  />
                </div>
                <span
                  className={`text-sm font-semibold ${
                    isPrimary ? 'text-white' : 'text-fw-text'
                  }`}
                >
                  {action.label}
                </span>
              </div>

              {/* Hover effect */}
              <div
                className={`
                absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity
                ${
                  isPrimary
                    ? 'bg-white/10'
                    : 'bg-gradient-to-br from-fw-primary/5 to-fw-blue/5'
                }
              `}
              />
            </motion.button>
          );
        })}
      </div>
    </motion.div>
  );
}

