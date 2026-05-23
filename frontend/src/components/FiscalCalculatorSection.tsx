import React, { useState } from 'react';
import { CalculatorSimulator } from './CalculatorSimulator';
import { FiscalChat } from './FiscalChat';
import { SimulationHistory } from './SimulationHistory';

export function FiscalCalculatorSection({ userPlan = 'FREE' }) {
  const [activeTab, setActiveTab] = useState<'simulator' | 'chat' | 'history'>('simulator');

  const tabs = [
    { id: 'simulator', label: '📊 Simulador', icon: '📊' },
    { id: 'chat', label: '🤖 Chat IA', icon: '🤖' },
    { id: 'history', label: '📋 Histórico', icon: '📋' },
  ];

  return (
    <section className="w-full max-w-4xl mx-auto">
      <div className="mb-6">
        <h2 className="text-3xl font-bold text-gray-900 mb-2">
          Calculadora Fiscal com IA
        </h2>
        <p className="text-gray-600">
          Simule diferentes regimes tributários e receba recomendações personalizadas
        </p>
      </div>

      <div className="bg-white rounded-lg shadow-lg overflow-hidden">
        <div className="border-b flex">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`flex-1 py-4 px-4 font-medium text-center transition ${
                activeTab === tab.id
                  ? 'bg-blue-600 text-white border-b-4 border-blue-700'
                  : 'bg-gray-50 text-gray-700 hover:bg-gray-100'
              }`}
            >
              <span className="mr-2">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>

        <div className="p-6">
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

      <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
        <div className="flex items-start">
          <span className="text-2xl mr-3">💡</span>
          <div className="text-sm text-blue-900">
            <strong>Dica:</strong> A Calculadora Fiscal usa IA para analisar seu regime tributário
            e sugerir otimizações. Quanto mais detalhes você fornecer, melhor serão as recomendações.
          </div>
        </div>
      </div>
    </section>
  );
}
