import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        'surface': '#080e1d',
        'background': '#080e1d',
        'on-surface': '#e0e5fb',
        'on-background': '#e0e5fb',
        'surface-container-lowest': '#000000',
        'surface-container-low': '#0c1324',
        'surface-container': '#12192b',
        'surface-container-high': '#171f33',
        'surface-container-highest': '#1d253b',
        'surface-variant': '#1d253b',
        'surface-bright': '#222c43',
        'outline': '#6f7588',
        'outline-variant': '#424859',
        'primary': '#3bbffa',
        'primary-container': '#22b1ec',
        'primary-dim': '#05a9e3',
        'secondary': '#9492ff',
        'tertiary': '#e0ecff',
        'error': '#ff716c',
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

