import { Link } from 'react-router-dom';
import { Logo } from '@/components/Logo';
import { ThemeToggle } from '@/components/ThemeToggle';
import { COMPANY_ADDRESS, COMPANY_CNPJ } from '@/lib/company';

const FOCUS_RING =
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background';

/** Logo com wordmark navy no claro e claro no escuro. */
export function LoginLogo({ size = 28 }: { size?: number }) {
  return <Logo variant="full" theme="auto" size={size} />;
}

/** Topo da coluna do formulário: marca (link para a página inicial) e tema. O cadastro fica abaixo do botão Entrar. */
export function LoginTopBar() {
  return (
    <header className="flex h-16 w-full shrink-0 items-center justify-between gap-4">
      <Link to="/" aria-label="FiscWise, página inicial" className={`shrink-0 rounded-md ${FOCUS_RING}`}>
        <LoginLogo />
      </Link>
      <ThemeToggle />
    </header>
  );
}

/** Rodapé de uma linha. */
export function LoginFooter() {
  const link = `rounded-sm hover:text-foreground ${FOCUS_RING}`;
  return (
    <footer className="w-full">
      <div className="mx-auto flex w-full max-w-7xl flex-wrap items-center gap-x-3 gap-y-1 px-4 py-4 text-xs text-muted-foreground sm:gap-x-2 sm:px-6 lg:px-10">
        <span className="inline-flex items-center gap-2 whitespace-nowrap">
          <span>© {new Date().getFullYear()} FiscWise</span>
          <span aria-hidden="true">·</span>
          <a
            href="https://vstack-solutions.com.br"
            target="_blank"
            rel="noopener noreferrer"
            className={link}
          >
            Vstack Solutions
          </a>
        </span>
        <span aria-hidden="true" className="hidden sm:inline">
          ·
        </span>
        {/* Identificação do fornecedor (Decreto 7.962/2013, art. 2º). */}
        <span>
          CNPJ {COMPANY_CNPJ} · {COMPANY_ADDRESS}
        </span>
        <span aria-hidden="true" className="hidden sm:inline">
          ·
        </span>
        <span className="inline-flex items-center gap-2 whitespace-nowrap">
          <Link to="/termos" className={link}>
            Termos
          </Link>
          <span aria-hidden="true">·</span>
          <Link to="/privacidade" className={link}>
            Privacidade
          </Link>
          <span aria-hidden="true">·</span>
          {/* Página estática (precos.html), fora do roteador do app. */}
          <a href="/precos" className={link}>
            Preços
          </a>
        </span>
      </div>
    </footer>
  );
}
