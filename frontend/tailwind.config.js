/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class'],
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        success: {
          DEFAULT: 'hsl(var(--success))',
          foreground: 'hsl(var(--success-foreground))',
        },
        warning: {
          DEFAULT: 'hsl(var(--warning))',
          foreground: 'hsl(var(--warning-foreground))',
        },
        info: {
          DEFAULT: 'hsl(var(--info))',
          foreground: 'hsl(var(--info-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        sidebar: {
          DEFAULT: 'hsl(var(--sidebar-bg))',
          foreground: 'hsl(var(--sidebar-fg))',
          muted: 'hsl(var(--sidebar-muted))',
          'active-bg': 'hsl(var(--sidebar-active-bg))',
          'active-fg': 'hsl(var(--sidebar-active-fg))',
          'hover-bg': 'hsl(var(--sidebar-hover-bg))',
          border: 'hsl(var(--sidebar-border))',
          accent: 'hsl(var(--sidebar-logo-accent))',
        },
      },
      borderRadius: {
        // DESIGN.md §5: 6 / 8 / 12
        sm: 'var(--radius-sm)',
        md: 'var(--radius)',
        lg: 'var(--radius-lg)',
        // Aliases legados → 12px
        card: 'var(--radius-lg)',
        panel: 'var(--radius-lg)',
      },
      fontFamily: {
        // DESIGN.md §3: Geist (interface) + JetBrains Mono (dados)
        sans: ['"Geist Variable"', 'Geist', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        display: ['"Geist Variable"', 'Geist', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        mono: ['"JetBrains Mono Variable"', '"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      boxShadow: {
        // DESIGN.md §6: três níveis discretos
        sm: 'var(--shadow-sm)',
        DEFAULT: 'var(--shadow-sm)',
        md: 'var(--shadow-md)',
        lg: 'var(--shadow-lg)',
        xl: 'var(--shadow-lg)',
        '2xl': 'var(--shadow-lg)',
        // Aliases legados (sem glow, sem cor)
        'glow-sm': 'var(--shadow-sm)',
        glow: 'var(--shadow-sm)',
        'card-hover': 'var(--shadow-md)',
        'token-sm': 'var(--shadow-sm)',
        token: 'var(--shadow-md)',
        'token-glow': 'var(--shadow-sm)',
      },
      transitionTimingFunction: {
        spring: 'cubic-bezier(0.2, 0, 0, 1)',
        standard: 'cubic-bezier(0.2, 0, 0, 1)',
      },
      transitionDuration: {
        instant: '100ms',
        fast: '150ms',
        base: '200ms',
        enter: '250ms',
      },
      keyframes: {
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        'fade-in-up': {
          from: { opacity: '0', transform: 'translateY(6px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        shimmer: {
          from: { backgroundPosition: '200% 0' },
          to: { backgroundPosition: '-200% 0' },
        },
      },
      animation: {
        'fade-in': 'fade-in 0.15s ease-out both',
        'fade-in-up': 'fade-in-up 0.25s cubic-bezier(0.2, 0, 0, 1) both',
        // Legado: scale-in vira fade simples
        'scale-in': 'fade-in 0.2s cubic-bezier(0.2, 0, 0, 1) both',
        shimmer: 'shimmer 1.6s linear infinite',
      },
    },
  },
  // DESIGN.md §1.5: nada de backdrop-filter. As classes `backdrop-blur*` ainda
  // presentes nas páginas deixam de gerar CSS (superfícies planas).
  corePlugins: {
    backdropBlur: false,
    backdropFilter: false,
  },
  plugins: [],
}
