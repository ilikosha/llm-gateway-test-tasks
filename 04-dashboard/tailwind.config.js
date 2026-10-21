/** @type {import('tailwindcss').Config} */
const token = (name) => `rgb(var(--c-${name}) / <alpha-value>)`;

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        bg: token('bg'),
        surface: token('surface'),
        fg: token('text'),
        muted: token('muted'),
        line: token('border'),
        accent: token('accent'),
        ok: token('ok'),
        'ok-bg': token('ok-bg'),
        err: token('err'),
        'err-bg': token('err-bg'),
      },
    },
  },
  plugins: [],
};
