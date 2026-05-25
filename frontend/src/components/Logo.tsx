import { cn } from '@/lib/utils';

interface LogoProps {
  /** 'icon' = só o ícone quadrado | 'full' = ícone + wordmark */
  variant?: 'icon' | 'full';
  /** Tema do wordmark (não afeta o ícone colorido) */
  theme?: 'light' | 'dark';
  /** Tamanho do ícone em px */
  size?: number;
  className?: string;
}

/* Gradiente inline: cada instância precisa de um id único */
let _uid = 0;

export function Logo({ variant = 'full', theme = 'dark', size = 36, className }: LogoProps) {
  const id = `fw-logo-${++_uid}`;

  const textColor = theme === 'dark' ? '#EEF1FA' : '#1A2540';
  const subColor  = theme === 'dark' ? '#8B9ABF'  : '#6B7A99';

  const iconW = size;
  const totalW = variant === 'full' ? size + size * 3.6 : size;
  const totalH = size;

  /* Posições dos elementos do ícone (escalam via viewBox) */
  return (
    <svg
      viewBox={`0 0 ${totalW} ${totalH}`}
      width={totalW}
      height={totalH}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="FiscWise"
      className={cn('shrink-0', className)}
    >
      <defs>
        <linearGradient id={`${id}-bg`} x1="0" y1="0" x2={iconW} y2={iconW} gradientUnits="userSpaceOnUse">
          <stop offset="0%"   stopColor="#2DD4BF" />
          <stop offset="100%" stopColor="#0EA5E9" />
        </linearGradient>
      </defs>

      {/* ── Ícone ── */}
      {/* Background pill */}
      <rect width={iconW} height={iconW} rx={iconW * 0.25} fill={`url(#${id}-bg)`} />

      {/* Barra esquerda */}
      <rect
        x={iconW * 0.145} y={iconW * 0.625}
        width={iconW * 0.167} height={iconW * 0.25}
        rx={iconW * 0.042} fill="white" opacity="0.55"
      />
      {/* Barra central */}
      <rect
        x={iconW * 0.417} y={iconW * 0.458}
        width={iconW * 0.167} height={iconW * 0.417}
        rx={iconW * 0.042} fill="white" opacity="0.78"
      />
      {/* Barra direita */}
      <rect
        x={iconW * 0.688} y={iconW * 0.271}
        width={iconW * 0.167} height={iconW * 0.604}
        rx={iconW * 0.042} fill="white"
      />

      {/* Linha de tendência */}
      <path
        d={`M${iconW*0.229} ${iconW*0.625} L${iconW*0.500} ${iconW*0.458} L${iconW*0.771} ${iconW*0.271}`}
        stroke="white" strokeWidth={iconW * 0.042}
        strokeLinecap="round" strokeLinejoin="round" opacity="0.40"
      />

      {/* Seta de alta (canto sup-direito) */}
      <path
        d={`M${iconW*0.708} ${iconW*0.167} L${iconW*0.854} ${iconW*0.167} L${iconW*0.854} ${iconW*0.313}`}
        stroke="white" strokeWidth={iconW * 0.046}
        strokeLinecap="round" strokeLinejoin="round" fill="none" opacity="0.88"
      />
      <path
        d={`M${iconW*0.688} ${iconW*0.292} L${iconW*0.854} ${iconW*0.167}`}
        stroke="white" strokeWidth={iconW * 0.046}
        strokeLinecap="round" fill="none" opacity="0.88"
      />

      {/* ── Wordmark (só no variant=full) ── */}
      {variant === 'full' && (
        <>
          <text
            x={iconW + iconW * 0.28}
            y={totalH * 0.58}
            fontFamily="Inter, system-ui, sans-serif"
            fontSize={totalH * 0.42}
            fontWeight="700"
            letterSpacing="-0.4"
            fill={textColor}
          >
            FiscWise
          </text>
          <text
            x={iconW + iconW * 0.29}
            y={totalH * 0.88}
            fontFamily="Inter, system-ui, sans-serif"
            fontSize={totalH * 0.18}
            fontWeight="500"
            letterSpacing="1.6"
            fill={subColor}
          >
            ROTINA FISCAL
        </text>
      </>
    )}
    </svg>
  );
}
