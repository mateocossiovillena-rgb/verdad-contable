/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        marca: { 50: "#fff7ed", 100: "#ffedd5", 500: "#ea580c", 600: "#c2410c", 700: "#9a3412" },
      },
    },
  },
  plugins: [],
};
