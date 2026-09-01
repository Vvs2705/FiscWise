import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

// ─── Plan types ───────────────────────────────────────────────────────────────

export type SubscriptionPlan = 'free' | 'intermediario' | 'premium';

export type TaxRegime = 'simples_nacional' | 'lucro_presumido' | 'lucro_real';

export type SimulationType = 'regime' | 'icms' | 'pis_cofins';

export type BenefitStatus = 'applied' | 'pending';

// ─── Simulation types ─────────────────────────────────────────────────────────

export interface SimulationInput {
  gross_revenue: number;
  costs: number;
  sector: string;
  region: string;
  simulation_type: SimulationType;
}

export interface RegimeOption {
  regime: TaxRegime;
  label: string;
  tax_amount: number;
  effective_rate: number;
}

export interface IcmsResult {
  state: string;
  rate: number;
  tax_amount: number;
}

export interface PisCofinsResult {
  pis_rate: number;
  cofins_rate: number;
  pis_amount: number;
  cofins_amount: number;
  total_amount: number;
}

export interface SimulationResult {
  simulation_type: SimulationType;
  gross_revenue: number;
  costs: number;
  sector: string;
  region: string;
  regime_options?: RegimeOption[];
  icms_result?: IcmsResult;
  pis_cofins_result?: PisCofinsResult;
  // Only for intermediario/premium
  ai_recommendation?: string;
  recommended_regime?: TaxRegime;
}

// ─── Chat types ───────────────────────────────────────────────────────────────

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface ChatSession {
  id: string;
  messages: ChatMessage[];
  messages_used: number;
  messages_limit: number | null; // null = unlimited (premium)
  created_at: string;
}

export interface SendMessagePayload {
  session_id?: string;
  message: string;
}

export interface SendMessageResponse {
  session_id: string;
  user_message: ChatMessage;
  assistant_message: ChatMessage;
  messages_used: number;
  messages_limit: number | null;
}

// ─── History types ────────────────────────────────────────────────────────────

export interface SavedSimulation {
  id: string;
  tenant_id: string;
  simulation_type: SimulationType;
  gross_revenue: number;
  costs: number;
  sector: string;
  region: string;
  result: SimulationResult;
  created_at: string;
}

// ─── Fiscal benefits ──────────────────────────────────────────────────────────

export interface FiscalBenefit {
  id: string;
  name: string;
  description: string;
  state: string;
  estimated_savings: number;
  status: BenefitStatus;
  regime: TaxRegime | 'all';
}

// ─── Plan info ────────────────────────────────────────────────────────────────

export interface PlanInfo {
  slug: SubscriptionPlan;
  label: string;
  price: number | null;
  features: string[];
}

export const PLAN_INFO: Record<SubscriptionPlan, PlanInfo> = {
  free: {
    slug: 'free',
    label: 'Gratuito',
    price: null,
    features: [
      'Calculadoras básicas (Regime, ICMS, PIS/COFINS)',
      'Resultados numéricos',
    ],
  },
  intermediario: {
    slug: 'intermediario',
    label: 'Intermediário',
    price: 79,
    features: [
      'Tudo do plano gratuito',
      'Recomendação por IA',
      'Chat assistente (20 mensagens/mês)',
    ],
  },
  premium: {
    slug: 'premium',
    label: 'Premium',
    price: 199,
    features: [
      'Tudo do plano intermediário',
      'IA avançada sem limites',
      'Chat ilimitado',
      'Exportar PDF',
      'Benefícios fiscais por estado',
    ],
  },
};

export function planHasAI(plan: SubscriptionPlan): boolean {
  return plan === 'intermediario' || plan === 'premium';
}

export function planHasChat(plan: SubscriptionPlan): boolean {
  return plan === 'intermediario' || plan === 'premium';
}

export function planHasPDF(plan: SubscriptionPlan): boolean {
  return plan === 'premium';
}

export function planHasBenefits(plan: SubscriptionPlan): boolean {
  return plan === 'premium';
}

