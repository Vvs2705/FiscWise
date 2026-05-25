import { useRef } from 'react';
import { cn } from '@/lib/utils';

interface OtpInputProps {
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
}

/**
 * OtpInput — 6 caixas OTP com microinteração por dígito
 * Componente extraído do LoginPage para reutilização
 */
export function OtpInput({ value, onChange, disabled }: OtpInputProps) {
  const inputs = useRef<(HTMLInputElement | null)[]>([]);

  const digits = (value + '      ').slice(0, 6).split('');

  const handleKey = (idx: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace') {
      e.preventDefault();
      const next = digits.map((d, i) => (i === idx ? ' ' : d)).join('').trimEnd();
      onChange(next.trim());
      if (idx > 0) inputs.current[idx - 1]?.focus();
    }
  };

  const handleChange = (idx: number, e: React.ChangeEvent<HTMLInputElement>) => {
    const ch = e.target.value.replace(/\D/g, '').slice(-1);
    if (!ch) return;
    const next = digits.map((d, i) => (i === idx ? ch : d)).join('').replace(/ /g, '');
    onChange(next.padEnd(6, ' ').trim());
    if (idx < 5) inputs.current[idx + 1]?.focus();
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    const text = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (text.length > 0) {
      onChange(text);
      inputs.current[Math.min(text.length, 5)]?.focus();
    }
    e.preventDefault();
  };

  return (
    <div className="flex gap-2 justify-center" onPaste={handlePaste}>
      {Array.from({ length: 6 }).map((_, idx) => (
        <input
          key={idx}
          ref={(el) => {
            inputs.current[idx] = el;
          }}
          id={`otp-${idx}`}
          type="text"
          inputMode="numeric"
          maxLength={1}
          value={digits[idx]?.trim() ?? ''}
          onChange={(e) => handleChange(idx, e)}
          onKeyDown={(e) => handleKey(idx, e)}
          disabled={disabled}
          className={cn(
            'h-14 w-12 rounded-xl border-2 bg-background text-center text-xl font-bold',
            'text-foreground transition-all duration-150 outline-none',
            'border-border focus:border-primary focus:ring-2 focus:ring-primary/20',
            disabled && 'cursor-not-allowed opacity-50'
          )}
          autoComplete="one-time-code"
          aria-label={`Dígito ${idx + 1} do código OTP`}
        />
      ))}
    </div>
  );
}
