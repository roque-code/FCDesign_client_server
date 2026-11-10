import type { PointerEvent as ReactPointerEvent } from "react"

export type Panes = { programs: number; peek: number; output: number; students: number }

export const DEFAULT_PANES: Panes = { programs: 256, peek: 340, output: 144, students: 220 }

const KEY = "traza.foreign.panes"

export function clamp(value: number, min: number, max: number): number {
  return Math.round(Math.min(Math.max(value, min), Math.max(min, max)))
}

export function readPanes(storage: Pick<Storage, "getItem"> | null): Panes {
  try {
    const raw = storage?.getItem(KEY)
    const parsed: unknown = raw ? JSON.parse(raw) : null
    if (!parsed || typeof parsed !== "object") return DEFAULT_PANES
    const stored = parsed as Record<string, unknown>
    const pick = (key: keyof Panes) => {
      const value = stored[key]
      return typeof value === "number" && Number.isFinite(value) && value > 0 ? Math.round(value) : DEFAULT_PANES[key]
    }
    return { programs: pick("programs"), peek: pick("peek"), output: pick("output"), students: pick("students") }
  } catch {
    return DEFAULT_PANES
  }
}

export function writePanes(storage: Pick<Storage, "setItem"> | null, panes: Panes): void {
  try {
    storage?.setItem(KEY, JSON.stringify(panes))
  } catch {
    /* Sin almacenamiento, el tamaño dura lo que la pantalla. */
  }
}

export function browserStorage(): Storage | null {
  try {
    return typeof localStorage === "undefined" ? null : localStorage
  } catch {
    return null
  }
}

/** Sigue el puntero sobre un separador hasta soltarlo; `onMove` recibe la coordenada del eje. */
export function followPointer(event: ReactPointerEvent<HTMLElement>, axis: "x" | "y", onMove: (position: number) => void) {
  event.preventDefault()
  const handle = event.currentTarget
  try {
    handle.setPointerCapture(event.pointerId)
  } catch {
    /* El arrastre sigue por los eventos del propio separador. */
  }
  const page = document.body
  const cursor = page.style.cursor
  const select = page.style.userSelect
  page.style.cursor = axis === "x" ? "col-resize" : "row-resize"
  page.style.userSelect = "none"
  const move = (ev: PointerEvent) => onMove(axis === "x" ? ev.clientX : ev.clientY)
  const stop = () => {
    handle.removeEventListener("pointermove", move)
    handle.removeEventListener("pointerup", stop)
    handle.removeEventListener("pointercancel", stop)
    page.style.cursor = cursor
    page.style.userSelect = select
  }
  handle.addEventListener("pointermove", move)
  handle.addEventListener("pointerup", stop)
  handle.addEventListener("pointercancel", stop)
}
