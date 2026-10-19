import { useEffect, useState } from "react"
import mammoth from "mammoth"

import type { AccountRole } from "../api"
import { useLocale, useT, type MessageKey } from "../i18n"

type Manual = {
  viewHref: string
  downloadHref: string
  file: string
  label: MessageKey
}

const MANUALS: Record<"language" | "student" | "teacher", Manual> = {
  language: {
    viewHref: "/manuals/lenguaje.docx",
    downloadHref: "/manuals/lenguaje.pdf",
    file: "Manual-del-lenguaje.pdf",
    label: "languageManual",
  },
  student: {
    viewHref: "/manuals/alumno.docx",
    downloadHref: "/manuals/alumno.pdf",
    file: "Manual-del-alumno.pdf",
    label: "studentManual",
  },
  teacher: {
    viewHref: "/manuals/docente.docx",
    downloadHref: "/manuals/docente.pdf",
    file: "Manual-del-docente.pdf",
    label: "teacherManual",
  },
}

const GROUPS: { title: MessageKey; items: { es: string; en: string; text: MessageKey }[] }[] = [
  { title: "opGroupAssign", items: [{ es: "<-", en: "<-", text: "opAssign" }] },
  {
    title: "opGroupMath",
    items: [
      { es: "+", en: "+", text: "opPlus" },
      { es: "-", en: "-", text: "opMinus" },
      { es: "*", en: "*", text: "opTimes" },
      { es: "/", en: "/", text: "opSlash" },
      { es: "^", en: "^", text: "opPower" },
      { es: "DIV", en: "Div", text: "opDiv" },
      { es: "MOD", en: "Mod", text: "opMod" },
      { es: "%", en: "%", text: "opPercent" },
    ],
  },
  {
    title: "opGroupCompare",
    items: [
      { es: "=", en: "=", text: "opEq" },
      { es: "<>", en: "<>", text: "opNotEq" },
      { es: "!=", en: "!=", text: "opNotEqAlt" },
      { es: "<", en: "<", text: "opLt" },
      { es: "<=", en: "<=", text: "opLe" },
      { es: ">", en: ">", text: "opGt" },
      { es: ">=", en: ">=", text: "opGe" },
    ],
  },
  {
    title: "opGroupLogic",
    items: [
      { es: "NO", en: "Not", text: "opNot" },
      { es: "Y", en: "And", text: "opAnd" },
      { es: "O", en: "Or", text: "opOr" },
    ],
  },
  { title: "opGroupGroup", items: [{ es: "( )", en: "( )", text: "opParen" }] },
]

export function GuideButtons({ role }: { role: AccountRole }) {
  const t = useT()
  const locale = useLocale()
  const [operatorsOpen, setOperatorsOpen] = useState(false)
  const [manualsOpen, setManualsOpen] = useState(false)
  const [viewing, setViewing] = useState<Manual | null>(null)
  const manuals = role === "teacher"
    ? [MANUALS.language, MANUALS.student, MANUALS.teacher]
    : [MANUALS.language, MANUALS.student]

  useEffect(() => {
    if (!operatorsOpen && !manualsOpen) return
    function close(event: MouseEvent) {
      const target = event.target
      const element = target instanceof Element ? target : target instanceof Node ? target.parentElement : null
      if (element?.closest(".guide-anchor, .manual-backdrop")) return
      setOperatorsOpen(false)
      setManualsOpen(false)
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOperatorsOpen(false)
        setManualsOpen(false)
      }
    }
    document.addEventListener("mousedown", close)
    document.addEventListener("keydown", onKey)
    return () => {
      document.removeEventListener("mousedown", close)
      document.removeEventListener("keydown", onKey)
    }
  }, [operatorsOpen, manualsOpen])

  return (
    <>
      <div className="functions guide-anchor">
        <button
          className="top-action"
          type="button"
          aria-expanded={operatorsOpen}
          aria-controls="operadores"
          onClick={() => {
            setManualsOpen(false)
            setOperatorsOpen((open) => !open)
          }}
        >
          {t("operatorButton")}
        </button>
        {operatorsOpen && (
          <div className="functions-menu" id="operadores" role="dialog" aria-label={t("operatorsTitle")}>
            <h2>{t("operatorsTitle")}</h2>
            <p className="note">{t("operatorsNote")}</p>
            {GROUPS.map((group) => (
              <section key={group.title}>
                <h3>{t(group.title)}</h3>
                <ul>
                  {group.items.map((item) => (
                    <li key={item.text}>
                      <code>{locale === "en" ? item.en : item.es}</code>
                      <p>{t(item.text)}</p>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
        )}
      </div>
      <div className="functions guide-anchor">
        <button
          className="top-action"
          type="button"
          aria-expanded={manualsOpen}
          aria-controls="manuales"
          onClick={() => {
            setOperatorsOpen(false)
            setManualsOpen((open) => !open)
          }}
        >
          {t("manuals")}
        </button>
        {manualsOpen && (
          <div className="functions-menu manuals-menu" id="manuales" role="dialog" aria-label={t("manualsTitle")}>
            <h2>{t("manualsTitle")}</h2>
            <ul>
              {manuals.map((manual) => (
                <li key={manual.downloadHref} className="manual-row">
                  <strong>{t(manual.label)}</strong>
                  <span>
                    <button
                      type="button"
                      onClick={() => {
                        setManualsOpen(false)
                        setViewing(manual)
                      }}
                    >
                      {t("viewManual")}
                    </button>
                    <a className="manual-download" href={manual.downloadHref} download={manual.file}>
                      {t("downloadManual")}
                    </a>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
      {viewing ? <ManualView manual={viewing} onClose={() => setViewing(null)} /> : null}
    </>
  )
}

function ManualView({ manual, onClose }: { manual: Manual; onClose: () => void }) {
  const t = useT()
  const [html, setHtml] = useState("")
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let active = true
    setHtml("")
    setFailed(false)
    void fetch(manual.viewHref)
      .then(async (response) => {
        if (!response.ok) throw new Error("missing")
        const arrayBuffer = await response.arrayBuffer()
        const result = await mammoth.convertToHtml(
          { arrayBuffer },
          { convertImage: mammoth.images.dataUri },
        )
        if (active) setHtml(result.value)
      })
      .catch(() => {
        if (active) setFailed(true)
      })
    return () => {
      active = false
    }
  }, [manual])

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose()
    }
    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [onClose])

  return (
    <div className="manual-backdrop" onMouseDown={onClose}>
      <section
        className="manual-dialog"
        role="dialog"
        aria-modal="true"
        aria-label={t(manual.label)}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header>
          <h2>{t(manual.label)}</h2>
          <span>
            <a className="manual-download" href={manual.downloadHref} download={manual.file}>
              {t("downloadManual")}
            </a>
            <button type="button" onClick={onClose}>{t("close")}</button>
          </span>
        </header>
        {failed ? <p className="error">{t("manualError")}</p> : null}
        {!failed && html === "" ? <p className="note">{t("manualLoading")}</p> : null}
        {html !== "" ? <article className="manual-sheet" dangerouslySetInnerHTML={{ __html: html }} /> : null}
      </section>
    </div>
  )
}
