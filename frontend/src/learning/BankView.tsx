import { useEffect, useMemo, useState } from "react"

import { ApiError, api, type LabBank, type LabBankChallenge, type LabConcept } from "../api"
import { spellText } from "../dialect"
import { useLocale, useT, type MessageKey } from "../i18n"
import { ChallengeForm } from "./ChallengeForm"
import { formatLimit } from "./trace"
import { TOOL_GROUPS } from "./toolbox"

const ACTIVITY: Record<string, MessageKey> = {
  classify: "classify",
  order: "order",
  build: "build",
  predict: "predict",
}

const BLOCK_LABEL = new Map(
  TOOL_GROUPS.flatMap((group) => group.blocks.map((block) => [block.id, block.labelKey])),
)

function messageOf(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback
}

function ChallengeCard({
  item,
  busy,
  onEdit,
  onRetire,
}: {
  item: LabBankChallenge
  busy: boolean
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
            <span>{item.points} pts</span>
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
          <h4>{t("inputs")}</h4>
          <p>{item.inputs.length === 0 ? t("noneWord") : item.inputs.join(" · ")}</p>
          <h4>{t("expectedOutput")}</h4>
          <pre>{item.expected_output}</pre>
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
      <div className="practice-actions">
        <button type="button" onClick={() => onEdit(item.id)} disabled={busy}>
          {t("edit")}
        </button>
        <button type="button" className="danger" onClick={() => onRetire(item)} disabled={busy}>
          {t("retire")}
        </button>
      </div>
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

  const needle = query.trim().toLocaleLowerCase()
  const units = useMemo(() => {
    if (!bank) return []
    return bank.units
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
  }, [activity, bank, concept, needle])
  const total = bank?.units.reduce((sum, unit) => sum + unit.challenges.length, 0) ?? 0
  const shown = units.reduce((sum, unit) => sum + unit.challenges.length, 0)

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
          <h2>{bank?.name ?? t("bankOf")}</h2>
          {bank?.description ? <p className="roster-meta">{bank.description}</p> : null}
        </div>
        <p className="path-count">
          <strong>{bank ? shown : "—"}</strong>
          <span>{bank && shown !== total ? t("ofTotal", { total }) : t("challengesWord")}</span>
        </p>
      </section>
      <main className="lab-main bank-board">
        {error ? <p className="error">{error}</p> : null}
        <div className="bank-filters">
          <label>
            {t("topic")}
            <select value={concept} onChange={(event) => setConcept(event.target.value)}>
              <option value="">{t("all")}</option>
              {bank?.units.map((unit) => (
                <option key={unit.concept} value={unit.concept}>
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
          </div>
        </div>
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
                  {unit.challenges.length} {unit.challenges.length === 1 ? "reto" : "retos"}
                </p>
              </header>
              <div className="bank-list">
                {unit.challenges.map((item) => (
                  <ChallengeCard
                    key={item.id}
                    item={item}
                    busy={busy}
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
