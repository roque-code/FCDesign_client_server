import { useEffect, useRef, useState } from "react"

import { useT } from "../i18n"
import { inInstalledApp } from "../runtime"

/** F5, Ctrl+R o Cmd+R, con o sin Shift. */
export function isReloadKey(event: Pick<KeyboardEvent, "key" | "ctrlKey" | "metaKey" | "altKey">): boolean {
  if (event.key === "F5") return true
  return (event.ctrlKey || event.metaKey) && !event.altKey && event.key.toLowerCase() === "r"
}

/** El botón de recargar del navegador y cerrar la pestaña solo admiten el aviso propio del navegador. */
export function ReloadGuard({ active }: { active: boolean }) {
  const t = useT()
  const [asking, setAsking] = useState(false)
  const leaving = useRef(false)
  const stayRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!active) {
      setAsking(false)
      return
    }
    function onKey(event: KeyboardEvent) {
      if (!isReloadKey(event)) return
      event.preventDefault()
      event.stopPropagation()
      setAsking(true)
    }
    function onLeave(event: BeforeUnloadEvent) {
      if (leaving.current) return
      event.preventDefault()
      event.returnValue = ""
    }
    const native = !inInstalledApp()
    window.addEventListener("keydown", onKey, true)
    if (native) window.addEventListener("beforeunload", onLeave)
    return () => {
      window.removeEventListener("keydown", onKey, true)
      if (native) window.removeEventListener("beforeunload", onLeave)
    }
  }, [active])

  useEffect(() => {
    if (asking) stayRef.current?.focus()
  }, [asking])

  if (!active || !asking) return null
  return (
    <div className="reload-backdrop" role="presentation" onClick={() => setAsking(false)}>
      <section
        className="reload-dialog"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="reload-title"
        aria-describedby="reload-note"
        onClick={(event) => event.stopPropagation()}
        onKeyDown={(event) => {
          if (event.key === "Escape") setAsking(false)
        }}
      >
        <h2 id="reload-title">{t("reloadTitle")}</h2>
        <p id="reload-note">{t("reloadNote")}</p>
        <div className="reload-actions">
          <button
            type="button"
            onClick={() => {
              leaving.current = true
              window.location.reload()
            }}
          >
            {t("reloadConfirm")}
          </button>
          <button ref={stayRef} type="button" className="primary" onClick={() => setAsking(false)}>
            {t("reloadStay")}
          </button>
        </div>
      </section>
    </div>
  )
}
