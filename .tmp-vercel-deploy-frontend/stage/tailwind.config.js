/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        heading: ['Space Grotesk', 'sans-serif'],
        sans: ['DM Sans', 'Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        brand: {
          primary: '#0369A1',
          secondary: '#0EA5E9',
          cta: '#22C55E',
          background: '#F0F9FF',
          text: '#0C4A6E',
        }
      }
    },
  },
  plugins: [],
}
