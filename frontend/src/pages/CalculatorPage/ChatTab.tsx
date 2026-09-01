import { useState, useRef, useEffect } from 'react';
import toast from 'react-hot-toast';
import { Send, Bot, User, MessageSquare } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { PlanGate } from './PlanGate';
import { useSendChatMessage, planHasChat, type SubscriptionPlan, type ChatMessage } from '@/lib/hooks/useCalculator';
import { cn } from '@/lib/utils';

interface ChatTabProps {
  plan: SubscriptionPlan;
}

const CHAT_LIMIT = 20;

export function ChatTab({ plan }: ChatTabProps) {
  const hasChat = planHasChat(plan);
  const isUnlimited = plan === 'premium';
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [usedMessages, setUsedMessages] = useState(0);
  const [input, setInput] = useState('');
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const sendMessage = useSendChatMessage();

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const limitReached = !isUnlimited && usedMessages >= CHAT_LIMIT;
  const canSend = hasChat && !limitReached && input.trim().length > 0 && !sendMessage.isPending;

  async function handleSend() {
    if (!canSend) return;
    const text = input.trim();
    setInput('');

    const optimisticUser: ChatMessage = {
      id: `optimistic-${Date.now()}`,
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimisticUser]);

    try {
      const res = await sendMessage.mutateAsync({ session_id: sessionId, message: text });
      setSessionId(res.session_id);
      setUsedMessages(res.messages_used);
      setMessages((prev) => [
        ...prev.filter((m) => m.id !== optimisticUser.id),
        res.user_message,
        res.assistant_message,
      ]);
    } catch {
      setMessages((prev) => prev.filter((m) => m.id !== optimisticUser.id));
      toast.error('Erro ao enviar mensagem. Tente novamente.');
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  if (!hasChat) {
    return (
      <PlanGate requiredPlan="intermediario" currentPlan={plan}>
        <span />
      </PlanGate>
    );
  }

  return (
    <div className="flex h-[600px] flex-col rounded-xl border border-border bg-card shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <MessageSquare className="h-4 w-4 text-primary" aria-hidden="true" />
          <span className="text-sm font-semibold">Assistente Fiscal</span>
        </div>
        {!isUnlimited && (
          <span
            className={cn(
              'rounded-full px-2.5 py-0.5 text-xs font-medium',
              usedMessages >= CHAT_LIMIT
                ? 'bg-destructive/10 text-destructive'
                : usedMessages >= CHAT_LIMIT * 0.8
                  ? 'bg-yellow-500/10 text-yellow-500'
                  : 'bg-muted text-muted-foreground',
            )}
            aria-label={`${usedMessages} de ${CHAT_LIMIT} mensagens usadas neste mês`}
          >
            {usedMessages}/{CHAT_LIMIT} mensagens
          </span>
        )}
        {isUnlimited && (
          <span className="rounded-full bg-amber-500/10 px-2.5 py-0.5 text-xs font-medium text-amber-400">
            Ilimitado
          </span>
        )}
      </div>

      {/* Messages */}
      <div
        className="flex-1 overflow-y-auto p-4 space-y-4"
        role="log"
        aria-label="Conversa com o assistente fiscal"
        aria-live="polite"
      >
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
            <Bot className="h-10 w-10 text-muted-foreground/40" aria-hidden="true" />
            <p className="text-sm text-muted-foreground">
              Olá! Sou o assistente fiscal do FiscWise.
              <br />
              Pergunte sobre tributos, regimes, deduções e muito mais.
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={cn(
              'flex items-start gap-3',
              msg.role === 'user' ? 'flex-row-reverse' : 'flex-row',
            )}
          >
            {/* Avatar */}
            <div
              className={cn(
                'flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
                msg.role === 'user'
                  ? 'bg-primary/20 text-primary'
                  : 'bg-muted text-muted-foreground',
              )}
              aria-hidden="true"
            >
              {msg.role === 'user' ? (
                <User className="h-4 w-4" />
              ) : (
                <Bot className="h-4 w-4" />
              )}
            </div>

            {/* Bubble */}
            <div
              className={cn(
                'max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-sm',
                msg.role === 'user'
                  ? 'rounded-tr-sm bg-primary text-primary-foreground'
                  : 'rounded-tl-sm border border-border bg-muted/60',
              )}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {/* Typing indicator */}
        {sendMessage.isPending && (
          <div className="flex items-start gap-3">
            <div
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground"
              aria-hidden="true"
            >
              <Bot className="h-4 w-4" />
            </div>
            <div className="rounded-2xl rounded-tl-sm border border-border bg-muted/60 px-4 py-3">
              <div className="flex gap-1" aria-label="Assistente digitando..." role="status">
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground/60"
                    style={{ animationDelay: `${i * 150}ms` }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}

        <div ref={endRef} />
      </div>

      {/* Input */}
      <div className="border-t border-border p-4">
        {limitReached ? (
          <p className="text-center text-sm text-muted-foreground">
            Você atingiu o limite de {CHAT_LIMIT} mensagens mensais.{' '}
            <button
              type="button"
              className="text-primary underline hover:no-underline focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              onClick={() => (window.location.href = '/financeiro')}
            >
              Faça upgrade para Premium
            </button>{' '}
            para chat ilimitado.
          </p>
        ) : (
          <form
            onSubmit={(e) => { e.preventDefault(); handleSend(); }}
            className="flex gap-2"
            aria-label="Enviar mensagem"
          >
            <Input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Pergunte algo sobre tributos..."
              aria-label="Mensagem para o assistente fiscal"
              disabled={sendMessage.isPending}
              className="flex-1"
            />
            <Button
              type="submit"
              size="md"
              disabled={!canSend}
              aria-label="Enviar mensagem"
            >
              <Send className="h-4 w-4" aria-hidden="true" />
              <span className="sr-only">Enviar</span>
            </Button>
          </form>
        )}
      </div>
    </div>
  );
}
