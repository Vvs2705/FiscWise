import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@/lib/hooks/useAuth';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';

export function RegisterPage() {
  const { register, isLoading } = useAuth();
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    company_name: '',
    owner_email: '',
    owner_password: '',
    owner_full_name: '',
    plan_slug: 'free',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (step < 3) {
      setStep(step + 1);
    } else {
      await register(formData);
    }
  };

  const handleBack = () => {
    if (step > 1) setStep(step - 1);
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <CardTitle className="text-3xl font-bold text-center">Criar Conta</CardTitle>
          <CardDescription className="text-center">
            Passo {step} de 3
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {step === 1 && (
              <div className="space-y-4">
                <div className="space-y-2">
                  <label htmlFor="company_name" className="text-sm font-medium">
                    Nome da Empresa
                  </label>
                  <Input
                    id="company_name"
                    type="text"
                    placeholder="Minha Empresa Ltda"
                    value={formData.company_name}
                    onChange={(e) => setFormData({ ...formData, company_name: e.target.value })}
                    required
                  />
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="space-y-4">
                <div className="space-y-2">
                  <label htmlFor="owner_full_name" className="text-sm font-medium">
                    Nome Completo
                  </label>
                  <Input
                    id="owner_full_name"
                    type="text"
                    placeholder="João Silva"
                    value={formData.owner_full_name}
                    onChange={(e) => setFormData({ ...formData, owner_full_name: e.target.value })}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <label htmlFor="owner_email" className="text-sm font-medium">
                    Email
                  </label>
                  <Input
                    id="owner_email"
                    type="email"
                    placeholder="joao@empresa.com"
                    value={formData.owner_email}
                    onChange={(e) => setFormData({ ...formData, owner_email: e.target.value })}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <label htmlFor="owner_password" className="text-sm font-medium">
                    Senha
                  </label>
                  <Input
                    id="owner_password"
                    type="password"
                    placeholder="••••••••"
                    value={formData.owner_password}
                    onChange={(e) => setFormData({ ...formData, owner_password: e.target.value })}
                    required
                  />
                </div>
              </div>
            )}

            {step === 3 && (
              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Escolha seu Plano</label>
                  <div className="space-y-2">
                    <label className="flex items-center space-x-3 border rounded-lg p-4 cursor-pointer hover:bg-accent">
                      <input
                        type="radio"
                        name="plan"
                        value="free"
                        checked={formData.plan_slug === 'free'}
                        onChange={(e) => setFormData({ ...formData, plan_slug: e.target.value })}
                      />
                      <div>
                        <div className="font-medium">Free</div>
                        <div className="text-sm text-muted-foreground">Grátis - 10.000 tokens/mês</div>
                      </div>
                    </label>
                    <label className="flex items-center space-x-3 border rounded-lg p-4 cursor-pointer hover:bg-accent">
                      <input
                        type="radio"
                        name="plan"
                        value="starter"
                        checked={formData.plan_slug === 'starter'}
                        onChange={(e) => setFormData({ ...formData, plan_slug: e.target.value })}
                      />
                      <div>
                        <div className="font-medium">Starter</div>
                        <div className="text-sm text-muted-foreground">R$ 49/mês - 100.000 tokens/mês</div>
                      </div>
                    </label>
                    <label className="flex items-center space-x-3 border rounded-lg p-4 cursor-pointer hover:bg-accent">
                      <input
                        type="radio"
                        name="plan"
                        value="pro"
                        checked={formData.plan_slug === 'pro'}
                        onChange={(e) => setFormData({ ...formData, plan_slug: e.target.value })}
                      />
                      <div>
                        <div className="font-medium">Pro</div>
                        <div className="text-sm text-muted-foreground">R$ 149/mês - 500.000 tokens/mês</div>
                      </div>
                    </label>
                  </div>
                </div>
              </div>
            )}

            <div className="flex gap-2">
              {step > 1 && (
                <Button type="button" variant="outline" onClick={handleBack} className="flex-1">
                  Voltar
                </Button>
              )}
              <Button type="submit" className="flex-1" disabled={isLoading}>
                {step === 3 ? (isLoading ? 'Criando...' : 'Criar Conta') : 'Próximo'}
              </Button>
            </div>
          </form>
          <div className="mt-4 text-center text-sm">
            <span className="text-muted-foreground">Já tem uma conta? </span>
            <Link to="/login" className="text-primary hover:underline">
              Fazer login
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
