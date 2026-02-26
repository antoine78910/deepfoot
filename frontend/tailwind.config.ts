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
          cyan: "#00d4ff",
          green: "#00f0a0",
        },
      },
      backgroundImage: {
        "gradient-input": "linear-gradient(135deg, #00d4ff 0%, #00f0a0 100%)",
        "gradient-btn": "linear-gradient(135deg, #00d4ff 0%, #00f0a0 100%)",
      },
      boxShadow: {
        glow: "0 0 20px rgba(0, 212, 255, 0.2)",
        "glow-green": "0 0 20px rgba(0, 240, 160, 0.2)",
      },
    },
  },
  plugins: [],
};
export default config;
