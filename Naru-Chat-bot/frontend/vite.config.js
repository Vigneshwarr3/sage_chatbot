import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/chat":              "http://localhost:5001",
      "/learn":             "http://localhost:5001",
      "/learned_solutions": "http://localhost:5001",
      "/history":           "http://localhost:5001",
      "/batch_chat":        "http://localhost:5001",
    },
  },
});
