import { HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

interface ProgressRingProps extends HTMLAttributes<HTMLDivElement> {
  score: number;
  size?: number;
  strokeWidth?: number;
  showText?: boolean;
}

export function ProgressRing({
  score,
  size = 64,
  strokeWidth = 4,
  showText = true,
  className,
  ...props
}: ProgressRingProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (score / 100) * circumference;

  const ringColor =
    score >= 90
      ? 'text-emerald-500'
      : score >= 75
      ? 'text-sky-500'
      : score >= 55
      ? 'text-amber-500'
      : 'text-red-500';

  const ringBgColor =
    score >= 90
      ? 'bg-emerald-500/10'
      : score >= 75
      ? 'bg-sky-500/10'
      : score >= 55
      ? 'bg-amber-500/10'
      : 'bg-red-500/10';

  return (
    <div
      className={cn('relative flex items-center justify-center flex-shrink-0', className)}
      style={{ width: size, height: size }}
      {...props}
    >
      <svg className="w-full h-full transform -rotate-90" viewBox={`0 0 ${size} ${size}`}>
        {/* Background track */}
        <circle
          className="text-border/40"
          strokeWidth={strokeWidth}
          stroke="currentColor"
          fill="none"
          r={radius}
          cx={size / 2}
          cy={size / 2}
        />
        {/* Animated progressive ring */}
        <circle
          className={cn('transition-all duration-700 ease-out', ringColor)}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          stroke="currentColor"
          fill="none"
          r={radius}
          cx={size / 2}
          cy={size / 2}
        />
      </svg>
      {showText && (
        <div className={cn('absolute inset-0 flex items-center justify-center font-bold text-sm text-foreground rounded-full', ringBgColor)}>
          {score}
        </div>
      )}
    </div>
  );
}
