import { createReadStream, existsSync, readFileSync, statSync } from "node:fs"
import type { IncomingMessage, ServerResponse } from "node:http"
import { dirname, resolve } from "node:path"
import { fileURLToPath } from "node:url"
import type { Connect, Plugin } from "vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vitest/config"

const frontendDir = dirname(fileURLToPath(import.meta.url))
const repoDir = resolve(frontendDir, "..")

const MANUALS = [
  ["docs/Manual-del-lenguaje.docx", "lenguaje.docx", "Manual-del-lenguaje.docx"],
  ["docs/manual-alumno/Manual-del-alumno.docx", "alumno.docx", "Manual-del-alumno.docx"],
  ["docs/manual-docente/Manual-del-docente.docx", "docente.docx", "Manual-del-docente.docx"],
  ["docs/Manual-del-lenguaje.pdf", "lenguaje.pdf", "Manual-del-lenguaje.pdf"],
  ["docs/manual-alumno/Manual-del-alumno.pdf", "alumno.pdf", "Manual-del-alumno.pdf"],
  ["docs/manual-docente/Manual-del-docente.pdf", "docente.pdf", "Manual-del-docente.pdf"],
] as const

const MANUAL_TYPES: Record<string, string> = {
  ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  ".pdf": "application/pdf",
}

function contentDisposition(filename: string, download: boolean): string {
  const mode = download ? "attachment" : "inline"
  return `${mode}; filename="${filename}"; filename*=UTF-8''${encodeURIComponent(filename)}`
}

function byteRange(header: string, size: number): { start: number; end: number } | "invalid" | null {
  if (!header) return null
  if (header.includes(",")) return "invalid"
  const match = /^bytes=(\d*)-(\d*)$/.exec(header.trim())
  if (!match) return "invalid"
  const [, startText, endText] = match
  if (!startText && !endText) return "invalid"
  let start: number
  let end: number
  if (!startText) {
    const suffix = Number(endText)
    if (!Number.isInteger(suffix) || suffix <= 0) return "invalid"
    start = Math.max(0, size - suffix)
    end = size - 1
  } else {
    start = Number(startText)
    end = endText ? Number(endText) : size - 1
  }
  if (!Number.isInteger(start) || !Number.isInteger(end) || start < 0 || start >= size || end < start) return "invalid"
  return { start, end: Math.min(end, size - 1) }
}

function sendManual(
  req: IncomingMessage,
  res: ServerResponse,
  source: string,
  type: string,
  filename: string,
  download: boolean,
) {
  const size = statSync(source).size
  res.setHeader("Content-Type", type)
  res.setHeader("X-Content-Type-Options", "nosniff")
  res.setHeader("Content-Disposition", contentDisposition(filename, download))
  res.setHeader("Accept-Ranges", "bytes")
  res.setHeader("Cache-Control", "private, max-age=0, must-revalidate")
  if (size === 0 || req.method === "HEAD") {
    res.statusCode = 200
    res.setHeader("Content-Length", size)
    res.end()
    return
  }
  const range = byteRange(typeof req.headers.range === "string" ? req.headers.range : "", size)
  if (range === "invalid") {
    res.statusCode = 416
    res.setHeader("Content-Range", `bytes */${size}`)
    res.end()
    return
  }
  const start = range?.start ?? 0
  const end = range?.end ?? size - 1
  res.statusCode = range ? 206 : 200
  if (range) res.setHeader("Content-Range", `bytes ${start}-${end}/${size}`)
  res.setHeader("Content-Length", end - start + 1)
  const stream = createReadStream(source, { start, end })
  stream.on("error", () => {
    res.destroy()
  })
  stream.pipe(res)
}

function manuals(): Plugin {
  const files = MANUALS.map(([from, name, downloadName]) => ({
    name,
    downloadName,
    source: resolve(repoDir, from),
    type: MANUAL_TYPES[name.slice(name.lastIndexOf("."))] ?? "application/octet-stream",
  }))
  const serve: Connect.NextHandleFunction = (req, res, next) => {
    const pathname = (req.url ?? "").split("?")[0] ?? ""
    if (!pathname.startsWith("/manuals/")) {
      next()
      return
    }
    const match = files.find((file) => pathname === `/manuals/${file.name}`)
    if (!match || !existsSync(match.source)) {
      res.statusCode = 404
      res.setHeader("Content-Type", "text/plain; charset=utf-8")
      res.setHeader("X-Content-Type-Options", "nosniff")
      res.setHeader("Cache-Control", "no-store")
      res.end("Not found")
      return
    }
    if (req.method !== "GET" && req.method !== "HEAD") {
      res.statusCode = 405
      res.setHeader("Allow", "GET, HEAD")
      res.end()
      return
    }
    const query = new URL(req.url ?? "/", "http://127.0.0.1").searchParams
    sendManual(req, res, match.source, match.type, match.downloadName, query.get("download") === "1")
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
