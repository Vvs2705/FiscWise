import { useState, useEffect, useRef } from 'react';
import {
  Search,
  SendHorizontal,
  Link2,
  CalendarPlus,
  Paperclip,
  FileText,
  Image,
  Bot,
  CheckCircle,
  AlertCircle,
  ExternalLink,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  useWhatsAppInboxes,
  useWhatsAppMessages,
  useSendWhatsAppMessage,
  useLinkInboxClient,
  useConvertMessageToTask,
  WhatsAppMessage,
} from '@/lib/hooks/useWhatsApp';
import { useClients } from '@/lib/hooks/useOperations';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Dialog } from '@/components/ui/Dialog';
import { FormField } from '@/components/ui/FormField';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';

export function WhatsAppInboxPage() {
  const [selectedInboxId, setSelectedInboxId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [messageText, setMessageText] = useState('');
  const [showLinkModal, setShowLinkModal] = useState(false);
  const [showTaskModal, setShowTaskModal] = useState(false);
  
  // Link Client state
  const [targetClientId, setTargetClientId] = useState<string>('');
  
  // Task conversion state
  const [selectedMessage, setSelectedMessage] = useState<WhatsAppMessage | null>(null);
  const [taskTitle, setTaskTitle] = useState('');
  const [taskDueDate, setTaskDueDate] = useState('');
  const [taskPriority, setTaskPriority] = useState('medium');

  // WhatsApp Hook queries
  const { data: inboxes = [], isLoading: loadingInboxes } = useWhatsAppInboxes();
  const { data: messages = [], isLoading: loadingMessages } = useWhatsAppMessages(selectedInboxId || undefined);
  const { data: clients = [] } = useClients();

  // Selected Inbox Object
  const selectedInbox = inboxes.find((i) => i.id === selectedInboxId) || null;

  // Scroll ref for chat messages
  const chatBottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (chatBottomRef.current) {
      chatBottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Mutations
  const sendMutation = useSendWhatsAppMessage(selectedInboxId || '');
  const linkMutation = useLinkInboxClient(selectedInboxId || '');
  const convertTaskMutation = useConvertMessageToTask();

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!messageText.trim() || !selectedInboxId) return;

    try {
      await sendMutation.mutateAsync({
        body: messageText,
        message_type: 'text',
      });
      setMessageText('');
    } catch (err: any) {
      toast.error('Erro ao enviar mensagem: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleLinkClient = async () => {
    if (!selectedInboxId) return;
    try {
      await linkMutation.mutateAsync(targetClientId || null);
      toast.success(targetClientId ? 'Conversa vinculada com sucesso!' : 'Conversa desvinculada com sucesso!');
      setShowLinkModal(false);
    } catch (err: any) {
      toast.error('Erro ao vincular cliente: ' + (err.response?.data?.detail || err.message));
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
      toast.success('Mensagem convertida em tarefa contábil com sucesso!');
      setShowTaskModal(false);
    } catch (err: any) {
      toast.error('Erro ao criar tarefa: ' + (err.response?.data?.detail || err.message));
    }
  };

  const openTaskModal = (msg: WhatsAppMessage) => {
    setSelectedMessage(msg);
    setTaskTitle(msg.body ? msg.body.substring(0, 50) + (msg.body.length > 50 ? '...' : '') : 'Ajustar pendência contábil');
    setTaskDueDate(new Date(Date.now() + 2 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]); // Default 2 days from now
    setTaskPriority('medium');
    setShowTaskModal(true);
  };

  // Filter inboxes based on query
  const filteredInboxes = inboxes.filter((i) => {
    const name = i.customer_name?.toLowerCase() || '';
    const phone = i.phone_number.toLowerCase();
    const query = searchQuery.toLowerCase();
    return name.includes(query) || phone.includes(query);
  });

  const getInitials = (name: string) => {
    if (!name) return 'U';
    return name.split(' ').map((n) => n[0]).slice(0, 2).join('').toUpperCase();
  };

  // Fast Quick Reply Template Dispatcher
  const insertTemplate = (templateType: 'das' | 'docs' | 'certificado') => {
    if (!selectedInbox) return;
    const clientName = selectedInbox.customer_name || 'Prezado(a)';
    let text = '';
    if (templateType === 'das') {
      text = `Olá ${clientName}, sua guia DAS mensal já está disponível para pagamento em seu portal FiscWise.`;
    } else if (templateType === 'docs') {
      text = `Olá ${clientName}, constatamos a ausência de documentos obrigatórios para fechamento deste mês. Por favor, envie os arquivos pendentes.`;
    } else if (templateType === 'certificado') {
      text = `Olá ${clientName}, informamos que seu certificado digital A1 está próximo do vencimento. Favor providenciar a renovação.`;
    }
    setMessageText(text);
  };

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-5 overflow-hidden">
      {/* LEFT COLUMN: INBOX THREADS */}
      <Card className="flex w-80 shrink-0 flex-col overflow-hidden border border-white/5 bg-slate-900/40 backdrop-blur-xl">
        <div className="border-b border-white/5 p-4 space-y-3">
          <h2 className="text-sm font-bold text-white uppercase tracking-wider">
            WhatsApp Central
          </h2>
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Buscar contatos..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-xl border border-white/5 bg-slate-950/60 py-2 pl-9 pr-4 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-primary focus:border-transparent"
            />
          </div>
        </div>

        {/* THREADS LIST */}
        <div className="flex-1 overflow-y-auto divide-y divide-white/5 scrollbar">
          {loadingInboxes ? (
            <div className="flex h-32 items-center justify-center">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            </div>
          ) : filteredInboxes.length === 0 ? (
            <div className="flex h-32 flex-col items-center justify-center text-slate-500 p-4 text-center">
              <p className="text-xs">Nenhuma conversa encontrada.</p>
            </div>
          ) : (
            filteredInboxes.map((inbox) => {
              const isSelected = inbox.id === selectedInboxId;
              return (
                <div
                  key={inbox.id}
                  onClick={() => {
                    setSelectedInboxId(inbox.id);
                    setTargetClientId(inbox.client_id || '');
                  }}
                  className={`flex cursor-pointer items-start gap-3 p-4 transition-colors hover:bg-white/5 ${
                    isSelected ? 'bg-white/5 border-l-2 border-primary' : ''
                  }`}
                >
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-800 text-xs font-bold text-slate-300">
                    {getInitials(inbox.customer_name || '')}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between">
                      <p className="truncate text-xs font-semibold text-slate-200">
                        {inbox.customer_name}
                      </p>
                      {inbox.last_message_at && (
                        <span className="text-[9px] text-slate-500">
                          {new Date(inbox.last_message_at).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </span>
                      )}
                    </div>
                    <p className="truncate text-[11px] text-slate-400 mt-0.5">
                      {inbox.last_message_preview || 'Nenhuma mensagem'}
                    </p>
                    <div className="flex items-center justify-between mt-1">
                      <span className="text-[9px] text-slate-500 font-mono">
                        +{inbox.phone_number}
                      </span>
                      <div className="flex items-center gap-1.5">
                        {inbox.client_id ? (
                          <Badge variant="success" className="text-[8px] py-0 px-1 shrink-0">
                            Vinculado
                          </Badge>
                        ) : (
                          <Badge variant="warning" className="text-[8px] py-0 px-1 shrink-0">
                            Sem Cliente
                          </Badge>
                        )}
                        {inbox.unread_count > 0 && (
                          <span className="flex h-4 w-4 items-center justify-center rounded-full bg-emerald-500 text-[9px] font-bold text-slate-950">
                            {inbox.unread_count}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </Card>

      {/* RIGHT COLUMN: ACTIVE CONVERSATION */}
      <Card className="flex flex-1 flex-col overflow-hidden border border-white/5 bg-slate-900/40 backdrop-blur-xl">
        {selectedInbox ? (
          <>
            {/* CONVERSATION HEADER */}
            <div className="flex items-center justify-between border-b border-white/5 px-6 py-4">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-800 text-xs font-bold text-slate-300">
                  {getInitials(selectedInbox.customer_name || '')}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wide">
                      {selectedInbox.customer_name}
                    </h3>
                    <span className="text-[10px] text-slate-400 font-mono">
                      (+{selectedInbox.phone_number})
                    </span>
                  </div>
                  <div className="flex items-center gap-2 mt-0.5">
                    {selectedInbox.client_id ? (
                      <span className="text-[10px] text-emerald-400 flex items-center gap-1">
                        <CheckCircle className="h-3 w-3" />
                        Cliente vinculado
                      </span>
                    ) : (
                      <span className="text-[10px] text-amber-500 flex items-center gap-1">
                        <AlertCircle className="h-3 w-3" />
                        Sem cliente vinculado
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* ACTIONS */}
              <div className="flex gap-2">
                <Button
                  onClick={() => setShowLinkModal(true)}
                  variant="ghost"
                  className="h-8 gap-1.5 text-xs text-slate-300 hover:bg-white/5 border border-white/10"
                >
                  <Link2 className="h-3.5 w-3.5" />
                  Vincular Cliente
                </Button>
                {selectedInbox.client_id && (
                  <Button
                    onClick={() => {
                      window.open(`/clientes/${selectedInbox.client_id}`, '_blank');
                    }}
                    variant="ghost"
                    className="h-8 gap-1.5 text-xs text-slate-300 hover:bg-white/5 border border-white/10"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                    Ver Cadastro
                  </Button>
                )}
              </div>
            </div>

            {/* MESSAGES THREAD SCROLLABLE BODY */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-slate-950/20 scrollbar">
              {loadingMessages ? (
                <div className="flex h-full items-center justify-center">
                  <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                </div>
              ) : messages.length === 0 ? (
                <div className="flex h-full flex-col items-center justify-center text-slate-500">
                  <Bot className="h-8 w-8 text-slate-600 mb-2" />
                  <p className="text-xs">Nenhuma mensagem neste chat.</p>
                  <p className="text-[10px] text-slate-600 mt-1">
                    Envie uma mensagem abaixo para iniciar.
                  </p>
                </div>
              ) : (
                messages.map((msg) => {
                  const isOutbound = msg.direction === 'outbound';
                  return (
                    <div
                      key={msg.id}
                      className={`group flex ${isOutbound ? 'justify-end' : 'justify-start'}`}
                    >
                      <div className="flex max-w-[70%] flex-col gap-1 relative">
                        <div
                          className={`rounded-2xl px-4 py-2.5 text-xs shadow-sm border ${
                            isOutbound
                              ? 'bg-gradient-to-r from-teal-500/20 to-teal-400/10 border-teal-500/20 text-slate-100'
                              : 'bg-slate-900 border-white/5 text-slate-100'
                          }`}
                        >
                          {/* SENDER LABEL (IF INBOUND AND NAME EXISTS) */}
                          {!isOutbound && msg.sender_name && (
                            <p className="font-bold text-[10px] text-teal-400 mb-1">
                              {msg.sender_name}
                            </p>
                          )}

                          {/* BODY MESSAGE */}
                          {msg.body && <p className="whitespace-pre-wrap leading-relaxed">{msg.body}</p>}

                          {/* MEDIA ANEXO IF DOCUMENT/IMAGE */}
                          {msg.media_url && (
                            <div className="mt-2 rounded-xl bg-slate-950/40 p-3 border border-white/5 space-y-2">
                              <div className="flex items-center gap-2">
                                {msg.message_type === 'image' ? (
                                  <Image className="h-4 w-4 text-emerald-400" />
                                ) : (
                                  <FileText className="h-4 w-4 text-emerald-400" />
                                )}
                                <span className="text-[10px] truncate text-slate-300 font-medium">
                                  {msg.body || 'Arquivo recebido'}
                                </span>
                              </div>
                              <div className="flex gap-2">
                                <a
                                  href={msg.media_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-[9px] font-bold text-teal-400 hover:underline flex items-center gap-1"
                                >
                                  <Paperclip className="h-3 w-3" />
                                  Baixar Arquivo
                                </a>
                                <Badge variant="success" className="text-[8px] py-0 px-1 flex items-center gap-1 select-none">
                                  <CheckCircle className="h-2 w-2" />
                                  Coletado Auto
                                </Badge>
                              </div>
                            </div>
                          )}

                          {/* FOOTER BUBBLE INFO */}
                          <div className="flex items-center justify-end gap-1.5 mt-1 text-[8px] text-slate-500">
                            <span>
                              {new Date(msg.created_at).toLocaleTimeString([], {
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </span>
                          </div>
                        </div>

                        {/* HOVER CONVERT MESSAGE TO TASK BUTTON */}
                        {!isOutbound && (
                          <div className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-8 opacity-0 transition-opacity group-hover:opacity-100">
                            <button
                              onClick={() => openTaskModal(msg)}
                              title="Converter em Tarefa da Agenda"
                              className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-800 hover:bg-slate-700 text-teal-400 border border-white/10 hover:border-primary/40 transition-colors shadow"
                            >
                              <CalendarPlus className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
              <div ref={chatBottomRef} />
            </div>

            {/* QUICK TEMPLATE SHORTCUT BAR */}
            <div className="border-t border-white/5 px-6 py-2 bg-slate-900/60 flex items-center gap-2">
              <span className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">
                Respostas rápidas:
              </span>
              <button
                onClick={() => insertTemplate('das')}
                className="text-[10px] bg-slate-800 hover:bg-slate-700 text-slate-300 px-2 py-1 rounded-lg border border-white/5 transition-colors"
              >
                Guia DAS
              </button>
              <button
                onClick={() => insertTemplate('docs')}
                className="text-[10px] bg-slate-800 hover:bg-slate-700 text-slate-300 px-2 py-1 rounded-lg border border-white/5 transition-colors"
              >
                Cobrar Documentos
              </button>
              <button
                onClick={() => insertTemplate('certificado')}
                className="text-[10px] bg-slate-800 hover:bg-slate-700 text-slate-300 px-2 py-1 rounded-lg border border-white/5 transition-colors"
              >
                Certificado Digital
              </button>
            </div>

            {/* COMPOSE TEXT INPUT FOOTER */}
            <div className="border-t border-white/5 p-4 bg-slate-900/40">
              <form onSubmit={handleSendMessage} className="flex gap-2">
                <input
                  type="text"
                  placeholder="Escreva uma mensagem..."
                  value={messageText}
                  onChange={(e) => setMessageText(e.target.value)}
                  className="flex-1 rounded-xl border border-white/5 bg-slate-950/60 px-4 py-3 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-primary focus:border-transparent"
                />
                <Button
                  type="submit"
                  disabled={!messageText.trim() || sendMutation.isPending}
                  className="rounded-xl px-4 bg-emerald-500 text-slate-950 hover:bg-emerald-400 shrink-0"
                >
                  <SendHorizontal className="h-4 w-4" />
                </Button>
              </form>
            </div>
          </>
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center text-slate-500">
            <Bot className="h-10 w-10 text-slate-600 mb-2" />
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Nenhuma conversa selecionada
            </h3>
            <p className="text-[10px] text-slate-500 mt-1 max-w-xs text-center">
              Selecione um contato na barra lateral esquerda para visualizar o histórico de mensagens e iniciar o atendimento contábil via WhatsApp.
            </p>
          </div>
        )}
      </Card>

      {/* ─── LINK CLIENT DIALOG ────────────────────────────────────────────────── */}
      <Dialog
        open={showLinkModal}
        onClose={() => setShowLinkModal(false)}
        title="Vincular Conversa a um Cliente"
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setShowLinkModal(false)}>
              Cancelar
            </Button>
            <Button
              className="bg-emerald-500 text-slate-950 hover:bg-emerald-400"
              onClick={handleLinkClient}
              disabled={linkMutation.isPending}
            >
              Vincular
            </Button>
          </div>
        }
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-400">
            Vincular esta conversa a um cliente contábil permite arquivar automaticamente os documentos enviados por ele e associar prazos de entrega e relatórios.
          </p>
          <FormField label="Selecione o Cliente" htmlFor="link_client_id">
            <Select
              id="link_client_id"
              value={targetClientId}
              onChange={(e) => setTargetClientId(e.target.value)}
            >
              <option value="">-- Desvincular Conversa --</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} (CNPJ: {c.document || 'N/D'})
                </option>
              ))}
            </Select>
          </FormField>
        </div>
      </Dialog>

      {/* ─── CONVERT MESSAGE TO TASK DIALOG ────────────────────────────────────── */}
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
          <p className="text-xs text-slate-400 leading-relaxed">
            Isto criará um prazo operacional na agenda de prazos do cliente. O corpo da mensagem será copiado como descrição detalhada da tarefa.
          </p>
          <div className="rounded-xl border border-white/5 bg-slate-950/60 p-3 text-[11px] text-slate-300 font-mono italic">
            "{selectedMessage?.body}"
          </div>
          <FormField label="Título da Tarefa" htmlFor="task_title">
            <Input
              id="task_title"
              value={taskTitle}
              onChange={(e) => setTaskTitle(e.target.value)}
              placeholder="Ex: Enviar folha de pagamento"
            />
          </FormField>
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Data de Vencimento" htmlFor="task_due_date">
              <Input
                id="task_due_date"
                type="date"
                value={taskDueDate}
                onChange={(e) => setTaskDueDate(e.target.value)}
              />
            </FormField>
            <FormField label="Prioridade" htmlFor="task_priority">
              <Select
                id="task_priority"
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
    </div>
  );
}
