import type { LabBinding } from "../api"

export type StageName = "comprender" | "razonar" | "construir" | "comprobar" | "lenguaje" | "explicar"

export function blockOnLine(bindings: LabBinding[], line: number | null): string | null {
  if (line == null) return null
  const hits = bindings.filter((item) => item.line === line)
  if (hits.length === 0) return null
  hits.sort((a, b) => a.column - b.column)
  return hits[0].block_id
}

export function stagesFor(activity: string): StageName[] {
  if (activity === "classify" || activity === "order") return ["comprender", "razonar", "explicar"]
  if (activity === "predict") return ["comprender", "razonar", "comprobar", "explicar"]
  return ["comprender", "razonar", "construir", "comprobar", "lenguaje", "explicar"]
}

export function formatClock(seconds: number): string {
  const safe = Math.max(0, Math.floor(seconds))
  const minutes = Math.floor(safe / 60)
  const rest = safe % 60
  return `${minutes}:${String(rest).padStart(2, "0")}`
}

export function formatWhen(iso: string, locale: "es" | "en" = "es"): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ""
  return date.toLocaleString(locale === "en" ? "en-US" : "es-MX", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export function formatLimit(seconds: number): string {
  if (seconds < 60) return `${seconds} s`
  const minutes = Math.floor(seconds / 60)
  const rest = seconds % 60
  if (rest === 0) return `${minutes} min`
  return formatClock(seconds)
}

export function buildLocked(activity: string, nextStage: string): boolean {
  return activity === "build" && (nextStage === "comprender" || nextStage === "razonar")
}
