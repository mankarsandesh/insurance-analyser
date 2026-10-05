import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Calls to /api are forwarded to the FastAPI server during development
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
