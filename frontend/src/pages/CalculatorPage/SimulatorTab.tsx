import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import {
  Calculator,
  Building2,
  BarChart3,
  TrendingUp,
  Sparkles,
  Save,
  FileDown,
  ChevronRight,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { FormField } from '@/components/ui/FormField';
import { Badge } from '@/components/ui/Badge';
import { PlanGate } from './PlanGate';
import {
  useSimulate,
  useSaveSimulation,
  SECTORS,
  REGIONS,
  REGIME_LABELS,
  moneyBRL,
  percentBR,
  planHasAI,
  planHasPDF,
  type SubscriptionPlan,
  type SimulationType,
  type SimulationResult,
  type TaxRegime,
} from '@/lib/hooks/useCalculator';
import { cn } from '@/lib/utils';

const schema = z.object({
  gross_revenue: z.coerce
    .number({ invalid_type_error: 'Informe um valor numérico' })
    .positive('Receita deve ser maior que zero'),
  costs: z.coerce
    .number({ invalid_type_error: 'Informe um valor numérico' })
    .min(0, 'Custos não podem ser negativos'),
  sector: z.string().min(1, 'Selecione um setor'),
  region: z.string().min(1, 'Selecione um estado'),
});

type FormValues = z.infer<typeof schema>;

interface SimulatorTabProps {
  plan: SubscriptionPlan;
}

const SIM_TYPES: { type: SimulationType; label: string; icon: React.ElementType; description: string }[] = [
  {
    type: 'regime',
    label: 'Regime Tributário',
    icon: BarChart3,
    description: 'Compare Simples, Presumido e Real',
  },
  {
    type: 'icms',
    label: 'ICMS',
    icon: Building2,
    description: 'Imposto sobre circulação de mercadorias',
  },
  {
    type: 'pis_cofins',
    label: 'PIS/COFINS',
    icon: TrendingUp,
    description: 'Contribuições sobre faturamento',
  },
];

const REGIME_COLORS: Record<TaxRegime, string> = {
  simples_nacional: 'text-green-400 bg-green-500/10 border-green-500/20',
  lucro_presumido: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
  lucro_real: 'text-purple-400 bg-purple-500/10 border-purple-500/20',
};

export function SimulatorTab({ plan }: SimulatorTabProps) {
  const [simType, setSimType] = useState<SimulationType>('regime');
  const [result, setResult] = useState<SimulationResult | null>(null);
  const simulate = useSimulate();
  const save = useSaveSimulation();
  const hasAI = planHasAI(plan);
  const hasPDF = planHasPDF(plan);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { costs: 0 },
  });

  async function onSubmit(values: FormValues) {
    try {
      const res = await simulate.mutateAsync({
        ...values,
        simulation_type: simType,
      });
      setResult(res);
    } catch {
      toast.error('Erro ao executar simulação. Tente novamente.');
    }
  }

  async function handleSave() {
    if (!result) return;
    try {
      await save.mutateAsync(result);
      toast.success('Simulação salva no histórico!');
    } catch {
      toast.error('Erro ao salvar simulação.');
    }
  }

  return (
    <div className="space-y-6">
      {/* Simulation type selector */}
      <div
        role="group"
        aria-label="Tipo de simulação"
        className="grid grid-cols-1 gap-3 sm:grid-cols-3"
      >
        {SIM_TYPES.map(({ type, label, icon: Icon, description }) => (
          <button
            key={type}
            type="button"
            onClick={() => { setSimType(type); setResult(null); }}
            aria-pressed={simType === type}
            className={cn(
              'flex flex-col gap-1.5 rounded-xl border p-4 text-left transition-all duration-150 ease-spring',
              'hover:border-primary/40 hover:bg-accent',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
              simType === type
                ? 'border-primary/60 bg-primary/5 shadow-glow-sm'
                : 'border-border bg-card',
            )}
          >
            <div className="flex items-center gap-2">
              <Icon
                className={cn('h-4 w-4', simType === type ? 'text-primary' : 'text-muted-foreground')}
                aria-hidden="true"
              />
              <span className={cn('text-sm font-semibold', simType === type ? 'text-primary' : 'text-foreground')}>
                {label}
              </span>
            </div>
            <p className="text-xs text-muted-foreground">{description}</p>
          </button>
        ))}
      </div>

      {/* Form + Result side-by-side on large screens */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* ─── Form ─────────────────────────────────────────────────────────── */}
        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2 text-base">
              <Calculator className="h-4 w-4 text-primary" aria-hidden="true" />
              Dados da simulação
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
              <FormField label="Receita bruta mensal" error={errors.gross_revenue?.message}>
                <Input
                  type="number"
                  min={0}
                  step={0.01}
                  placeholder="Ex.: 150000"
                  aria-describedby={errors.gross_revenue ? 'gross_revenue-error' : undefined}
                  {...register('gross_revenue')}
                />
              </FormField>

              <FormField label="Custos e despesas mensais" error={errors.costs?.message}>
                <Input
                  type="number"
                  min={0}
                  step={0.01}
                  placeholder="Ex.: 60000"
                  aria-describedby={errors.costs ? 'costs-error' : undefined}
                  {...register('costs')}
                />
              </FormField>

              <FormField label="Setor de atividade" error={errors.sector?.message}>
                <Select
                  aria-describedby={errors.sector ? 'sector-error' : undefined}
                  {...register('sector')}
                >
                  <option value="">Selecione o setor</option>
                  {SECTORS.map(({ value, label }) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </Select>
              </FormField>

              <FormField label="Estado (UF)" error={errors.region?.message}>
                <Select
                  aria-describedby={errors.region ? 'region-error' : undefined}
                  {...register('region')}
                >
                  <option value="">Selecione o estado</option>
                  {REGIONS.map(({ value, label }) => (
                    <option key={value} value={value}>
                      {value} — {label}
                    </option>
                  ))}
                </Select>
              </FormField>

              <Button
                type="submit"
                className="w-full"
                disabled={simulate.isPending}
                aria-busy={simulate.isPending}
              >
                {simulate.isPending ? (
                  <>
                    <span
                      className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
                      aria-hidden="true"
                    />
                    Simulando...
                  </>
                ) : (
                  <>
                    <Calculator className="h-4 w-4" aria-hidden="true" />
                    Simular {SIM_TYPES.find((s) => s.type === simType)?.label}
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* ─── Results ──────────────────────────────────────────────────────── */}
        <div className="flex flex-col gap-4">
          {!result && !simulate.isPending && (
            <Card className="flex-1">
              <CardContent className="flex h-full min-h-[280px] flex-col items-center justify-center gap-3 text-center">
                <Calculator className="h-10 w-10 text-muted-foreground/40" aria-hidden="true" />
                <p className="text-sm text-muted-foreground">
                  Preencha os dados e clique em Simular para ver os resultados.
                </p>
              </CardContent>
            </Card>
          )}

          {simulate.isPending && (
            <Card className="flex-1">
              <CardContent className="flex h-full min-h-[280px] flex-col items-center justify-center gap-4">
                <div
                  className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent"
                  role="status"
                  aria-label="Calculando..."
                />
                <p className="text-sm text-muted-foreground">Calculando...</p>
              </CardContent>
            </Card>
          )}

          {result && !simulate.isPending && (
            <Card className="animate-fade-in-up">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">Resultado</CardTitle>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleSave}
                      disabled={save.isPending}
                      aria-label="Salvar simulação no histórico"
                    >
                      <Save className="h-3.5 w-3.5" aria-hidden="true" />
                      <span className="hidden sm:inline">Salvar</span>
                    </Button>
                    {hasPDF ? (
                      <Button
                        size="sm"
                        variant="outline"
                        aria-label="Exportar resultado como PDF"
                        onClick={() => toast('Exportação de PDF em breve!', { icon: '📄' })}
                      >
                        <FileDown className="h-3.5 w-3.5" aria-hidden="true" />
                        <span className="hidden sm:inline">PDF</span>
                      </Button>
                    ) : (
                      <PlanGate requiredPlan="premium" currentPlan={plan} inline>
                        <span />
                      </PlanGate>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* ─── Regime result ─────────────────────────────────────── */}
                {result.simulation_type === 'regime' && result.regime_options && (
                  <div className="space-y-2" role="list" aria-label="Opções de regime tributário">
                    {result.regime_options.map((opt) => (
                      <div
                        key={opt.regime}
                        role="listitem"
                        className={cn(
                          'flex items-center justify-between rounded-lg border p-3',
                          result.recommended_regime === opt.regime && planHasAI(plan)
                            ? REGIME_COLORS[opt.regime]
                            : 'border-border bg-muted/30',
                        )}
                      >
                        <div className="flex items-center gap-2">
                          {result.recommended_regime === opt.regime && hasAI && (
                            <Sparkles className="h-3.5 w-3.5 text-amber-400" aria-hidden="true" />
                          )}
                          <span className="text-sm font-medium">{REGIME_LABELS[opt.regime]}</span>
                          {result.recommended_regime === opt.regime && hasAI && (
                            <Badge variant="success" className="text-[10px]">
                              Recomendado
                            </Badge>
                          )}
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-semibold">{moneyBRL(opt.tax_amount)}</p>
                          <p className="text-xs text-muted-foreground">
                            {percentBR(opt.effective_rate)} efetivo
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* ─── ICMS result ───────────────────────────────────────── */}
                {result.simulation_type === 'icms' && result.icms_result && (
                  <div className="space-y-2">
                    <div className="flex justify-between rounded-lg border border-border bg-muted/30 p-3">
                      <span className="text-sm text-muted-foreground">Estado</span>
                      <span className="text-sm font-semibold">{result.icms_result.state}</span>
                    </div>
                    <div className="flex justify-between rounded-lg border border-border bg-muted/30 p-3">
                      <span className="text-sm text-muted-foreground">Alíquota</span>
                      <span className="text-sm font-semibold">{percentBR(result.icms_result.rate)}</span>
                    </div>
                    <div className="flex justify-between rounded-lg border border-primary/30 bg-primary/5 p-3">
                      <span className="text-sm font-medium">ICMS a recolher</span>
                      <span className="text-sm font-bold text-primary">
                        {moneyBRL(result.icms_result.tax_amount)}
                      </span>
                    </div>
                  </div>
                )}

                {/* ─── PIS/COFINS result ─────────────────────────────────── */}
                {result.simulation_type === 'pis_cofins' && result.pis_cofins_result && (
                  <div className="space-y-2">
                    <div className="flex justify-between rounded-lg border border-border bg-muted/30 p-3">
                      <span className="text-sm text-muted-foreground">
                        PIS ({percentBR(result.pis_cofins_result.pis_rate)})
                      </span>
                      <span className="text-sm font-semibold">
                        {moneyBRL(result.pis_cofins_result.pis_amount)}
                      </span>
                    </div>
                    <div className="flex justify-between rounded-lg border border-border bg-muted/30 p-3">
                      <span className="text-sm text-muted-foreground">
                        COFINS ({percentBR(result.pis_cofins_result.cofins_rate)})
                      </span>
                      <span className="text-sm font-semibold">
                        {moneyBRL(result.pis_cofins_result.cofins_amount)}
                      </span>
                    </div>
                    <div className="flex justify-between rounded-lg border border-primary/30 bg-primary/5 p-3">
                      <span className="text-sm font-medium">Total PIS + COFINS</span>
                      <span className="text-sm font-bold text-primary">
                        {moneyBRL(result.pis_cofins_result.total_amount)}
                      </span>
                    </div>
                  </div>
                )}

                {/* ─── AI Recommendation ────────────────────────────────── */}
                {hasAI && result.ai_recommendation ? (
                  <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-4">
                    <div className="mb-2 flex items-center gap-2">
                      <Sparkles className="h-4 w-4 text-amber-400" aria-hidden="true" />
                      <span className="text-sm font-semibold text-amber-400">Recomendação IA</span>
                    </div>
                    <p className="text-sm leading-relaxed text-foreground/90">
                      {result.ai_recommendation}
                    </p>
                  </div>
                ) : !hasAI ? (
                  <PlanGate requiredPlan="intermediario" currentPlan={plan} inline>
                    <span />
                  </PlanGate>
                ) : null}

                {/* ─── Summary ──────────────────────────────────────────── */}
                <div className="grid grid-cols-2 gap-2 pt-1">
                  <div className="rounded-lg bg-muted/50 p-3 text-center">
                    <p className="text-xs text-muted-foreground">Receita bruta</p>
                    <p className="text-sm font-semibold">{moneyBRL(result.gross_revenue)}</p>
                  </div>
                  <div className="rounded-lg bg-muted/50 p-3 text-center">
                    <p className="text-xs text-muted-foreground">Margem líquida</p>
                    <p className="text-sm font-semibold">
                      {result.gross_revenue > 0
                        ? percentBR(((result.gross_revenue - result.costs) / result.gross_revenue) * 100)
                        : '—'}
                    </p>
                  </div>
                </div>

                {/* PDF gate inline when result exists and not premium */}
                {!hasPDF && (
                  <PlanGate requiredPlan="premium" currentPlan={plan} inline>
                    <span />
                  </PlanGate>
                )}
              </CardContent>
            </Card>
          )}

          {simulate.isError && (
            <Card className="border-destructive/40">
              <CardContent className="flex items-center gap-3 px-4 py-3">
                <ChevronRight className="h-4 w-4 text-destructive" aria-hidden="true" />
                <p className="text-sm text-destructive">
                  Não foi possível executar a simulação. Verifique os dados e tente novamente.
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
