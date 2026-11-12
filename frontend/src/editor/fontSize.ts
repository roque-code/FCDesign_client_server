import { useEffect, useSyncExternalStore } from "react"

import { api } from "../api"

export const EDITOR_FONT_SIZE = 16

let size = EDITOR_FONT_SIZE
const listeners = new Set<() => void>()

/** Un solo tamaño de letra para todos los editores; los campos de código lo leen de `--editor-font-size`. */
export function shareEditorFont(next: number) {
  if (!Number.isFinite(next) || next <= 0 || next === size) return
  size = next
  if (typeof document !== "undefined") document.documentElement.style.setProperty("--editor-font-size", `${next}px`)
  for (const listener of listeners) listener()
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

function current() {
  return size
}

export function useEditorFont(): number {
  return useSyncExternalStore(subscribe, current, current)
}

/** Lee el tamaño guardado de la cuenta al entrar; sin cuenta vuelve al tamaño de fábrica. */
export function useAccountEditorFont(accountId: number | null) {
  useEffect(() => {
    if (accountId === null) {
      shareEditorFont(EDITOR_FONT_SIZE)
      return
    }
    let active = true
    void api.preferences().then(
      (prefs) => {
        if (active) shareEditorFont(prefs.font_size)
      },
      () => undefined,
    )
    return () => {
      active = false
    }
  }, [accountId])
}
