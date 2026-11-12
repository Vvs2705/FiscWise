import { api } from './api';
import type {
  CalculatorPlan,
  SimulationRequest,
  SimulationResult,
  ChatRequest,
  ChatResponse,
  Simulation,
  TaxScenario,
} from './types/calculator';

export type ApiTaxScenario = {
  regime: string;
  total_tax: number | string;
  effective_rate: number | string;
  tax_breakdown: Record<string, number>;
  is_recommended?: boolean;
  ineligible?: boolean;
};

type FatorRMonthInput = { revenue?: number | string };

type CalculatorInputData = {
  annual_revenue?: number | string;
  annual_costs?: number | string;
  monthly_revenue?: number | string;
  operation_value?: number | string;
  months?: FatorRMonthInput[];
};

type FatorRResultData = {
  rbt12?: number | string;
  anexo?: string;
  total_das_anual?: number | string;
  monthly_details?: { aliquota_efetiva?: number | string }[];
  comparison?: {
    anexo?: string;
    aliquota_efetiva?: number | string;
    total_das_anual?: number | string;
    diferenca_anual?: number | string;
  };
};

export type ApiSimulationItem = {
  id: string;
  created_at: string;
  simulation_type: string;
  input_data?: CalculatorInputData;
  result_data?: { scenarios?: ApiTaxScenario[] } & FatorRResultData;
};

export type ApiRegimeResponse = {
  scenarios: ApiTaxScenario[];
  ai_recommendation?: string | null;
};

// ── Plano ────────────────────────────────────────────────────────────────────

/** Normaliza o plano efetivo vindo do backend (`/auth/tenant` já resolve assinatura/override). */
export function normalizeCalculatorPlan(raw: string | null | undefined): CalculatorPlan {
  const up = (raw || '').toUpperCase();
  if (up === 'PREMIUM') return 'PREMIUM';
  if (up === 'INTERMEDIARIO') return 'INTERMEDIARIO';
  return 'FREE';
}

/** Mesma regra do backend: export PDF exige Premium. */
export function canExportPdf(plan: CalculatorPlan): boolean {
  return plan === 'PREMIUM';
}

// ── Mapeadores puros ─────────────────────────────────────────────────────────

/** CNAE: 7 dígitos, aceitando a máscara usual (ex.: 6201-5/00). */
export function isValidCnae(value: string): boolean {
  const v = value.trim();
  return /^[\d./-]+$/.test(v) && v.replace(/\D/g, '').length === 7;
}

export function regimeLabel(regime: string): string {
  if (regime === 'simples_nacional') return 'Simples Nacional';
  if (regime === 'lucro_presumido') return 'Lucro Presumido';
  if (regime === 'lucro_real') return 'Lucro Real';
  return regime;
}

function mapScenario(s: ApiTaxScenario): TaxScenario {
  return {
    regime: regimeLabel(s.regime),
    annual_tax: Number(s.total_tax),
    effective_rate: Number(s.effective_rate),
    monthly_tax: Number(s.total_tax) / 12,
    breakdown: s.tax_breakdown,
  };
}

function savingsBetween(scenarios: ApiTaxScenario[]): number {
  const taxes = scenarios.map((s) => Number(s.total_tax));
  return taxes.length > 0 ? Math.max(...taxes) - Math.min(...taxes) : 0;
}

export function buildRegimePayload(data: SimulationRequest) {
  const annual = data.monthly_revenue * 12;
  const cnae = (data.activity_code || '').replace(/\D/g, '');
  return {
    annual_revenue: annual,
    annual_costs: data.annual_cogs,
    annual_payroll: 0,
    // Vazio → omitido (backend usa o anexo padrão); nunca enviar string vazia.
    ...(cnae ? { activity_code: cnae } : {}),
    title: `Simulação - R$ ${annual.toLocaleString('pt-BR')}/ano`,
  };
}

