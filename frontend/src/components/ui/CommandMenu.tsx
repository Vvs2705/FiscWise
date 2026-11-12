import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Command } from 'cmdk';
import { Search, User, FileText, Calendar, Plus, Settings, Receipt, MessageSquare } from 'lucide-react';
import { useClients } from '@/lib/hooks/useOperations';
import { cn } from '@/lib/utils';

export function CommandMenu() {
  const [open, setOpen] = useState(false);
  const { data: clients } = useClients();
  const navigate = useNavigate();

  // Listen for Ctrl+K / Cmd+K
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((open) => !open);
      }
    };

    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, []);

  const runCommand = (command: () => void) => {
    setOpen(false);
    command();
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center p-4 pt-[15vh]"
      role="dialog"
      aria-modal="true"
    >
      {/* Backdrop sem blur */}
      <div
        className="absolute inset-0 bg-foreground/40 animate-fade-in"
        aria-hidden="true"
        onClick={() => setOpen(false)}
      />

      {/* Command Palette Panel */}
      <Command
        className={cn(
          'relative z-10 flex max-h-[60vh] w-full max-w-lg flex-col overflow-hidden rounded-lg border border-border bg-card text-card-foreground shadow-lg',
          'animate-fade-in-up'
        )}
      >
        <div className="flex items-center border-b px-4 py-3">
          <Search className="mr-2 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
          <Command.Input
            placeholder="Digite para buscar clientes ou comandos..."
            className="h-6 w-full bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
            autoFocus
          />
        </div>

        <Command.List className="overflow-y-auto p-2 flex-1 scrollbar">
          <Command.Empty className="py-6 text-center text-sm text-muted-foreground">
            Nenhum resultado encontrado.
          </Command.Empty>

          <Command.Group heading="Ações rápidas" className="px-1 py-1.5 text-xs font-medium text-muted-foreground [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:pb-1">
            <Command.Item
              onSelect={() => runCommand(() => navigate('/clientes'))}
              className="flex cursor-pointer items-center gap-3 rounded-md px-3 py-2 text-sm text-foreground transition-colors duration-100 data-[selected=true]:bg-accent data-[selected=true]:text-accent-foreground"
            >
              <Plus className="w-4 h-4" />
              <span>Cadastrar novo cliente</span>
            </Command.Item>
            <Command.Item
              onSelect={() => runCommand(() => navigate('/documentos'))}
              className="flex cursor-pointer items-center gap-3 rounded-md px-3 py-2 text-sm text-foreground transition-colors duration-100 data-[selected=true]:bg-accent data-[selected=true]:text-accent-foreground"
            >
              <FileText className="w-4 h-4" />
              <span>Enviar documento fiscal</span>
            </Command.Item>
            <Command.Item
              onSelect={() => runCommand(() => navigate('/whatsapp'))}
              className="flex cursor-pointer items-center gap-3 rounded-md px-3 py-2 text-sm text-foreground transition-colors duration-100 data-[selected=true]:bg-accent data-[selected=true]:text-accent-foreground"
            >
              <MessageSquare className="w-4 h-4" />
              <span>Abrir WhatsApp</span>
            </Command.Item>
            <Command.Item
              onSelect={() => runCommand(() => navigate('/obrigacoes'))}
              className="flex cursor-pointer items-center gap-3 rounded-md px-3 py-2 text-sm text-foreground transition-colors duration-100 data-[selected=true]:bg-accent data-[selected=true]:text-accent-foreground"
            >
              <Calendar className="w-4 h-4" />
              <span>Ver obrigações</span>
            </Command.Item>
            <Command.Item
              onSelect={() => runCommand(() => navigate('/financeiro'))}
              className="flex cursor-pointer items-center gap-3 rounded-md px-3 py-2 text-sm text-foreground transition-colors duration-100 data-[selected=true]:bg-accent data-[selected=true]:text-accent-foreground"
            >
              <Receipt className="w-4 h-4" />
              <span>Abrir financeiro</span>
            </Command.Item>
            <Command.Item
              onSelect={() => runCommand(() => navigate('/configuracoes'))}
              className="flex cursor-pointer items-center gap-3 rounded-md px-3 py-2 text-sm text-foreground transition-colors duration-100 data-[selected=true]:bg-accent data-[selected=true]:text-accent-foreground"
            >
              <Settings className="w-4 h-4" />
              <span>Configurações</span>
            </Command.Item>
          </Command.Group>

          {clients && clients.length > 0 && (
            <Command.Group heading="Clientes" className="mt-2 px-1 py-1.5 text-xs font-medium text-muted-foreground [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:pb-1">
              {clients.map((client) => (
                <Command.Item
                  key={client.id}
                  onSelect={() => runCommand(() => navigate(`/clientes?id=${client.id}`))}
                  className="flex cursor-pointer items-center gap-3 rounded-md px-3 py-2 text-sm text-foreground transition-colors duration-100 data-[selected=true]:bg-accent data-[selected=true]:text-accent-foreground"
                >
                  <User className="w-4 h-4" />
                  <div className="flex flex-col min-w-0">
                    <span className="font-medium truncate">{client.name}</span>
                    <span className="text-xs text-muted-foreground truncate">{client.document || 'Sem CPF/CNPJ'}</span>
                  </div>
                </Command.Item>
              ))}
            </Command.Group>
          )}
        </Command.List>

        <div className="flex shrink-0 items-center justify-between border-t border-border bg-muted/40 px-4 py-2 text-xs text-muted-foreground">
          <span>
            Pressione <kbd className="rounded-sm border border-border bg-card px-1 font-mono text-[11px]">ESC</kbd> para fechar
          </span>
          <span className="flex items-center gap-1">
            Navegue com <kbd className="rounded-sm border border-border bg-card px-1 font-mono text-[11px]">↑</kbd>{' '}
            <kbd className="rounded-sm border border-border bg-card px-1 font-mono text-[11px]">↓</kbd>
          </span>
        </div>
      </Command>
    </div>
  );
}
