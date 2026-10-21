import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // para abrirlo desde el celular en la misma red wifi
    proxy: { "/api": "http://localhost:8000" },
  },
});
