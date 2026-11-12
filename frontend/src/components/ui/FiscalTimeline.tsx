import { HTMLAttributes, ReactNode } from 'react';
import { LucideIcon, Calendar } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface TimelineItem {
  id: string | number;
  title: string;
  description?: string;
  date: string;
  type?: 'success' | 'warning' | 'error' | 'info' | 'default';
  icon?: LucideIcon;
  action?: ReactNode;
}

interface FiscalTimelineProps extends HTMLAttributes<HTMLDivElement> {
  items: TimelineItem[];
  isLoading?: boolean;
}

export function FiscalTimeline({ items, isLoading, className, ...props }: FiscalTimelineProps) {
  if (isLoading) {
    return (
      <div className={cn('space-y-6', className)} {...props}>
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex gap-4">
            <div className="flex flex-col items-center">
              <div className="skeleton h-8 w-8 rounded-md" />
              <div className="h-16 w-px bg-border" />
            </div>
            <div className="flex-1 space-y-2 pt-1">
              <div className="skeleton h-4 w-1/3 rounded-sm" />
              <div className="skeleton h-3 w-2/3 rounded-sm" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className={cn('text-center py-8 text-sm text-muted-foreground', className)} {...props}>
        Nenhum registro no histórico.
      </div>
    );
  }

  return (
    <div className={cn('relative space-y-6 pl-2', className)} {...props}>
      {/* Central vertical connecting line */}
      <div className="absolute bottom-2 left-6 top-2 w-px bg-border" aria-hidden="true" />

      {items.map((item) => {
        const Icon = item.icon || Calendar;
        
        const typeColors = {
          default: 'bg-muted border-border text-muted-foreground',
          success: 'bg-success/10 border-success/25 text-success',
          warning: 'bg-warning/10 border-warning/25 text-warning',
          error: 'bg-destructive/10 border-destructive/25 text-destructive',
          info: 'bg-info/10 border-info/25 text-info',
        };

        const currentTypeColor = typeColors[item.type || 'default'];

        return (
          <div key={item.id} className="relative flex gap-5 group items-start">
            {/* Timeline icon node */}
            <div
              className={cn(
                'relative z-10 flex h-9 w-9 items-center justify-center rounded-md border bg-card',
                currentTypeColor
              )}
            >
              <Icon className="w-4 h-4" />
            </div>

            {/* Content card */}
            <div className="flex-1 min-w-0 pt-0.5">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-1">
                <h4 className="text-sm font-semibold text-foreground">
                  {item.title}
                </h4>
                <span className="whitespace-nowrap text-xs tabular-nums text-muted-foreground">
                  {item.date}
                </span>
              </div>
              {item.description && (
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {item.description}
                </p>
              )}
              {item.action && <div className="mt-2">{item.action}</div>}
            </div>
          </div>
        );
      })}
    </div>
  );
}
