import { api } from './api';
import type { SimulationRequest, SimulationResult, ChatRequest, ChatResponse, Simulation } from './types/calculator';

type ApiTaxScenario = {
  regime: string;
  total_tax: number | string;
  effective_rate: number | string;
  tax_breakdown: Record<string, number>;
  is_recommended?: boolean;
};

type CalculatorInputData = {
  annual_revenue?: number | string;
  annual_costs?: number | string;
  monthly_revenue?: number | string;
  operation_value?: number | string;
};

type ApiSimulationItem = {
  id: string;
  created_at: string;
  simulation_type: string;
  input_data?: CalculatorInputData;
  result_data?: {
    scenarios?: ApiTaxScenario[];
  };
};

type ICMSPayload = Record<string, unknown>;
type PISCOFINSPayload = Record<string, unknown>;

export const calculatorAPI = {
  async simulateRegime(data: SimulationRequest): Promise<SimulationResult> {
    const payload = {
      annual_revenue: data.monthly_revenue * 12,
      annual_costs: data.annual_cogs,
      annual_payroll: 0,
      activity_code: '6201500', // default service activity code for calculations
      title: `Simulação - R$ ${(data.monthly_revenue * 12).toLocaleString('pt-BR')}/ano`,
    };
    
    const response = await api.post('/api/v1/calculator/simulate-regime', payload);
    const responseData = response.data;
    
    const scenarios = responseData.scenarios.map((s: ApiTaxScenario) => ({
      regime: s.regime === 'simples_nacional' ? 'Simples Nacional'
            : s.regime === 'lucro_presumido' ? 'Lucro Presumido'
            : 'Lucro Real',
      annual_tax: Number(s.total_tax),
      effective_rate: Number(s.effective_rate),
      monthly_tax: Number(s.total_tax) / 12,
      breakdown: s.tax_breakdown,
    }));
    
    const recommendedScenario = responseData.scenarios.find((s: ApiTaxScenario) => s.is_recommended);
    const recommended_regime = recommendedScenario
      ? (recommendedScenario.regime === 'simples_nacional' ? 'Simples Nacional'
         : recommendedScenario.regime === 'lucro_presumido' ? 'Lucro Presumido'
         : 'Lucro Real')
      : 'N/A';
      
    const eligibleTaxes = responseData.scenarios.map((s: ApiTaxScenario) => Number(s.total_tax));
    const maxTax = eligibleTaxes.length > 0 ? Math.max(...eligibleTaxes) : 0;
    const minTax = eligibleTaxes.length > 0 ? Math.min(...eligibleTaxes) : 0;
    const annual_savings = maxTax - minTax;
    
    return {
      revenue: data.monthly_revenue * 12,
      cogs: data.annual_cogs,
      scenarios,
      recommended_regime,
      annual_savings,
    };
  },

  async simulateICMS(data: ICMSPayload): Promise<unknown> {
    const response = await api.post('/api/v1/calculator/simulate-icms', data);
    return response.data;
  },

  async simulatePISCOFINS(data: PISCOFINSPayload): Promise<unknown> {
    const response = await api.post('/api/v1/calculator/simulate-pis-cofins', data);
    return response.data;
  },

  async chat(request: ChatRequest): Promise<ChatResponse> {
    const payload = {
      content: request.message,
    };
    
    const response = await api.post('/api/v1/calculator/chat', payload);
    return {
      response: response.data.assistant_message.content,
      recommendations: [],
      remaining_quota: response.data.remaining_quota,
    };
  },

  async getSimulations(): Promise<Simulation[]> {
    const response = await api.get('/api/v1/calculator/simulations');
    const items = response.data.items || [];
    
    return items.map((item: ApiSimulationItem) => {
      let revenue = 0;
      let regime = 'N/A';
      let annual_savings = 0;
      const scenarios = item.result_data?.scenarios || [];
      
      if (item.simulation_type === 'regime') {
        revenue = Number(item.input_data?.annual_revenue || 0);
        const recommendedScenario = scenarios.find((s: ApiTaxScenario) => s.is_recommended);
        regime = recommendedScenario ? (recommendedScenario.regime === 'simples_nacional' ? 'Simples Nacional' : recommendedScenario.regime === 'lucro_presumido' ? 'Lucro Presumido' : 'Lucro Real') : 'N/A';
        
        const eligibleTaxes = scenarios.map((s: ApiTaxScenario) => Number(s.total_tax));
        const maxTax = eligibleTaxes.length > 0 ? Math.max(...eligibleTaxes) : 0;
        const minTax = eligibleTaxes.length > 0 ? Math.min(...eligibleTaxes) : 0;
        annual_savings = maxTax - minTax;
      } else if (item.simulation_type === 'pis_cofins') {
        revenue = Number(item.input_data?.monthly_revenue || 0) * 12;
        regime = 'PIS/COFINS';
        annual_savings = 0;
      } else if (item.simulation_type === 'icms') {
        revenue = Number(item.input_data?.operation_value || 0);
        regime = 'ICMS';
        annual_savings = 0;
      }
      
      return {
        id: item.id,
        user_id: '',
        created_at: item.created_at,
        revenue,
        regime,
        annual_savings,
        result: {
          revenue,
          cogs: Number(item.input_data?.annual_costs || 0),
          scenarios: scenarios.map((s: ApiTaxScenario) => ({
            regime: s.regime === 'simples_nacional' ? 'Simples Nacional' : s.regime === 'lucro_presumido' ? 'Lucro Presumido' : 'Lucro Real',
            annual_tax: Number(s.total_tax),
            effective_rate: Number(s.effective_rate),
            monthly_tax: Number(s.total_tax) / 12,
            breakdown: s.tax_breakdown,
          })),
          recommended_regime: regime,
          annual_savings,
        }
      };
    });
  },

  async exportPDF(simulationId: string): Promise<Blob> {
    const response = await api.post('/api/v1/calculator/export-pdf', {
      simulation_id: simulationId,
      include_ai_recommendation: true,
    }, {
      responseType: 'blob',
    });
    return response.data;
  },
};
