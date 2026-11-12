/**
 * FiscWise Motion Library
 * Tokens de movimento do SISTEMA_DE_DESIGN.md §7: resposta ≤150 ms, entrada ≤250 ms,
 * só opacity/transform, sem scale no hover. `MotionConfig reducedMotion="user"`
 * cobre o reduced-motion no framer-motion.
 */

import type { Variants, Transition } from 'framer-motion';

/* ═══════════════════════════════════════════════════════════════════
   Transições Base
   ═══════════════════════════════════════════════════════════════════ */

/** Curva padrão do sistema (`ease-spring` no Tailwind). */
export const EASE_STANDARD = [0.2, 0, 0, 1] as const;

export const durations = {
  instant: 0.1,
  fast: 0.15,
  base: 0.2,
  enter: 0.25,
} as const;

export const transitions = {
  /** Mantido por compatibilidade: agora é tween curto (sem mola/overshoot). */
  spring: {
    type: 'tween',
    duration: durations.base,
    ease: EASE_STANDARD,
  } as Transition,

  /** Entrada de conteúdo (fade + 6px). */
  smooth: {
    duration: durations.enter,
    ease: EASE_STANDARD,
  } as Transition,

  fast: {
    duration: durations.fast,
    ease: 'easeOut',
  } as Transition,

  /** Mantido por compatibilidade: limitado a 250 ms. */
  slow: {
    duration: durations.enter,
    ease: EASE_STANDARD,
  } as Transition,

  instant: {
    duration: durations.instant,
    ease: 'easeOut',
  } as Transition,
};

/* ═══════════════════════════════════════════════════════════════════
   Variantes de Animação
   ═══════════════════════════════════════════════════════════════════ */

/**
 * Fade In — Aparecimento suave
 */
export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  show: { 
    opacity: 1,
    transition: transitions.smooth,
  },
};

/**
 * Slide Up — Desliza de baixo para cima
 */
export const slideUp: Variants = {
  hidden: { opacity: 0, y: 6 },
  show: { 
    opacity: 1, 
    y: 0,
    transition: transitions.smooth,
  },
};

/**
 * Slide Down — Desliza de cima para baixo
 */
export const slideDown: Variants = {
  hidden: { opacity: 0, y: -6 },
  show: { 
    opacity: 1, 
    y: 0,
    transition: transitions.smooth,
  },
};

/**
 * Slide Left — Desliza da direita para esquerda
 */
export const slideLeft: Variants = {
  hidden: { opacity: 0, x: 6 },
  show: { 
    opacity: 1, 
    x: 0,
    transition: transitions.smooth,
  },
};

/**
 * Slide Right — Desliza da esquerda para direita
 */
export const slideRight: Variants = {
  hidden: { opacity: 0, x: -6 },
  show: { 
    opacity: 1, 
    x: 0,
    transition: transitions.smooth,
  },
};

/**
 * Scale In — mantido por compatibilidade; agora é fade simples (sem zoom).
 */
export const scaleIn: Variants = {
  hidden: { opacity: 0 },
  show: { 
    opacity: 1, 
    transition: transitions.spring,
  },
};

/**
 * Scale Out — mantido por compatibilidade; agora é fade-out simples.
 */
export const scaleOut: Variants = {
  hidden: { opacity: 1 },
  show: { 
    opacity: 0, 
    transition: transitions.fast,
  },
};

/**
 * Stagger Container — Container para animações em cascata
 */
export const staggerContainer: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.04,
      delayChildren: 0,
    },
  },
};

/**
 * Stagger Item — Item filho para animação em cascata
 */
export const staggerItem: Variants = {
  hidden: { opacity: 0, y: 6 },
  show: { 
    opacity: 1, 
    y: 0,
    transition: transitions.smooth,
  },
};

/**
 * Card Hover — sem scale/deslocamento no hover (o realce é borda/sombra via CSS).
 */
export const cardHover = {
  rest: { 
    scale: 1,
    y: 0,
  },
  hover: { 
    scale: 1,
    y: 0,
    transition: transitions.fast,
  },
  tap: {
    scale: 0.98,
    transition: transitions.instant,
  },
};

/**
 * Button Hover — só o toque comprime (0.98).
 */
export const buttonHover = {
  rest: { 
    scale: 1,
  },
  hover: { 
    scale: 1,
    y: 0,
    transition: transitions.fast,
  },
  tap: {
    scale: 0.98,
    transition: transitions.instant,
  },
};

/**
 * Page Transition — Transição entre páginas
 */
export const pageTransition: Variants = {
  hidden: { 
    opacity: 0,
    y: 6,
  },
  show: { 
    opacity: 1,
    y: 0,
    transition: transitions.smooth,
  },
  exit: {
    opacity: 0,
    transition: transitions.fast,
  },
};

/**
 * Modal Motion — Animação para modais e drawers
 */
export const modalMotion: Variants = {
  hidden: { 
    opacity: 0,
    y: 6,
  },
  show: { 
    opacity: 1,
    y: 0,
    transition: transitions.spring,
  },
  exit: {
    opacity: 0,
    y: 6,
    transition: transitions.fast,
  },
};

/**
 * Backdrop Motion — Animação para backdrop de modais
 */
export const backdropMotion: Variants = {
  hidden: { opacity: 0 },
  show: { 
    opacity: 1,
    transition: transitions.fast,
  },
  exit: {
    opacity: 0,
    transition: transitions.fast,
  },
};

/**
 * Drawer Motion — Animação para drawers laterais
 */
export const drawerMotion = {
  right: {
    hidden: { x: '100%' },
    show: { 
      x: 0,
      transition: transitions.smooth,
    },
    exit: {
      x: '100%',
      transition: transitions.fast,
    },
  },
  left: {
    hidden: { x: '-100%' },
    show: { 
      x: 0,
      transition: transitions.smooth,
    },
    exit: {
      x: '-100%',
      transition: transitions.fast,
    },
  },
};

/**
 * Floating — mantido por compatibilidade, mas estático:
 * loop só é permitido em spinner e skeleton (SISTEMA_DE_SISTEMA_DE_DESIGN.md §7).
 */
export const floating = {
  animate: {
    y: 0,
  },
};

/**
 * Pulse — mantido por compatibilidade, mas estático (sem loop).
 */
export const pulse = {
  animate: {
    scale: 1,
  },
};

/**
 * Shake Animation — Animação de tremor (para erros)
 */
export const shake: Variants = {
  shake: {
    x: [0, -4, 4, -4, 4, 0],
    transition: {
      duration: durations.enter,
    },
  },
};

/* ═══════════════════════════════════════════════════════════════════
   Helpers
   ═══════════════════════════════════════════════════════════════════ */

/**
 * Cria uma animação de stagger customizada
 */
export function createStagger(staggerDelay = 0.04, delayChildren = 0): Variants {
  return {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: staggerDelay,
        delayChildren,
      },
    },
  };
}

/**
 * Cria uma transição customizada
 */
export function createTransition(duration = durations.enter, ease: 'easeIn' | 'easeOut' | 'easeInOut' | 'linear' = 'easeOut'): Transition {
  return {
    duration,
    ease,
  };
}

/**
 * Delay para animações
 */
export function withDelay(variants: Variants, delay: number): Variants {
  const showVariant =
    variants.show && typeof variants.show === 'object' ? variants.show : {};
  const existingTransition =
    'transition' in showVariant && showVariant.transition
      ? (showVariant.transition as Transition)
      : undefined;

  return {
    ...variants,
    show: {
      ...showVariant,
      transition: {
        ...existingTransition,
        delay,
      },
    },
  };
}
