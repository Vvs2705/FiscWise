import { ButtonHTMLAttributes, forwardRef } from 'react';
import { cn } from '@/lib/utils';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'outline' | 'ghost' | 'destructive';
  size?: 'sm' | 'md' | 'lg';
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'md', ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          // Base
          'relative inline-flex items-center justify-center rounded-md font-medium select-none',
          // Transições suaves
          'transition-all duration-150 ease-spring',
          // Focus ring
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
          // Desabilitado
          'disabled:pointer-events-none disabled:opacity-50',
          // Hover lift + active press
          'hover:-translate-y-px active:translate-y-0 active:scale-[0.98]',

          // Variantes
          variant === 'default' && [
            'bg-primary text-primary-foreground shadow-sm',
            'hover:bg-primary/90 hover:shadow-glow-sm',
            'active:bg-primary/95',
          ],
          variant === 'outline' && [
            'border border-input bg-background shadow-sm',
            'hover:bg-accent hover:text-accent-foreground hover:border-primary/40',
          ],
          variant === 'ghost' && [
            'hover:bg-accent hover:text-accent-foreground',
          ],
          variant === 'destructive' && [
            'bg-destructive text-destructive-foreground shadow-sm',
            'hover:bg-destructive/90',
          ],

          // Tamanhos
          size === 'sm' && 'h-8 gap-1.5 px-3 text-sm',
          size === 'md' && 'h-10 gap-2 px-4 text-sm',
          size === 'lg' && 'h-11 gap-2 px-6 text-base',

          className,
        )}
        {...props}
      />
    );
  },
);

Button.displayName = 'Button';
