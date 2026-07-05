/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Foggy-forest palette (creativerootsblog.com reference).
        // We remap the two families the app already uses — `stone` (neutrals)
        // and `indigo` (accent/brand) — so every component adopts the palette.

        // Neutrals: cool green-grey mist. Page bg -> mist, text -> forest.
        stone: {
          50: '#f4f7f6',
          100: '#e6edec', // page background
          200: '#d3dcdb', // borders / hairlines
          300: '#b6c3c3',
          400: '#8fa1ab', // slate mist — muted text (swatch 5)
          500: '#6b7a7c',
          600: '#4f5d54',
          700: '#3a4a37',
          800: '#2a3626',
          900: '#1f2a1b', // body text
          950: '#141c11',
        },

        // Accent/brand: moss & forest greens.
        indigo: {
          50: '#eef2e6',
          100: '#dde6cc',
          200: '#c1d09f',
          300: '#a2b184', // sage (swatch 4)
          400: '#829e52',
          500: '#5c6e3a', // moss (swatch 3) — accent
          600: '#4a5a2e', // primary button
          700: '#3a4724', // hover
          800: '#2f3d24', // dark forest (swatch 2)
          900: '#24301c',
          950: '#1b2416', // near-black green (swatch 1)
        },
      },
    },
  },
  plugins: [],
}
