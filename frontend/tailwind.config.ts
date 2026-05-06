import type { Config } from 'tailwindcss'

const tokenColor = (token: string) => `rgb(var(${token}) / <alpha-value>)`

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        'surface': tokenColor('--color-surface'),
        'background': tokenColor('--color-background'),
        'on-surface': tokenColor('--color-on-surface'),
        'on-background': tokenColor('--color-on-background'),
        'surface-container-lowest': tokenColor('--color-surface-container-lowest'),
        'surface-container-low': tokenColor('--color-surface-container-low'),
        'surface-container': tokenColor('--color-surface-container'),
        'surface-container-high': tokenColor('--color-surface-container-high'),
        'surface-container-highest': tokenColor('--color-surface-container-highest'),
        'surface-variant': tokenColor('--color-surface-variant'),
        'surface-bright': tokenColor('--color-surface-bright'),
        'outline': tokenColor('--color-outline'),
        'outline-variant': tokenColor('--color-outline-variant'),
        'primary': tokenColor('--color-primary'),
        'primary-container': tokenColor('--color-primary-container'),
        'primary-dim': tokenColor('--color-primary-dim'),
        'secondary': tokenColor('--color-secondary'),
        'tertiary': tokenColor('--color-tertiary'),
        'error': tokenColor('--color-error'),
      },
      borderRadius: {
        md: '0.75rem',
        xl: '1.5rem',
      },
      fontFamily: {
        headline: ['Manrope', 'system-ui', 'sans-serif'],
        body: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        ambient: '0 20px 60px rgba(224, 229, 251, 0.06)',
      },
    },
  },
  plugins: [],
} satisfies Config

