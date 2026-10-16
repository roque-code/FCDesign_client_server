import { useEffect, useState } from "react"

import type { Diagnostic, Translation } from "../api"
import { useT } from "../i18n"

export function TranslateDialog({
  translations,
  diagnostics,
  busy,
  filename,
  onClose,
}: {
  translations: Translation[]
  diagnostics: Diagnostic[]
  busy: boolean
  filename: string
  onClose: () => void
}) {
  const t = useT()
  const [language, setLanguage] = useState(translations[0]?.language ?? "python")
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose()
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [onClose])
  const [copied, setCopied] = useState(false)
  const current = translations.find((item) => item.language === language) ?? translations[0]
  const errors = diagnostics.filter((item) => item.severity === "error")

  function download() {
    if (!current?.code) return
    const blob = new Blob([current.code], { type: "text/plain;charset=utf-8" })
    const link = document.createElement("a")
    link.href = URL.createObjectURL(blob)
    link.download = `${filename}.${current.extension}`
    document.body.append(link)
    link.click()
    link.remove()
    window.setTimeout(() => URL.revokeObjectURL(link.href), 1000)
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
    <div className="translate-backdrop" role="presentation" onClick={onClose}>
      <section
        className="translate-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="translate-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header>
          <h2 id="translate-title">{t("translateTitle")}</h2>
          <button type="button" onClick={onClose}>
            {t("close")}
          </button>
        </header>
        <p>{t("translateNote")}</p>
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
        {!busy && translations.length === 0 && errors.length === 0 && <p>{t("translateEmpty")}</p>}
      </section>
    </div>
  )
}
