import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          0: "#07090d",
          1: "#0c1118",
          2: "#121823",
          3: "#1a2333",
        },
        accent: {
          DEFAULT: "#38bdf8", // cyan-400
          500: "#38bdf8",
          600: "#0ea5e9",
          700: "#0284c7",
        },
        line: "rgba(148, 163, 184, 0.14)",
        "line-strong": "rgba(148, 163, 184, 0.28)",
      },
      fontFamily: {
        // No Inter. Indic-friendly system stack first; Noto fallbacks for native scripts.
        sans: [
          '"Noto Sans"',
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica",
          "Arial",
          "sans-serif",
        ],
        indic: [
          '"Noto Sans Devanagari"',
          '"Noto Sans Telugu"',
          '"Noto Sans Tamil"',
          '"Noto Sans Kannada"',
          '"Noto Sans Malayalam"',
          '"Noto Sans Bengali"',
          '"Noto Sans Gujarati"',
          '"Noto Sans Gurmukhi"',
          '"Noto Sans Oriya"',
          '"Noto Sans"',
          "system-ui",
          "sans-serif",
        ],
        mono: ["ui-monospace", '"SF Mono"', "Menlo", "monospace"],
      },
      borderRadius: {
        // Override the default `rounded` (0.25rem) with a more refined scale.
        sm: "4px",
        md: "8px",
        lg: "12px",
        xl: "16px",
      },
    },
  },
  plugins: [],
};
export default config;
