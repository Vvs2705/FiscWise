import { LucideIcon, FolderOpen } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from './Button';

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: LucideIcon;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

export function EmptyState({
  title,
  description,
  icon: Icon = FolderOpen,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'fiscwise-surface flex flex-col items-center justify-center text-center p-8 md:p-12 rounded-card border border-border/70 max-w-lg mx-auto',
        'animate-fade-in-up',
        className
      )}
    >
      <div className="w-16 h-16 rounded-card bg-primary/10 border border-primary/20 flex items-center justify-center text-primary mb-6 shadow-glow-sm">
        <Icon className="w-8 h-8" />
      </div>
      <h3 className="text-xl font-bold text-foreground mb-2">{title}</h3>
      <p className="text-sm text-muted-foreground mb-6 max-w-sm leading-relaxed">
        {description}
      </p>
      {action && (
        <Button onClick={action.onClick} variant="premium" size="md">
          {action.label}
        </Button>
      )}
    </div>
  );
}
