/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Indigo tie-dye palette (fabmood.com reference).
        // We remap the two families the app already uses — `stone` (neutrals)
        // and `indigo` (accent/brand) — so every component adopts the palette.

        // Neutrals: cool blue-greys. Page bg -> periwinkle, text -> navy.
        stone: {
          50: '#f2f4fa',
          100: '#e6eaf4', // page background
          200: '#d2d8ea', // borders / hairlines
          300: '#b8c1dd',
          400: '#8b97be', // muted text
          500: '#6b78a0',
          600: '#4e5a82',
          700: '#3a456a',
          800: '#26314f',
          900: '#1a2340', // body text
          950: '#101a2e', // near-black navy (swatch 6)
        },

        // Accent/brand: slate -> steel -> navy blues.
        indigo: {
          50: '#eef1f9',
          100: '#dce2f2',
          200: '#c7cee2', // light periwinkle (swatch 1)
          300: '#a9b3d0', // periwinkle-grey (swatch 2)
          400: '#6076a8', // slate blue (swatch 3)
          500: '#405a86', // steel blue (swatch 4)
          600: '#33497a', // primary button
          700: '#22315f', // navy (swatch 5) — hover
          800: '#1a2749',
          900: '#131d38',
          950: '#101a2e', // near-black navy (swatch 6)
        },
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
