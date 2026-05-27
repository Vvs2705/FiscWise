import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { invoiceSchema } from '../schemas/invoice.schema';
import { useCreateInvoice, useIssuers } from '../hooks/useInvoices';
import { FormField } from '@/components/ui/FormField';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { ArrowLeft, Save } from 'lucide-react';
import { useClients } from '@/lib/hooks/useOperations';
import toast from 'react-hot-toast';
import { formatCurrencyBRL, parseCurrencyBRL } from '@/lib/utils';

type FormValues = {
  issuer_id: string;
  client_id?: string;
  valor_servico: string;
  valor_deducoes: string;
  valor_iss: string;
  descricao_servico: string;
  competencia: string;
  tomador_nome: string;
  tomador_cpf_cnpj: string;
  tomador_email: string;
  tomador_municipio_ibge: string;
};

export function InvoiceNewPage() {
  const navigate = useNavigate();
  const createInvoice = useCreateInvoice();
  const { data: issuers } = useIssuers();
  const { data: clients } = useClients();

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(invoiceSchema),
    defaultValues: {
      issuer_id: '',
      client_id: '',
      valor_servico: '',
      valor_deducoes: '0',
      valor_iss: '',
      descricao_servico: '',
      competencia: new Date().toISOString().split('T')[0],
      tomador_nome: '',
      tomador_cpf_cnpj: '',
      tomador_email: '',
      tomador_municipio_ibge: '',
    },
  });

  const selectedClientId = watch('client_id');

  // Autofill fields when client is selected
  useEffect(() => {
    if (selectedClientId && clients) {
      const client = clients.find((c) => c.id === selectedClientId);
      if (client) {
        setValue('tomador_nome', client.name);
        setValue('tomador_cpf_cnpj', client.document || '');
        setValue('tomador_email', client.email || '');
        // Autofill IBGE code if available in backend-evolved fields
        const extendedClient = client as unknown as { municipio_ibge?: string };
        if (extendedClient.municipio_ibge) {
          setValue('tomador_municipio_ibge', extendedClient.municipio_ibge);
        } else {
          setValue('tomador_municipio_ibge', '');
        }
      }
    }
  }, [selectedClientId, clients, setValue]);

  // Set default issuer if available
  useEffect(() => {
    if (issuers && issuers.length > 0) {
      setValue('issuer_id', issuers[0].id);
    }
  }, [issuers, setValue]);

  const onSubmit = async (data: FormValues) => {
    try {
      const valServico = parseCurrencyBRL(data.valor_servico);
      const valDeducoes = parseCurrencyBRL(data.valor_deducoes) || 0;
      const valIss = data.valor_iss ? parseCurrencyBRL(data.valor_iss) : undefined;

      const response = await createInvoice.mutateAsync({
        issuer_id: data.issuer_id,
        client_id: data.client_id || undefined,
        valor_servico: valServico,
        valor_deducoes: valDeducoes,
        valor_iss: valIss,
        descricao_servico: data.descricao_servico,
        competencia: data.competencia,
        tomador_nome: data.tomador_nome,
        tomador_cpf_cnpj: data.tomador_cpf_cnpj.replace(/\D/g, ''),
        tomador_email: data.tomador_email || undefined,
        tomador_municipio_ibge: data.tomador_municipio_ibge,
      });

      toast.success('Rascunho de nota fiscal criado com sucesso!');
      navigate(`/notas-fiscais/${response.id}`);
    } catch (err) {
      console.error(err);
      toast.error('Erro ao gerar nota fiscal.');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" onClick={() => navigate('/notas-fiscais')}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Voltar para a Lista
        </Button>
      </div>

      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Criar Rascunho de NFS-e
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Gere um rascunho e revise todas as informações tributárias antes de emitir
        </p>
      </div>

      <Card className="border-border/60 bg-card">
        <CardContent className="p-6">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            <div className="grid gap-6 md:grid-cols-2">
              <FormField label="Emissor (Minha Firma)" htmlFor="issuer_id" error={errors.issuer_id?.message}>
                <Select id="issuer_id" {...register('issuer_id')}>
                  <option value="">Selecione o emissor</option>
                  {issuers?.map((i) => (
                    <option key={i.id} value={i.id}>
                      CNPJ: {i.cnpj} {i.regime_tributario}
                    </option>
                  ))}
                </Select>
              </FormField>

              <FormField label="Cliente FiscWise (Autocomplete)" htmlFor="client_id" error={errors.client_id?.message}>
                <Select id="client_id" {...register('client_id')}>
                  <option value="">Selecione um cliente cadastrado</option>
                  {clients?.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </Select>
              </FormField>
            </div>

            <div className="border-t border-border/40 pt-4">
              <h3 className="text-sm font-semibold text-foreground uppercase tracking-wider mb-4">
                Dados do Tomador
              </h3>
              <div className="grid gap-4 sm:grid-cols-2">
                <FormField label="Nome / Razão Social" htmlFor="tomador_nome" error={errors.tomador_nome?.message}>
                  <Input type="text" id="tomador_nome" {...register('tomador_nome')} />
                </FormField>

                <FormField label="CPF / CNPJ" htmlFor="tomador_cpf_cnpj" error={errors.tomador_cpf_cnpj?.message}>
                  <Input type="text" id="tomador_cpf_cnpj" {...register('tomador_cpf_cnpj')} />
                </FormField>

                <FormField label="E-mail (Para envio do PDF/XML)" htmlFor="tomador_email" error={errors.tomador_email?.message}>
                  <Input type="text" id="tomador_email" placeholder="cliente@email.com" {...register('tomador_email')} />
                </FormField>

                <FormField label="Código IBGE Município Tomador" htmlFor="tomador_municipio_ibge" error={errors.tomador_municipio_ibge?.message}>
                  <Input type="text" id="tomador_municipio_ibge" placeholder="3550308" maxLength={7} {...register('tomador_municipio_ibge')} />
                </FormField>
              </div>
            </div>

            <div className="border-t border-border/40 pt-4">
              <h3 className="text-sm font-semibold text-foreground uppercase tracking-wider mb-4">
                Serviço e Valores
              </h3>
              <div className="grid gap-4 sm:grid-cols-3">
                <FormField label="Competência (Mês Referência)" htmlFor="competencia" error={errors.competencia?.message}>
                  <Input type="date" id="competencia" {...register('competencia')} />
                </FormField>

                <FormField label="Valor do Serviço (R$)" htmlFor="valor_servico" error={errors.valor_servico?.message}>
                  <Input
                    type="text"
                    id="valor_servico"
                    placeholder="1.500,00"
                    {...register('valor_servico', {
                      onChange: (e) => {
                        e.target.value = formatCurrencyBRL(e.target.value);
                      },
                    })}
                  />
                </FormField>

                <FormField label="Deduções (R$)" htmlFor="valor_deducoes" error={errors.valor_deducoes?.message}>
                  <Input
                    type="text"
                    id="valor_deducoes"
                    placeholder="0,00"
                    {...register('valor_deducoes', {
                      onChange: (e) => {
                        e.target.value = formatCurrencyBRL(e.target.value);
                      },
                    })}
                  />
                </FormField>
              </div>

              <div className="mt-4">
                <FormField label="Descrição do Serviço Prestado" htmlFor="descricao_servico" error={errors.descricao_servico?.message}>
                  <textarea
                    id="descricao_servico"
                    rows={4}
                    className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                    placeholder="Descreva detalhadamente o serviço prestado..."
                    {...register('descricao_servico')}
                  />
                </FormField>
              </div>
            </div>

            <div className="flex justify-end gap-3 border-t border-border/40 pt-4">
              <Button type="button" variant="outline" disabled={isSubmitting} onClick={() => navigate('/notas-fiscais')}>
                Cancelar
              </Button>
              <Button type="submit" disabled={isSubmitting} className="flex items-center gap-2">
                <Save className="h-4 w-4" />
                {isSubmitting ? 'Gerando...' : 'Salvar Rascunho'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
export default InvoiceNewPage;
