/** @type {import('tailwindcss').Config} */
module.exports = {
  important: true,
  content: ["../templates/**/*.{html,js}", "../../**/templates/**/*.{html,js}"],
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#F6EAE9",
          100: "#EDD4D3",
          200: "#E5BFBD",
          300: "#DCA9A7",
          400: "#D39492",
          500: "#CA7E7C",
          600: "#C16966",
          700: "#B95350",
          800: "#B03E3A",
          900: "#A72824",
        },
        black: {
          100: "#E6E6E6",
          200: "#CCCCCC",
          300: "#B3B3B3",
          400: "#999999",
          500: "#808080",
          600: "#666666",
          700: "#4C4C4C",
          800: "#333333",
          900: "#191919",
        },
        magenta: {
          50: "#F2ECEE",
          100: "#E5D9DD",
          200: "#D9C7CC",
          300: "#CCB4BB",
          400: "#BFA1AA",
          500: "#B28E99",
          600: "#A57B88",
          700: "#996977",
          800: "#8C5666",
          900: "#7F4355",
        },
      },
    },
  },
  plugins: [],
};
