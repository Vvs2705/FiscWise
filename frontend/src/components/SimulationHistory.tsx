import { useState, useEffect } from 'react';
import { Simulation } from '../lib/types/calculator';
import { calculatorAPI } from '../lib/fiscwise-calculator-api';

export function SimulationHistory() {
  const [simulations, setSimulations] = useState<Simulation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadSimulations();
  }, []);

  const loadSimulations = async () => {
    try {
      setLoading(true);
      const data = await calculatorAPI.getSimulations();
      setSimulations(data);
    } catch (err) {
      setError('Erro ao carregar histórico');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleExportPDF = async (simulationId: string) => {
    try {
      const blob = await calculatorAPI.exportPDF(simulationId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `simulacao_${simulationId}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch (err) {
      console.error('Erro ao exportar PDF:', err);
    }
  };

  if (loading) {
    return <div className="text-center py-8 text-muted-foreground animate-pulse">Carregando histórico...</div>;
  }

  if (error) {
    return <div className="text-center py-8 text-destructive font-medium">{error}</div>;
  }

  if (simulations.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <p className="font-semibold text-foreground">Nenhuma simulação ainda.</p>
        <p className="text-sm mt-2">Crie uma simulação na aba Simulador para vê-la aqui.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {simulations.map((sim) => (
        <div key={sim.id} className="bg-card text-card-foreground p-4 rounded-lg border border-border hover:shadow-md transition">
          <div className="flex justify-between items-start mb-2">
            <div>
              <div className="text-sm text-muted-foreground">
                {new Date(sim.created_at).toLocaleDateString('pt-BR')}
              </div>
              <div className="font-semibold text-foreground">
                Receita: R$ {sim.revenue.toLocaleString('pt-BR')}
              </div>
            </div>
            <div className="text-right">
              <div className="text-sm text-muted-foreground">Melhor Regime</div>
              <div className="font-semibold text-primary uppercase">{sim.regime}</div>
            </div>
          </div>

          <div className="bg-green-50/50 dark:bg-green-950/20 p-2 rounded mb-3 border border-green-200/50 dark:border-green-900/30">
            <div className="text-sm text-green-800 dark:text-green-200">
              Economia Anual: <span className="font-bold">R$ {sim.annual_savings.toLocaleString('pt-BR')}</span>
            </div>
          </div>

          <div className="flex gap-2">
            <button
              onClick={() => handleExportPDF(sim.id)}
              className="flex-1 text-sm bg-primary/10 text-primary py-2 rounded hover:bg-primary/20 transition"
            >
              📄 Exportar PDF
            </button>
            <button
              onClick={() => loadSimulations()}
              className="flex-1 text-sm bg-muted text-muted-foreground py-2 rounded hover:bg-muted/80 transition"
            >
              ↻ Detalhar
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
