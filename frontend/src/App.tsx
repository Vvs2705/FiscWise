import React, { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { initTheme } from '@/lib/hooks/useTheme';

// Aplica o tema salvo antes do primeiro render para evitar flash
initTheme();

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { RouteTitle } from '@/lib/RouteTitle';
import { OfflineProvider } from '@/lib/offline/OfflineProvider';
import { captureException } from '@/lib/monitoring';

// ─── Casca e provedores sob demanda (fora do chunk index) ────────────────────
// AppShell = MotionConfig (framer-motion) + DashboardLayout + busca global.
const AppShell           = lazy(() => import('@/components/AppShell'));
// Provider do Google só nas rotas com GoogleLogin; evita o script do Google no resto.
const GoogleAuthProvider = lazy(() => import('@/components/GoogleAuthProvider'));
// sonner em chunk próprio; baixa em paralelo com a página.
const Toaster            = lazy(() => import('sonner').then(m => ({ default: m.Toaster })));

// ─── Existing pages (lazy) ──────────────────────────────────────────────────
const LandingPage      = lazy(() => import('@/pages/LandingPage').then(m => ({ default: m.LandingPage })));
const LoginPage        = lazy(() => import('@/pages/LoginPage').then(m => ({ default: m.LoginPage })));
const RegisterPage     = lazy(() => import('@/pages/RegisterPage').then(m => ({ default: m.RegisterPage })));
const NotFoundPage     = lazy(() => import('@/pages/NotFoundPage').then(m => ({ default: m.NotFoundPage })));
const DashboardPage    = lazy(() => import('@/pages/DashboardPage').then(m => ({ default: m.DashboardPage })));
const ClientsPage      = lazy(() => import('@/pages/ClientsPage').then(m => ({ default: m.ClientsPage })));
const DocumentsPage    = lazy(() => import('@/pages/DocumentsPage').then(m => ({ default: m.DocumentsPage })));
const CertificatesPage = lazy(() => import('@/pages/CertificatesPage').then(m => ({ default: m.CertificatesPage })));
const FinancePage      = lazy(() => import('@/pages/FinancePage').then(m => ({ default: m.FinancePage })));
const SettingsPage     = lazy(() => import('@/pages/SettingsPage').then(m => ({ default: m.SettingsPage })));
const CalculatorPage   = lazy(() => import('@/pages/Calculator').then(m => ({ default: m.CalculatorPage })));
const ObrigacoesPage   = lazy(() => import('@/pages/ObrigacoesPage').then(m => ({ default: m.ObrigacoesPage })));
const PortalLoginPage  = lazy(() => import('@/pages/PortalLoginPage').then(m => ({ default: m.PortalLoginPage })));
const ForgotPasswordPage = lazy(() => import('@/pages/ForgotPasswordPage').then(m => ({ default: m.ForgotPasswordPage })));
const ResetPasswordPage  = lazy(() => import('@/pages/ResetPasswordPage').then(m => ({ default: m.ResetPasswordPage })));
const TermsPage        = lazy(() => import('@/pages/TermsPage').then(m => ({ default: m.TermsPage })));
const PrivacyPage      = lazy(() => import('@/pages/PrivacyPage').then(m => ({ default: m.PrivacyPage })));
const ClientDetailPage = lazy(() => import('@/pages/ClientDetailPage'));
const LearningPage     = lazy(() => import('@/pages/LearningPage').then(m => ({ default: m.LearningPage })));
const SyncPage          = lazy(() => import('@/pages/SyncPage').then(m => ({ default: m.SyncPage })));
const WhatsAppInboxPage = lazy(() => import('@/pages/WhatsAppInboxPage').then(m => ({ default: m.WhatsAppInboxPage })));

// ─── Feature pages (new) ────────────────────────────────────────────────────
const FocoPage                  = lazy(() => import('@/pages/FocoPage').then(m => ({ default: m.FocoPage })));
const FiscalMailboxPage         = lazy(() => import('@/pages/FiscalMailboxPage').then(m => ({ default: m.FiscalMailboxPage })));
const MonthlyClosingsPage       = lazy(() => import('@/pages/MonthlyClosingsPage').then(m => ({ default: m.MonthlyClosingsPage })));
const MonthlyClosingDetailPage  = lazy(() => import('@/pages/MonthlyClosingDetailPage').then(m => ({ default: m.MonthlyClosingDetailPage })));
const PowersOfAttorneyPage      = lazy(() => import('@/pages/PowersOfAttorneyPage').then(m => ({ default: m.PowersOfAttorneyPage })));
const ReportsPage               = lazy(() => import('@/pages/ReportsPage').then(m => ({ default: m.ReportsPage })));
const PortalDashboardPage       = lazy(() => import('@/pages/PortalDashboardPage').then(m => ({ default: m.PortalDashboardPage })));
const PortalClientePage         = lazy(() => import('@/pages/PortalClientePage').then(m => ({ default: m.PortalClientePage })));

// ─── Feature module pages ───────────────────────────────────────────────────
const InvoicesListPage  = lazy(() => import('@/features/invoices/pages/InvoicesListPage').then(m => ({ default: m.InvoicesListPage })));
const InvoiceDetailPage = lazy(() => import('@/features/invoices/pages/InvoiceDetailPage').then(m => ({ default: m.InvoiceDetailPage })));
const InvoiceNewPage    = lazy(() => import('@/features/invoices/pages/InvoiceNewPage').then(m => ({ default: m.InvoiceNewPage })));
const InvoiceEmitPage   = lazy(() => import('@/features/invoices/pages/InvoiceEmitPage').then(m => ({ default: m.InvoiceEmitPage })));
const EcacCentralPage   = lazy(() => import('@/features/ecac/pages/EcacCentralPage').then(m => ({ default: m.EcacCentralPage })));
const GuiasListPage     = lazy(() => import('@/features/guias/pages/GuiasListPage').then(m => ({ default: m.GuiasListPage })));
const GuiaDetailPage    = lazy(() => import('@/features/guias/pages/GuiaDetailPage').then(m => ({ default: m.GuiaDetailPage })));

// Skeleton leve exibido enquanto um chunk lazy carrega. Só classes Tailwind,
// sem componentes de ui/, para não puxar dependências para o chunk index.
function PageLoader() {
  return (
    <div
      className="min-h-screen bg-background p-5 md:p-6"
      role="status"
      aria-busy="true"
      aria-label="Carregando"
    >
      <div className="mx-auto max-w-5xl animate-pulse space-y-4">
        <div className="h-7 w-48 rounded-md bg-muted" />
        <div className="h-4 w-72 max-w-full rounded-md bg-muted" />
        <div className="grid gap-4 pt-2 sm:grid-cols-3">
          <div className="h-24 rounded-lg bg-muted" />
          <div className="h-24 rounded-lg bg-muted" />
          <div className="h-24 rounded-lg bg-muted" />
        </div>
        <div className="h-64 rounded-lg bg-muted" />
      </div>
    </div>
  );
}

// Defaults de cache: evita refetch a cada navegação (staleTime 0 gerava
// tráfego excessivo no banco). As queryKeys das páginas não mudam.
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 5 * 60_000,
      retry: 1,
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
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

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    captureException(error, { extra: { componentStack: info.componentStack } });
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
        <OfflineProvider>
        <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <RouteTitle />
          <Suspense fallback={<PageLoader />}>
            <Routes>
              {/* Public routes */}
              <Route path="/"            element={<LandingPage />} />
              <Route path="/login"       element={<GoogleAuthProvider><LoginPage /></GoogleAuthProvider>} />
              <Route path="/register"    element={<GoogleAuthProvider><RegisterPage /></GoogleAuthProvider>} />
              <Route path="/portal/login" element={<PortalLoginPage />} />
              <Route path="/esqueci-senha"   element={<ForgotPasswordPage />} />
              <Route path="/redefinir-senha" element={<ResetPasswordPage />} />
              <Route path="/termos"      element={<TermsPage />} />
              <Route path="/privacidade" element={<PrivacyPage />} />
              <Route path="/404"         element={<NotFoundPage />} />

              {/* Portal do cliente final (role client) — fora do layout da equipe */}
              <Route
                path="/portal/dashboard"
                element={
                  <ProtectedRoute area="portal">
                    <PortalDashboardPage />
                  </ProtectedRoute>
                }
              />

              {/* Protected app routes (layout sem caminho; "/" é sempre a página inicial pública) */}
              <Route
                element={
                  <ProtectedRoute>
                    <AppShell />
                  </ProtectedRoute>
                }
              >
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
                <Route path="sincronizacao" element={<SyncPage />} />
                <Route path="calculadora"  element={<CalculatorPage />} />

                {/* ── Legacy redirects ─────────────────────────────────── */}
                <Route path="dashboard"    element={<Navigate to="/painel" replace />} />
                <Route path="mensagens"    element={<Navigate to="/whatsapp" replace />} />
                <Route path="agenda-prazos" element={<Navigate to="/obrigacoes" replace />} />
                <Route path="das-mensal"   element={<Navigate to="/guias" replace />} />
                <Route path="billing"      element={<Navigate to="/financeiro" replace />} />
                <Route path="settings"     element={<Navigate to="/configuracoes" replace />} />
              </Route>

              {/* Rota inexistente: página 404 (noindex via RouteTitle) */}
              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </Suspense>
        </BrowserRouter>
        </OfflineProvider>
        <Suspense fallback={null}>
          <Toaster position="top-right" theme="dark" richColors closeButton />
        </Suspense>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
