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
      {/* Backdrop blur */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-[3px]"
        onClick={() => setOpen(false)}
      />

      {/* Command Palette Panel */}
      <Command
        className={cn(
          'relative z-10 w-full max-w-lg overflow-hidden rounded-card border border-border/80 bg-card/95 text-card-foreground shadow-token backdrop-blur-md',
          'animate-scale-in max-h-[50vh] flex flex-col'
        )}
      >
        <div className="flex items-center border-b px-4 py-3">
          <Search className="w-5 h-5 text-muted-foreground mr-2" />
          <Command.Input
            placeholder="Digite para buscar clientes ou comandos..."
            className="w-full bg-transparent text-sm text-foreground outline-none placeholder-muted-foreground"
            autoFocus
          />
        </div>

        <Command.List className="overflow-y-auto p-2 flex-1 scrollbar">
          <Command.Empty className="py-6 text-center text-sm text-muted-foreground">
            Nenhum resultado encontrado.
          </Command.Empty>

          <Command.Group heading="Ações rápidas" className="text-xs font-semibold text-muted-foreground px-2 py-1.5 uppercase tracking-wider">
            <Command.Item
              onSelect={() => runCommand(() => navigate('/clientes'))}
              className="flex items-center gap-3 px-3 py-2 text-sm text-foreground rounded-lg cursor-pointer hover:bg-primary/10 hover:text-primary transition-colors data-[selected=true]:bg-primary/10 data-[selected=true]:text-primary"
            >
              <Plus className="w-4 h-4" />
              <span>Cadastrar Novo Cliente</span>
            </Command.Item>
            <Command.Item
              onSelect={() => runCommand(() => navigate('/documentos'))}
              className="flex items-center gap-3 px-3 py-2 text-sm text-foreground rounded-lg cursor-pointer hover:bg-primary/10 hover:text-primary transition-colors data-[selected=true]:bg-primary/10 data-[selected=true]:text-primary"
            >
              <FileText className="w-4 h-4" />
              <span>Subir Documento Fiscal</span>
            </Command.Item>
            <Command.Item
              onSelect={() => runCommand(() => navigate('/mensagens'))}
              className="flex items-center gap-3 px-3 py-2 text-sm text-foreground rounded-lg cursor-pointer hover:bg-primary/10 hover:text-primary transition-colors data-[selected=true]:bg-primary/10 data-[selected=true]:text-primary"
            >
              <MessageSquare className="w-4 h-4" />
              <span>Abrir Central de Mensagens WhatsApp</span>
            </Command.Item>
            <Command.Item
              onSelect={() => runCommand(() => navigate('/agenda-prazos'))}
              className="flex items-center gap-3 px-3 py-2 text-sm text-foreground rounded-lg cursor-pointer hover:bg-primary/10 hover:text-primary transition-colors data-[selected=true]:bg-primary/10 data-[selected=true]:text-primary"
            >
              <Calendar className="w-4 h-4" />
              <span>Ver Agenda Fiscal</span>
            </Command.Item>
            <Command.Item
              onSelect={() => runCommand(() => navigate('/financeiro'))}
              className="flex items-center gap-3 px-3 py-2 text-sm text-foreground rounded-lg cursor-pointer hover:bg-primary/10 hover:text-primary transition-colors data-[selected=true]:bg-primary/10 data-[selected=true]:text-primary"
            >
              <Receipt className="w-4 h-4" />
              <span>Gerenciar Financeiro</span>
            </Command.Item>
            <Command.Item
              onSelect={() => runCommand(() => navigate('/configuracoes'))}
              className="flex items-center gap-3 px-3 py-2 text-sm text-foreground rounded-lg cursor-pointer hover:bg-primary/10 hover:text-primary transition-colors data-[selected=true]:bg-primary/10 data-[selected=true]:text-primary"
            >
              <Settings className="w-4 h-4" />
              <span>Configurações</span>
            </Command.Item>
          </Command.Group>

          {clients && clients.length > 0 && (
            <Command.Group heading="Clientes" className="text-xs font-semibold text-muted-foreground px-2 py-1.5 mt-2 uppercase tracking-wider">
              {clients.map((client) => (
                <Command.Item
                  key={client.id}
                  onSelect={() => runCommand(() => navigate(`/clientes?id=${client.id}`))}
                  className="flex items-center gap-3 px-3 py-2 text-sm text-foreground rounded-lg cursor-pointer hover:bg-primary/10 hover:text-primary transition-colors data-[selected=true]:bg-primary/10 data-[selected=true]:text-primary"
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

        <div className="flex items-center justify-between border-t px-4 py-2 bg-muted/20 text-xs text-muted-foreground shrink-0">
          <span>
            Pressione <kbd className="font-sans font-semibold border rounded px-1 bg-card">ESC</kbd> para fechar
          </span>
          <span className="flex items-center gap-1">
            Navegue com <kbd className="font-sans font-semibold border rounded px-1 bg-card">↑</kbd>{' '}
            <kbd className="font-sans font-semibold border rounded px-1 bg-card">↓</kbd>
          </span>
        </div>
      </Command>
    </div>
  );
}
