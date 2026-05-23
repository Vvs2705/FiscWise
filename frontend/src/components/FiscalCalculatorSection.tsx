import { useState } from 'react';
import { CalculatorSimulator } from './CalculatorSimulator';
import { FiscalChat } from './FiscalChat';
import { SimulationHistory } from './SimulationHistory';

interface Props {
  userPlan?: 'FREE' | 'INTERMEDIARIO' | 'PREMIUM';
}

export function FiscalCalculatorSection({ userPlan = 'FREE' }: Props = {}) {
  const [activeTab, setActiveTab] = useState<'simulator' | 'chat' | 'history'>('simulator');

  const tabs = [
    { id: 'simulator', label: '📊 Simulador', icon: '📊' },
    { id: 'chat', label: '🤖 Chat IA', icon: '🤖' },
    { id: 'history', label: '📋 Histórico', icon: '📋' },
  ];

  return (
    <section className="w-full max-w-4xl mx-auto text-foreground">
      <div className="mb-6">
        <h2 className="text-3xl font-bold text-foreground mb-2">
          Calculadora Fiscal com IA
        </h2>
        <p className="text-muted-foreground">
          Simule diferentes regimes tributários e receba recomendações personalizadas
        </p>
      </div>

      <div className="bg-card text-card-foreground rounded-lg border border-border shadow-lg overflow-hidden">
        <div className="border-b border-border flex">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`flex-1 py-4 px-4 font-medium text-center transition ${
                activeTab === tab.id
                  ? 'bg-primary text-primary-foreground border-b-4 border-primary-foreground/30'
                  : 'bg-muted/40 text-muted-foreground hover:bg-muted/80'
              }`}
            >
              <span className="mr-2">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>

        <div className="p-6 bg-card text-card-foreground">
          {activeTab === 'simulator' && (
            <CalculatorSimulator userPlan={userPlan} />
          )}

          {activeTab === 'chat' && (
            <FiscalChat userPlan={userPlan} />
          )}

          {activeTab === 'history' && (
            <SimulationHistory />
          )}
        </div>
      </div>

      <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-950/20 rounded-lg border border-blue-200 dark:border-blue-900/50">
        <div className="flex items-start">
          <span className="text-2xl mr-3">💡</span>
          <div className="text-sm text-blue-900 dark:text-blue-200">
            <strong>Dica:</strong> A Calculadora Fiscal usa IA para analisar seu regime tributário
            e sugerir otimizações. Quanto mais detalhes você fornecer, melhor serão as recomendações.
          </div>
        </div>
      </div>
    </section>
  );
}