// ─── Keys ─────────────────────────────────────────────────────────────────────

const calculatorKey = ['calculator'] as const;

// ─── Hooks ───────────────────────────────────────────────────────────────────

export function useSimulate() {
  return useMutation({
    mutationFn: async (input: SimulationInput): Promise<SimulationResult> => {
      const { data } = await api.post<SimulationResult>('/api/v1/calculator/simulate', input);
      return data;
    },
  });
}

export function useSaveSimulation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (result: SimulationResult): Promise<SavedSimulation> => {
      const { data } = await api.post<SavedSimulation>('/api/v1/calculator/simulations', result);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [...calculatorKey, 'history'] });
    },
  });
}

export function useSimulationHistory() {
  return useQuery({
    queryKey: [...calculatorKey, 'history'],
    queryFn: async (): Promise<SavedSimulation[]> => {
      const { data } = await api.get<SavedSimulation[]>('/api/v1/calculator/simulations');
      return data;
    },
  });
}

export function useSendChatMessage() {
  return useMutation({
    mutationFn: async (payload: SendMessagePayload): Promise<SendMessageResponse> => {
      const { data } = await api.post<SendMessageResponse>('/api/v1/calculator/chat', payload);
      return data;
    },
  });
}

export function useFiscalBenefits() {
  return useQuery({
    queryKey: [...calculatorKey, 'benefits'],
    queryFn: async (): Promise<FiscalBenefit[]> => {
      const { data } = await api.get<FiscalBenefit[]>('/api/v1/calculator/benefits');
      return data;
    },
  });
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

export const SECTORS = [
  { value: 'comercio', label: 'Comércio' },
  { value: 'industria', label: 'Indústria' },
  { value: 'servicos', label: 'Serviços' },
  { value: 'tecnologia', label: 'Tecnologia' },
  { value: 'saude', label: 'Saúde' },
  { value: 'educacao', label: 'Educação' },
  { value: 'construcao', label: 'Construção Civil' },
  { value: 'agronegocio', label: 'Agronegócio' },
  { value: 'transporte', label: 'Transporte' },
  { value: 'outros', label: 'Outros' },
];

export const REGIONS = [
  { value: 'AC', label: 'Acre' },
  { value: 'AL', label: 'Alagoas' },
  { value: 'AM', label: 'Amazonas' },
  { value: 'BA', label: 'Bahia' },
  { value: 'CE', label: 'Ceará' },
  { value: 'DF', label: 'Distrito Federal' },
  { value: 'ES', label: 'Espírito Santo' },
  { value: 'GO', label: 'Goiás' },
  { value: 'MA', label: 'Maranhão' },
  { value: 'MG', label: 'Minas Gerais' },
  { value: 'MS', label: 'Mato Grosso do Sul' },
  { value: 'MT', label: 'Mato Grosso' },
  { value: 'PA', label: 'Pará' },
  { value: 'PB', label: 'Paraíba' },
  { value: 'PE', label: 'Pernambuco' },
  { value: 'PI', label: 'Piauí' },
  { value: 'PR', label: 'Paraná' },
  { value: 'RJ', label: 'Rio de Janeiro' },
  { value: 'RN', label: 'Rio Grande do Norte' },
  { value: 'RO', label: 'Rondônia' },
  { value: 'RR', label: 'Roraima' },
  { value: 'RS', label: 'Rio Grande do Sul' },
  { value: 'SC', label: 'Santa Catarina' },
  { value: 'SE', label: 'Sergipe' },
  { value: 'SP', label: 'São Paulo' },
  { value: 'TO', label: 'Tocantins' },
];

export const REGIME_LABELS: Record<TaxRegime, string> = {
  simples_nacional: 'Simples Nacional',
  lucro_presumido: 'Lucro Presumido',
  lucro_real: 'Lucro Real',
};

export function moneyBRL(value: number): string {
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

export function percentBR(value: number): string {
  return `${value.toFixed(2).replace('.', ',')}%`;
}
