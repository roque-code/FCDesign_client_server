import { useEffect, useRef, useState, type FormEvent } from "react"
import { createPortal } from "react-dom"

import { ApiError, api, type ExerciseFeedback, type ExerciseKind, type FeedbackPage } from "../api"
import { translatedMessage, useLocale, useT } from "../i18n"
import { saveDownload } from "../saveFile"
import { feedbackOn, formatDay, formatGrade, gradeInput, withBom } from "./grades"

function problem(caught: unknown, fallback: string): string {
  return caught instanceof ApiError ? translatedMessage(caught.message) : fallback
}

export function useMyFeedback(enabled: boolean, kind: ExerciseKind, exerciseId: string): ExerciseFeedback[] {
  const [items, setItems] = useState<ExerciseFeedback[]>([])
  useEffect(() => {
    setItems([])
    if (!enabled || !exerciseId) return
    let ignore = false
    void api.myFeedback({ kind, exercise: exerciseId, pageSize: 50 }).then(
      (payload) => {
        if (!ignore) setItems(payload.results)
      },
      () => undefined,
    )
    return () => {
      ignore = true
    }
  }, [enabled, kind, exerciseId])
  return items
}

export function FeedbackForm({ kind, exerciseId, exerciseName }: { kind: ExerciseKind; exerciseId: string; exerciseName: string }) {
  const t = useT()
  const [grade, setGrade] = useState("")
  const [comment, setComment] = useState("")
  const [busy, setBusy] = useState(true)
  const [note, setNote] = useState("")
  const [failure, setFailure] = useState("")

  useEffect(() => {
    let ignore = false
    setBusy(true)
    setNote("")
    setFailure("")
    setGrade("")
    setComment("")
    void api.exerciseFeedback(kind, exerciseId).then(
      (payload) => {
        if (ignore) return
        setGrade(gradeInput(payload.feedback?.grade ?? null))
        setComment(payload.feedback?.comment ?? "")
        setBusy(false)
      },
      (caught: unknown) => {
        if (ignore) return
        setFailure(problem(caught, t("feedbackLoadFailed")))
        setBusy(false)
      },
    )
    return () => {
      ignore = true
    }
  }, [kind, exerciseId])

  async function save(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setNote("")
    setFailure("")
    try {
      const payload = await api.saveExerciseFeedback(kind, exerciseId, {
        grade: grade.trim() === "" ? null : grade.trim(),
        comment,
      })
      setGrade(gradeInput(payload.feedback?.grade ?? null))
      setComment(payload.feedback?.comment ?? "")
      setNote(payload.feedback ? t("feedbackSaved") : t("feedbackCleared"))
    } catch (caught) {
      setFailure(problem(caught, t("feedbackFailed")))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="feedback-form" onSubmit={(event) => void save(event)} aria-busy={busy}>
      <h2>{t("feedbackTitle")}</h2>
      <p className="note">{t("feedbackFor", { name: exerciseName })}</p>
      <label>
        {t("feedbackGrade")}
        <input
          type="text"
          inputMode="decimal"
          maxLength={6}
          placeholder="0 – 100"
          value={grade}
          onChange={(event) => setGrade(event.target.value)}
        />
      </label>
      <label>
        {t("feedbackComment")}
        <textarea rows={3} maxLength={2000} value={comment} onChange={(event) => setComment(event.target.value)} />
      </label>
      <button className="primary" type="submit" disabled={busy}>
        {t("feedbackSave")}
      </button>
      <p className="note">{t("feedbackClearHint")}</p>
      {note ? <p className="note" role="status">{note}</p> : null}
      {failure ? <p className="error" role="alert">{failure}</p> : null}
    </form>
  )
}

export function FeedbackNotes({ items, kind, exerciseId }: { items: ExerciseFeedback[]; kind: ExerciseKind; exerciseId: string }) {
  const t = useT()
  const locale = useLocale()
  const shown = feedbackOn(items, kind, exerciseId)
  if (shown.length === 0) return null
  return (
    <section className="feedback-notes" aria-label={t("feedbackFromTeacher")}>
      <h2>{t("feedbackFromTeacher")}</h2>
      {shown.map((item) => (
        <FeedbackItem key={item.id} item={item} locale={locale} />
      ))}
    </section>
  )
}

function FeedbackItem({ item, locale }: { item: ExerciseFeedback; locale: string }) {
  const t = useT()
  return (
    <article className="feedback-item">
      <p>
        <span className="feedback-grade">{item.grade === null ? t("feedbackNoGrade") : formatGrade(locale, item.grade)}</span>
        <span className="note">{t("feedbackBy", { teacher: item.teacher.display_name })}</span>
      </p>
      {item.comment ? <p className="feedback-comment">{item.comment}</p> : null}
    </article>
  )
}

export function GradesDownload({ group }: { group: string }) {
  const t = useT()
  const locale = useLocale()
  const [busy, setBusy] = useState(false)
  const [failure, setFailure] = useState("")

  async function download() {
    setBusy(true)
    setFailure("")
    try {
      const csv = await api.gradesCsv(locale === "en" ? "en" : "es", group)
      await saveDownload(gradesFilename(group), new Blob([withBom(csv)], { type: "text/csv;charset=utf-8" }))
    } catch (caught) {
      setFailure(problem(caught, t("gradesCsvFailed")))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grades-download">
      <button type="button" onClick={() => void download()} disabled={busy}>
        {t("gradesCsv")}
      </button>
      <p className="note">{group ? t("gradesCsvGroup", { group }) : t("gradesCsvAll")}</p>
      {failure ? <p className="error" role="alert">{failure}</p> : null}
    </div>
  )
}

function gradesFilename(group: string): string {
  const folded = group.normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase()
  const cleaned = folded.replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60)
  return `calificaciones-${cleaned || "alumnos"}.csv`
}

export function MyGradesMenu() {
  const t = useT()
  const [open, setOpen] = useState(false)
  const opener = useRef<HTMLButtonElement>(null)

  return (
    <>
      <button
        ref={opener}
        className="top-action"
        type="button"
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => setOpen(true)}
      >
        {t("myGrades")}
      </button>
      {open &&
        createPortal(
          <MyGradesDialog
            onClose={() => {
              setOpen(false)
              opener.current?.focus()
            }}
          />,
          document.body,
        )}
    </>
  )
}

