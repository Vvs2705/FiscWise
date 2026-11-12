import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Skeleton } from './LoadingSkeleton';

// Estados únicos: EmptyState e ErrorState vivem nos próprios arquivos e são
// reexportados aqui para manter os imports antigos funcionando.
export { EmptyState } from './EmptyState';
export type { EmptyStateProps } from './EmptyState';
export { ErrorState } from './ErrorState';
export type { ErrorStateProps } from './ErrorState';

export function LoadingRows({ cols = 4, rows = 5 }: { cols?: number; rows?: number }) {
  return (
    <>
      {Array.from({ length: rows }).map((_, i) => (
        <tr key={i} className="h-11 border-b border-border" aria-hidden="true">
          {Array.from({ length: cols }).map((_, j) => (
            <td key={j} className="px-4">
              <Skeleton className={cn('h-3', j === 0 ? 'w-3/4' : 'w-1/2')} />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

export function LoadingCards({ count = 3 }: { count?: number }) {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="space-y-3 rounded-lg border border-border bg-card p-5" aria-hidden="true">
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="h-3 w-1/2" />
          <Skeleton className="h-3 w-1/3" />
        </div>
      ))}
    </>
  );
}

export function PageSpinner() {
  return (
    <div className="flex items-center justify-center py-12" role="status">
      <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" aria-hidden="true" />
      <span className="sr-only">Carregando</span>
    </div>
  );
}
