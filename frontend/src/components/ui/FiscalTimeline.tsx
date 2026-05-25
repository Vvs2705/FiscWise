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
              <div className="w-8 h-8 rounded-full bg-muted animate-pulse" />
              <div className="w-0.5 h-16 bg-border/40" />
            </div>
            <div className="flex-1 space-y-2 pt-1">
              <div className="h-4 w-1/3 bg-muted animate-pulse rounded" />
              <div className="h-3 w-2/3 bg-muted animate-pulse rounded" />
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
      <div className="absolute left-6 top-2 bottom-2 w-0.5 bg-border/45" />

      {items.map((item) => {
        const Icon = item.icon || Calendar;
        
        const typeColors = {
          default: 'bg-muted border-border text-muted-foreground',
          success: 'bg-emerald-500/10 border-emerald-500/35 text-emerald-400 shadow-[0_0_12px_-2px_rgba(16,185,129,0.2)]',
          warning: 'bg-amber-500/10 border-amber-500/35 text-amber-400 shadow-[0_0_12px_-2px_rgba(245,158,11,0.2)]',
          error: 'bg-red-500/10 border-red-500/35 text-red-400 shadow-[0_0_12px_-2px_rgba(239,68,68,0.2)]',
          info: 'bg-sky-500/10 border-sky-500/35 text-sky-400 shadow-[0_0_12px_-2px_rgba(56,189,248,0.2)]',
        };

        const currentTypeColor = typeColors[item.type || 'default'];

        return (
          <div key={item.id} className="relative flex gap-5 group items-start">
            {/* Timeline icon node */}
            <div
              className={cn(
                'relative z-10 w-9 h-9 rounded-xl border flex items-center justify-center transition-transform group-hover:scale-105',
                currentTypeColor
              )}
            >
              <Icon className="w-4 h-4" />
            </div>

            {/* Content card */}
            <div className="flex-1 min-w-0 pt-0.5">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-1">
                <h4 className="text-sm font-semibold text-foreground tracking-tight group-hover:text-primary transition-colors">
                  {item.title}
                </h4>
                <span className="text-[10px] font-medium text-muted-foreground whitespace-nowrap">
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
