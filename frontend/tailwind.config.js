/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
      },
      colors: {
        // Custom graph colors
        graph: {
          bg: '#0f172a',
          grid: '#1e293b33',
          content: '#818cf8',
          concept: '#34d399',
          note: '#fbbf24',
          edge: '#475569',
        },
      },
      animation: {
        'pulse-slow': 'pulse 3s ease-in-out infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(129, 140, 248, 0.4)' },
          '100%': { boxShadow: '0 0 20px rgba(129, 140, 248, 0.6)' },
        },
      },
      typography: {
        DEFAULT: {
          css: {
            maxWidth: 'none',
          },
        },
        invert: {
          css: {
            '--tw-prose-body': '#cbd5e1',
            '--tw-prose-headings': '#f1f5f9',
            '--tw-prose-lead': '#94a3b8',
            '--tw-prose-links': '#818cf8',
            '--tw-prose-bold': '#f1f5f9',
            '--tw-prose-counters': '#94a3b8',
            '--tw-prose-bullets': '#64748b',
            '--tw-prose-hr': '#334155',
            '--tw-prose-quotes': '#f1f5f9',
            '--tw-prose-quote-borders': '#818cf8',
            '--tw-prose-captions': '#94a3b8',
            '--tw-prose-code': '#34d399',
            '--tw-prose-pre-code': '#e2e8f0',
            '--tw-prose-pre-bg': '#1e293b',
            '--tw-prose-th-borders': '#475569',
            '--tw-prose-td-borders': '#334155',
          },
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}

