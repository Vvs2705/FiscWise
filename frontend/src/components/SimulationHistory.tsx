import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FileDown, ChevronDown, ChevronUp, AlertCircle, History } from 'lucide-react';
import { Simulation } from '../lib/types/calculator';
import { calculatorAPI } from '../lib/fiscwise-calculator-api';

function moneyBRL(value: number) {
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

export function SimulationHistory() {
  const [simulations, setSimulations] = useState<Simulation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [exportingId, setExportingId] = useState<string | null>(null);

  useEffect(() => {
    loadSimulations();
  }, []);

  const loadSimulations = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await calculatorAPI.getSimulations();
      setSimulations(data);
    } catch (rawErr: unknown) {
      const err = rawErr as { response?: { data?: { detail?: unknown } } };
      const msg = err?.response?.data?.detail || 'Erro ao carregar histórico de simulações.';
      setError(typeof msg === 'string' ? msg : 'Erro ao carregar histórico.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleExportPDF = async (simulationId: string) => {
    setExportingId(simulationId);
    try {
      const blob = await calculatorAPI.exportPDF(simulationId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `fiscwise-simulacao-${simulationId.slice(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (rawErr: unknown) {
      const err = rawErr as { response?: { status?: number } };
      const status = err?.response?.status;
      if (status === 403) {
        alert('Exportação de PDF disponível apenas no plano Premium.');
      } else {
        console.error('Erro ao exportar PDF:', err);
        alert('Não foi possível exportar o PDF. Tente novamente.');
      }
    } finally {
      setExportingId(null);
    }
  };

  const toggleExpand = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-16 text-muted-foreground">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        <p className="text-sm">Carregando histórico...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-destructive/20 bg-destructive/5 py-12 text-center">
        <AlertCircle className="h-8 w-8 text-destructive" />
        <p className="text-sm font-medium text-destructive">{error}</p>
        <button
          onClick={loadSimulations}
          className="text-xs text-primary underline hover:no-underline"
        >
          Tentar novamente
        </button>
      </div>
    );
  }

  if (simulations.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-border bg-muted/20 py-16 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted border border-border">
          <History className="h-6 w-6 text-muted-foreground" />
        </div>
        <div>
          <p className="font-semibold text-foreground">Nenhuma simulação realizada ainda</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Crie sua primeira simulação na aba{' '}
            <strong>Simulador</strong> para vê-la aqui.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {simulations.length} simulação{simulations.length !== 1 ? 'ões' : ''} encontrada{simulations.length !== 1 ? 's' : ''}
        </p>
        <button
          onClick={loadSimulations}
          className="text-xs text-primary hover:underline flex items-center gap-1"
        >
          ↻ Atualizar
        </button>
      </div>

      {simulations.map((sim, i) => {
        const isExpanded = expandedId === sim.id;
        const isExporting = exportingId === sim.id;

        return (
          <motion.div
            key={sim.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            className="rounded-xl border border-border bg-card overflow-hidden"
          >
            {/* Summary row */}
            <div className="flex items-center justify-between gap-4 px-4 py-3">
              <div className="min-w-0 flex-1">
                <p className="text-xs text-muted-foreground">
                  {new Date(sim.created_at).toLocaleDateString('pt-BR', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </p>
                <p className="mt-0.5 font-semibold text-foreground truncate">
                  Receita: {moneyBRL(sim.revenue)}/ano
                </p>
              </div>
              <div className="shrink-0 text-right">
                <p className="text-xs text-muted-foreground">Recomendado</p>
                <p className="font-semibold text-primary text-sm uppercase">{sim.regime}</p>
              </div>
              {sim.annual_savings > 0 && (
                <div className="shrink-0 hidden sm:block text-right">
                  <p className="text-xs text-muted-foreground">Economia</p>
                  <p className="font-semibold text-emerald-500 text-sm">{moneyBRL(sim.annual_savings)}/ano</p>
                </div>
              )}
              <div className="flex items-center gap-1 shrink-0">
                <button
                  onClick={() => handleExportPDF(sim.id)}
                  disabled={isExporting}
                  title="Exportar PDF (requer plano Premium)"
                  className="flex items-center gap-1 rounded-lg border border-border bg-muted/30 px-2.5 py-1.5 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-50 transition"
                >
                  {isExporting ? (
                    <svg className="h-3.5 w-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                    </svg>
                  ) : (
                    <FileDown className="h-3.5 w-3.5" />
                  )}
                  PDF
                </button>
                <button
                  onClick={() => toggleExpand(sim.id)}
                  title={isExpanded ? 'Fechar detalhes' : 'Ver detalhes'}
                  className="flex items-center gap-1 rounded-lg border border-border bg-muted/30 px-2.5 py-1.5 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition"
                >
                  {isExpanded ? (
                    <ChevronUp className="h-3.5 w-3.5" />
                  ) : (
                    <ChevronDown className="h-3.5 w-3.5" />
                  )}
                  {isExpanded ? 'Fechar' : 'Detalhes'}
                </button>
              </div>
            </div>

            {/* Expanded detail */}
            <AnimatePresence>
              {isExpanded && (
                <motion.div
                  key="detail"
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.25 }}
                  className="overflow-hidden"
                >
                  <div className="border-t border-border px-4 py-3 bg-muted/10">
                    <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-3">
                      Cenários comparados
                    </p>
                    <div className="grid gap-2 sm:grid-cols-3">
                      {sim.result.scenarios.map((scenario) => {
                        const isRec = scenario.regime === sim.regime;
                        return (
                          <div
                            key={scenario.regime}
                            className={`rounded-lg border p-3 ${
                              isRec
                                ? 'border-emerald-500/30 bg-emerald-500/5'
                                : 'border-border bg-card'
                            }`}
                          >
                            <p className={`text-xs font-semibold uppercase ${isRec ? 'text-emerald-500' : 'text-muted-foreground'}`}>
                              {scenario.regime} {isRec && '✓'}
                            </p>
                            <p className="mt-1 text-sm font-bold text-foreground">
                              {moneyBRL(scenario.annual_tax)}/ano
                            </p>
                            <p className="text-xs text-muted-foreground">
                              Alíquota: {(scenario.effective_rate * 100).toFixed(2)}%
                            </p>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        );
      })}
    </div>
  );
}
