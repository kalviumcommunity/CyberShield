/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cyber: {
          50: '#f0f4ff',
          100: '#dde7ff',
          200: '#c2d4ff',
          300: '#9ab6fe',
          400: '#708efa',
          500: '#4d65f5',
          600: '#3344ea',
          700: '#2832d0',
          800: '#252ba9',
          900: '#252b85',
          950: '#161750',
        },
        threat: {
          low: '#22c55e',
          medium: '#f59e0b',
          high: '#ef4444',
          critical: '#7c3aed',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
}
