import { HTMLAttributes, ThHTMLAttributes, TdHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

export function Table({ className, ...props }: HTMLAttributes<HTMLTableElement>) {
  return (
    <div className="relative w-full overflow-auto rounded-lg border border-border bg-card">
      <table
        className={cn('w-full caption-bottom text-sm border-collapse', className)}
        {...props}
      />
    </div>
  );
}

export function TableHeader({ className, ...props }: HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <thead
      className={cn('sticky top-0 z-10 border-b border-border bg-muted [&_tr]:border-b-0', className)}
      {...props}
    />
  );
}

export function TableBody({ className, ...props }: HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <tbody
      className={cn('[&_tr:last-child]:border-0', className)}
      {...props}
    />
  );
}

export function TableFooter({ className, ...props }: HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <tfoot
      className={cn('border-t border-border bg-muted/40 font-medium [&_tr]:last:border-0', className)}
      {...props}
    />
  );
}

export function TableRow({ className, ...props }: HTMLAttributes<HTMLTableRowElement>) {
  return (
    <tr
      className={cn(
        'h-11 border-b border-border transition-colors duration-100 hover:bg-muted/50 data-[state=selected]:bg-accent',
        className
      )}
      {...props}
    />
  );
}

export function TableHead({ className, ...props }: ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={cn(
        'h-10 whitespace-nowrap px-4 text-left align-middle text-xs font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0',
        className
      )}
      {...props}
    />
  );
}

export function TableCell({ className, ...props }: TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td
      className={cn(
        'px-4 py-2.5 align-middle text-foreground [&:has([role=checkbox])]:pr-0 [&.text-right]:tabular-nums [&.tabular-nums]:font-mono',
        className
      )}
      {...props}
    />
  );
}

export function TableCaption({ className, ...props }: HTMLAttributes<HTMLTableCaptionElement>) {
  return (
    <caption
      className={cn('mt-4 text-xs text-muted-foreground', className)}
      {...props}
    />
  );
}

/** Célula numérica: alinhada à direita, mono tabular (valores, CNPJ, chaves). */
export function TableNumericCell({ className, ...props }: TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td
      className={cn('px-4 py-2.5 text-right align-middle font-mono tabular-nums text-foreground', className)}
      {...props}
    />
  );
}
