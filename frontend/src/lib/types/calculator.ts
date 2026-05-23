export interface SimulationRequest {
  monthly_revenue: number;
  annual_cogs: number;
  state: string;
  regime: 'simples' | 'lucro_presumido' | 'lucro_real';
  has_pis_cofins_credit: boolean;
}

export interface TaxScenario {
  regime: string;
  annual_tax: number;
  effective_rate: number;
  monthly_tax: number;
  breakdown: Record<string, number>;
}

export interface SimulationResult {
  revenue: number;
  cogs: number;
  scenarios: TaxScenario[];
  recommended_regime: string;
  annual_savings: number;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export interface ChatRequest {
  message: string;
  conversation_history: ChatMessage[];
}

export interface ChatResponse {
  response: string;
  recommendations: string[];
}

export interface Simulation {
  id: string;
  user_id: string;
  created_at: string;
  revenue: number;
  regime: string;
  annual_savings: number;
  result: SimulationResult;
}

export interface PlanFeatures {
  FREE: {
    canUseCalculator: boolean;
    aiRecommendations: boolean;
    chatMessages: number;
    pdfExport: boolean;
  };
  INTERMEDIARIO: {
    canUseCalculator: boolean;
    aiRecommendations: boolean;
    chatMessages: number;
    pdfExport: boolean;
  };
  PREMIUM: {
    canUseCalculator: boolean;
    aiRecommendations: boolean;
    chatMessages: number;
    pdfExport: boolean;
  };
}
