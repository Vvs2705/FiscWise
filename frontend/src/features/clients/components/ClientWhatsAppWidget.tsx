import { useState, useRef, useEffect } from 'react';
import {
  SendHorizontal,
  Bot,
  CalendarPlus,
  FileText,
  Image,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  useWhatsAppInboxes,
  useWhatsAppMessages,
  useSendWhatsAppMessage,
  useConvertMessageToTask,
  WhatsAppMessage,
} from '@/lib/hooks/useWhatsApp';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Dialog } from '@/components/ui/Dialog';
import { FormField } from '@/components/ui/FormField';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { getApiErrorMessage } from '@/lib/api';

interface ClientWhatsAppWidgetProps {
  clientId: string;
  clientPhone: string | null;
}

export function ClientWhatsAppWidget({ clientId, clientPhone }: ClientWhatsAppWidgetProps) {
  const [replyText, setReplyText] = useState('');
  const [showTaskModal, setShowTaskModal] = useState(false);
  const [selectedMessage, setSelectedMessage] = useState<WhatsAppMessage | null>(null);
  
  // Task state
  const [taskTitle, setTaskTitle] = useState('');
  const [taskDueDate, setTaskDueDate] = useState('');
  const [taskPriority, setTaskPriority] = useState('medium');

  // Fetch thread for this specific client
  const { data: inboxes = [], isLoading: loadingInboxes } = useWhatsAppInboxes(clientId);
  const inbox = inboxes[0] || null;
  const inboxId = inbox?.id || null;

  const { data: messages = [], isLoading: loadingMessages } = useWhatsAppMessages(inboxId || undefined);

  const sendMutation = useSendWhatsAppMessage(inboxId || '');
  const convertTaskMutation = useConvertMessageToTask();
  const chatBottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (chatBottomRef.current) {
      chatBottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  if (!clientPhone) {
    return (
      <Card className="p-6 border border-white/5 bg-slate-900/30 text-center text-slate-500">
        <p className="text-xs">Este cliente não possui telefone celular cadastrado.</p>
        <p className="text-[10px] mt-1">Adicione um telefone no resumo cadastral para habilitar o WhatsApp.</p>
      </Card>
    );
  }

  if (loadingInboxes) {
    return (
      <div className="flex h-48 items-center justify-center">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!inbox) {
    return (
      <Card className="p-6 border border-white/5 bg-slate-900/30 text-center text-slate-500">
        <Bot className="h-8 w-8 text-slate-600 mx-auto mb-2" />
        <p className="text-xs">Nenhum histórico de mensagens associado a este telefone (+{clientPhone}).</p>
        <p className="text-[10px] mt-1 max-w-xs mx-auto">
          Escreva uma mensagem no compositor ao lado e use o atalho para abrir o WhatsApp Web, ou aguarde o primeiro contato do cliente para registrar a conversa aqui.
        </p>
      </Card>
    );
  }

  const handleSendReply = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!replyText.trim() || !inboxId) return;

    try {
      await sendMutation.mutateAsync({
        body: replyText,
        message_type: 'text',
      });
      setReplyText('');
    } catch (err: unknown) {
      toast.error(`Erro ao responder: ${getApiErrorMessage(err, 'Falha ao enviar resposta.')}`);
    }
  };

  const handleConvertTask = async () => {
    if (!selectedMessage) return;
    try {
      await convertTaskMutation.mutateAsync({
        messageId: selectedMessage.id,
        title: taskTitle,
        due_date: taskDueDate,
        priority: taskPriority,
      });
      toast.success('Mensagem convertida em tarefa com sucesso!');
      setShowTaskModal(false);
    } catch (err: unknown) {
      toast.error(`Erro ao criar tarefa: ${getApiErrorMessage(err, 'Falha ao criar tarefa.')}`);
    }
  };

  const openTaskModal = (msg: WhatsAppMessage) => {
    setSelectedMessage(msg);
    setTaskTitle(msg.body ? msg.body.substring(0, 55) + (msg.body.length > 55 ? '...' : '') : 'Ajustar pendência contábil');
    setTaskDueDate(new Date(Date.now() + 2 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]);
    setTaskPriority('medium');
    setShowTaskModal(true);
  };

  return (
    <Card className="flex flex-col h-[400px] border border-white/5 bg-slate-900/20 overflow-hidden">
      {/* HEADER */}
      <div className="bg-slate-900/50 px-4 py-2 border-b border-white/5 flex items-center justify-between">
        <span className="text-[10px] font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          Histórico WhatsApp Live
        </span>
        <Badge variant="success" className="text-[8px] py-0 px-1 font-mono">
          +{inbox.phone_number}
        </Badge>
      </div>

      {/* MESSAGES BODY */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-slate-950/10 scrollbar">
        {loadingMessages ? (
          <div className="flex h-full items-center justify-center">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        ) : messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-slate-500 text-center">
            <p className="text-[10px]">Chat vazio. Envie uma mensagem abaixo para iniciar.</p>
          </div>
        ) : (
          messages.map((msg) => {
            const isOutbound = msg.direction === 'outbound';
            return (
              <div key={msg.id} className={`group flex ${isOutbound ? 'justify-end' : 'justify-start'}`}>
                <div className="flex max-w-[80%] flex-col gap-0.5 relative">
                  <div
                    className={`rounded-xl px-3 py-1.5 text-xs border ${
                      isOutbound
                        ? 'bg-teal-500/10 border-teal-500/20 text-slate-100'
                        : 'bg-slate-900 border-white/5 text-slate-100'
                    }`}
                  >
                    {msg.body && <p className="whitespace-pre-wrap leading-relaxed">{msg.body}</p>}
                    
                    {msg.media_url && (
                      <div className="mt-1 bg-slate-950/40 p-2 rounded border border-white/5 space-y-1">
                        <div className="flex items-center gap-1.5 text-[10px] text-slate-300">
                          {msg.message_type === 'image' ? <Image className="h-3 w-3 text-emerald-400" /> : <FileText className="h-3 w-3 text-emerald-400" />}
                          <span className="truncate max-w-[120px]">{msg.body || 'Arquivo'}</span>
                        </div>
                        <a
                          href={msg.media_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[9px] text-teal-400 hover:underline block font-bold"
                        >
                          Baixar
                        </a>
                      </div>
                    )}
                    
                    <span className="block text-[8px] text-slate-500 text-right mt-0.5">
                      {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>

                  {/* HOVER CREATE TASK SHORTCUT */}
                  {!isOutbound && (
                    <button
                      onClick={() => openTaskModal(msg)}
                      title="Converter em Tarefa"
                      className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-6 opacity-0 group-hover:opacity-100 flex h-5 w-5 items-center justify-center rounded-full bg-slate-800 text-teal-400 hover:bg-slate-700 border border-white/10 transition-colors shadow"
                    >
                      <CalendarPlus className="h-3 w-3" />
                    </button>
                  )}
                </div>
              </div>
            );
          })
        )}
        <div ref={chatBottomRef} />
      </div>

      {/* QUICK REPLY COMPOSER FOOTER */}
      <div className="p-2 border-t border-white/5 bg-slate-900/30">
        <form onSubmit={handleSendReply} className="flex gap-1.5">
          <input
            type="text"
            placeholder="Responder pelo WhatsApp..."
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            className="flex-1 rounded-lg border border-white/5 bg-slate-950/60 px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-primary"
          />
          <Button
            type="submit"
            disabled={!replyText.trim() || sendMutation.isPending}
            className="rounded-lg h-8 w-8 p-0 bg-emerald-500 text-slate-950 hover:bg-emerald-400 shrink-0"
          >
            <SendHorizontal className="h-3.5 w-3.5" />
          </Button>
        </form>
      </div>

      {/* ─── CONVERT TASK DIALOG ─── */}
      <Dialog
        open={showTaskModal}
        onClose={() => setShowTaskModal(false)}
        title="Criar Tarefa a partir de Mensagem"
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setShowTaskModal(false)}>
              Cancelar
            </Button>
            <Button
              className="bg-emerald-500 text-slate-950 hover:bg-emerald-400"
              onClick={handleConvertTask}
              disabled={convertTaskMutation.isPending}
            >
              Criar Tarefa
            </Button>
          </div>
        }
      >
        <div className="space-y-4">
          <div className="rounded-xl border border-white/5 bg-slate-950/60 p-3 text-[11px] text-slate-300 font-mono italic">
            "{selectedMessage?.body}"
          </div>
          <FormField label="Título da Tarefa" htmlFor="widget_task_title">
            <Input
              id="widget_task_title"
              value={taskTitle}
              onChange={(e) => setTaskTitle(e.target.value)}
              placeholder="Ex: Enviar folha de pagamento"
            />
          </FormField>
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Data de Vencimento" htmlFor="widget_task_due_date">
              <Input
                id="widget_task_due_date"
                type="date"
                value={taskDueDate}
                onChange={(e) => setTaskDueDate(e.target.value)}
              />
            </FormField>
            <FormField label="Prioridade" htmlFor="widget_task_priority">
              <Select
                id="widget_task_priority"
                value={taskPriority}
                onChange={(e) => setTaskPriority(e.target.value)}
              >
                <option value="low">Baixa</option>
                <option value="medium">Média</option>
                <option value="high">Alta</option>
              </Select>
            </FormField>
          </div>
        </div>
      </Dialog>
    </Card>
  );
}
