import { useState } from 'react';
import {
  Globe, Upload, FileText, CheckCircle2, Clock,
  AlertTriangle, Coins, Bell, Eye,
} from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { MetricCard } from '@/components/ui/OperationalStates';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { FeatureGate } from '@/components/ui/FeatureGate';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

// Mock portal data — what the client can see
const PORTAL_TABS = [
  { key: 'overview', label: 'Visão Geral', icon: Globe },
  { key: 'documents', label: 'Documentos', icon: FileText },
  { key: 'guides', label: 'Guias', icon: Coins },
  { key: 'pending', label: 'Pendências', icon: Bell },
] as const;

type PortalTab = typeof PORTAL_TABS[number]['key'];

const MOCK_PORTAL = {
  clientName: 'Tech Solutions Ltda',
  cnpj: '12.345.678/0001-90',
  closingStatus: 'in_progress' as const,
  closingScore: 65,
  pendingDocuments: 3,
  pendingActions: 2,
  guides: [
    { id: 'g1', type: 'DAS Simples Nacional', competence: 'Mai/2026', value: 1240.00, due: '2026-06-20', status: 'awaiting_payment' as const },
    { id: 'g2', type: 'DAS Simples Nacional', competence: 'Abr/2026', value: 1180.50, due: '2026-05-20', status: 'paid' as const },
  ],
  documents: [
    { id: 'd1', name: 'Extrato bancário Maio/2026', status: 'pending', requestedAt: '2026-05-15', uploadedAt: null },
    { id: 'd2', name: 'Fatura de serviços', status: 'received', requestedAt: '2026-05-10', uploadedAt: '2026-05-12' },
    { id: 'd3', name: 'Comprovante DAS Abril', status: 'received', requestedAt: '2026-05-01', uploadedAt: '2026-05-03' },
  ],
  pendencies: [
    { id: 'p1', title: 'Enviar extrato bancário', deadline: '2026-05-28', status: 'open' },
    { id: 'p2', title: 'Confirmar dados do sócio administrador', deadline: '2026-05-30', status: 'open' },
  ],
};

