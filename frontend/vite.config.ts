/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Same-origin /api in production; in dev, proxy to the local FastAPI server.
    proxy: { "/api": "http://127.0.0.1:8000", "/healthz": "http://127.0.0.1:8000" },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
    chunkSizeWarningLimit: 600, // recharts alone is ~530 kB minified (150 kB gzip); split into its own chunk
    rollupOptions: { output: { manualChunks: { charts: ["recharts"] } } },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
