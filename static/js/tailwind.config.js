// Token warna design system (sumber: static/css/global.css) sebagai kelas Tailwind.
// Contoh: bg-crypt-900, text-bone-200, border-crypt-700, text-ecto-400, bg-ecto-400/10
const pnColor = (name) => `rgb(var(--pn-${name}) / <alpha-value>)`;

tailwind.config = {
  theme: {
    extend: {
      colors: {
        crypt: { 950: pnColor("crypt-950"), 900: pnColor("crypt-900"), 800: pnColor("crypt-800"), 700: pnColor("crypt-700") },
        bone: { 50: pnColor("bone-50"), 200: pnColor("bone-200"), 400: pnColor("bone-400") },
        ecto: { 300: pnColor("ecto-300"), 400: pnColor("ecto-400") },
        ember: { 400: pnColor("ember-400") },
        blood: { 400: pnColor("blood-400") },
        hex: { 400: pnColor("hex-400") },
        frost: { 400: pnColor("frost-400") },
      },
      fontFamily: {
        display: ["Fraunces", "Georgia", "serif"],
        sans: ['"Plus Jakarta Sans"', "system-ui", "sans-serif"],
      },
    },
  },
};
