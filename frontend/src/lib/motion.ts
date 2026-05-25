/**
 * FiscWise Motion Library
 * Padrões reutilizáveis de animação para consistência visual
 */

import type { Variants, Transition } from 'framer-motion';

/* ═══════════════════════════════════════════════════════════════════
   Transições Base
   ═══════════════════════════════════════════════════════════════════ */

export const transitions = {
  spring: {
    type: 'spring',
    stiffness: 260,
    damping: 20,
  } as Transition,

  smooth: {
    duration: 0.35,
    ease: 'easeOut',
  } as Transition,

  fast: {
    duration: 0.2,
    ease: 'easeOut',
  } as Transition,

  slow: {
    duration: 0.5,
    ease: [0.16, 1, 0.3, 1],
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
  hidden: { opacity: 0, y: 18 },
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
  hidden: { opacity: 0, y: -18 },
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
  hidden: { opacity: 0, x: 18 },
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
  hidden: { opacity: 0, x: -18 },
  show: { 
    opacity: 1, 
    x: 0,
    transition: transitions.smooth,
  },
};

/**
 * Scale In — Aparece com zoom
 */
export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.95 },
  show: { 
    opacity: 1, 
    scale: 1,
    transition: transitions.spring,
  },
};

/**
 * Scale Out — Desaparece com zoom reverso
 */
export const scaleOut: Variants = {
  hidden: { opacity: 1, scale: 1 },
  show: { 
    opacity: 0, 
    scale: 0.95,
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
      staggerChildren: 0.08,
      delayChildren: 0.05,
    },
  },
};

/**
 * Stagger Item — Item filho para animação em cascata
 */
export const staggerItem: Variants = {
  hidden: { opacity: 0, y: 18 },
  show: { 
    opacity: 1, 
    y: 0,
    transition: transitions.smooth,
  },
};

/**
 * Card Hover — Animação de hover para cards
 */
export const cardHover = {
  rest: { 
    scale: 1,
    y: 0,
  },
  hover: { 
    scale: 1.02,
    y: -4,
    transition: transitions.fast,
  },
  tap: {
    scale: 0.98,
  },
};

/**
 * Button Hover — Animação de hover para botões
 */
export const buttonHover = {
  rest: { 
    scale: 1,
  },
  hover: { 
    scale: 1.02,
    y: -1,
    transition: transitions.fast,
  },
  tap: {
    scale: 0.98,
  },
};

/**
 * Page Transition — Transição entre páginas
 */
export const pageTransition: Variants = {
  hidden: { 
    opacity: 0,
    y: 12,
  },
  show: { 
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.4,
      ease: [0.16, 1, 0.3, 1],
    },
  },
  exit: {
    opacity: 0,
    y: -12,
    transition: transitions.fast,
  },
};

/**
 * Modal Motion — Animação para modais e drawers
 */
export const modalMotion: Variants = {
  hidden: { 
    opacity: 0,
    scale: 0.95,
    y: 20,
  },
  show: { 
    opacity: 1,
    scale: 1,
    y: 0,
    transition: {
      duration: 0.25,
      ease: [0.16, 1, 0.3, 1],
    },
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    y: 20,
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
    transition: { duration: 0.2 },
  },
  exit: {
    opacity: 0,
    transition: { duration: 0.2 },
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
      transition: {
        duration: 0.3,
        ease: [0.16, 1, 0.3, 1],
      },
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
      transition: {
        duration: 0.3,
        ease: [0.16, 1, 0.3, 1],
      },
    },
    exit: {
      x: '-100%',
      transition: transitions.fast,
    },
  },
};

/**
 * Floating Animation — Animação flutuante contínua
 */
export const floating = {
  animate: {
    y: [0, -8, 0],
    transition: {
      duration: 3,
      repeat: Infinity,
      ease: 'easeInOut',
    },
  },
};

/**
 * Pulse Animation — Animação de pulso
 */
export const pulse = {
  animate: {
    scale: [1, 1.05, 1],
    transition: {
      duration: 2,
      repeat: Infinity,
      ease: 'easeInOut',
    },
  },
};

/**
 * Shake Animation — Animação de tremor (para erros)
 */
export const shake: Variants = {
  shake: {
    x: [0, -10, 10, -10, 10, 0],
    transition: {
      duration: 0.4,
    },
  },
};

/* ═══════════════════════════════════════════════════════════════════
   Helpers
   ═══════════════════════════════════════════════════════════════════ */

/**
 * Cria uma animação de stagger customizada
 */
export function createStagger(staggerDelay = 0.08, delayChildren = 0.05): Variants {
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
export function createTransition(duration = 0.35, ease: 'easeIn' | 'easeOut' | 'easeInOut' | 'linear' = 'easeOut'): Transition {
  return {
    duration,
    ease,
  };
}

/**
 * Delay para animações
 */
export function withDelay(variants: Variants, delay: number): Variants {
  return {
    ...variants,
    show: {
      ...variants.show,
      transition: {
        ...(variants.show as any).transition,
        delay,
      },
    },
  };
}
