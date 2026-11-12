import { ReactNode } from 'react';
import { AlertCircle, RotateCw } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from './Button';

export interface ErrorStateProps {
  /** Mensagem curta (API antiga de `StateViews`). */
  message?: string;
  title?: string;
  description?: ReactNode;
  /** Mostra o botão "Tentar novamente". Passe o `refetch` da query. */
  onRetry?: () => void;
  /** Ação extra (ou substituta) como nó React. */
  action?: ReactNode;
  className?: string;
}

/** Estado de erro único do sistema (SISTEMA_DE_DESIGN.md §8). */
export function ErrorState({
  message,
  title,
  description,
  onRetry,
  action,
  className,
}: ErrorStateProps) {
  const heading = title ?? message ?? 'Não foi possível carregar os dados.';
  const body = title ? (description ?? message) : description;

  return (
    <div
      role="alert"
      className={cn(
        'flex flex-col gap-3 rounded-lg border border-destructive/25 bg-destructive/5 p-4 sm:flex-row sm:items-center',
        className,
      )}
    >
      <div className="flex min-w-0 flex-1 items-start gap-3">
        <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-destructive" aria-hidden="true" />
        <div className="min-w-0">
          <p className="text-sm font-medium text-foreground">{heading}</p>
          {body && <p className="mt-0.5 text-sm text-muted-foreground">{body}</p>}
        </div>
      </div>
      {(onRetry || action) && (
        <div className="flex shrink-0 items-center gap-2 pl-8 sm:pl-0">
          {action}
          {onRetry && (
            <Button variant="outline" size="sm" onClick={onRetry}>
              <RotateCw className="h-4 w-4" aria-hidden="true" />
              Tentar novamente
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
