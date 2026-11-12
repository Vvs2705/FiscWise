import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  CheckCircle,
  Calendar,
  Key,
  DollarSign,
  ChevronRight,
  Sparkles,
  Clock,
  Send,
  User,
  ArrowRight,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  useDeadlines,
  useCertificates,
  useReceivables,
  useClients,
  useUpdateDeadline,
  useUpdateReceivable,
  moneyBRL,
  dateBR,
  type AccountReceivable,
  type DeadlineItem,
  type DigitalCertificate,
} from '@/lib/hooks/useOperations';
import { Button } from '@/components/ui/Button';
import { getApiErrorMessage } from '@/lib/api';
import {
  describeClientEmailResult,
  useSendClientReminder,
  type ClientReminderKind,
} from '@/lib/hooks/useNotifications';
import { focusQueueState } from './focusQueue';
import { addLocalDays, parseLocalDate, toLocalISODate } from '@/lib/dates';

interface ModoFocoModalProps {
  isOpen: boolean;
  onClose: () => void;
  beforeScore: number;
}

interface FocusTask {
  id: string;
  type: 'deadline' | 'certificate' | 'receivable';
  title: string;
  clientName: string;
  dueDate: string;
  description: string;
  originalItem: DeadlineItem | DigitalCertificate | AccountReceivable;
}