export function PortalClientePage() {
  const [activeTab, setActiveTab] = useState<PortalTab>('overview');
  const [uploadingDoc, setUploadingDoc] = useState<string | null>(null);

  const handleUpload = async (docId: string) => {
    setUploadingDoc(docId);
    await new Promise(r => setTimeout(r, 1500));
    setUploadingDoc(null);
    toast.success('Documento enviado com sucesso!');
  };

  return (
    <FeatureGate feature="feature_portal_client">
      <div className="space-y-6 p-6">
        <PageHeader
          title="Portal do Cliente"
          subtitle="Visualize o portal como seus clientes o veem. Gerencie solicitações e documentos."
          icon={<Globe className="h-5 w-5" />}
        />

        {/* Client preview banner */}
        <div className="flex items-center justify-between rounded-xl border border-primary/30 bg-primary/5 p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/20 text-primary font-bold text-sm">
              TS
            </div>
            <div>
              <p className="text-sm font-semibold text-foreground">{MOCK_PORTAL.clientName}</p>
              <p className="text-xs text-muted-foreground">{MOCK_PORTAL.cnpj}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-primary/20 px-2.5 py-1 text-xs font-medium text-primary">Modo preview</span>
            <button
              onClick={() => toast.info('Link do portal do cliente disponível em breve.')}
              className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              <Eye className="h-3.5 w-3.5" />
              Ver link do portal
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 overflow-x-auto border-b border-border">
          {PORTAL_TABS.map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={cn(
                'flex items-center gap-1.5 whitespace-nowrap px-4 py-2.5 text-sm font-medium border-b-2 transition-colors',
                activeTab === tab.key
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground',
              )}
            >
              <tab.icon className="h-3.5 w-3.5" />
              {tab.label}
              {tab.key === 'pending' && MOCK_PORTAL.pendencies.length > 0 && (
                <span className="ml-1 rounded-full bg-red-500/20 px-1.5 text-[10px] font-bold text-red-400">
                  {MOCK_PORTAL.pendencies.length}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Tab: Overview */}
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <MetricCard title="Fechamento" value={`${MOCK_PORTAL.closingScore}%`} icon={<CheckCircle2 className="h-4 w-4" />} variant="warning" subtitle="Em andamento" />
              <MetricCard title="Documentos pendentes" value={MOCK_PORTAL.pendingDocuments} icon={<FileText className="h-4 w-4" />} variant="warning" />
              <MetricCard title="Ações necessárias" value={MOCK_PORTAL.pendingActions} icon={<Bell className="h-4 w-4" />} variant="danger" />
              <MetricCard title="Guias em aberto" value="1" icon={<Coins className="h-4 w-4" />} variant="warning" />
            </div>

            <div className="rounded-xl border border-border bg-card p-5">
              <h3 className="mb-3 text-sm font-semibold text-foreground">Situação do fechamento — Mai/2026</h3>
              <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-yellow-500 transition-all"
                  style={{ width: `${MOCK_PORTAL.closingScore}%` }}
                />
              </div>
              <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
                <span>{MOCK_PORTAL.closingScore}% concluído</span>
                <StatusBadge status={MOCK_PORTAL.closingStatus} />
              </div>
            </div>
          </div>
        )}

        {/* Tab: Documents */}
        {activeTab === 'documents' && (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">Documentos solicitados pelo seu contador.</p>
            {MOCK_PORTAL.documents.map(doc => (
              <div key={doc.id} className="flex items-center gap-3 rounded-lg border border-border bg-card p-4">
                <div className={cn(
                  'flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
                  doc.status === 'received' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-orange-500/10 text-orange-400',
                )}>
                  {doc.status === 'received' ? <CheckCircle2 className="h-4 w-4" /> : <Clock className="h-4 w-4" />}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-foreground">{doc.name}</p>
                  <p className="text-xs text-muted-foreground">
                    Solicitado em {new Date(doc.requestedAt).toLocaleDateString('pt-BR')}
                    {doc.uploadedAt && ` · Recebido em ${new Date(doc.uploadedAt).toLocaleDateString('pt-BR')}`}
                  </p>
                </div>
                {doc.status === 'pending' && (
                  <button
                    onClick={() => handleUpload(doc.id)}
                    disabled={uploadingDoc === doc.id}
                    className="flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-50"
                  >
                    <Upload className="h-3.5 w-3.5" />
                    {uploadingDoc === doc.id ? 'Enviando...' : 'Enviar'}
                  </button>
                )}
                {doc.status === 'received' && (
                  <span className="text-xs text-emerald-400 font-medium">Recebido</span>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Tab: Guides */}
        {activeTab === 'guides' && (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">Guias de pagamento geradas pelo seu contador.</p>
            {MOCK_PORTAL.guides.map(guide => (
              <div key={guide.id} className="flex items-center gap-3 rounded-lg border border-border bg-card p-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium text-foreground">{guide.type}</p>
                    <StatusBadge status={guide.status} />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {guide.competence} · Vencimento: {new Date(guide.due).toLocaleDateString('pt-BR')}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold tabular-nums text-foreground">
                    {guide.value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                  </p>
                  <div className="mt-1 flex gap-2 justify-end">
                    <button
                      onClick={() => toast.info('Download da guia disponível em breve.')}
                      className="text-xs text-primary hover:underline"
                    >
                      Baixar guia
                    </button>
                    {guide.status !== 'paid' && (
                      <button
                        onClick={() => toast.info('Envio de comprovante disponível em breve.')}
                        className="text-xs text-primary hover:underline"
                      >
                        Anexar comprovante
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Tab: Pending */}
        {activeTab === 'pending' && (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">Ações que você precisa tomar para que seu contador finalize o fechamento.</p>
            {MOCK_PORTAL.pendencies.map(p => (
              <div key={p.id} className="flex items-center gap-3 rounded-lg border border-orange-500/20 bg-orange-500/5 p-4">
                <AlertTriangle className="h-4 w-4 shrink-0 text-orange-400" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-foreground">{p.title}</p>
                  <p className="text-xs text-muted-foreground">
                    Prazo: {new Date(p.deadline).toLocaleDateString('pt-BR')}
                  </p>
                </div>
                <button
                  onClick={() => toast.info(`Resolução de "${p.title}" disponível em breve.`)}
                  className="rounded-lg bg-orange-600/20 px-3 py-1.5 text-xs font-medium text-orange-400 hover:bg-orange-600/30 transition-colors"
                >
                  Resolver
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </FeatureGate>
  );
}
