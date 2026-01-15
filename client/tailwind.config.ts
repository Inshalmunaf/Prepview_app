import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#1F3A8A', // Deep Blue
          50: '#e8ecf5',
          100: '#c5d0e6',
          200: '#9fb0d4',
          300: '#7890c2',
          400: '#5b78b5',
          500: '#3d60a8',
          600: '#1F3A8A', // Main primary
          700: '#1a2f6f',
          800: '#142554',
          900: '#0d1738',
        },
        accent: {
          DEFAULT: '#01F1BF', // Bright Teal
          50: '#e0fdf9',
          100: '#b3faf0',
          200: '#80f7e6',
          300: '#4df4dc',
          400: '#26f1d5',
          500: '#01F1BF', // Main accent
          600: '#01d9ac',
          700: '#01bf96',
          800: '#01a580',
          900: '#017c5c',
        },
        button: {
          primary: '#00BFA5', // Primary button color
        },
        background: {
          DEFAULT: '#F8F9FA', // Off-White
        },
        text: {
          primary: '#212529', // Dark Charcoal
        },
        border: {
          DEFAULT: '#DEE2E6', // Light Gray
        },
        success: '#28A745',
        warning: '#FFC107',
        danger: '#DC3545',
      },
    },
  },
  plugins: [],
}
export default config

