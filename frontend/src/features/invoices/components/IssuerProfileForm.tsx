import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { issuerSchema } from '../schemas/invoice.schema';
import { useCreateIssuer } from '../hooks/useInvoices';
import { FormField } from '@/components/ui/FormField';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Button } from '@/components/ui/Button';
import { Save } from 'lucide-react';
import toast from 'react-hot-toast';

interface IssuerProfileFormProps {
  onSuccess?: () => void;
}

type FormValues = {
  cnpj: string;
  inscricao_municipal: string;
  regime_tributario: string;
  municipio_ibge: string;
  cod_servico_lc116: string;
  aliquota_iss: string;
  retencao_iss: boolean;
};

export function IssuerProfileForm({ onSuccess }: IssuerProfileFormProps) {
  const createIssuer = useCreateIssuer();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(issuerSchema),
    defaultValues: {
      cnpj: '',
      inscricao_municipal: '',
      regime_tributario: 'simples_nacional',
      municipio_ibge: '',
      cod_servico_lc116: '',
      aliquota_iss: '',
      retencao_iss: false,
    },
  });

  const onSubmit = async (data: FormValues) => {
    try {
      await createIssuer.mutateAsync({
        cnpj: data.cnpj.replace(/\D/g, ''),
        inscricao_municipal: data.inscricao_municipal || undefined,
        regime_tributario: data.regime_tributario,
        municipio_ibge: data.municipio_ibge,
        cod_servico_lc116: data.cod_servico_lc116 || undefined,
        aliquota_iss: data.aliquota_iss ? parseFloat(data.aliquota_iss) / 100 : undefined,
        retencao_iss: data.retencao_iss,
      });
      toast.success('Perfil emissor configurado com sucesso!');
      onSuccess?.();
    } catch (err) {
      console.error(err);
      toast.error('Erro ao salvar perfil emissor.');
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <FormField label="CNPJ do Emissor" htmlFor="cnpj" error={errors.cnpj?.message}>
        <Input
          type="text"
          id="cnpj"
          placeholder="00.000.000/0000-00"
          {...register('cnpj')}
        />
      </FormField>

      <div className="grid grid-cols-2 gap-4">
        <FormField label="Inscrição Municipal" htmlFor="inscricao_municipal" error={errors.inscricao_municipal?.message}>
          <Input
            type="text"
            id="inscricao_municipal"
            placeholder="123456-7"
            {...register('inscricao_municipal')}
          />
        </FormField>

        <FormField label="Código IBGE Município" htmlFor="municipio_ibge" error={errors.municipio_ibge?.message}>
          <Input
            type="text"
            id="municipio_ibge"
            placeholder="3550308"
            maxLength={7}
            {...register('municipio_ibge')}
          />
        </FormField>
      </div>

      <FormField label="Regime Tributário" htmlFor="regime_tributario" error={errors.regime_tributario?.message}>
        <Select id="regime_tributario" {...register('regime_tributario')}>
          <option value="simples_nacional">Simples Nacional</option>
          <option value="mei">MEI</option>
          <option value="lucro_presumido">Lucro Presumido</option>
          <option value="lucro_real">Lucro Real</option>
        </Select>
      </FormField>

      <div className="grid grid-cols-2 gap-4">
        <FormField label="Cód. Serviço (LC 116)" htmlFor="cod_servico_lc116" error={errors.cod_servico_lc116?.message}>
          <Input
            type="text"
            id="cod_servico_lc116"
            placeholder="01.07"
            {...register('cod_servico_lc116')}
          />
        </FormField>

        <FormField label="Alíquota ISS (%)" htmlFor="aliquota_iss" error={errors.aliquota_iss?.message}>
          <Input
            type="text"
            id="aliquota_iss"
            placeholder="2.00"
            {...register('aliquota_iss')}
          />
        </FormField>
      </div>

      <div className="flex items-center gap-2 py-2">
        <input
          type="checkbox"
          id="retencao_iss"
          className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
          {...register('retencao_iss')}
        />
        <label htmlFor="retencao_iss" className="text-sm font-medium text-foreground">
          Reter ISS na Fonte
        </label>
      </div>

      <div className="flex justify-end pt-2">
        <Button type="submit" disabled={isSubmitting} className="flex items-center gap-2">
          <Save className="h-4 w-4" />
          {isSubmitting ? 'Salvando...' : 'Salvar Perfil'}
        </Button>
      </div>
    </form>
  );
}
