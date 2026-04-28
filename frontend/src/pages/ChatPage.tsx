import { useNavigate } from 'react-router-dom';
import { useChat } from '@/lib/hooks/useChat';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Plus, MessageSquare } from 'lucide-react';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';

export function ChatPage() {
  const navigate = useNavigate();
  const { sessions, createSession } = useChat();

  const handleNewSession = async () => {
    const session = await createSession.mutateAsync(undefined);
    if (session) {
      navigate(`/chat/${session.id}`);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Conversas</h1>
          <p className="text-muted-foreground">Histórico de sessões de chat</p>
        </div>
        <Button onClick={handleNewSession} disabled={createSession.isPending}>
          <Plus className="h-4 w-4 mr-2" />
          Nova Conversa
        </Button>
      </div>

      <div className="space-y-4">
        {sessions.isLoading && <div>Carregando sessões...</div>}
        {sessions.data?.map((session) => (
          <Card
            key={session.id}
            className="cursor-pointer hover:bg-accent transition-colors"
            onClick={() => navigate(`/chat/${session.id}`)}
          >
            <CardContent className="flex items-center justify-between p-6">
              <div className="flex items-center gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
                  <MessageSquare className="h-6 w-6 text-primary" />
                </div>
                <div>
                  <h3 className="font-semibold">{session.title}</h3>
                  <div className="flex gap-4 mt-1 text-sm text-muted-foreground">
                    <span>{session.message_count} mensagens</span>
                    <span>{session.total_tokens.toLocaleString()} tokens</span>
                    <span>
                      {format(new Date(session.updated_at), 'dd/MM/yyyy HH:mm', { locale: ptBR })}
                    </span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
        {sessions.data?.length === 0 && (
          <Card>
            <CardContent className="flex flex-col items-center justify-center p-12 text-center">
              <MessageSquare className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">Nenhuma conversa ainda</h3>
              <p className="text-muted-foreground mb-4">
                Inicie uma nova conversa para começar a usar o chat com IA
              </p>
              <Button onClick={handleNewSession} disabled={createSession.isPending}>
                <Plus className="h-4 w-4 mr-2" />
                Nova Conversa
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
