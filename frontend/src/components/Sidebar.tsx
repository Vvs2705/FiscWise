import { Link, useLocation } from 'react-router-dom';
import {
  CalendarClock,
  FolderKanban,
  LayoutDashboard,
  ReceiptText,
  Settings,
  ShieldCheck,
  UsersRound,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Clientes', href: '/clientes', icon: UsersRound },
  { name: 'Documentos', href: '/documentos', icon: FolderKanban },
  { name: 'Agenda e Prazos', href: '/agenda-prazos', icon: CalendarClock },
  { name: 'Certificados', href: '/certificados', icon: ShieldCheck },
  { name: 'Financeiro', href: '/financeiro', icon: ReceiptText },
  { name: 'Configurações', href: '/configuracoes', icon: Settings },
];

export function Sidebar() {
  const location = useLocation();

  return (
    <div className="flex h-full w-20 shrink-0 flex-col border-r bg-card md:w-64">
      <div className="flex h-16 items-center justify-center border-b px-3 md:justify-start md:px-6">
        <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-sm font-bold text-primary-foreground">
          CT
        </div>
        <div className="ml-3 hidden md:block">
          <h1 className="text-lg font-bold leading-tight text-primary">CTFlow</h1>
          <p className="text-xs text-muted-foreground">Operação contábil</p>
        </div>
      </div>
      <nav className="flex-1 space-y-1 px-3 py-4">
        {navigation.map((item) => {
          const isActive =
            location.pathname === item.href || location.pathname.startsWith(`${item.href}/`);

          return (
            <Link
              key={item.name}
              to={item.href}
              aria-label={item.name}
              className={cn(
                'flex items-center justify-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors md:justify-start',
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
              )}
            >
              <item.icon className="h-5 w-5 shrink-0" />
              <span className="hidden md:inline">{item.name}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
