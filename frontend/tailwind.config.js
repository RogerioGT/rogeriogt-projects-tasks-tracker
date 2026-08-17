/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontSize: {
        xxs: ["10px", "1.35"],
      },
    },
  },
  plugins: [],
}
