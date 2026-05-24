import React, { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { initTheme } from '@/lib/hooks/useTheme';

// Aplica o tema salvo antes do primeiro render para evitar flash
initTheme();

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { DashboardLayout } from '@/layouts/DashboardLayout';

// Lazy-loaded pages — each page is its own JS chunk, loaded only when visited.
// This reduces the initial bundle from ~1.36 MB to the layout + current page only.
const LoginPage       = lazy(() => import('@/pages/LoginPage').then(m => ({ default: m.LoginPage })));
const RegisterPage    = lazy(() => import('@/pages/RegisterPage').then(m => ({ default: m.RegisterPage })));
const DashboardPage   = lazy(() => import('@/pages/DashboardPage').then(m => ({ default: m.DashboardPage })));
const ClientsPage     = lazy(() => import('@/pages/ClientsPage').then(m => ({ default: m.ClientsPage })));
const DocumentsPage   = lazy(() => import('@/pages/DocumentsPage').then(m => ({ default: m.DocumentsPage })));
const DeadlinesPage   = lazy(() => import('@/pages/DeadlinesPage').then(m => ({ default: m.DeadlinesPage })));
const CertificatesPage = lazy(() => import('@/pages/CertificatesPage').then(m => ({ default: m.CertificatesPage })));
const FinancePage     = lazy(() => import('@/pages/FinancePage').then(m => ({ default: m.FinancePage })));
const SettingsPage    = lazy(() => import('@/pages/SettingsPage').then(m => ({ default: m.SettingsPage })));
const CalculatorPage  = lazy(() => import('@/pages/Calculator').then(m => ({ default: m.CalculatorPage })));
const DasMensalPage   = lazy(() => import('@/pages/DasMensalPage').then(m => ({ default: m.DasMensalPage })));
const ObrigacoesPage  = lazy(() => import('@/pages/ObrigacoesPage').then(m => ({ default: m.ObrigacoesPage })));

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
          <Suspense fallback={<PageLoader />}>
            <Routes>
              <Route path="/login"    element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />

              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <DashboardLayout />
                  </ProtectedRoute>
                }
              >
                <Route index element={<Navigate to="/dashboard" replace />} />
                <Route path="dashboard"    element={<DashboardPage />} />
                <Route path="clientes"     element={<ClientsPage />} />
                <Route path="documentos"   element={<DocumentsPage />} />
                <Route path="agenda-prazos" element={<DeadlinesPage />} />
                <Route path="certificados" element={<CertificatesPage />} />
                <Route path="financeiro"   element={<FinancePage />} />
                <Route path="calculadora"  element={<CalculatorPage />} />
                <Route path="das-mensal"    element={<DasMensalPage />} />
                <Route path="obrigacoes"   element={<ObrigacoesPage />} />
                <Route path="configuracoes" element={<SettingsPage />} />
                <Route path="billing"   element={<Navigate to="/financeiro" replace />} />
                <Route path="settings"  element={<Navigate to="/configuracoes" replace />} />
              </Route>
            </Routes>
          </Suspense>
        </BrowserRouter>
        <Toaster position="top-right" />
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
