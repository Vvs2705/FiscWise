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
    return <div className="text-center py-8">Carregando histórico...</div>;
  }

  if (error) {
    return <div className="text-center py-8 text-red-600">{error}</div>;
  }

  if (simulations.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p>Nenhuma simulação ainda.</p>
        <p className="text-sm mt-2">Crie uma simulação na aba Simulador para vê-la aqui.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {simulations.map((sim) => (
        <div key={sim.id} className="bg-white p-4 rounded-lg border border-gray-200 hover:shadow-md transition">
          <div className="flex justify-between items-start mb-2">
            <div>
              <div className="text-sm text-gray-600">
                {new Date(sim.created_at).toLocaleDateString('pt-BR')}
              </div>
              <div className="font-semibold text-gray-900">
                Receita: R$ {sim.revenue.toLocaleString('pt-BR')}
              </div>
            </div>
            <div className="text-right">
              <div className="text-sm text-gray-600">Melhor Regime</div>
              <div className="font-semibold text-blue-600 uppercase">{sim.regime}</div>
            </div>
          </div>

          <div className="bg-green-50 p-2 rounded mb-3">
            <div className="text-sm text-green-800">
              Economia Anual: <span className="font-bold">R$ {sim.annual_savings.toLocaleString('pt-BR')}</span>
            </div>
          </div>

          <div className="flex gap-2">
            <button
              onClick={() => handleExportPDF(sim.id)}
              className="flex-1 text-sm bg-blue-100 text-blue-700 py-2 rounded hover:bg-blue-200"
            >
              📄 Exportar PDF
            </button>
            <button
              onClick={() => loadSimulations()}
              className="flex-1 text-sm bg-gray-100 text-gray-700 py-2 rounded hover:bg-gray-200"
            >
              ↻ Detalhar
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
