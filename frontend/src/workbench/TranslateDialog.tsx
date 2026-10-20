import { useEffect, useRef, useState, type MouseEvent } from "react"

import type { Diagnostic, Translation } from "../api"
import { useT } from "../i18n"
import { saveDownload } from "../saveFile"

export function TranslateDialog({
  translations,
  diagnostics,
  busy,
  failure,
  filename,
  onClose,
}: {
  translations: Translation[]
  diagnostics: Diagnostic[]
  busy: boolean
  failure: string
  filename: string
  onClose: () => void
}) {
  const t = useT()
  const [language, setLanguage] = useState(translations[0]?.language ?? "python")
  const armed = useRef(false)
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose()
    }
    // The opening click can be delivered again to this layer once it covers the
    // toolbar. Brave and the desktop webview do that; Safari does not. Ignore
    // that click and accept a later one, whose pointerup arrives first.
    function arm() {
      armed.current = true
    }
    window.addEventListener("keydown", onKey)
    window.addEventListener("pointerup", arm)
    window.addEventListener("pointercancel", arm)
    return () => {
      window.removeEventListener("keydown", onKey)
      window.removeEventListener("pointerup", arm)
      window.removeEventListener("pointercancel", arm)
    }
  }, [onClose])
  function dismissBackdrop(event: MouseEvent<HTMLDivElement>) {
    if (!armed.current || event.target !== event.currentTarget) return
    onClose()
  }
  const [copied, setCopied] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const current = translations.find((item) => item.language === language) ?? translations[0]
  const errors = diagnostics.filter((item) => item.severity === "error")

  function download() {
    if (!current?.code) return
    void saveDownload(`${filename}.${current.extension}`, new Blob([current.code], { type: "text/plain;charset=utf-8" }))
  }

  async function copy() {
    if (!current?.code) return
    try {
      await navigator.clipboard.writeText(current.code)
      setCopied(true)
    } catch {
      setCopied(false)
    }
  }

  return (
    <div className="translate-backdrop" role="presentation" onMouseDown={dismissBackdrop} onClick={dismissBackdrop}>
      <section
        className={expanded ? "translate-dialog is-expanded" : "translate-dialog"}
        role="dialog"
        aria-modal="true"
        aria-labelledby="translate-title"
        onMouseDown={(event) => event.stopPropagation()}
        onClick={(event) => event.stopPropagation()}
      >
        <header>
          <h2 id="translate-title">{t("translateTitle")}</h2>
          <div className="translate-header-actions">
            <button type="button" aria-pressed={expanded} onClick={() => setExpanded((value) => !value)}>
              {expanded ? t("translateRestore") : t("translateExpand")}
            </button>
            <button type="button" onClick={onClose}>
              {t("close")}
            </button>
          </div>
        </header>
        <p>{t("translateNote")}</p>
        {failure && <p className="error">{failure}</p>}
        {busy && <p>{t("loading")}</p>}
        {errors.length > 0 && (
          <>
            <p className="translate-errors">{t("translateErrors")}</p>
            <ul className="translate-errors">
              {errors.map((item) => (
                <li key={`${item.code}-${item.line}-${item.column}`}>
                  {item.line}:{item.column} {item.message}
                </li>
              ))}
            </ul>
          </>
        )}
        {translations.length > 0 && current && (
          <>
            <div className="translate-tabs" role="tablist">
              {translations.map((item) => (
                <button
                  key={item.language}
                  type="button"
                  role="tab"
                  aria-selected={item.language === current.language}
                  onClick={() => {
                    setLanguage(item.language)
                    setCopied(false)
                  }}
                >
                  {item.label}
                </button>
              ))}
            </div>
            <textarea readOnly spellCheck={false} value={current.code} aria-label={current.label} />
            <div className="translate-actions">
              <button type="button" onClick={() => void copy()} disabled={!current.code}>
                {copied ? t("copied") : t("copy")}
              </button>
              <button type="button" onClick={download} disabled={!current.code}>
                {t("download")}
              </button>
            </div>
          </>
        )}
        {!busy && !failure && translations.length === 0 && errors.length === 0 && <p>{t("translateEmpty")}</p>}
      </section>
    </div>
  )
}
