/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // 风险等级配色（与 docs/07 一致）
        risk: {
          normal: "#10B981",
          attention: "#F59E0B",
          abnormal: "#F97316",
          high: "#EF4444",
        },
        engineering: {
          bg: "#0F172A",
          surface: "#1E293B",
          border: "#334155",
          text: "#E2E8F0",
          muted: "#94A3B8",
        },
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "sans-serif"],
        mono: ["JetBrains Mono", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};
