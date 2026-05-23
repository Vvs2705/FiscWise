import { useState } from 'react';
import { SimulationResult, SimulationRequest } from '../lib/types/calculator';
import { calculatorAPI } from '../lib/fiscwise-calculator-api';
import { validateSimulation } from '../lib/validations/calculator';

interface Props {
  userPlan?: 'FREE' | 'INTERMEDIARIO' | 'PREMIUM';
}

export function CalculatorSimulator({ userPlan: _userPlan }: Props = {}) {
  const [formData, setFormData] = useState<SimulationRequest>({
    monthly_revenue: 0,
    annual_cogs: 0,
    state: 'SP',
    regime: 'simples',
    has_pis_cofins_credit: false,
  });

  const [result, setResult] = useState<SimulationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const validation = validateSimulation(formData);
    if (!validation.isValid) {
      setError('Preencha todos os campos corretamente');
      return;
    }

    setLoading(true);
    try {
      const result = await calculatorAPI.simulateRegime(formData);
      setResult(result);
    } catch (err) {
      setError('Erro ao processar simulação');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 text-foreground">
      <form onSubmit={handleSubmit} className="space-y-4 bg-card text-card-foreground p-6 rounded-lg border border-border shadow-sm">
        <div>
          <label className="block text-sm font-medium text-muted-foreground">
            Receita Mensal (R$)
          </label>
          <input
            type="number"
            min="0"
            value={formData.monthly_revenue}
            onChange={(e) => setFormData({ ...formData, monthly_revenue: parseFloat(e.target.value) })}
            className="mt-1 block w-full rounded-md border border-input bg-background text-foreground shadow-sm focus:border-primary focus:ring-primary px-3 py-2"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-muted-foreground">
            Custo Anual (R$)
          </label>
          <input
            type="number"
            min="0"
            value={formData.annual_cogs}
            onChange={(e) => setFormData({ ...formData, annual_cogs: parseFloat(e.target.value) })}
            className="mt-1 block w-full rounded-md border border-input bg-background text-foreground shadow-sm focus:border-primary focus:ring-primary px-3 py-2"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-muted-foreground">
            Estado
          </label>
          <select
            value={formData.state}
            onChange={(e) => setFormData({ ...formData, state: e.target.value })}
            className="mt-1 block w-full rounded-md border border-input bg-background text-foreground shadow-sm focus:border-primary focus:ring-primary px-3 py-2"
          >
            {['SP', 'RJ', 'MG', 'BA', 'SC', 'RS', 'PR'].map((state) => (
              <option key={state} value={state} className="bg-background text-foreground">
                {state}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center">
          <input
            type="checkbox"
            id="pis_cofins"
            checked={formData.has_pis_cofins_credit}
            onChange={(e) => setFormData({ ...formData, has_pis_cofins_credit: e.target.checked })}
            className="rounded border-input bg-background text-primary focus:ring-primary"
          />
          <label htmlFor="pis_cofins" className="ml-2 text-sm text-muted-foreground">
            Possui crédito de PIS/COFINS
          </label>
        </div>

        {error && <div className="text-destructive text-sm font-medium">{error}</div>}

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-primary text-primary-foreground py-2 rounded-md hover:bg-primary/95 transition disabled:bg-muted disabled:text-muted-foreground"
        >
          {loading ? 'Processando...' : 'Simular'}
        </button>
      </form>

      {result && (
        <div className="bg-green-50/50 dark:bg-green-950/20 p-6 rounded-lg border border-green-200/50 dark:border-green-900/30">
          <h3 className="font-semibold text-lg text-foreground mb-4">Resultados da Simulação</h3>

          {result.scenarios.map((scenario) => (
            <div key={scenario.regime} className="mb-4 p-4 bg-card text-card-foreground rounded border border-border shadow-sm">
              <div className="font-semibold text-foreground">{scenario.regime.toUpperCase()}</div>
              <div className="grid grid-cols-2 gap-2 mt-2 text-sm">
                <div className="text-muted-foreground">Imposto Anual: <span className="font-semibold text-foreground">R$ {scenario.annual_tax.toLocaleString('pt-BR')}</span></div>
                <div className="text-muted-foreground">Taxa Efetiva: <span className="font-semibold text-foreground">{(scenario.effective_rate * 100).toFixed(2)}%</span></div>
              </div>
            </div>
          ))}

          <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-950/30 rounded border border-blue-200 dark:border-blue-900/40 shadow-sm">
            <div className="text-lg font-semibold text-blue-900 dark:text-blue-200">
              Melhor Regime: {result.recommended_regime}
            </div>
            <div className="text-sm text-blue-800 dark:text-blue-300 mt-2">
              Economia Anual: R$ {result.annual_savings.toLocaleString('pt-BR')}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
