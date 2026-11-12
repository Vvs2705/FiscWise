/**
 * NotFoundPage — 404 personalizada (rota inexistente).
 * O noindex é aplicado por RouteTitle para qualquer rota fora da lista pública.
 */
import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Logo } from '@/components/Logo';

export function NotFoundPage() {
  useEffect(() => {
    document.title = 'Página não encontrada · FiscWise';
  }, []);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-background p-8 text-center">
      <Logo variant="full" theme="auto" size={32} />
      <div>
        <p className="text-sm font-semibold text-primary">Erro 404</p>
        <h1 className="mt-2 text-2xl font-bold">Página não encontrada</h1>
        <p className="mt-2 max-w-md text-sm text-muted-foreground">
          O endereço que você abriu não existe ou foi movido. Volte ao painel ou entre na sua conta.
        </p>
      </div>
      <div className="flex gap-3">
        <Link
          to="/painel"
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
        >
          Ir para o painel
        </Link>
        <Link to="/login" className="rounded-md border border-border px-4 py-2 text-sm font-medium hover:bg-muted">
          Entrar
        </Link>
      </div>
    </div>
  );
}
