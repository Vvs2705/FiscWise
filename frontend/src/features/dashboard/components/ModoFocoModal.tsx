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

  const [currentIndex, setCurrentIndex] = useState(0);
  const [direction, setDirection] = useState(0); // -1 for left, 1 for right
  const [resolvedCount, setResolvedCount] = useState(0);
  const [snoozedCount, setSnoozedCount] = useState(0);
  const [skippedCount, setSkippedCount] = useState(0);
  const [isCompleted, setIsCompleted] = useState(false);

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

  const currentTask = focusTasks[currentIndex];
  const totalTasks = focusTasks.length;

  if (!isOpen) return null;

  const handleNext = () => {
    if (currentIndex + 1 < totalTasks) {
      setDirection(1);
      setCurrentIndex((prev) => prev + 1);
    } else {
      setIsCompleted(true);
    }
  };

  const handleResolve = async () => {
    if (!currentTask) return;

    try {
      if (currentTask.type === 'deadline') {
        await updateDeadlineMutation.mutateAsync({
          id: currentTask.originalItem.id,
          payload: { status: 'completed' },
        });
        toast.success('Tarefa marcada como concluída!');
      } else if (currentTask.type === 'receivable') {
        await updateReceivableMutation.mutateAsync({
          id: currentTask.originalItem.id,
          payload: { status: 'paid', paid_at: new Date().toISOString().split('T')[0] },
        });
        toast.success('Honorário marcado como pago!');
      } else if (currentTask.type === 'certificate') {
        // Mock certificate notification/renewal trigger
        toast.success('Lembrete enviado ao cliente!');
      }
      setResolvedCount((prev) => prev + 1);
      handleNext();
    } catch {
      toast.error('Erro ao resolver tarefa.');
    }
  };

  const handleSnooze = async () => {
    if (!currentTask) return;

    try {
      // Postpone by 7 days
      const currentDueDate = new Date(currentTask.dueDate);
      currentDueDate.setDate(currentDueDate.getDate() + 7);
      const newDueDateStr = currentDueDate.toISOString().split('T')[0];

      if (currentTask.type === 'deadline') {
        await updateDeadlineMutation.mutateAsync({
          id: currentTask.originalItem.id,
          payload: { due_date: newDueDateStr },
        });
        toast.success(`Tarefa adiada para ${dateBR(newDueDateStr)}`);
      } else if (currentTask.type === 'receivable') {
        await updateReceivableMutation.mutateAsync({
          id: currentTask.originalItem.id,
          payload: { due_date: newDueDateStr },
        });
        toast.success(`Cobrança adiada para ${dateBR(newDueDateStr)}`);
      } else if (currentTask.type === 'certificate') {
        toast.success('Aviso adiado por 7 dias');
      }
      setSnoozedCount((prev) => prev + 1);
      handleNext();
    } catch {
      toast.error('Erro ao adiar tarefa.');
    }
  };

  const handleWaitingClient = async () => {
    if (!currentTask) return;

    try {
      if (currentTask.type === 'deadline') {
        await updateDeadlineMutation.mutateAsync({
          id: currentTask.originalItem.id,
          payload: { description: `[Aguardando Cliente] ${currentTask.description}` },
        });
        toast.success('Marcado como aguardando cliente');
      } else {
        toast.success('Lembrete reforçado com o cliente');
      }
      setResolvedCount((prev) => prev + 1); // treat as addressed
      handleNext();
    } catch {
      toast.error('Erro ao atualizar status.');
    }
  };

  const handleSkip = () => {
    setSkippedCount((prev) => prev + 1);
    setDirection(1);
    handleNext();
  };

  const taskTypeConfig = {
    deadline: {
      label: 'Obrigação Fiscal',
      icon: Calendar,
      color: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
      actionLabel: 'Concluir Obrigação',
    },
    certificate: {
      label: 'Certificado Digital',
      icon: Key,
      color: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30',
      actionLabel: 'Notificar Cliente',
    },
    receivable: {
      label: 'Cobrança / Honorário',
      icon: DollarSign,
      color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm">
      <div className="relative w-full max-w-2xl overflow-hidden rounded-[32px] border border-white/10 bg-[#090f19] shadow-2xl">
        
        {/* Header decoration */}
        <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-cyan-400 to-transparent" />

        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-white/5 px-6 py-4">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-cyan-300 animate-pulse" />
            <h2 className="text-lg font-bold text-white tracking-wide uppercase">Modo Foco</h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-full border border-white/10 bg-white/5 p-1.5 text-slate-400 hover:text-white transition"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Progress bar */}
        {totalTasks > 0 && !isCompleted && (
          <div className="h-1 w-full bg-white/5">
            <div
              className="h-full bg-gradient-to-r from-cyan-400 to-teal-400 transition-all duration-300"
              style={{ width: `${((currentIndex + 1) / totalTasks) * 100}%` }}
            />
          </div>
        )}

        <div className="p-6 md:p-8">
          {totalTasks === 0 ? (
            <div className="text-center py-10 space-y-4">
              <CheckCircle className="h-16 w-16 text-emerald-400 mx-auto" />
              <h3 className="text-xl font-bold text-white">Nenhuma pendência crítica</h3>
              <p className="text-sm text-slate-400 max-w-md mx-auto">
                Sua carteira está 100% atualizada para hoje! Não há obrigações atrasadas, certificados vencendo ou mensalidades pendentes.
              </p>
              <Button onClick={onClose} className="mt-4">
                Voltar ao Painel
              </Button>
            </div>
          ) : isCompleted ? (
            /* SUCCESS COMPLETION SCREEN */
            <div className="text-center py-6 space-y-6">
              <div className="relative inline-block">
                <div className="absolute inset-0 bg-cyan-500/20 blur-xl rounded-full" />
                <div className="relative border border-cyan-400/30 bg-cyan-500/10 p-5 rounded-full text-cyan-300">
                  <CheckCircle className="h-12 w-12" />
                </div>
              </div>
              <div className="space-y-2">
                <h3 className="text-2xl font-bold text-white">Modo Foco Concluído!</h3>
                <p className="text-sm text-slate-400 max-w-md mx-auto">
                  Excelente trabalho! Você resolveu e organizou suas pendências mais críticas de hoje de forma eficiente.
                </p>
              </div>

              {/* Stats Grid */}
              <div className="grid grid-cols-3 gap-3 max-w-md mx-auto bg-white/5 border border-white/10 rounded-2xl p-4 text-xs font-semibold">
                <div>
                  <span className="text-emerald-400 block text-lg font-bold">{resolvedCount}</span>
                  <span className="text-slate-400">Resolvidos</span>
                </div>
                <div>
                  <span className="text-amber-400 block text-lg font-bold">{snoozedCount}</span>
                  <span className="text-slate-400">Adiados</span>
                </div>
                <div>
                  <span className="text-slate-300 block text-lg font-bold">{skippedCount}</span>
                  <span className="text-slate-400">Pulados</span>
                </div>
              </div>

              {/* Score impact display */}
              <div className="flex items-center justify-center gap-4 bg-gradient-to-r from-cyan-950/40 to-teal-950/40 border border-cyan-500/20 rounded-2xl p-4 max-w-md mx-auto">
                <div className="text-right">
                  <p className="text-[10px] uppercase font-bold text-slate-400">Score Anterior</p>
                  <p className="text-xl font-bold text-slate-300">{beforeScore}</p>
                </div>
                <ArrowRight className="text-cyan-400 h-5 w-5 shrink-0" />
                <div className="text-left">
                  <p className="text-[10px] uppercase font-bold text-cyan-300">Novo Score Estimado</p>
                  <p className="text-2xl font-extrabold text-emerald-400 flex items-center gap-1.5">
                    {afterScore}
                    <Sparkles className="h-4 w-4 animate-bounce text-cyan-300" />
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
              <div className="flex justify-between items-center text-xs font-semibold text-slate-400">
                <span>TAREFA {currentIndex + 1} DE {totalTasks}</span>
                <span className="px-2 py-0.5 rounded bg-white/5 border border-white/10 uppercase tracking-wider text-cyan-300">
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
                      <div className={`p-3 rounded-2xl border shrink-0 ${taskTypeConfig[currentTask.type].color}`}>
                        {(() => {
                          const IconComponent = taskTypeConfig[currentTask.type].icon;
                          return <IconComponent className="h-6 w-6" />;
                        })()}
                      </div>
                      <div className="space-y-1">
                        <span className="flex items-center gap-1.5 text-xs text-slate-400 font-semibold">
                          <User className="h-3.5 w-3.5" />
                          {currentTask.clientName}
                        </span>
                        <h3 className="text-xl font-bold text-white tracking-tight leading-snug">
                          {currentTask.title}
                        </h3>
                      </div>
                    </div>

                    <div className="border border-white/5 bg-white/5 rounded-2xl p-4 text-sm text-slate-300 leading-relaxed">
                      {currentTask.description}
                    </div>

                    <div className="flex items-center gap-1.5 text-xs text-slate-400 font-semibold font-mono">
                      <Clock className="h-3.5 w-3.5" />
                      Prazo original: {dateBR(currentTask.dueDate)}
                    </div>
                  </motion.div>
                </AnimatePresence>
              </div>

              {/* Action Buttons Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-6 border-t border-white/5">
                <button
                  onClick={handleResolve}
                  className="inline-flex items-center justify-center gap-1.5 rounded-2xl bg-emerald-500 text-slate-950 py-3 text-xs font-bold hover:bg-emerald-400 active:scale-98 transition shadow-[0_0_15px_-3px_rgba(16,185,129,0.3)]"
                >
                  <CheckCircle className="h-4 w-4" />
                  {taskTypeConfig[currentTask.type].actionLabel}
                </button>
                <button
                  onClick={handleSnooze}
                  className="inline-flex items-center justify-center gap-1.5 rounded-2xl border border-amber-500/20 bg-amber-500/10 text-amber-300 py-3 text-xs font-bold hover:bg-amber-500/20 active:scale-98 transition"
                >
                  <Clock className="h-4 w-4" />
                  Adiar 7 dias
                </button>
                <button
                  onClick={handleWaitingClient}
                  className="inline-flex items-center justify-center gap-1.5 rounded-2xl border border-cyan-500/20 bg-cyan-500/10 text-cyan-300 py-3 text-xs font-bold hover:bg-cyan-500/20 active:scale-98 transition"
                >
                  <Send className="h-4 w-4" />
                  Aguardar Cliente
                </button>
                <button
                  onClick={handleSkip}
                  className="inline-flex items-center justify-center gap-1.5 rounded-2xl border border-white/10 bg-white/5 text-slate-300 py-3 text-xs font-bold hover:bg-white/10 active:scale-98 transition"
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
