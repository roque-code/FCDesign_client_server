import type { PointerEvent as ReactPointerEvent } from "react"

type Layout = Record<string, number | boolean>

export function clamp(value: number, min: number, max: number): number {
  return Math.round(Math.min(Math.max(value, min), Math.max(min, max)))
}

/** Toma de lo guardado solo los valores del mismo tipo que el predeterminado; el resto se descarta. */
export function readLayout<T extends Layout>(storage: Pick<Storage, "getItem"> | null, key: string, defaults: T): T {
  try {
    const raw = storage?.getItem(key)
    const parsed: unknown = raw ? JSON.parse(raw) : null
    if (!parsed || typeof parsed !== "object") return defaults
    const stored = parsed as Record<string, unknown>
    const result: Layout = { ...defaults }
    for (const name of Object.keys(defaults)) {
      const value = stored[name]
      if (typeof defaults[name] === "boolean" && typeof value === "boolean") result[name] = value
      if (typeof defaults[name] === "number" && typeof value === "number" && Number.isFinite(value) && value > 0) {
        result[name] = Math.round(value)
      }
    }
    return result as T
  } catch {
    return defaults
  }
}

export function writeLayout(storage: Pick<Storage, "setItem"> | null, key: string, layout: Layout): void {
  try {
    storage?.setItem(key, JSON.stringify(layout))
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
