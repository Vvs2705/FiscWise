import { useState, useRef, useEffect } from 'react';
import { ChatMessage } from '../lib/types/calculator';
import { calculatorAPI } from '../lib/fiscwise-calculator-api';

export function FiscalChat({ userPlan = 'FREE' }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [messageCount, setMessageCount] = useState(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const getMessageLimit = () => {
    if (userPlan === 'PREMIUM') return Infinity;
    if (userPlan === 'INTERMEDIARIO') return 20;
    return 0; // FREE tier can't use chat
  };

  const canUseChat = userPlan !== 'FREE';
  const messageLimit = getMessageLimit();

  const handleSendMessage = async () => {
    if (!input.trim() || !canUseChat || messageCount >= messageLimit) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setMessageCount((prev) => prev + 1);
    setLoading(true);

    try {
      const response = await calculatorAPI.chat({
        message: input,
        conversation_history: messages,
      });

      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.response,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Erro ao enviar mensagem:', error);
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Desculpe, houve um erro ao processar sua mensagem.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  if (!canUseChat) {
    return (
      <div className="p-6 bg-yellow-50 border border-yellow-200 rounded-lg text-center">
        <p className="text-yellow-900 font-semibold">Chat com IA não disponível</p>
        <p className="text-sm text-yellow-800 mt-2">Upgrade para INTERMEDIÁRIO ou PREMIUM para usar o assistente fiscal.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-96 bg-white rounded-lg shadow">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center text-gray-500 mt-8">
            <p>Olá! Sou seu assistente fiscal com IA.</p>
            <p className="text-sm mt-2">Faça perguntas sobre impostos e regimes tributários.</p>
          </div>
        ) : (
          messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-xs px-4 py-2 rounded-lg ${
                  msg.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-900'
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="border-t p-4 space-y-2">
        <div className="text-xs text-gray-600">
          Mensagens: {messageCount}/{messageLimit === Infinity ? '∞' : messageLimit}
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && !loading && handleSendMessage()}
            placeholder={messageCount >= messageLimit ? 'Limite de mensagens atingido' : 'Digite sua pergunta...'}
            disabled={loading || messageCount >= messageLimit}
            className="flex-1 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 disabled:bg-gray-100"
          />
          <button
            onClick={handleSendMessage}
            disabled={loading || !input.trim() || messageCount >= messageLimit}
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:bg-gray-400"
          >
            {loading ? '...' : 'Enviar'}
          </button>
        </div>
      </div>
    </div>
  );
}
