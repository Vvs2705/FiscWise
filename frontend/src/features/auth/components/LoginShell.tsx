import { Link } from 'react-router-dom';
import { Logo } from '@/components/Logo';
import { ThemeToggle } from '@/components/ThemeToggle';

const FOCUS_RING =
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background';

/** Logo com wordmark navy no claro e claro no escuro. */
export function LoginLogo({ size = 28 }: { size?: number }) {
  return (
    <>
      <Logo variant="full" theme="light" size={size} className="dark:hidden" />
      <Logo variant="full" theme="dark" size={size} className="hidden dark:block" />
    </>
  );
}

/** Barra superior do login: marca (link para a página inicial) e cadastro. */
export function LoginTopBar() {
  return (
    <header className="w-full lg:border-b lg:border-border">
      <div className="mx-auto flex h-16 w-full max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-10">
        <Link to="/" aria-label="FiscWise, página inicial" className={`shrink-0 rounded-md ${FOCUS_RING}`}>
          <LoginLogo />
        </Link>

        <div className="flex items-center gap-2 text-sm sm:gap-3">
          <ThemeToggle />
          <span className="hidden text-muted-foreground sm:inline">Ainda não tem conta?</span>
          <Link
            to="/register"
            className={[
              'inline-flex h-10 select-none items-center justify-center whitespace-nowrap rounded-md px-3 font-medium sm:px-4',
              'bg-primary text-primary-foreground shadow-sm hover:bg-primary/90',
              'transition-[background-color,transform] duration-100 ease-out active:scale-[0.98]',
              FOCUS_RING,
            ].join(' ')}
          >
            Criar conta grátis
          </Link>
        </div>
      </div>
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
        <span className="inline-flex items-center gap-2 whitespace-nowrap">
          <Link to="/termos" className={link}>
            Termos
          </Link>
          <span aria-hidden="true">·</span>
          <Link to="/privacidade" className={link}>
            Privacidade
          </Link>
        </span>
      </div>
    </footer>
  );
}
