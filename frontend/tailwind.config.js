/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        socialfy: {
          primary: '#6366f1',
          secondary: '#8b5cf6',
          dark: '#0f172a',
          card: '#1e293b',
        },
      },
    },
  },
  plugins: [],
};
