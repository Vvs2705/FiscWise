import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Lock, AlertCircle } from 'lucide-react';
import { ChatMessage } from '../lib/types/calculator';
import { calculatorAPI } from '../lib/fiscwise-calculator-api';

interface Props {
  userPlan?: 'FREE' | 'INTERMEDIARIO' | 'PREMIUM';
}

// Normalise plan slug coming from the backend (may be null / lowercase / uppercase)
function normalisePlan(raw: string | undefined): 'FREE' | 'INTERMEDIARIO' | 'PREMIUM' {
  if (!raw) return 'FREE';
  const up = raw.toUpperCase();
  if (up === 'PREMIUM') return 'PREMIUM';
  if (up === 'INTERMEDIARIO') return 'INTERMEDIARIO';
  return 'FREE';
}

export function FiscalChat({ userPlan: rawPlan = 'FREE' }: Props) {
  const userPlan = normalisePlan(rawPlan);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  // remaining comes from backend after each message; starts as null (unknown)
  const [remaining, setRemaining] = useState<number | null | 'unlimited'>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Plan-level access
  const canUseChat = userPlan === 'INTERMEDIARIO' || userPlan === 'PREMIUM';

  // Whether the user has quota left (optimistic until first message is sent)
  const hasQuota =
    !canUseChat
      ? false
      : remaining === 'unlimited' || remaining === null || (typeof remaining === 'number' && remaining > 0);

  const quotaLabel = (() => {
    if (!canUseChat) return null;
    if (userPlan === 'PREMIUM') return '∞ mensagens (ilimitado)';
    if (remaining === null) return 'Verificando quota...';
    if (typeof remaining === 'number') return `${remaining} mensagens restantes este mês`;
    return '∞ mensagens (ilimitado)';
  })();

  const handleSendMessage = async () => {
    if (!input.trim() || !canUseChat || !hasQuota || loading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const sentInput = input.trim();
    setInput('');
    setLoading(true);

    try {
      const response = await calculatorAPI.chat({
        message: sentInput,
        conversation_history: messages,
      });

      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.response,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);

      // Sync remaining quota from backend response
      if (response.remaining_quota !== undefined) {
        setRemaining(response.remaining_quota === null ? 'unlimited' : response.remaining_quota);
      }
    } catch (error: unknown) {
      const status =
        typeof error === 'object' && error !== null && 'response' in error
          ? (error as { response?: { status?: number } }).response?.status
          : undefined;
      let errorContent = 'Desculpe, houve um erro ao processar sua mensagem. Tente novamente.';

      if (status === 429) {
        // Quota exceeded — update remaining to 0
        setRemaining(0);
        errorContent =
          'Você atingiu o limite de 20 mensagens mensais do plano Intermediário. Faça upgrade para o plano Premium para acesso ilimitado.';
      } else if (status === 403) {
        errorContent = 'Seu plano não permite acesso ao chat com IA.';
      }

      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: errorContent,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
      console.error('Chat error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !loading) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // — Plan gate —
  if (!canUseChat) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 rounded-xl border border-amber-500/20 bg-amber-500/5 p-10 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-full border border-amber-500/20 bg-amber-500/10">
          <Lock className="h-7 w-7 text-amber-500" />
        </div>
        <div>
          <p className="text-base font-semibold text-foreground">Chat com IA não disponível no plano Gratuito</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Faça upgrade para o plano{' '}
            <strong className="text-amber-500">Intermediário</strong> (20 mensagens/mês) ou{' '}
            <strong className="text-primary">Premium</strong> (ilimitado) para conversar com o assistente fiscal.
          </p>
        </div>
      </div>
    );
  }

  // — Quota exhausted —
  if (typeof remaining === 'number' && remaining === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 rounded-xl border border-red-500/20 bg-red-500/5 p-10 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-full border border-red-500/20 bg-red-500/10">
          <AlertCircle className="h-7 w-7 text-red-400" />
        </div>
        <div>
          <p className="text-base font-semibold text-foreground">Limite mensal de mensagens atingido</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Você usou todas as 20 mensagens mensais do plano Intermediário.
            O limite renova no início do próximo mês, ou faça upgrade para o{' '}
            <strong className="text-primary">Premium</strong> para acesso ilimitado.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[500px] rounded-xl border border-border bg-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border bg-muted/30 px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 border border-primary/20">
            <Bot className="h-4 w-4 text-primary" />
          </div>
          <div>
            <p className="text-sm font-semibold text-foreground">Assistente Fiscal IA</p>
            <p className="text-xs text-muted-foreground">Powered by GPT-4o Mini</p>
          </div>
        </div>
        {quotaLabel && (
          <span className="text-xs text-muted-foreground bg-muted rounded-full px-2.5 py-1">
            {quotaLabel}
          </span>
        )}
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 border border-primary/15">
              <Bot className="h-6 w-6 text-primary" />
            </div>
            <div>
              <p className="font-semibold text-foreground">Olá! Sou seu assistente fiscal com IA.</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Faça perguntas sobre regimes tributários, impostos, deduções e otimizações fiscais.
              </p>
            </div>
            <div className="grid grid-cols-1 gap-2 w-full max-w-sm mt-2">
              {[
                'Qual o melhor regime para minha empresa?',
                'Como funciona o Simples Nacional?',
                'Como reduzir a carga tributária legalmente?',
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => setInput(suggestion)}
                  className="rounded-lg border border-border bg-muted/30 px-3 py-2 text-xs text-left text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex items-start gap-2 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
            >
              <div
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                  msg.role === 'user'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted border border-border text-muted-foreground'
                }`}
              >
                {msg.role === 'user' ? <User className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5" />}
              </div>
              <div
                className={`max-w-[75%] rounded-xl px-4 py-2.5 text-sm leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-primary text-primary-foreground rounded-tr-none'
                    : 'bg-muted text-foreground border border-border rounded-tl-none'
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))
        )}

        {loading && (
          <div className="flex items-start gap-2">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-muted border border-border">
              <Bot className="h-3.5 w-3.5 text-muted-foreground" />
            </div>
            <div className="rounded-xl rounded-tl-none bg-muted border border-border px-4 py-2.5">
              <div className="flex gap-1">
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    className="h-2 w-2 rounded-full bg-muted-foreground/50 animate-bounce"
                    style={{ animationDelay: `${i * 150}ms` }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-border p-3">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Digite sua pergunta sobre impostos..."
            disabled={loading}
            className="flex-1 rounded-lg border border-input bg-background text-foreground text-sm px-3 py-2.5 placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary disabled:opacity-50 transition"
          />
          <button
            onClick={handleSendMessage}
            disabled={loading || !input.trim()}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            aria-label="Enviar mensagem"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
