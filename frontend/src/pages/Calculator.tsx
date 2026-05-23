import { useEffect, useState } from 'react';
import { FiscalCalculatorSection } from '../components/FiscalCalculatorSection';
import { fetchTenant } from '../lib/auth';

export function CalculatorPage() {
  const [userPlan, setUserPlan] = useState<'FREE' | 'INTERMEDIARIO' | 'PREMIUM'>('FREE');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchUserPlan = async () => {
      try {
        const tenant = await fetchTenant();
        const plan = (tenant.plan_slug || 'FREE').toUpperCase() as 'FREE' | 'INTERMEDIARIO' | 'PREMIUM';
        setUserPlan(plan);
      } catch (err) {
        console.error('Erro ao buscar plano do usuário:', err);
        setUserPlan('FREE');
      } finally {
        setLoading(false);
      }
    };

    fetchUserPlan();
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center min-h-screen">Carregando...</div>;
  }

  return (
    <div className="min-h-screen bg-background py-8 px-4 text-foreground">
      <FiscalCalculatorSection userPlan={userPlan} />

      <div className="mt-12 max-w-4xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-card p-6 rounded-lg border border-border shadow-sm">
            <div className="text-3xl mb-2">🎯</div>
            <h3 className="font-semibold text-foreground mb-2">Simulação Rápida</h3>
            <p className="text-sm text-muted-foreground">
              Compare diferentes regimes tributários em segundos
            </p>
          </div>

          <div className="bg-card p-6 rounded-lg border border-border shadow-sm">
            <div className="text-3xl mb-2">🤖</div>
            <h3 className="font-semibold text-foreground mb-2">IA Especializada</h3>
            <p className="text-sm text-muted-foreground">
              Receba recomendações personalizadas do assistente fiscal
            </p>
          </div>

          <div className="bg-card p-6 rounded-lg border border-border shadow-sm">
            <div className="text-3xl mb-2">📈</div>
            <h3 className="font-semibold text-foreground mb-2">Economia Garantida</h3>
            <p className="text-sm text-muted-foreground">
              Descubra quanto você pode economizar em impostos
            </p>
          </div>
        </div>
      </div>
    </div>
  );

}

export default CalculatorPage;
