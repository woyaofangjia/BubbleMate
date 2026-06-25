import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // BubbleMate品牌色
        primary: {
          50: '#fef7ee',
          100: '#fdecd3',
          200: '#f9d5a8',
          300: '#f5b97d',
          400: '#f09a52',
          500: '#eb7d27',  // 主色：奶茶橙
          600: '#d96a1e',
          700: '#b75518',
          800: '#954413',
          900: '#73350e',
        },
        bubble: {
          light: '#fff5eb',
          DEFAULT: '#f5e6d3',
          dark: '#e5d0b8',
        },
      },
      animation: {
        'bubble-float': 'bubbleFloat 3s ease-in-out infinite',
        'typing': 'typing 1s steps(3) infinite',
      },
      keyframes: {
        bubbleFloat: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        typing: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' },
        },
      },
    },
  },
  plugins: [],
};

export default config;