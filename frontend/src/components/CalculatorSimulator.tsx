import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { TrendingDown, Star, AlertCircle, ChevronDown } from 'lucide-react';
import { SimulationResult, SimulationRequest } from '../lib/types/calculator';
import { calculatorAPI } from '../lib/fiscwise-calculator-api';
import { formatCurrencyBRL, parseCurrencyBRL } from '@/lib/utils';

const ESTADOS_BR = [
  'AC','AL','AM','AP','BA','CE','DF','ES','GO','MA',
  'MG','MS','MT','PA','PB','PE','PI','PR','RJ','RN',
  'RO','RR','RS','SC','SE','SP','TO',
];

function moneyBRL(value: number) {
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

interface Props {
  userPlan?: 'FREE' | 'INTERMEDIARIO' | 'PREMIUM';
}

export function CalculatorSimulator({ userPlan = 'FREE' }: Props = {}) {
  const [formData, setFormData] = useState<SimulationRequest>({
    monthly_revenue: '' as unknown as number,  // starts empty so placeholder shows
    annual_cogs: '' as unknown as number,
    state: 'SP',
    regime: 'simples',
    has_pis_cofins_credit: false,
  });

  const [result, setResult] = useState<SimulationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [apiError, setApiError] = useState<string | null>(null);

  const validate = (): boolean => {
    const errors: Record<string, string> = {};
    const rev = Number(formData.monthly_revenue);
    const costs = Number(formData.annual_cogs);

    if (!formData.monthly_revenue && formData.monthly_revenue !== 0) {
      errors.monthly_revenue = 'Informe a receita mensal';
    } else if (isNaN(rev) || rev <= 0) {
      errors.monthly_revenue = 'Receita mensal deve ser maior que R$ 0';
    }

    if (formData.annual_cogs !== ('' as unknown as number) && (isNaN(costs) || costs < 0)) {
      errors.annual_cogs = 'Custo anual não pode ser negativo';
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setApiError(null);

    if (!validate()) return;

    setLoading(true);
    try {
      const res = await calculatorAPI.simulateRegime({
        ...formData,
        monthly_revenue: Number(formData.monthly_revenue) || 0,
        annual_cogs: Number(formData.annual_cogs) || 0,
      });
      setResult(res);
    } catch (rawErr: unknown) {
      const err = rawErr as { response?: { data?: { detail?: unknown } } };
      const msg = err?.response?.data?.detail || 'Erro ao processar simulação. Tente novamente.';
      setApiError(typeof msg === 'string' ? msg : JSON.stringify(msg));
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const field = (id: string) => ({
    'aria-describedby': fieldErrors[id] ? `${id}-error` : undefined,
    'aria-invalid': !!fieldErrors[id],
  });

  return (
    <div className="space-y-6">
      <form onSubmit={handleSubmit} data-plan={userPlan} className="space-y-5 rounded-xl border border-border bg-card p-6">
        <h3 className="text-sm font-semibold uppercase tracking-widest text-muted-foreground">
          Dados da simulação
        </h3>

        {/* Receita mensal */}
        <div>
          <label htmlFor="monthly_revenue" className="block text-sm font-medium text-foreground mb-1">
            Receita Mensal <span className="text-destructive">*</span>
          </label>
          <div className="relative">
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">R$</span>
            <input
              id="monthly_revenue"
              type="text"
              placeholder="0,00"
              value={formData.monthly_revenue === ('' as unknown as number) ? '' : formatCurrencyBRL(formData.monthly_revenue)}
              onChange={(e) =>
                setFormData({ ...formData, monthly_revenue: parseCurrencyBRL(e.target.value) })
              }
              {...field('monthly_revenue')}
              className={`w-full rounded-lg border pl-9 pr-3 py-2.5 text-sm bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition ${
                fieldErrors.monthly_revenue ? 'border-destructive' : 'border-input'
              }`}
            />
          </div>
          {fieldErrors.monthly_revenue && (
            <p id="monthly_revenue-error" className="mt-1 flex items-center gap-1 text-xs text-destructive">
              <AlertCircle className="h-3 w-3 shrink-0" />
              {fieldErrors.monthly_revenue}
            </p>
          )}
        </div>

        {/* Custo anual */}
        <div>
          <label htmlFor="annual_cogs" className="block text-sm font-medium text-foreground mb-1">
            Custo Anual{' '}
            <span className="text-muted-foreground text-xs font-normal">(opcional)</span>
          </label>
          <div className="relative">
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">R$</span>
            <input
              id="annual_cogs"
              type="text"
              placeholder="0,00"
              value={formData.annual_cogs === ('' as unknown as number) ? '' : formatCurrencyBRL(formData.annual_cogs)}
              onChange={(e) =>
                setFormData({ ...formData, annual_cogs: parseCurrencyBRL(e.target.value) })
              }
              {...field('annual_cogs')}
              className={`w-full rounded-lg border pl-9 pr-3 py-2.5 text-sm bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition ${
                fieldErrors.annual_cogs ? 'border-destructive' : 'border-input'
              }`}
            />
          </div>
          {fieldErrors.annual_cogs && (
            <p id="annual_cogs-error" className="mt-1 flex items-center gap-1 text-xs text-destructive">
              <AlertCircle className="h-3 w-3 shrink-0" />
              {fieldErrors.annual_cogs}
            </p>
          )}
        </div>

        {/* Estado */}
        <div>
          <label htmlFor="state" className="block text-sm font-medium text-foreground mb-1">
            Estado <span className="text-destructive">*</span>
          </label>
          <div className="relative">
            <select
              id="state"
              value={formData.state}
              onChange={(e) => setFormData({ ...formData, state: e.target.value })}
              className="w-full appearance-none rounded-lg border border-input bg-background text-foreground text-sm pl-3 pr-8 py-2.5 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition"
            >
              {ESTADOS_BR.map((s) => (
                <option key={s} value={s} className="bg-background text-foreground">
                  {s}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          </div>
        </div>

        {/* Crédito PIS/COFINS */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            role="checkbox"
            aria-checked={formData.has_pis_cofins_credit}
            id="pis_cofins"
            onClick={() =>
              setFormData({ ...formData, has_pis_cofins_credit: !formData.has_pis_cofins_credit })
            }
            className={`relative flex h-5 w-5 shrink-0 items-center justify-center rounded border transition ${
              formData.has_pis_cofins_credit
                ? 'bg-primary border-primary'
                : 'border-input bg-background'
            }`}
          >
            {formData.has_pis_cofins_credit && (
              <svg viewBox="0 0 12 10" className="h-3 w-3 text-primary-foreground" fill="none">
                <path d="M1 5l3.5 4L11 1" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            )}
          </button>
          <label htmlFor="pis_cofins" className="text-sm text-foreground cursor-pointer select-none" onClick={() => setFormData({ ...formData, has_pis_cofins_credit: !formData.has_pis_cofins_credit })}>
            Possui crédito de PIS/COFINS
          </label>
        </div>

        {/* API error */}
        {apiError && (
          <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2.5 text-sm text-destructive">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{apiError}</span>
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-primary py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-60 disabled:cursor-not-allowed transition-all"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              Calculando...
            </span>
          ) : (
            'Simular regimes tributários'
          )}
        </button>
      </form>

      {/* Results */}
      <AnimatePresence>
        {result && (
          <motion.div
            key="results"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            transition={{ duration: 0.4 }}
            className="space-y-4"
          >
            <h3 className="text-sm font-semibold uppercase tracking-widest text-muted-foreground">
              Resultado da simulação
            </h3>

            {/* Scenarios */}
            <div className="grid gap-3 sm:grid-cols-3">
              {result.scenarios.map((scenario, i) => {
                const isRecommended = scenario.regime === result.recommended_regime;
                return (
                  <motion.div
                    key={scenario.regime}
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.08 }}
                    className={`relative rounded-xl border p-4 transition-all ${
                      isRecommended
                        ? 'border-success/40 bg-success/5 shadow-sm'
                        : 'border-border bg-card'
                    }`}
                  >
                    {isRecommended && (
                      <div className="absolute -top-2.5 left-4 flex items-center gap-1 rounded-full bg-success px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-white">
                        <Star className="h-2.5 w-2.5" />
                        Recomendado
                      </div>
                    )}
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                      {scenario.regime}
                    </p>
                    <p className={`text-xl font-bold ${isRecommended ? 'text-success' : 'text-foreground'}`}>
                      {moneyBRL(scenario.annual_tax)}
                    </p>
                    <p className="text-xs text-muted-foreground">imposto anual</p>
                    <div className="mt-2 pt-2 border-t border-border">
                      <p className="text-xs text-muted-foreground">
                        Alíquota efetiva:{' '}
                        <span className="font-semibold text-foreground">
                          {(scenario.effective_rate * 100).toFixed(2)}%
                        </span>
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Mensal:{' '}
                        <span className="font-semibold text-foreground">
                          {moneyBRL(scenario.monthly_tax)}
                        </span>
                      </p>
                    </div>
                  </motion.div>
                );
              })}
            </div>

            {/* Savings banner */}
            {result.annual_savings > 0 && (
              <motion.div
                initial={{ opacity: 0, scale: 0.97 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.3 }}
                className="flex items-center gap-3 rounded-xl border border-primary/25 bg-primary/5 px-5 py-4"
              >
                <TrendingDown className="h-6 w-6 shrink-0 text-primary" />
                <div>
                  <p className="text-sm font-semibold text-foreground">
                    Economia potencial com o melhor regime:{' '}
                    <span className="text-primary">{moneyBRL(result.annual_savings)}/ano</span>
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Comparado ao regime mais caro disponível para o seu perfil.
                  </p>
                </div>
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
