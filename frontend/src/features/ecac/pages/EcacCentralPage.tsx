import { useState } from 'react';
import { ProxiesListPage } from './ProxiesListPage';
import { FiscalSituationPage } from './FiscalSituationPage';
import { ShieldCheck, FileText, ClipboardList } from 'lucide-react';

export function EcacCentralPage() {
  const [activeTab, setActiveTab] = useState<'proxies' | 'situation'>('proxies');

  return (
    <div className="space-y-6">
      <div className="border-b border-border/40 pb-2">
        <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
          <ShieldCheck className="h-6 w-6 text-primary" />
          Central e-CAC Receita Federal
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Acompanhe pendências cadastrais, débitos e procurações de forma consolidada
        </p>
      </div>

      {/* Tabs list */}
      <div className="flex gap-2 border-b border-border/40">
        <button
          onClick={() => setActiveTab('proxies')}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-semibold border-b-2 transition-all ${
            activeTab === 'proxies'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <ClipboardList className="h-4 w-4" />
          Procurações Fiscais
        </button>

        <button
          onClick={() => setActiveTab('situation')}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-semibold border-b-2 transition-all ${
            activeTab === 'situation'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <FileText className="h-4 w-4" />
          Situação Fiscal Federal
        </button>
      </div>

      {/* Tab content */}
      <div className="mt-4">
        {activeTab === 'proxies' ? <ProxiesListPage /> : <FiscalSituationPage />}
      </div>
    </div>
  );
}
export default EcacCentralPage;
