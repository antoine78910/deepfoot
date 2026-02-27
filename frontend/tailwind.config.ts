import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          bg: "#0f0f14",
          card: "#1a1a24",
          input: "#16161e",
          border: "#2a2a3a",
        },
        accent: {
          cyan: "#00ffe8",
          green: "#00ffe8",
        },
      },
      backgroundImage: {
        "gradient-input": "linear-gradient(135deg, #00ffe8 0%, #00ddcc 100%)",
        "gradient-btn": "linear-gradient(135deg, #00ffe8 0%, #00ddcc 100%)",
        "app-gradient": "linear-gradient(to bottom, #050509 0%, #061016 50%, #071a22 100%)",
      },
      boxShadow: {
        glow: "0 0 20px rgba(0, 255, 232, 0.35)",
        "glow-green": "0 0 20px rgba(0, 255, 232, 0.35)",
      },
    },
  },
  plugins: [],
};
export default config;
