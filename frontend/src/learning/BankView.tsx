import { useEffect, useMemo, useRef, useState } from "react"

import { ApiError, api, type CsvChallengeFormat, type LabBank, type LabBankChallenge, type LabBankShelf, type LabConcept } from "../api"
import { spellText } from "../dialect"
import { translatedMessage, useLocale, useT, type MessageKey } from "../i18n"
import { ChallengeForm } from "./ChallengeForm"
import { formatLimit } from "./trace"
import { TOOL_GROUPS } from "./toolbox"

const ACTIVITY: Record<string, MessageKey> = {
  classify: "classify",
  order: "order",
  build: "build",
  predict: "predict",
}

const CSV_KIND: Record<string, MessageKey> = {
  clasificar: "classify",
  ordenar: "order",
  construir: "build",
  predecir: "predict",
}

const CSV_NOTE: Record<string, MessageKey> = {
  clasificar: "csvNoteClassify",
  ordenar: "csvNoteOrder",
  construir: "csvNoteBuild",
  predecir: "csvNotePredict",
}

const BLOCK_LABEL = new Map(
  TOOL_GROUPS.flatMap((group) => group.blocks.map((block) => [block.id, block.labelKey])),
)

function messageOf(error: unknown, fallback: string): string {
  return error instanceof ApiError ? translatedMessage(error.message) : fallback
}

