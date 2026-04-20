import type { Config } from "tailwindcss";

// Palette transcribed from backend/src/mare/brand/identity.py — the single
// source of truth for MaRe brand colors. Keep these values in sync.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Primary palette (brand-kit hero set)
        light: "#E2E2DE",
        key: "#296167",
        "extra-dark": "#2A2420",
        dark: "#3B3632",
        "brand-brown": "#653D24",

        // Full tonal ramps
        brown: {
          50: "#F0ECE9",
          100: "#E0D8D3",
          200: "#C1B1A7",
          300: "#A38B7C",
          400: "#846450",
          500: "#653D24",
          600: "#51311D",
          700: "#3D2516",
          800: "#28180E",
          900: "#1E120B",
        },
        water: {
          50: "#E4ECED",
          100: "#CFDDDE",
          200: "#A6BEC0",
          300: "#7C9FA3",
          400: "#538085",
          500: "#296167",
          600: "#214E52",
          700: "#193A3E",
          800: "#102729",
          900: "#0C1D1F",
        },
      },
      fontFamily: {
        // Principal display serif — editorial, hero moments only.
        display: ["Playfair Display", "ui-serif", "Georgia", "serif"],
        // Complementary sans — headings + UI + body default.
        sans: ["Manrope", "ui-sans-serif", "system-ui", "sans-serif"],
        // Long-form body alternate.
        body: ["Albert Sans", "Manrope", "ui-sans-serif", "sans-serif"],
      },
      letterSpacing: {
        // From the brand kit: tracking -4% on Manrope body/heading.
        "tight-4": "-0.04em",
      },
      lineHeight: {
        // 112% for display, 136% for body — per the style guide.
        display: "1.12",
        body: "1.36",
      },
    },
  },
  plugins: [],
};

export default config;