export function ModoFocoModal({ isOpen, onClose, beforeScore }: ModoFocoModalProps) {
  const { data: clients = [] } = useClients();
  const { data: deadlines = [] } = useDeadlines();
  const { data: certificates = [] } = useCertificates();
  const { data: receivables = [] } = useReceivables();

  const updateDeadlineMutation = useUpdateDeadline();
  const updateReceivableMutation = useUpdateReceivable();

  const sendReminder = useSendClientReminder();

  // Ids das tarefas já tratadas (resolvidas, adiadas, puladas): ver focusQueue.ts.
  const [handledIds, setHandledIds] = useState<ReadonlySet<string>>(() => new Set());
  const [direction, setDirection] = useState(0); // -1 for left, 1 for right
  const [resolvedCount, setResolvedCount] = useState(0);
  const [snoozedCount, setSnoozedCount] = useState(0);
  const [skippedCount, setSkippedCount] = useState(0);

  // Clients mapping for fast lookup
  const clientMap = useMemo(() => {
    return new Map(clients.map((c) => [c.id, c.name]));
  }, [clients]);

  // Compile pending tasks
  const focusTasks = useMemo(() => {
    const list: FocusTask[] = [];

    // 1. Pending or overdue deadlines due today or in the past
    const todayStr = new Date().toISOString().split('T')[0];
    deadlines.forEach((dl) => {
      if (dl.status === 'pending' || dl.status === 'overdue') {
        const isPastOrToday = dl.due_date <= todayStr;
        if (isPastOrToday) {
          list.push({
            id: `deadline-${dl.id}`,
            type: 'deadline',
            title: dl.title,
            clientName: clientMap.get(dl.client_id) || 'Cliente não identificado',
            dueDate: dl.due_date,
            description: dl.description || `${dl.category} - Compromisso operacional.`,
            originalItem: dl,
          });
        }
      }
    });

    // 2. Certificates expiring in next 30 days
    const next30Days = new Date();
    next30Days.setDate(next30Days.getDate() + 30);
    const next30DaysStr = next30Days.toISOString().split('T')[0];
    
    certificates.forEach((cert) => {
      if (cert.status === 'expiring' || (cert.valid_until <= next30DaysStr && cert.status !== 'expired' && cert.status !== 'revoked')) {
        list.push({
          id: `certificate-${cert.id}`,
          type: 'certificate',
          title: `Renovar Certificado: ${cert.label}`,
          clientName: clientMap.get(cert.client_id) || 'Cliente não identificado',
          dueDate: cert.valid_until,
          description: `Certificado do tipo ${cert.certificate_type.toUpperCase()} está próximo do vencimento.`,
          originalItem: cert,
        });
      }
    });

    // 3. Overdue accounts receivables
    receivables.forEach((rec) => {
      if (rec.status === 'overdue') {
        list.push({
          id: `receivable-${rec.id}`,
          type: 'receivable',
          title: `Cobrança: ${rec.description}`,
          clientName: clientMap.get(rec.client_id) || 'Cliente não identificado',
          dueDate: rec.due_date,
          description: `Mensalidade em atraso no valor de ${moneyBRL(rec.amount)}.`,
          originalItem: rec,
        });
      }
    });

    return list;
  }, [deadlines, certificates, receivables, clientMap]);

  const queue = focusQueueState(focusTasks, handledIds);
  const currentTask = queue.current;
  const totalTasks = queue.total;
  const isCompleted = queue.finished;
  const busy =
    sendReminder.isPending || updateDeadlineMutation.isPending || updateReceivableMutation.isPending;

  if (!isOpen) return null;

  const markHandled = (taskId: string) => {
    setDirection(1);
    setHandledIds((prev) => new Set(prev).add(taskId));
  };

  /** Envia o lembrete por e-mail; devolve true só se o provedor aceitou. */
  const remindClient = async (task: FocusTask): Promise<boolean> => {
    const clientId = (task.originalItem as { client_id: string }).client_id;
    let kind: ClientReminderKind = 'custom';
    let message: string | undefined;
    if (task.type === 'receivable') {
      kind = 'payment';
    } else if (task.type === 'certificate') {
      const cert = task.originalItem as DigitalCertificate;
      message =
        `Olá ${task.clientName},\n\n` +
        `O certificado digital "${cert.label}" vence em ${dateBR(cert.valid_until)}. ` +
        'Sem ele não conseguimos emitir notas nem acessar os sistemas da Receita em seu nome.\n\n' +
        'Por favor, providencie a renovação e nos envie o novo certificado.\n\n' +
        'Atenciosamente,\nSeu escritório contábil';
    } else {
      kind = 'pending_documents';
    }
    try {
      const result = await sendReminder.mutateAsync({ clientId, kind, message });
      const t = describeClientEmailResult(result);
      toast[t.kind](t.message);
      return result.sent;
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Erro ao enviar o lembrete.'));
      return false;
    }
  };

  const handleResolve = async () => {
    if (!currentTask || busy) return;
    const task = currentTask;

    try {
      if (task.type === 'deadline') {
        await updateDeadlineMutation.mutateAsync({
          id: task.originalItem.id,
          payload: { status: 'completed' },
        });
        toast.success('Tarefa marcada como concluída!');
      } else if (task.type === 'receivable') {
        await updateReceivableMutation.mutateAsync({
          id: task.originalItem.id,
          payload: { status: 'paid', paid_at: new Date().toISOString().split('T')[0] },
        });
        toast.success('Honorário marcado como pago!');
      } else if (task.type === 'certificate') {
        // Só conta como resolvida se o e-mail saiu de verdade.
        if (!(await remindClient(task))) return;
      }
      setResolvedCount((prev) => prev + 1);
      markHandled(task.id);
    } catch {
      toast.error('Erro ao resolver tarefa.');
    }
  };

  const handleSnooze = async () => {
    if (!currentTask || busy || currentTask.type === 'certificate') return;
    const task = currentTask;

    try {
      // Postpone by 7 days
      const currentDueDate = parseLocalDate(currentTask.dueDate) ?? new Date();
      const newDueDateStr = toLocalISODate(addLocalDays(currentDueDate, 7));

      if (task.type === 'deadline') {
        await updateDeadlineMutation.mutateAsync({
          id: task.originalItem.id,
          payload: { due_date: newDueDateStr },
        });
        toast.success(`Tarefa adiada para ${dateBR(newDueDateStr)}`);
      } else if (task.type === 'receivable') {
        await updateReceivableMutation.mutateAsync({
          id: task.originalItem.id,
          payload: { due_date: newDueDateStr },
        });
        toast.success(`Cobrança adiada para ${dateBR(newDueDateStr)}`);
      }
      setSnoozedCount((prev) => prev + 1);
      markHandled(task.id);
    } catch {
      toast.error('Erro ao adiar tarefa.');
    }
  };

  const handleWaitingClient = async () => {
    if (!currentTask || busy) return;
    const task = currentTask;

    try {
      if (task.type === 'deadline') {
        await updateDeadlineMutation.mutateAsync({
          id: task.originalItem.id,
          payload: { description: `[Aguardando Cliente] ${task.description}` },
        });
        toast.success('Marcado como aguardando cliente');
      } else if (!(await remindClient(task))) {
        // Lembrete não saiu: a tarefa continua na fila.
        return;
      }
      setResolvedCount((prev) => prev + 1); // treat as addressed
      markHandled(task.id);
    } catch {
      toast.error('Erro ao atualizar status.');
    }
  };

  const handleSkip = () => {
    if (!currentTask) return;
    setSkippedCount((prev) => prev + 1);
    markHandled(currentTask.id);
  };

  const taskTypeConfig = {
    deadline: {
      label: 'Obrigação Fiscal',
      icon: Calendar,
      color: 'text-warning bg-warning/10 border-warning/30',
      actionLabel: 'Concluir Obrigação',
    },
    certificate: {
      label: 'Certificado Digital',
      icon: Key,
      color: 'text-primary bg-primary/10 border-primary/30',
      actionLabel: 'Notificar Cliente',
    },
    receivable: {
      label: 'Cobrança / Honorário',
      icon: DollarSign,
      color: 'text-success bg-success/10 border-success/30',
      actionLabel: 'Confirmar Pagamento',
    },
  };

  const slideVariants = {
    enter: (dir: number) => ({
      x: dir > 0 ? 300 : -300,
      opacity: 0,
    }),
    center: {
      x: 0,
      opacity: 1,
    },
    exit: (dir: number) => ({
      x: dir < 0 ? 300 : -300,
      opacity: 0,
    }),
  };

  // Re-calculate mock score improvement
  const afterScore = Math.min(100, beforeScore + resolvedCount * 4 + snoozedCount * 2);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 p-4 backdrop-blur-sm">
      <div className="relative w-full max-w-2xl overflow-hidden rounded-panel border border-border bg-card shadow-token">

        {/* Header decoration */}
        <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-primary to-transparent" />

        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary animate-pulse" />
            <h2 className="text-lg font-bold text-foreground tracking-wide uppercase">Modo Foco</h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-full border border-border bg-muted p-1.5 text-muted-foreground hover:text-foreground transition"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Progress bar */}
        {totalTasks > 0 && !isCompleted && (
          <div className="h-1 w-full bg-muted">
            <div
              className="h-full bg-gradient-to-r from-primary to-primary/60 transition-all duration-300"
              style={{ width: `${(queue.position / totalTasks) * 100}%` }}
            />
          </div>
        )}

        <div className="p-6 md:p-8">
          {totalTasks === 0 ? (
            <div className="text-center py-10 space-y-4">
              <CheckCircle className="h-16 w-16 text-success mx-auto" />
              <h3 className="text-xl font-bold text-foreground">Nenhuma pendência crítica</h3>
              <p className="text-sm text-muted-foreground max-w-md mx-auto">
                Sua carteira está 100% atualizada para hoje! Não há obrigações atrasadas, certificados vencendo ou mensalidades pendentes.
              </p>
              <Button onClick={onClose} className="mt-4">
                Voltar ao Painel
              </Button>
            </div>
          ) : isCompleted || !currentTask ? (
            /* SUCCESS COMPLETION SCREEN */
            <div className="text-center py-6 space-y-6">
              <div className="relative inline-block">
                <div className="absolute inset-0 bg-primary/20 blur-xl rounded-full" />
                <div className="relative border border-primary/30 bg-primary/10 p-5 rounded-full text-primary">
                  <CheckCircle className="h-12 w-12" />
                </div>
              </div>
              <div className="space-y-2">
                <h3 className="text-2xl font-bold text-foreground">Modo Foco Concluído!</h3>
                <p className="text-sm text-muted-foreground max-w-md mx-auto">
                  Excelente trabalho! Você resolveu e organizou suas pendências mais críticas de hoje de forma eficiente.
                </p>
              </div>

              {/* Stats Grid */}
              <div className="grid grid-cols-3 gap-3 max-w-md mx-auto bg-muted border border-border rounded-card p-4 text-xs font-semibold">
                <div>
                  <span className="text-success block text-lg font-bold">{resolvedCount}</span>
                  <span className="text-muted-foreground">Resolvidos</span>
                </div>
                <div>
                  <span className="text-warning block text-lg font-bold">{snoozedCount}</span>
                  <span className="text-muted-foreground">Adiados</span>
                </div>
                <div>
                  <span className="text-foreground block text-lg font-bold">{skippedCount}</span>
                  <span className="text-muted-foreground">Pulados</span>
                </div>
              </div>

              {/* Score impact display */}
              <div className="flex items-center justify-center gap-4 bg-gradient-to-r from-primary/10 to-primary/5 border border-primary/20 rounded-card p-4 max-w-md mx-auto">
                <div className="text-right">
                  <p className="text-[10px] uppercase font-bold text-muted-foreground">Score Anterior</p>
                  <p className="text-xl font-bold text-foreground">{beforeScore}</p>
                </div>
                <ArrowRight className="text-primary h-5 w-5 shrink-0" />
                <div className="text-left">
                  <p className="text-[10px] uppercase font-bold text-primary">Novo Score Estimado</p>
                  <p className="text-2xl font-extrabold text-success flex items-center gap-1.5">
                    {afterScore}
                    <Sparkles className="h-4 w-4 animate-bounce text-primary" />
                  </p>
                </div>
              </div>

              <div className="flex justify-center gap-3 pt-4">
                <Button onClick={onClose} variant="default" className="px-8 py-3 rounded-full">
                  Voltar ao Painel
                </Button>
              </div>
            </div>
          ) : (
            /* ACTIVE FOCUS STACK CARD */
            <div className="space-y-6">
              {/* Stepper info */}
              <div className="flex justify-between items-center text-xs font-semibold text-muted-foreground">
                <span>TAREFA {queue.position} DE {totalTasks}</span>
                <span className="px-2 py-0.5 rounded bg-muted border border-border uppercase tracking-wider text-primary">
                  {taskTypeConfig[currentTask.type].label}
                </span>
              </div>

              {/* Active task slider */}
              <div className="relative min-h-[160px] flex items-center">
                <AnimatePresence mode="wait" custom={direction}>
                  <motion.div
                    key={currentTask.id}
                    custom={direction}
                    variants={slideVariants}
                    initial="enter"
                    animate="center"
                    exit="exit"
                    transition={{ x: { type: 'spring', stiffness: 300, damping: 30 }, opacity: { duration: 0.2 } }}
                    className="w-full space-y-4"
                  >
                    {/* Task type badge & Client name */}
                    <div className="flex items-start gap-4">
                      <div className={`p-3 rounded-card border shrink-0 ${taskTypeConfig[currentTask.type].color}`}>
                        {(() => {
                          const IconComponent = taskTypeConfig[currentTask.type].icon;
                          return <IconComponent className="h-6 w-6" />;
                        })()}
                      </div>
                      <div className="space-y-1">
                        <span className="flex items-center gap-1.5 text-xs text-muted-foreground font-semibold">
                          <User className="h-3.5 w-3.5" />
                          {currentTask.clientName}
                        </span>
                        <h3 className="text-xl font-bold text-foreground tracking-tight leading-snug">
                          {currentTask.title}
                        </h3>
                      </div>
                    </div>

                    <div className="border border-border bg-muted rounded-card p-4 text-sm text-foreground leading-relaxed">
                      {currentTask.description}
                    </div>

                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-semibold font-mono">
                      <Clock className="h-3.5 w-3.5" />
                      Prazo original: {dateBR(currentTask.dueDate)}
                    </div>
                  </motion.div>
                </AnimatePresence>
              </div>

              {/* Action Buttons Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-6 border-t border-border">
                <button
                  onClick={handleResolve}
                  disabled={busy}
                  className="disabled:opacity-60 inline-flex items-center justify-center gap-1.5 rounded-card bg-success text-success-foreground py-3 text-xs font-bold hover:bg-success/90 active:scale-98 transition shadow-token-sm"
                >
                  <CheckCircle className="h-4 w-4" />
                  {taskTypeConfig[currentTask.type].actionLabel}
                </button>
                {/* Certificado não tem "lembrar em" persistido: sem opção de adiar. */}
                {currentTask.type !== 'certificate' && (
                  <button
                    onClick={handleSnooze}
                    disabled={busy}
                    className="disabled:opacity-60 inline-flex items-center justify-center gap-1.5 rounded-card border border-warning/20 bg-warning/10 text-warning py-3 text-xs font-bold hover:bg-warning/20 active:scale-98 transition"
                  >
                    <Clock className="h-4 w-4" />
                    Adiar 7 dias
                  </button>
                )}
                <button
                  onClick={handleWaitingClient}
                  disabled={busy}
                  className="disabled:opacity-60 inline-flex items-center justify-center gap-1.5 rounded-card border border-primary/20 bg-primary/10 text-primary py-3 text-xs font-bold hover:bg-primary/20 active:scale-98 transition"
                >
                  <Send className="h-4 w-4" />
                  {currentTask.type === 'deadline' ? 'Aguardar Cliente' : 'Lembrar por E-mail'}
                </button>
                <button
                  onClick={handleSkip}
                  className="inline-flex items-center justify-center gap-1.5 rounded-card border border-border bg-muted text-foreground py-3 text-xs font-bold hover:bg-muted/80 active:scale-98 transition"
                >
                  Pular
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
