export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0C1014",
        header: "#DFD0B8",
        sidebar: "#948979",
        card: "#141B22",
        border: "#2A3340",
        accent: "#C9A86C",
        muted: "#6B7A8D",
      },
      fontFamily: {
        display: ['"Playfair Display"', "Georgia", "serif"],
        body: ['"DM Sans"', "sans-serif"],
        mono: ['"JetBrains Mono"', "monospace"],
      },
      boxShadow: {
        glow: "0 0 20px rgba(201,168,108,0.15)",
        card: "0 4px 24px rgba(0,0,0,0.4)",
      },
      animation: {
        "fade-in": "fadeIn 0.4s ease-out",
        "slide-in": "slideIn 0.3s ease-out",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: 0, transform: "translateY(8px)" },
          "100%": { opacity: 1, transform: "translateY(0)" },
        },
        slideIn: {
          "0%": { opacity: 0, transform: "translateX(-16px)" },
          "100%": { opacity: 1, transform: "translateX(0)" },
        },
      },
    },
  },
  plugins: [],
};
