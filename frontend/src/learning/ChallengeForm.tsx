import { FormEvent, useEffect, useState } from "react"

import { ApiError, api, type LabChallengeDraft, type LabChallengeInput, type LabConcept } from "../api"
import { commitSource, presentSource } from "../dialect"
import { translatedMessage, useLocale, useT, type MessageKey } from "../i18n"
import { TOOL_GROUPS } from "./toolbox"
import { WeightFields } from "./WeightFields"
import { defaultWeights, parseWeights, weightTotal, type LabWeights } from "./weights"

const ACTIVITIES: { id: string; label: MessageKey }[] = [
  { id: "classify", label: "classify" },
  { id: "order", label: "order" },
  { id: "build", label: "build" },
  { id: "predict", label: "predict" },
]

const BUILD_TOOLS: { id: string; label: MessageKey }[] = [
  { id: "codigo", label: "writeCode" },
  { id: "diagrama", label: "composeTitle" },
  { id: "bloques", label: "blocksTool" },
]

function shownOutput(value: string): string {
  return value.endsWith("\n") ? value.slice(0, -1) : value
}

function lines(value: string): string[] {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter((item) => item.length > 0)
}

function messageOf(error: unknown): string {
  return error instanceof ApiError ? translatedMessage(error.message) : translatedMessage("No se pudo guardar el reto.")
}

