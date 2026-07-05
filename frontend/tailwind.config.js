/** @type {import('tailwindcss').Config} */

// The stone (neutral) and indigo (accent) scales are driven by CSS variables
// defined in index.css. Light values live on :root; "Ghost mode" swaps them
// under html.ghost. Using the <alpha-value> channel form keeps opacity
// utilities (bg-white/90, bg-indigo-600/50, etc.) working.
const withVar = (name) => `rgb(var(${name}) / <alpha-value>)`;

const scale = (family) =>
  Object.fromEntries(
    [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950].map((step) => [
      step,
      withVar(`--c-${family}-${step}`),
    ])
  );

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        stone: scale('stone'),
        indigo: scale('indigo'),
        // Card / panel surface. White in light mode, elevated navy in ghost.
        surface: withVar('--c-surface'),
      },

      // Sharper boxes: crisp corners across the app. `full` is left untouched
      // so status dots, the avatar, and spinners stay round.
      borderRadius: {
        DEFAULT: '0.125rem', // 2px
        md: '0.125rem', // 2px
        lg: '0.1875rem', // 3px
        xl: '0.25rem', // 4px
        '2xl': '0.25rem', // 4px
        '3xl': '0.375rem', // 6px
      },
    },
  },
  plugins: [],
}
