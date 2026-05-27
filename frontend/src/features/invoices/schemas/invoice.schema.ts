import { z } from 'zod';

export const issuerSchema = z.object({
  cnpj: z.string().min(14, 'CNPJ deve ter pelo menos 14 dígitos').max(18, 'CNPJ muito longo'),
  inscricao_municipal: z.string().optional(),
  regime_tributario: z.string().min(1, 'Selecione o regime tributário'),
  municipio_ibge: z.string().min(7, 'Código IBGE do município é obrigatório (7 dígitos)'),
  cod_servico_lc116: z.string().optional(),
  aliquota_iss: z.preprocess(
    (val) => (val === '' ? undefined : Number(val)),
    z.number().min(0, 'Alíquota deve ser positiva').max(100, 'Alíquota máxima de 100%').optional()
  ),
  retencao_iss: z.boolean().default(false),
});

export const invoiceSchema = z.object({
  issuer_id: z.string().uuid('Selecione um emissor válido'),
  client_id: z.preprocess(
    (val) => (val === '' ? undefined : val),
    z.string().uuid('Selecione um cliente válido').optional()
  ),
  valor_servico: z.preprocess(
    (val) => (typeof val === 'string' ? parseFloat(val.replace(/[^\d,.-]/g, '').replace(',', '.')) : val),
    z.number().positive('O valor do serviço deve ser maior que zero')
  ),
  valor_deducoes: z.preprocess(
    (val) => (val === '' || val === undefined ? 0 : typeof val === 'string' ? parseFloat(val.replace(/[^\d,.-]/g, '').replace(',', '.')) : val),
    z.number().min(0, 'Valor de deduções deve ser positivo').optional()
  ),
  valor_iss: z.preprocess(
    (val) => (val === '' || val === undefined ? undefined : typeof val === 'string' ? parseFloat(val.replace(/[^\d,.-]/g, '').replace(',', '.')) : val),
    z.number().min(0, 'Valor do ISS deve ser positivo').optional()
  ),
  descricao_servico: z.string().min(5, 'A descrição deve ter pelo menos 5 caracteres'),
  competencia: z.string().min(1, 'Selecione a competência (mês de referência)'),
  tomador_nome: z.string().min(2, 'Nome do tomador é obrigatório'),
  tomador_cpf_cnpj: z.string().min(11, 'CPF ou CNPJ inválido'),
  tomador_email: z.string().email('E-mail inválido').optional().or(z.literal('')),
  tomador_municipio_ibge: z.string().min(7, 'Código IBGE do município do tomador é obrigatório (7 dígitos)'),
});
