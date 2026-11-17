import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// During development (npm run dev) every request to /api is forwarded to the
// FastAPI backend, so the browser only talks to one address.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      "/api": process.env.VITE_BACKEND_URL ?? "http://localhost:8000",
    },
  },
});
