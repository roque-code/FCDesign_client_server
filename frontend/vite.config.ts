import { createReadStream, existsSync, readFileSync } from "node:fs"
import { dirname, resolve } from "node:path"
import { fileURLToPath } from "node:url"
import type { Connect, Plugin } from "vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vitest/config"

const frontendDir = dirname(fileURLToPath(import.meta.url))
const repoDir = resolve(frontendDir, "..")

const MANUALS = [
  ["docs/Manual-del-lenguaje.docx", "lenguaje.docx"],
  ["docs/manual-alumno/Manual-del-alumno.docx", "alumno.docx"],
  ["docs/manual-docente/Manual-del-docente.docx", "docente.docx"],
  ["docs/Manual-del-lenguaje.pdf", "lenguaje.pdf"],
  ["docs/manual-alumno/Manual-del-alumno.pdf", "alumno.pdf"],
  ["docs/manual-docente/Manual-del-docente.pdf", "docente.pdf"],
] as const

const MANUAL_TYPES: Record<string, string> = {
  ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  ".pdf": "application/pdf",
}

function manuals(): Plugin {
  const files = MANUALS.map(([from, name]) => ({
    name,
    source: resolve(repoDir, from),
    type: MANUAL_TYPES[name.slice(name.lastIndexOf("."))] ?? "application/octet-stream",
  }))
  const serve: Connect.NextHandleFunction = (req, res, next) => {
    const url = req.url?.split("?")[0] ?? ""
    const match = files.find((file) => url === `/manuals/${file.name}`)
    if (!match || !existsSync(match.source)) {
      next()
      return
    }
    res.setHeader("Content-Type", match.type)
    createReadStream(match.source).pipe(res)
  }
  return {
    name: "traza-manuals",
    configureServer(server) {
      server.middlewares.use(serve)
    },
    configurePreviewServer(server) {
      server.middlewares.use(serve)
    },
    generateBundle() {
      for (const file of files) {
        if (!existsSync(file.source)) continue
        this.emitFile({
          type: "asset",
          fileName: `manuals/${file.name}`,
          source: readFileSync(file.source),
        })
      }
    },
  }
}

export default defineConfig({
  plugins: [react(), manuals()],
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
