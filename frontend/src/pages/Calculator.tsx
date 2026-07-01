import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Calculator, BrainCircuit, TrendingDown, History } from 'lucide-react';
import { FiscalCalculatorSection } from '../components/FiscalCalculatorSection';
import { fetchTenant } from '../lib/auth';

const highlights = [
  {
    icon: Calculator,
    title: 'Simulação Rápida',
    description: 'Compare Simples Nacional, Lucro Presumido e Lucro Real em segundos.',
  },
  {
    icon: BrainCircuit,
    title: 'IA Especializada',
    description: 'Assistente fiscal com GPT-4o Mini que analisa seu cenário tributário.',
  },
  {
    icon: TrendingDown,
    title: 'Economia Garantida',
    description: 'Descubra quanto você pode reduzir de impostos com o regime ideal.',
  },
  {
    icon: History,
    title: 'Histórico Completo',
    description: 'Acesse e exporte todas as suas simulações anteriores em PDF.',
  },
];

export function CalculatorPage() {
  const [userPlan, setUserPlan] = useState<'FREE' | 'INTERMEDIARIO' | 'PREMIUM'>('FREE');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTenant()
      .then((tenant) => {
        const plan = (tenant.plan_slug || 'FREE').toUpperCase() as
          | 'FREE'
          | 'INTERMEDIARIO'
          | 'PREMIUM';
        setUserPlan(plan);
      })
      .catch(() => setUserPlan('FREE'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="text-sm text-muted-foreground">Carregando calculadora...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="mx-auto max-w-5xl space-y-8 p-6 md:p-8">

        {/* ── Hero ── */}
        <motion.div
          initial={{ opacity: 0, y: -18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, ease: 'easeOut' }}
        >
          <div className="flex items-center gap-3 mb-1">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 border border-primary/20">
              <Calculator className="h-5 w-5 text-primary" />
            </div>
            <h1 className="text-2xl font-bold md:text-3xl">
              Calculadora Fiscal{' '}
              <span className="text-primary">com IA</span>
            </h1>
          </div>
          <p className="mt-1 text-sm text-muted-foreground ml-[52px]">
            Simule regimes tributários e receba recomendações personalizadas do assistente fiscal.
          </p>

          {/* Plan badge */}
          <div className="mt-3 ml-[52px]">
            <span
              className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold border ${
                userPlan === 'PREMIUM'
                  ? 'bg-warning/10 text-warning border-warning/25'
                  : userPlan === 'INTERMEDIARIO'
                  ? 'bg-primary/10 text-primary border-primary/25'
                  : 'bg-muted text-muted-foreground border-border'
              }`}
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  userPlan === 'PREMIUM'
                    ? 'bg-warning'
                    : userPlan === 'INTERMEDIARIO'
                    ? 'bg-primary'
                    : 'bg-muted-foreground'
                }`}
              />
              Plano {userPlan === 'FREE' ? 'Gratuito' : userPlan === 'INTERMEDIARIO' ? 'Intermediário' : 'Premium'}
            </span>
          </div>
        </motion.div>

        {/* ── Main calculator section ── */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          <FiscalCalculatorSection userPlan={userPlan} />
        </motion.div>

        {/* ── Feature highlights grid ── */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.25 }}
          className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
        >
          {highlights.map(({ icon: Icon, title, description }, i) => (
            <motion.div
              key={title}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.3 + i * 0.08 }}
              className="group relative overflow-hidden rounded-xl border border-border bg-card p-5 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-token-sm hover:border-primary/30"
            >
              <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 border border-primary/15 transition-colors group-hover:bg-primary/15">
                <Icon className="h-4 w-4 text-primary" />
              </div>
              <h3 className="font-semibold text-foreground mb-1">{title}</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">{description}</p>
            </motion.div>
          ))}
        </motion.div>

        {/* ── Info banner ── */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.5 }}
          className="rounded-xl border border-primary/20 bg-primary/5 px-5 py-4"
        >
          <div className="flex items-start gap-3">
            <BrainCircuit className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
            <div className="text-sm text-foreground">
              <strong className="font-semibold">Dica:</strong>{' '}
              <span className="text-muted-foreground">
                A Calculadora Fiscal usa IA para analisar seu regime tributário e sugerir
                otimizações. Quanto mais detalhes você fornecer, melhores serão as recomendações.{' '}
                {userPlan === 'FREE' && (
                  <span className="text-primary font-medium">
                    Faça upgrade para INTERMEDIÁRIO ou PREMIUM para desbloquear o chat com IA.
                  </span>
                )}
              </span>
            </div>
          </div>
        </motion.div>

      </div>
    </div>
  );
}

export default CalculatorPage;
