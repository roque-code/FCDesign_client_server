import react from "@vitejs/plugin-react"
import { defineConfig } from "vitest/config"

export default defineConfig({
  plugins: [react()],
  server: {
    host: process.env.VITE_HOST ?? "127.0.0.1",
    port: 5173,
    allowedHosts: true,
    watch: process.env.VITE_USE_POLLING === "1" ? { usePolling: true } : undefined,
    hmr: process.env.VITE_HMR_CLIENT_PORT
      ? { clientPort: Number(process.env.VITE_HMR_CLIENT_PORT) }
      : undefined,
    proxy: {
      "/api": {
        target: process.env.VITE_API_PROXY ?? "http://127.0.0.1:8002",
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: "node",
  },
})
