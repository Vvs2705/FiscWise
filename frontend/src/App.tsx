import React, { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { initTheme } from '@/lib/hooks/useTheme';

// Aplica o tema salvo antes do primeiro render para evitar flash
initTheme();

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { DashboardLayout } from '@/layouts/DashboardLayout';
import { CommandMenu } from '@/components/ui/CommandMenu';
import { RouteTitle } from '@/lib/RouteTitle';

// ─── Existing pages (lazy) ──────────────────────────────────────────────────
const LoginPage        = lazy(() => import('@/pages/LoginPage').then(m => ({ default: m.LoginPage })));
const RegisterPage     = lazy(() => import('@/pages/RegisterPage').then(m => ({ default: m.RegisterPage })));
const DashboardPage    = lazy(() => import('@/pages/DashboardPage').then(m => ({ default: m.DashboardPage })));
const ClientsPage      = lazy(() => import('@/pages/ClientsPage').then(m => ({ default: m.ClientsPage })));
const DocumentsPage    = lazy(() => import('@/pages/DocumentsPage').then(m => ({ default: m.DocumentsPage })));
const CertificatesPage = lazy(() => import('@/pages/CertificatesPage').then(m => ({ default: m.CertificatesPage })));
const FinancePage      = lazy(() => import('@/pages/FinancePage').then(m => ({ default: m.FinancePage })));
const SettingsPage     = lazy(() => import('@/pages/SettingsPage').then(m => ({ default: m.SettingsPage })));
const CalculatorPage   = lazy(() => import('@/pages/Calculator').then(m => ({ default: m.CalculatorPage })));
const ObrigacoesPage   = lazy(() => import('@/pages/ObrigacoesPage').then(m => ({ default: m.ObrigacoesPage })));
const PortalLoginPage  = lazy(() => import('@/pages/PortalLoginPage').then(m => ({ default: m.PortalLoginPage })));
const TermsPage        = lazy(() => import('@/pages/TermsPage').then(m => ({ default: m.TermsPage })));
const PrivacyPage      = lazy(() => import('@/pages/PrivacyPage').then(m => ({ default: m.PrivacyPage })));
const ClientDetailPage = lazy(() => import('@/pages/ClientDetailPage'));
const LearningPage     = lazy(() => import('@/pages/LearningPage').then(m => ({ default: m.LearningPage })));
const WhatsAppInboxPage = lazy(() => import('@/pages/WhatsAppInboxPage').then(m => ({ default: m.WhatsAppInboxPage })));

// ─── Feature pages (new) ────────────────────────────────────────────────────
const FocoPage                  = lazy(() => import('@/pages/FocoPage').then(m => ({ default: m.FocoPage })));
const FiscalMailboxPage         = lazy(() => import('@/pages/FiscalMailboxPage').then(m => ({ default: m.FiscalMailboxPage })));
const MonthlyClosingsPage       = lazy(() => import('@/pages/MonthlyClosingsPage').then(m => ({ default: m.MonthlyClosingsPage })));
const MonthlyClosingDetailPage  = lazy(() => import('@/pages/MonthlyClosingDetailPage').then(m => ({ default: m.MonthlyClosingDetailPage })));
const PowersOfAttorneyPage      = lazy(() => import('@/pages/PowersOfAttorneyPage').then(m => ({ default: m.PowersOfAttorneyPage })));
const ReportsPage               = lazy(() => import('@/pages/ReportsPage').then(m => ({ default: m.ReportsPage })));
const PortalClientePage         = lazy(() => import('@/pages/PortalClientePage').then(m => ({ default: m.PortalClientePage })));

// ─── Feature module pages ───────────────────────────────────────────────────
const InvoicesListPage  = lazy(() => import('@/features/invoices/pages/InvoicesListPage').then(m => ({ default: m.InvoicesListPage })));
const InvoiceDetailPage = lazy(() => import('@/features/invoices/pages/InvoiceDetailPage').then(m => ({ default: m.InvoiceDetailPage })));
const InvoiceNewPage    = lazy(() => import('@/features/invoices/pages/InvoiceNewPage').then(m => ({ default: m.InvoiceNewPage })));
const InvoiceEmitPage   = lazy(() => import('@/features/invoices/pages/InvoiceEmitPage').then(m => ({ default: m.InvoiceEmitPage })));
const EcacCentralPage   = lazy(() => import('@/features/ecac/pages/EcacCentralPage').then(m => ({ default: m.EcacCentralPage })));
const GuiasListPage     = lazy(() => import('@/features/guias/pages/GuiasListPage').then(m => ({ default: m.GuiasListPage })));
const GuiaDetailPage    = lazy(() => import('@/features/guias/pages/GuiaDetailPage').then(m => ({ default: m.GuiaDetailPage })));

// Full-screen spinner shown while a lazy chunk is loading
function PageLoader() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
    </div>
  );
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; message: string }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, message: '' };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, message: error.message };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center p-8 text-center">
          <div>
            <h2 className="mb-2 text-xl font-semibold">Algo deu errado</h2>
            <p className="mb-4 text-sm text-muted-foreground">{this.state.message}</p>
            <button
              className="text-sm text-primary underline"
              onClick={() => window.location.reload()}
            >
              Recarregar página
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <RouteTitle />
          <CommandMenu />
          <Suspense fallback={<PageLoader />}>
            <Routes>
              {/* Public routes */}
              <Route path="/login"       element={<LoginPage />} />
              <Route path="/register"    element={<RegisterPage />} />
              <Route path="/portal/login" element={<PortalLoginPage />} />
              <Route path="/termos"      element={<TermsPage />} />
              <Route path="/privacidade" element={<PrivacyPage />} />

              {/* Protected app routes */}
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <DashboardLayout />
                  </ProtectedRoute>
                }
              >
                {/* Root redirect */}
                <Route index element={<Navigate to="/painel" replace />} />

                {/* ── Operação diária ──────────────────────────────────── */}
                <Route path="painel"  element={<DashboardPage />} />
                <Route path="foco"    element={<FocoPage />} />

                {/* ── Gestão ───────────────────────────────────────────── */}
                <Route path="clientes"     element={<ClientsPage />} />
                <Route path="clientes/:id" element={<ClientDetailPage />} />
                <Route path="fechamento"   element={<MonthlyClosingsPage />} />
                <Route path="fechamento/:id" element={<MonthlyClosingDetailPage />} />
                <Route path="obrigacoes"   element={<ObrigacoesPage />} />
                <Route path="documentos"   element={<DocumentsPage />} />

                {/* ── Fiscal ───────────────────────────────────────────── */}
                <Route path="notas-fiscais"           element={<InvoicesListPage />} />
                <Route path="notas-fiscais/nova"      element={<InvoiceNewPage />} />
                <Route path="notas-fiscais/:id"       element={<InvoiceDetailPage />} />
                <Route path="notas-fiscais/:id/emitir" element={<InvoiceEmitPage />} />
                <Route path="ecac"                    element={<EcacCentralPage />} />
                <Route path="guias"                   element={<GuiasListPage />} />
                <Route path="guias/:id"               element={<GuiaDetailPage />} />
                <Route path="caixa-postal-fiscal"     element={<FiscalMailboxPage />} />
                <Route path="procuracoes"             element={<PowersOfAttorneyPage />} />
                <Route path="certificados"            element={<CertificatesPage />} />

                {/* ── Financeiro & Canais ──────────────────────────────── */}
                <Route path="financeiro"   element={<FinancePage />} />
                <Route path="whatsapp"     element={<WhatsAppInboxPage />} />
                <Route path="portal"       element={<PortalClientePage />} />
                <Route path="relatorios"   element={<ReportsPage />} />

                {/* ── Sistema ──────────────────────────────────────────── */}
                <Route path="aprender"     element={<LearningPage />} />
                <Route path="configuracoes" element={<SettingsPage />} />
                <Route path="calculadora"  element={<CalculatorPage />} />

                {/* ── Legacy redirects ─────────────────────────────────── */}
                <Route path="dashboard"    element={<Navigate to="/painel" replace />} />
                <Route path="mensagens"    element={<Navigate to="/whatsapp" replace />} />
                <Route path="agenda-prazos" element={<Navigate to="/obrigacoes" replace />} />
                <Route path="das-mensal"   element={<Navigate to="/guias" replace />} />
                <Route path="billing"      element={<Navigate to="/financeiro" replace />} />
                <Route path="settings"     element={<Navigate to="/configuracoes" replace />} />
              </Route>
            </Routes>
          </Suspense>
        </BrowserRouter>
        <Toaster position="top-right" theme="dark" richColors closeButton />
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
