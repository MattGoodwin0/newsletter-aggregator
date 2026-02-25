import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Forward /api/* to Flask during development — no CORS needed
      "/api": {
        target: process.env.VITE_API_URL || "http://localhost:5002",
        changeOrigin: true,
      },
    },
  },
});
