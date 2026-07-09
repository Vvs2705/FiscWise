import { ButtonHTMLAttributes, forwardRef } from 'react';
import { cn } from '@/lib/utils';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'outline' | 'ghost' | 'destructive' | 'secondary' | 'premium';
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
            'bg-primary text-primary-foreground shadow-[0_12px_30px_rgba(224,94,24,0.22)]',
            'hover:bg-primary/95 hover:shadow-[0_16px_38px_rgba(224,94,24,0.28)]',
            'active:bg-primary/90',
          ],
          variant === 'premium' && [
            'bg-[linear-gradient(135deg,hsl(var(--primary)),hsl(38_92%_55%))] text-primary-foreground',
            'shadow-[0_14px_36px_rgba(224,94,24,0.28)]',
            'hover:shadow-[0_18px_44px_rgba(224,94,24,0.34)] hover:saturate-110',
          ],
          variant === 'outline' && [
            'border border-input bg-background/80 shadow-sm backdrop-blur-sm',
            'hover:bg-accent/80 hover:text-accent-foreground hover:border-primary/35',
          ],
          variant === 'secondary' && [
            'bg-secondary text-secondary-foreground shadow-sm',
            'hover:bg-secondary/80',
          ],
          variant === 'ghost' && [
            'hover:bg-accent/80 hover:text-accent-foreground',
          ],
          variant === 'destructive' && [
            'bg-destructive text-destructive-foreground shadow-[0_12px_30px_rgba(239,68,68,0.22)]',
            'hover:bg-destructive/90 hover:shadow-[0_16px_34px_rgba(239,68,68,0.28)]',
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