function ChallengeCard({
  item,
  busy,
  canChange,
  onEdit,
  onRetire,
}: {
  item: LabBankChallenge
  busy: boolean
  canChange: boolean
  onEdit: (id: string) => void
  onRetire: (item: LabBankChallenge) => void
}) {
  const t = useT()
  const locale = useLocale()
  const blocks =
    item.allowed_blocks.length === 0
      ? t("fullToolbox")
      : item.allowed_blocks.map((block) => (BLOCK_LABEL.get(block) ? t(BLOCK_LABEL.get(block) as MessageKey) : block)).join(", ")
  return (
    <article className="bank-card">
      <header className="entry-head">
        <span className="path-index">{item.position}</span>
        <div className="path-copy">
          <strong>{item.title}</strong>
          <p>
            <span className={`activity-chip activity-${item.activity_type}`}>
              {ACTIVITY[item.activity_type] ? t(ACTIVITY[item.activity_type]) : item.activity_type}
            </span>
            <span>{item.concept}</span>
            <span>{t("difficulty", { level: item.difficulty })}</span>
            <span>{t("pointsCount", { count: item.points })}</span>
            <span>{item.time_limit_seconds ? formatLimit(item.time_limit_seconds) : t("noLimit")}</span>
            {item.owned ? <span>{t("yours")}</span> : null}
          </p>
        </div>
      </header>
      <p className="bank-prompt">{item.prompt}</p>
      {item.activity_type === "classify" ? (
        <div className="bank-block">
          <h4>{t("categories")}</h4>
          <p>{item.categories.join(" · ")}</p>
          <h4>{t("phrases")}</h4>
          <ul>
            {item.items.map((row, index) => (
              <li key={`${index}-${row.text}`}>
                {row.text} <span>{row.category}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {item.activity_type === "order" ? (
        <div className="bank-block">
          <h4>{t("correctOrder")}</h4>
          <ol>
            {item.items.map((row) => (
              <li key={row.text}>{row.text}</li>
            ))}
          </ol>
        </div>
      ) : null}
      {item.activity_type === "build" || item.activity_type === "predict" ? (
        <div className="bank-block">
          <h4>{t("question")}</h4>
          <p>{item.question}</p>
          <h4>{t("acceptedAnswers")}</h4>
          <p>{item.accepted.join(" · ")}</p>
        </div>
      ) : null}
      {item.activity_type === "build" ? (
        <div className="bank-block">
          {item.cases.length > 0 ? (
            <>
              <h4>{t("casesWord")}</h4>
              <ul>
                {item.cases.map((row) => (
                  <li key={row.name}>
                    <strong>{row.name}</strong>
                    <span>{row.inputs.length === 0 ? t("noneWord") : row.inputs.join(" · ")}</span>
                    <pre>{row.expected_output}</pre>
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <>
              <h4>{t("inputs")}</h4>
              <p>{item.inputs.length === 0 ? t("noneWord") : item.inputs.join(" · ")}</p>
              <h4>{t("expectedOutput")}</h4>
              <pre>{item.expected_output}</pre>
            </>
          )}
          <h4>{t("blocksWord")}</h4>
          <p>{blocks}</p>
        </div>
      ) : null}
      {item.activity_type === "predict" && item.source ? (
        <div className="bank-block">
          <h4>{t("pseudocode")}</h4>
          <pre>{spellText(locale, item.source)}</pre>
        </div>
      ) : null}
      {item.hints.length > 0 ? (
        <div className="bank-block">
          <h4>{t("hints")}</h4>
          <ol className="hint-list">
            {item.hints.map((hint) => (
              <li key={hint} className={hint.includes("Esta es la solución explicada") ? "hint-solution" : undefined}>
                {hint}
              </li>
            ))}
          </ol>
        </div>
      ) : null}
      {canChange ? (
        <div className="practice-actions">
          <button type="button" onClick={() => onEdit(item.id)} disabled={busy}>
            {t("edit")}
          </button>
          <button type="button" className="danger" onClick={() => onRetire(item)} disabled={busy}>
            {t("retire")}
          </button>
        </div>
      ) : null}
    </article>
  )
}

export function BankView() {
  const t = useT()
  const [bank, setBank] = useState<LabBank | null>(null)
  const [concepts, setConcepts] = useState<LabConcept[]>([])
  const [error, setError] = useState("")
  const [concept, setConcept] = useState("")
  const [activity, setActivity] = useState("")
  const [query, setQuery] = useState("")
  const [editor, setEditor] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [reloadKey, setReloadKey] = useState(0)
  const [shelf, setShelf] = useState<"catalog" | "contest">("catalog")
  const [notice, setNotice] = useState("")
  const [formats, setFormats] = useState<CsvChallengeFormat[] | null>(null)
  const [formatOpen, setFormatOpen] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    let cancelled = false
    void Promise.all([api.labBank(), api.labCatalog()]).then(
      ([result, catalog]) => {
        if (cancelled) return
        setBank(result)
        setConcepts(catalog.concepts)
      },
      (caught: unknown) => {
        if (!cancelled) setError(messageOf(caught, t("bankError")))
      },
    )
    return () => {
      cancelled = true
    }
  }, [reloadKey])

  const active: LabBankShelf | null = bank == null ? null : shelf === "contest" ? bank.contest : bank
  const needle = query.trim().toLocaleLowerCase()
  const units = useMemo(() => {
    if (!active) return []
    return active.units
      .map((unit) => ({
        ...unit,
        challenges: unit.challenges.filter((item) => {
          if (concept && item.concept !== concept) return false
          if (activity && item.activity_type !== activity) return false
          if (!needle) return true
          return `${item.title} ${item.prompt}`.toLocaleLowerCase().includes(needle)
        }),
      }))
      .filter((unit) => unit.challenges.length > 0)
  }, [active, activity, concept, needle])
  const total = active?.units.reduce((sum, unit) => sum + unit.challenges.length, 0) ?? 0
  const shown = units.reduce((sum, unit) => sum + unit.challenges.length, 0)

  function chooseShelf(next: "catalog" | "contest") {
    setShelf(next)
    setConcept("")
    setEditor(null)
  }

  async function openFormat() {
    if (formatOpen) {
      setFormatOpen(false)
      return
    }
    setFormatOpen(true)
    if (formats) return
    try {
      const body = await api.labCsvFormats()
      setFormats(body.types)
    } catch (caught) {
      setError(messageOf(caught, t("bankError")))
    }
  }

  async function upload(file: File | undefined) {
    if (!file) {
      setError(t("csvChoose"))
      return
    }
    setBusy(true)
    setError("")
    setNotice("")
    try {
      const result = await api.importLabCsv(await file.text())
      setNotice(t("csvImported", { count: result.created }))
      setShelf("catalog")
      setConcept("")
      setReloadKey((value) => value + 1)
    } catch (caught) {
      setError(messageOf(caught, t("bankError")))
    } finally {
      setBusy(false)
      if (fileRef.current) fileRef.current.value = ""
    }
  }

  function download(item: CsvChallengeFormat) {
    const url = URL.createObjectURL(new Blob([item.example], { type: "text/csv;charset=utf-8" }))
    const link = document.createElement("a")
    link.href = url
    link.download = `${item.tipo}.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  async function retire(item: LabBankChallenge) {
    if (!window.confirm(t("retireConfirm", { name: item.title }))) return
    setBusy(true)
    setError("")
    try {
      await api.deleteLabChallenge(item.id)
      if (editor === item.id) setEditor(null)
      setReloadKey((value) => value + 1)
    } catch (caught) {
      setError(messageOf(caught, t("bankError")))
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <section className="enunciado path-intro">
        <div>
          <p className="enunciado-kicker">{t("bank")}</p>
          <h2>{active?.name ?? t("bankOf")}</h2>
          {active?.description ? <p className="roster-meta">{active.description}</p> : null}
        </div>
        <p className="path-count">
          <strong>{active ? shown : "—"}</strong>
          <span>{active && shown !== total ? t("ofTotal", { total }) : t("challengesWord")}</span>
        </p>
      </section>
      <main className="lab-main bank-board">
        {error ? <p className="error">{error}</p> : null}
        {notice ? <p className="roster-meta">{notice}</p> : null}
        {shelf === "contest" ? <p className="roster-meta">{t("contestLocked")}</p> : null}
        <div className="bank-filters">
          <div className="bank-toolbar">
            <button type="button" aria-current={shelf === "catalog" ? "page" : undefined} onClick={() => chooseShelf("catalog")}>
              {t("mainShelf")}
            </button>
            <button type="button" aria-current={shelf === "contest" ? "page" : undefined} onClick={() => chooseShelf("contest")} disabled={!bank?.contest}>
              {t("contestShelf")}
            </button>
          </div>
          <label>
            {t("topic")}
            <select value={concept} onChange={(event) => setConcept(event.target.value)}>
              <option value="">{t("all")}</option>
              {active?.units.map((unit) => (
                <option key={unit.title} value={unit.concept}>
                  {unit.title}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t("kindWord")}
            <select value={activity} onChange={(event) => setActivity(event.target.value)}>
              <option value="">{t("all")}</option>
              {Object.entries(ACTIVITY).map(([id, label]) => (
                <option key={id} value={id}>
                  {t(label)}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t("search")}
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={t("searchChallenge")}
            />
          </label>
          <div className="bank-toolbar">
            <button type="button" className="primary" onClick={() => setEditor("new")} disabled={busy}>
              {t("newChallenge")}
            </button>
            <button type="button" onClick={() => fileRef.current?.click()} disabled={busy}>
              {t("uploadCsv")}
            </button>
            <button type="button" onClick={() => void openFormat()} disabled={busy}>
              {formatOpen ? t("closeFormat") : t("csvFormat")}
            </button>
            <input
              ref={fileRef}
              type="file"
              accept=".csv,text/csv"
              hidden
              onChange={(event) => void upload(event.target.files?.[0])}
            />
          </div>
        </div>
        {formatOpen && formats ? (
          <div className="bank-format">
            {formats.map((item) => (
              <section key={item.tipo}>
                <header>
                  <h3>{CSV_KIND[item.tipo] ? t(CSV_KIND[item.tipo]) : item.tipo}</h3>
                  <button type="button" onClick={() => download(item)}>
                    {t("downloadTemplate")}
                  </button>
                </header>
                <p>{CSV_NOTE[item.tipo] ? t(CSV_NOTE[item.tipo]) : item.notes}</p>
                <h4>{t("csvColumns")}</h4>
                <p className="csv-columns">{item.columns.join(", ")}</p>
                <h4>{t("csvExample")}</h4>
                <pre>{item.example}</pre>
              </section>
            ))}
          </div>
        ) : null}
        {editor ? (
          <div className="path-panel path-tone-editor bank-editor">
            <ChallengeForm
              challengeId={editor === "new" ? null : editor}
              concepts={concepts}
              onCancel={() => setEditor(null)}
              onSaved={() => {
                setEditor(null)
                setReloadKey((value) => value + 1)
              }}
            />
          </div>
        ) : null}
        {bank && shown === 0 ? <p className="roster-empty">{t("noBankMatch")}</p> : null}
        <div className="route-groups">
          {units.map((unit) => (
            <section key={unit.concept} className="route-group">
              <header>
                <h3>{unit.title}</h3>
                <p>
                  {t(unit.challenges.length === 1 ? "countChallenge" : "countChallenges", { count: unit.challenges.length })}
                </p>
              </header>
              <div className="bank-list">
                {unit.challenges.map((item) => (
                  <ChallengeCard
                    key={item.id}
                    item={item}
                    busy={busy}
                    canChange={shelf === "catalog"}
                    onEdit={setEditor}
                    onRetire={(row) => void retire(row)}
                  />
                ))}
              </div>
            </section>
          ))}
        </div>
      </main>
    </>
  )
}
