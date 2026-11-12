import { type InputHTMLAttributes, type TextareaHTMLAttributes, forwardRef } from 'react';
import { cn } from '@/lib/utils';

/** Classes compartilhadas por Input, Select e Textarea (SISTEMA_DE_DESIGN.md §8). */
export const fieldBaseClasses =
  'w-full rounded-md border border-input bg-card px-3 text-sm text-foreground transition-[border-color,box-shadow] duration-150 ease-out placeholder:text-muted-foreground hover:border-muted-foreground/40 focus-visible:outline-none focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-ring/25 focus-visible:shadow-sm disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:border-input aria-[invalid=true]:border-destructive aria-[invalid=true]:focus-visible:ring-destructive/25';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  /** Atalho para `aria-invalid`: borda destructive. */
  invalid?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, invalid, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          fieldBaseClasses,
          'flex h-10 py-2',
          'file:border-0 file:bg-transparent file:text-sm file:font-medium',
          className,
        )}
        ref={ref}
        {...props}
        aria-invalid={invalid || props['aria-invalid'] || undefined}
      />
    );
  },
);

Input.displayName = 'Input';

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  invalid?: boolean;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, invalid, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(fieldBaseClasses, 'flex min-h-[80px] py-2', className)}
      {...props}
        aria-invalid={invalid || props['aria-invalid'] || undefined}
    />
  ),
);

Textarea.displayName = 'Textarea';