export function ChallengeForm({
  challengeId,
  concepts,
  onCancel,
  onSaved,
}: {
  challengeId: string | null
  concepts: LabConcept[]
  onCancel: () => void
  onSaved: (draft: LabChallengeDraft) => void
}) {
  const t = useT()
  const locale = useLocale()
  const [title, setTitle] = useState("")
  const [prompt, setPrompt] = useState("")
  const [activity, setActivity] = useState("classify")
  const [concept, setConcept] = useState(concepts[0]?.key ?? "")
  const [difficulty, setDifficulty] = useState("1")
  const [points, setPoints] = useState("10")
  const [minutes, setMinutes] = useState("")
  const [categories, setCategories] = useState("entrada\nsalida")
  const [phrases, setPhrases] = useState<{ text: string; category: string }[]>([
    { text: "", category: "" },
    { text: "", category: "" },
  ])
  const [order, setOrder] = useState("")
  const [question, setQuestion] = useState("")
  const [accepted, setAccepted] = useState("")
  const [inputs, setInputs] = useState("")
  const [expected, setExpected] = useState("")
  const [cases, setCases] = useState<{ inputs: string; expected: string }[]>([{ inputs: "", expected: "" }])
  const [tools, setTools] = useState<string[]>(["codigo", "diagrama", "bloques"])
  const [source, setSource] = useState("")
  const [sourceCaret, setSourceCaret] = useState<number | null>(null)
  const [limitBlocks, setLimitBlocks] = useState(false)
  const [blocks, setBlocks] = useState<string[]>([])
  const [hints, setHints] = useState<string[]>([""])
  const [weights, setWeights] = useState<LabWeights>(() => defaultWeights("classify"))
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(challengeId !== null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!challengeId) return
    let cancelled = false
    void api.labChallenge(challengeId).then(
      (draft) => {
        if (cancelled) return
        setTitle(draft.title)
        setPrompt(draft.prompt)
        setActivity(draft.activity_type)
        setConcept(draft.concept)
        setDifficulty(String(draft.difficulty))
        setPoints(String(draft.points))
        setMinutes(draft.time_limit_seconds ? String(Math.round(draft.time_limit_seconds / 60)) : "")
        setCategories(draft.categories.join("\n"))
        setPhrases(
          draft.items.length > 0
            ? draft.items.map((item) => ({ text: item.text, category: item.category }))
            : [
                { text: "", category: "" },
                { text: "", category: "" },
              ],
        )
        setOrder(draft.activity_type === "order" ? draft.items.map((item) => item.text).join("\n") : "")
        setQuestion(draft.question)
        setAccepted(draft.accepted.join("\n"))
        setInputs(draft.inputs.join("\n"))
        setExpected(draft.expected_output)
        const loaded = draft.cases.length > 0 ? draft.cases : draft.expected_output ? [{ inputs: draft.inputs, expected_output: draft.expected_output }] : []
        setCases(
          loaded.length > 0
            ? loaded.map((item) => ({ inputs: item.inputs.join("\n"), expected: shownOutput(item.expected_output) }))
            : [{ inputs: "", expected: "" }],
        )
        setTools(draft.activity_type === "build" && draft.tools.length > 0 ? draft.tools : ["bloques"])
        setSource(draft.source)
        setLimitBlocks(draft.allowed_blocks.length > 0)
        setBlocks(draft.allowed_blocks)
        setHints(draft.hints.length > 0 ? draft.hints : [""])
        setWeights(parseWeights(draft.weights, draft.activity_type))
        setLoading(false)
      },
      (caught: unknown) => {
        if (cancelled) return
        setError(messageOf(caught))
        setLoading(false)
      },
    )
    return () => {
      cancelled = true
    }
  }, [challengeId])

  async function save(event: FormEvent) {
    event.preventDefault()
    setError("")
    const seconds = minutes.trim() === "" ? null : Math.round(Number(minutes) * 60)
    if (seconds !== null && (!Number.isFinite(seconds) || seconds < 1)) {
      setError(t("badMinutes"))
      return
    }
    if (activity === "build" && tools.length === 0) {
      setError(t("needTool"))
      return
    }
    if (activity === "build" && cases.some((item) => item.expected.trim() === "")) {
      setError(t("needCaseOutput"))
      return
    }
    if (activity === "build" && limitBlocks && blocks.length === 0) {
      setError(t("needBlock"))
      return
    }
    const rubric = activity === "build" ? weights : { ...weights, lenguaje: 0 }
    if (weightTotal(rubric) !== 100) {
      setError(t("weightMust100"))
      return
    }
    const body: LabChallengeInput = {
      title: title.trim(),
      prompt: prompt.trim(),
      activity_type: activity,
      concept,
      difficulty: Number(difficulty),
      points: Number(points),
      time_limit_seconds: seconds,
      categories: lines(categories),
      items:
        activity === "order"
          ? lines(order)
          : phrases
              .map((item) => ({ text: item.text.trim(), category: item.category }))
              .filter((item) => item.text.length > 0),
      question: question.trim(),
      accepted: lines(accepted),
      inputs: activity === "build" ? lines(cases[0]?.inputs ?? "") : lines(inputs),
      expected_output: activity === "build" ? (cases[0]?.expected ?? "") : expected,
      cases:
        activity === "build"
          ? cases.map((item) => ({ inputs: lines(item.inputs), expected_output: item.expected }))
          : [],
      tools: activity === "build" ? tools : [],
      source,
      hints: hints.map((item) => item.trim()).filter((item) => item.length > 0),
      allowed_blocks: activity === "build" && limitBlocks ? blocks : [],
      weights: rubric,
    }
    setSaving(true)
    try {
      const saved = challengeId
        ? await api.updateLabChallenge(challengeId, body)
        : await api.createLabChallenge(body)
      onSaved(saved)
    } catch (caught) {
      setError(messageOf(caught))
    } finally {
      setSaving(false)
    }
  }

  const categoryNames = lines(categories)

  return (
    <form className="stage-form" onSubmit={(event) => void save(event)}>
      <h3>{challengeId ? t("editChallenge") : t("newChallenge")}</h3>
      {error ? <p className="error">{error}</p> : null}
      {loading ? <p>{t("loadingChallenge")}</p> : null}
      <label>
        {t("formTitle")}
        <input value={title} onChange={(event) => setTitle(event.target.value)} maxLength={120} required />
      </label>
      <label>
        {t("formPrompt")}
        <textarea
          className="prompt-field"
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          rows={10}
          required
        />
      </label>
      <div className="challenge-pair">
        <label>
          {t("concept")}
          <select value={concept} onChange={(event) => setConcept(event.target.value)} required>
            {concepts.length === 0 ? <option value="">{t("noConcepts")}</option> : null}
            {concepts.map((item) => (
              <option key={item.key} value={item.key}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t("kindWord")}
          <select
            value={activity}
            onChange={(event) => {
              const next = event.target.value
              setActivity(next)
              setWeights(defaultWeights(next))
            }}
          >
            {ACTIVITIES.map((item) => (
              <option key={item.id} value={item.id}>
                {t(item.label)}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t("difficultyWord")}
          <select value={difficulty} onChange={(event) => setDifficulty(event.target.value)}>
            {[1, 2, 3, 4, 5].map((level) => (
              <option key={level} value={level}>
                {level}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="challenge-pair">
        <label>
          {t("pointsWord")}
          <input
            type="number"
            min={1}
            max={500}
            value={points}
            onChange={(event) => setPoints(event.target.value)}
            required
          />
        </label>
        <label>
          {t("minutesOptional")}
          <input
            type="number"
            min={1}
            max={1440}
            value={minutes}
            onChange={(event) => setMinutes(event.target.value)}
            placeholder={t("noLimit")}
          />
        </label>
      </div>
      <WeightFields activity={activity} weights={weights} onChange={setWeights} />
      {activity === "classify" ? (
        <>
          <label>
            {t("categoriesPerLine")}
            <textarea value={categories} onChange={(event) => setCategories(event.target.value)} rows={3} />
          </label>
          {phrases.map((item, index) => (
            <div key={index} className="challenge-item">
              <label>
                {t("phrase")}
                <input
                  value={item.text}
                  onChange={(event) =>
                    setPhrases((rows) =>
                      rows.map((row, rowIndex) => (rowIndex === index ? { ...row, text: event.target.value } : row)),
                    )
                  }
                />
              </label>
              <label>
                {t("categoryWord")}
                <select
                  value={item.category}
                  onChange={(event) =>
                    setPhrases((rows) =>
                      rows.map((row, rowIndex) =>
                        rowIndex === index ? { ...row, category: event.target.value } : row,
                      ),
                    )
                  }
                >
                  <option value="">{t("choose")}</option>
                  {categoryNames.map((name) => (
                    <option key={name} value={name}>
                      {name}
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="button"
                className="danger"
                onClick={() => setPhrases((rows) => rows.filter((_, rowIndex) => rowIndex !== index))}
                disabled={phrases.length <= 2}
              >
                {t("removeMember")}
              </button>
            </div>
          ))}
          <button
            type="button"
            onClick={() => setPhrases((rows) => [...rows, { text: "", category: categoryNames[0] ?? "" }])}
          >
            {t("addPhrase")}
          </button>
        </>
      ) : null}
      {activity === "order" ? (
        <label>
          {t("orderLines")}
          <textarea value={order} onChange={(event) => setOrder(event.target.value)} rows={5} />
        </label>
      ) : null}
      {activity === "build" || activity === "predict" ? (
        <>
          <label>
            {t("reasonQuestion")}
            <input value={question} onChange={(event) => setQuestion(event.target.value)} maxLength={240} />
          </label>
          <label>
            {t("acceptedPerLine")}
            <textarea value={accepted} onChange={(event) => setAccepted(event.target.value)} rows={3} />
          </label>
        </>
      ) : null}
      {activity === "build" ? (
        <>
          <fieldset className="block-picker">
            <legend>{t("toolsLegend")}</legend>
            {BUILD_TOOLS.map((tool) => (
              <label key={tool.id} className="check-line">
                <input
                  type="checkbox"
                  checked={tools.includes(tool.id)}
                  onChange={() =>
                    setTools((current) =>
                      current.includes(tool.id) ? current.filter((item) => item !== tool.id) : [...current, tool.id],
                    )
                  }
                />
                {t(tool.label)}
              </label>
            ))}
          </fieldset>
          {cases.map((item, index) => (
            <div key={index} className="case-editor">
              <div className="case-editor-head">
                <p>{t("caseN", { number: index + 1 })}</p>
                <button
                  type="button"
                  className="danger"
                  disabled={cases.length <= 1}
                  onClick={() => setCases((rows) => rows.filter((_, rowIndex) => rowIndex !== index))}
                >
                  {t("removeCase")}
                </button>
              </div>
              <label>
                {t("caseInputsNote")}
                <textarea
                  value={item.inputs}
                  rows={8}
                  onChange={(event) =>
                    setCases((rows) =>
                      rows.map((row, rowIndex) => (rowIndex === index ? { ...row, inputs: event.target.value } : row)),
                    )
                  }
                />
              </label>
              <label>
                {t("expectedAsWritten")}
                <textarea
                  value={item.expected}
                  rows={8}
                  onChange={(event) =>
                    setCases((rows) =>
                      rows.map((row, rowIndex) =>
                        rowIndex === index ? { ...row, expected: event.target.value } : row,
                      ),
                    )
                  }
                />
              </label>
            </div>
          ))}
          <button
            type="button"
            onClick={() => setCases((rows) => [...rows, { inputs: "", expected: "" }])}
            disabled={cases.length >= 6}
          >
            {t("addCase")}
          </button>
          <label className="check-line">
            <input
              type="checkbox"
              checked={limitBlocks}
              onChange={(event) => setLimitBlocks(event.target.checked)}
            />
            {t("limitFigures")}
          </label>
          {limitBlocks ? (
            <div className="block-picker">
              {TOOL_GROUPS.map((group) => (
                <section key={group.name}>
                  <h4>{t(group.nameKey)}</h4>
                  <div className="block-options">
                    {group.blocks.map((block) => (
                      <label key={block.id} className="check-line">
                        <input
                          type="checkbox"
                          checked={blocks.includes(block.id)}
                          onChange={() =>
                            setBlocks((current) =>
                              current.includes(block.id)
                                ? current.filter((item) => item !== block.id)
                                : [...current, block.id],
                            )
                          }
                        />
                        {t(block.labelKey)}
                      </label>
                    ))}
                  </div>
                </section>
              ))}
            </div>
          ) : null}
        </>
      ) : null}
      {activity === "predict" ? (
        <label>
          {t("predictSource")}
          <textarea
            className="challenge-source"
            value={presentSource(locale, source, sourceCaret)}
            onChange={(event) => {
              const caret = event.target.selectionStart
              setSourceCaret(caret)
              setSource(commitSource(locale, source, event.target.value, caret))
            }}
            onBlur={() => setSourceCaret(null)}
            rows={8}
            spellCheck={false}
            placeholder={presentSource(locale, "Algoritmo Laboratorio\nDefinir n Como Entero;\nn <- 4;\nEscribir n;\nFinAlgoritmo")}
          />
        </label>
      ) : null}
      <div className="hint-editor-list">
        <p>{t("hintsNote")}</p>
        {hints.map((item, index) => (
          <div key={index} className="hint-editor">
            <label>
              {t("hintN", { number: index + 1 })}
              <textarea
                value={item}
                rows={2}
                maxLength={500}
                onChange={(event) =>
                  setHints((rows) => rows.map((row, rowIndex) => (rowIndex === index ? event.target.value : row)))
                }
              />
            </label>
            <button
              type="button"
              className="danger"
              onClick={() => setHints((rows) => (rows.length === 1 ? [""] : rows.filter((_, rowIndex) => rowIndex !== index)))}
            >
              {t("removeMember")}
            </button>
          </div>
        ))}
        <button type="button" onClick={() => setHints((rows) => [...rows, ""])} disabled={hints.length >= 5}>
          {t("addHint")}
        </button>
      </div>
      <div className="practice-actions">
        <button type="submit" className="primary" disabled={saving || loading}>
          {t("saveChallenge")}
        </button>
        <button type="button" onClick={onCancel} disabled={saving}>
          {t("cancel")}
        </button>
      </div>
    </form>
  )
}
