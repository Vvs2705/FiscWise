import { type SelectHTMLAttributes, forwardRef } from 'react';
import { cn } from '@/lib/utils';
import { fieldBaseClasses } from './Input';

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  /** Atalho para `aria-invalid`: borda destructive. */
  invalid?: boolean;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, children, invalid, ...props }, ref) => {
    return (
      <select
        ref={ref}
        className={cn(fieldBaseClasses, 'flex h-10 py-2', className)}
        {...props}
        aria-invalid={invalid || props['aria-invalid'] || undefined}
      >
        {children}
      </select>
    );
  }
);

Select.displayName = 'Select';
