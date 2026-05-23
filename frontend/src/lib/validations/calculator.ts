export const simulationSchema = {
  monthly_revenue: {
    min: 0,
    max: 999999999,
    label: 'Receita Mensal (R$)',
  },
  annual_cogs: {
    min: 0,
    max: 999999999,
    label: 'Custo Anual (R$)',
  },
  state: {
    label: 'Estado',
    options: [
      'SP', 'RJ', 'MG', 'BA', 'SC', 'RS', 'PR', 'PE', 'CE', 'PA',
      'GO', 'PB', 'MA', 'ES', 'PI', 'RN', 'AL', 'MT', 'MS', 'DF',
      'RO', 'AC', 'AM', 'RR', 'AP', 'TO'
    ],
  },
  regime: {
    label: 'Regime Tributário',
    options: ['simples', 'lucro_presumido', 'lucro_real'],
  },
};

type SimulationValidationData = {
  monthly_revenue?: number;
  annual_cogs?: number;
  state?: string;
  regime?: string;
};

export const validateSimulation = (data: SimulationValidationData) => {
  const errors: Record<string, string> = {};

  if (!data.monthly_revenue || data.monthly_revenue < 0) {
    errors.monthly_revenue = 'Receita mensal deve ser maior que 0';
  }

  if ((data.annual_cogs ?? 0) < 0) {
    errors.annual_cogs = 'Custo anual não pode ser negativo';
  }

  if (!data.state) {
    errors.state = 'Selecione um estado';
  }

  if (!data.regime) {
    errors.regime = 'Selecione um regime tributário';
  }

  return {
    isValid: Object.keys(errors).length === 0,
    errors,
  };
};
