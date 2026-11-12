import { HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

/** Bloco de skeleton: um único mecanismo (shimmer em `.skeleton`), estático com reduced-motion. */
export function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div aria-hidden="true" className={cn('skeleton rounded-sm', className)} {...props} />;
}

export function SkeletonCard({ className }: { className?: string }) {
  return (
    <div
      role="status"
      aria-label="Carregando"
      className={cn('space-y-4 rounded-lg border border-border bg-card p-5', className)}
    >
      <div className="flex items-center justify-between">
        <Skeleton className="h-4 w-1/3" />
        <Skeleton className="h-9 w-9 rounded-md" />
      </div>
      <div className="space-y-2">
        <Skeleton className="h-7 w-2/3" />
        <Skeleton className="h-3 w-1/2" />
      </div>
    </div>
  );
}

export function SkeletonTable({
  rows = 5,
  cols = 4,
  className,
}: {
  rows?: number;
  cols?: number;
  className?: string;
}) {
  return (
    <div
      role="status"
      aria-label="Carregando"
      className={cn('overflow-hidden rounded-lg border border-border bg-card', className)}
    >
      <div className="flex h-10 items-center gap-4 border-b border-border bg-muted/40 px-4">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className="h-3 flex-1" />
        ))}
      </div>
      <div className="divide-y divide-border">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="flex h-11 items-center gap-4 px-4">
            {Array.from({ length: cols }).map((_, j) => (
              <Skeleton key={j} className={cn('h-3 flex-1', j === 0 && 'max-w-[40%]')} />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

export function SkeletonList({ count = 4, className }: { count?: number; className?: string }) {
  return (
    <div role="status" aria-label="Carregando" className={cn('space-y-3', className)}>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="flex items-center justify-between gap-4 rounded-lg border border-border bg-card p-4"
        >
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <Skeleton className="h-10 w-10 flex-shrink-0 rounded-md" />
            <div className="min-w-0 flex-1 space-y-1.5">
              <Skeleton className="h-4 w-1/3" />
              <Skeleton className="h-3 w-2/3" />
            </div>
          </div>
          <Skeleton className="h-5 w-16 flex-shrink-0" />
        </div>
      ))}
    </div>
  );
}
