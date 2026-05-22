import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { initTheme } from '@/lib/hooks/useTheme';

// Aplica o tema salvo antes do primeiro render para evitar flash
initTheme();
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { DashboardLayout } from '@/layouts/DashboardLayout';
import { LoginPage } from '@/pages/LoginPage';
import { RegisterPage } from '@/pages/RegisterPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { ClientsPage } from '@/pages/ClientsPage';
import { DocumentsPage } from '@/pages/DocumentsPage';
import { DeadlinesPage } from '@/pages/DeadlinesPage';
import { CertificatesPage } from '@/pages/CertificatesPage';
import { FinancePage } from '@/pages/FinancePage';
import { SettingsPage } from '@/pages/SettingsPage';

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
          <Routes>
            <Route path="/login" element={<LoginPage />} />
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
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="clientes" element={<ClientsPage />} />
              <Route path="documentos" element={<DocumentsPage />} />
              <Route path="agenda-prazos" element={<DeadlinesPage />} />
              <Route path="certificados" element={<CertificatesPage />} />
              <Route path="financeiro" element={<FinancePage />} />
              <Route path="configuracoes" element={<SettingsPage />} />
              <Route path="billing" element={<Navigate to="/financeiro" replace />} />
              <Route path="settings" element={<Navigate to="/configuracoes" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
        <Toaster position="top-right" />
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
