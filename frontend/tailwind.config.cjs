/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'cyber-cyan': 'hsl(185, 100%, 45%)',
        'cyber-purple': 'hsl(265, 80%, 50%)',
        'cyber-purple-bright': 'hsl(270, 90%, 65%)',
        'cyber-green': 'hsl(150, 90%, 50%)',
        'cyber-red': 'hsl(0, 90%, 60%)',
        'bg-deep': 'hsl(222, 47%, 8%)',
        'aurora': 'hsl(160, 80%, 55%)',
      },
      fontFamily: {
        display: ['system-ui', 'sans-serif'],
        mono: ['Consolas', 'monospace'],
      },
      animation: {
        'marquee': 'marquee 25s linear infinite',
      },
      keyframes: {
        marquee: {
          '0%': { transform: 'translateX(0%)' },
          '100%': { transform: 'translateX(-50%)' },
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
    require('tailwindcss-animate'),
  ],
}