export function mapRegimeResponse(data: SimulationRequest, response: ApiRegimeResponse): SimulationResult {
  const recommended = response.scenarios.find((s) => s.is_recommended);
  return {
    revenue: data.monthly_revenue * 12,
    cogs: data.annual_cogs,
    scenarios: response.scenarios.map(mapScenario),
    recommended_regime: recommended ? regimeLabel(recommended.regime) : 'N/A',
    annual_savings: savingsBetween(response.scenarios),
    ai_recommendation: response.ai_recommendation || null,
  };
}

const anexoLabel = (anexo?: string) => `Simples Nacional - Anexo ${anexo || '?'}`;

export function mapSimulationItem(item: ApiSimulationItem): Simulation {
  const result = item.result_data || {};
  const apiScenarios = result.scenarios || [];
  let revenue = 0;
  let regime = 'N/A';
  let annual_savings = 0;
  let scenarios: TaxScenario[] = apiScenarios.map(mapScenario);

  if (item.simulation_type === 'regime') {
    revenue = Number(item.input_data?.annual_revenue || 0);
    const rec = apiScenarios.find((s) => s.is_recommended);
    regime = rec ? regimeLabel(rec.regime) : 'N/A';
    annual_savings = savingsBetween(apiScenarios);
  } else if (item.simulation_type === 'fator_r') {
    // POST /calculator/simulate-fator-r grava input_data.months[] e result_data
    // com rbt12, anexo, total_das_anual e comparison (anexo alternativo).
    const monthsRevenue = (item.input_data?.months || []).reduce(
      (acc, m) => acc + Number(m.revenue || 0),
      0,
    );
    revenue = result.rbt12 !== undefined ? Number(result.rbt12) : monthsRevenue;
    regime = anexoLabel(result.anexo);
    const diff = Number(result.comparison?.diferenca_anual || 0);
    annual_savings = diff < 0 ? -diff : 0;
    const total = Number(result.total_das_anual || 0);
    scenarios = [
      {
        regime,
        annual_tax: total,
        effective_rate: Number(result.monthly_details?.[0]?.aliquota_efetiva || 0),
        monthly_tax: total / 12,
        breakdown: {},
      },
    ];
    if (result.comparison) {
      const altTotal = Number(result.comparison.total_das_anual || 0);
      scenarios.push({
        regime: anexoLabel(result.comparison.anexo),
        annual_tax: altTotal,
        effective_rate: Number(result.comparison.aliquota_efetiva || 0),
        monthly_tax: altTotal / 12,
        breakdown: {},
      });
    }
  } else if (item.simulation_type === 'pis_cofins') {
    revenue = Number(item.input_data?.monthly_revenue || 0) * 12;
    regime = 'PIS/COFINS';
  } else if (item.simulation_type === 'icms') {
    revenue = Number(item.input_data?.operation_value || 0);
    regime = 'ICMS';
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
      scenarios,
      recommended_regime: regime,
      annual_savings,
    },
  };
}

// ── Chamadas HTTP ────────────────────────────────────────────────────────────

export const calculatorAPI = {
  async simulateRegime(data: SimulationRequest): Promise<SimulationResult> {
    const response = await api.post('/api/v1/calculator/simulate-regime', buildRegimePayload(data));
    return mapRegimeResponse(data, response.data as ApiRegimeResponse);
  },

  async chat(request: ChatRequest): Promise<ChatResponse> {
    const response = await api.post('/api/v1/calculator/chat', { content: request.message });
    return {
      response: response.data.assistant_message.content,
      recommendations: [],
      remaining_quota: response.data.remaining_quota,
    };
  },

  async getSimulations(): Promise<Simulation[]> {
    const response = await api.get('/api/v1/calculator/simulations');
    const items: ApiSimulationItem[] = response.data.items || [];
    return items.map(mapSimulationItem);
  },

  async exportPDF(simulationId: string): Promise<Blob> {
    const response = await api.post(
      '/api/v1/calculator/export-pdf',
      { simulation_id: simulationId, include_ai_recommendation: true },
      { responseType: 'blob' },
    );
    return response.data;
  },
};
