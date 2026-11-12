import { ComponentType, ReactNode, isValidElement } from 'react';
import { FolderOpen } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from './Button';

/** Ação como objeto (`{ label, onClick }`) ou como nó React pronto. */
export type StateAction = { label: string; onClick: () => void } | ReactNode;

/** Ícone como componente (ex.: `FolderOpen`) ou como elemento (`<FolderOpen />`). */
export type StateIcon = ComponentType<{ className?: string }> | ReactNode;

function isActionObject(action: StateAction): action is { label: string; onClick: () => void } {
  return (
    typeof action === 'object' &&
    action !== null &&
    !isValidElement(action) &&
    'label' in action &&
    'onClick' in action
  );
}

function renderStateIcon(icon: StateIcon, className: string) {
  if (icon === null || icon === undefined || icon === false) return null;
  if (isValidElement(icon)) return icon;
  if (typeof icon === 'function' || (typeof icon === 'object' && '$$typeof' in icon)) {
    const Icon = icon as ComponentType<{ className?: string }>;
    return <Icon className={className} />;
  }
  return icon as ReactNode;
}

export interface EmptyStateProps {
  title: string;
  description?: ReactNode;
  icon?: StateIcon;
  action?: StateAction;
  /** `card` (padrão) desenha borda; `plain` fica sem moldura, para dentro de tabelas/cards. */
  variant?: 'card' | 'plain';
  className?: string;
}

/** Estado vazio único do sistema (DESIGN.md §8). */
export function EmptyState({
  title,
  description,
  icon = FolderOpen,
  action,
  variant = 'plain',
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'mx-auto flex w-full flex-col items-center justify-center px-4 py-12 text-center',
        variant === 'card' && 'max-w-lg rounded-lg border border-border bg-card',
        className,
      )}
    >
      <div
        className="mb-4 flex h-10 w-10 items-center justify-center rounded-md bg-muted text-muted-foreground [&>svg]:h-5 [&>svg]:w-5"
        aria-hidden="true"
      >
        {renderStateIcon(icon, 'h-5 w-5')}
      </div>
      <p className="text-base font-semibold text-foreground">{title}</p>
      {description && (
        <p className="mt-1 max-w-sm text-sm text-muted-foreground">{description}</p>
      )}
      {action && (
        <div className="mt-5">
          {isActionObject(action) ? (
            <Button onClick={action.onClick} size="md">
              {action.label}
            </Button>
          ) : (
            action
          )}
        </div>
      )}
    </div>
  );
}
