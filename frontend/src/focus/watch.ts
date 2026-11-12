import type { FocusReport } from "../api"

type FullscreenDocument = Document & {
  webkitFullscreenElement?: Element | null
}

type FullscreenElement = HTMLElement & {
  webkitRequestFullscreen?: () => Promise<void> | void
}

export function fullscreenSupported(): boolean {
  const root = document.documentElement as FullscreenElement
  return typeof root.requestFullscreen === "function" || typeof root.webkitRequestFullscreen === "function"
}

export function inFullscreen(): boolean {
  if (typeof document === "undefined") return false
  const doc = document as FullscreenDocument
  return Boolean(doc.fullscreenElement ?? doc.webkitFullscreenElement)
}

export function enterFullscreen(): void {
  if (inFullscreen()) return
  const root = document.documentElement as FullscreenElement
  try {
    const asked = root.requestFullscreen ? root.requestFullscreen() : root.webkitRequestFullscreen?.()
    if (asked && typeof asked.catch === "function") asked.catch(() => undefined)
  } catch {
    // El navegador puede negarse fuera de un clic; el aviso ofrece el botón.
  }
}

export function leaveFullscreen(): void {
  if (!document.fullscreenElement) return
  void document.exitFullscreen().catch(() => undefined)
}

export function awayClock(seconds: number): string {
  const whole = Math.max(0, Math.round(seconds))
  const minutes = Math.floor(whole / 60)
  const rest = whole % 60
  return minutes ? `${minutes} min ${rest} s` : `${rest} s`
}

export function exitsLeft(report: FocusReport): number | null {
  return report.limit == null ? null : Math.max(0, report.limit - report.exits)
}