const GRADES_PAGE = 10

function MyGradesDialog({ onClose }: { onClose: () => void }) {
  const t = useT()
  const locale = useLocale()
  const [kind, setKind] = useState<ExerciseKind | "">("")
  const [language, setLanguage] = useState("")
  const [page, setPage] = useState(1)
  const [data, setData] = useState<FeedbackPage | null>(null)
  const [busy, setBusy] = useState(true)
  const [failure, setFailure] = useState("")
  const closeButton = useRef<HTMLButtonElement>(null)
  const body = useRef<HTMLDivElement>(null)
  const closing = useRef(onClose)
  closing.current = onClose

  useEffect(() => {
    closeButton.current?.focus()
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") closing.current()
    }
    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [])

  useEffect(() => {
    let ignore = false
    setBusy(true)
    setFailure("")
    void api.myFeedback({ kind, language, page, pageSize: GRADES_PAGE }).then(
      (payload) => {
        if (ignore) return
        setData(payload)
        if (payload.page !== page) setPage(payload.page)
        setBusy(false)
        body.current?.scrollTo({ top: 0 })
      },
      (caught: unknown) => {
        if (ignore) return
        setFailure(problem(caught, t("feedbackLoadFailed")))
        setBusy(false)
      },
    )
    return () => {
      ignore = true
    }
  }, [kind, language, page])

  function choose(next: ExerciseKind | "") {
    setKind(next)
    setLanguage("")
    setPage(1)
  }

  const totals = data?.totals
  const tabs: [ExerciseKind | "", string][] = totals
    ? [
        ["", t("myGradesAll", { count: totals.all })],
        ["algorithm", t("myGradesPseudo", { count: totals.algorithm })],
        ["program", t("myGradesPrograms", { count: totals.program })],
      ]
    : []

  return (
    <div
      className="grades-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <section className="grades-dialog" role="dialog" aria-modal="true" aria-labelledby="grades-title">
        <header>
          <h2 id="grades-title">{t("myGradesTitle")}</h2>
          <button ref={closeButton} type="button" onClick={onClose}>
            {t("close")}
          </button>
        </header>
        {totals && totals.all > 0 ? (
          <div className="grades-filters">
            <div className="tabs" role="tablist" aria-label={t("myGradesFilter")}>
              {tabs.map(([value, label]) => (
                <button
                  key={value || "all"}
                  type="button"
                  role="tab"
                  aria-selected={kind === value}
                  onClick={() => choose(value)}
                >
                  {label}
                </button>
              ))}
            </div>
            {kind === "program" && data && data.languages.length > 0 ? (
              <label>
                {t("myGradesLanguage")}
                <select
                  value={language}
                  onChange={(event) => {
                    setLanguage(event.target.value)
                    setPage(1)
                  }}
                >
                  <option value="">{t("myGradesAnyLanguage")}</option>
                  {data.languages.map((item) => (
                    <option key={item.code} value={item.code}>
                      {item.label} ({item.count})
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
          </div>
        ) : null}
        {data && data.count > 0 ? (
          <p className="note grades-summary">
            {data.count === 1 ? t("myGradesCountOne") : t("myGradesCount", { count: data.count })}
            {data.average !== null ? ` · ${t("myGradesAverage", { average: formatGrade(locale, data.average) })}` : ""}
          </p>
        ) : null}
        {failure ? (
          <p className="error" role="alert">
            {failure}
          </p>
        ) : null}
        <div className="grades-body" ref={body} aria-busy={busy}>
          {data === null && busy ? <p className="note">{t("loading")}</p> : null}
          {data && data.totals.all === 0 ? <p className="note">{t("myGradesEmpty")}</p> : null}
          {data && data.totals.all > 0 && data.count === 0 ? <p className="note">{t("myGradesNone")}</p> : null}
          {data && data.results.length > 0 ? (
            <ol className="grades-list">
              {data.results.map((item) => (
                <li key={item.id}>
                  <GradeRow item={item} locale={locale} />
                </li>
              ))}
            </ol>
          ) : null}
        </div>
        {data && data.pages > 1 ? (
          <nav className="grades-pager" aria-label={t("myGradesPages")}>
            <button type="button" disabled={busy || data.page <= 1} onClick={() => setPage(data.page - 1)}>
              {t("myGradesPrev")}
            </button>
            <span aria-live="polite">{t("myGradesPage", { page: data.page, pages: data.pages })}</span>
            <button type="button" disabled={busy || data.page >= data.pages} onClick={() => setPage(data.page + 1)}>
              {t("myGradesNext")}
            </button>
          </nav>
        ) : null}
      </section>
    </div>
  )
}

function GradeRow({ item, locale }: { item: ExerciseFeedback; locale: string }) {
  const t = useT()
  const pseudo = item.kind === "algorithm"
  return (
    <article className="feedback-item grade-row">
      <div className="grade-row-head">
        <span className={pseudo ? "grade-kind" : "grade-kind is-program"}>{pseudo ? t("kindAlgorithm") : item.context}</span>
        <strong>{item.exercise_name}</strong>
        {pseudo ? <span className="note">{item.context}</span> : null}
      </div>
      <p>
        <span className="feedback-grade">{item.grade === null ? t("feedbackNoGrade") : formatGrade(locale, item.grade)}</span>
        <span className="note">
          {t("feedbackBy", { teacher: item.teacher.display_name })} · {formatDay(locale, item.updated_at)}
        </span>
      </p>
      {item.comment ? <p className="feedback-comment">{item.comment}</p> : null}
    </article>
  )
}
