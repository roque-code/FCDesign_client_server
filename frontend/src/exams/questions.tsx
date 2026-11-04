import type { MessageKey } from "../i18n"
import type { AttemptQuestion, ExamKind, ExamPayload, ExamQuestion } from "./types"

export const KINDS: ExamKind[] = [
  "choice",
  "multi",
  "true_false",
  "short",
  "numerical",
  "essay",
  "matching",
  "order",
  "cloze",
  "case",
]

const KIND_KEY: Record<ExamKind, MessageKey> = {
  choice: "examsKindChoice",
  multi: "examsKindMulti",
  true_false: "examsKindTrueFalse",
  short: "examsKindShort",
  numerical: "examsKindNumerical",
  essay: "examsKindEssay",
  matching: "examsKindMatching",
  order: "examsKindOrder",
  cloze: "examsKindCloze",
  case: "examsKindCase",
}

export function kindKey(kind: ExamKind): MessageKey {
  return KIND_KEY[kind]
}

function nid(): string {
  return crypto.randomUUID().replace(/-/g, "").slice(0, 8)
}

export function blankQuestion(kind: ExamKind): ExamQuestion {
  return { id: nid(), kind, prompt: "", points: 1, feedback: "", payload: blankPayload(kind) }
}

function blankPayload(kind: ExamKind): ExamPayload {
  if (kind === "choice" || kind === "multi") {
    return {
      options: [
        { id: nid(), text: "", correct: true },
        { id: nid(), text: "", correct: false },
      ],
    }
  }
  if (kind === "true_false") return { correct: true }
  if (kind === "short") return { answers: [{ text: "", fraction: 100 }], case_sensitive: false }
  if (kind === "numerical") return { answers: [{ value: 0, tolerance: 0, fraction: 100 }] }
  if (kind === "essay") return { rubric: "" }
  if (kind === "matching") {
    return {
      pairs: [
        { id: nid(), left: "", right: "" },
        { id: nid(), left: "", right: "" },
      ],
    }
  }
  if (kind === "order") return { items: [{ id: nid(), text: "" }, { id: nid(), text: "" }] }
  if (kind === "cloze") return { text: "Completa {{1}}", blanks: [{ id: "1", answers: [""] }] }
  return {
    statement: "",
    starter: 'Algoritmo Ejemplo\n    Escribir "Hola mundo";\nFinAlgoritmo\n',
    cases: [{ name: "caso 1", inputs: [], expected: "", points: 1, hidden: false }],
  }
}

type EditorProps = {
  question: ExamQuestion
  t: (key: MessageKey, vars?: Record<string, string | number>) => string
  onChange: (question: ExamQuestion) => void
}

export function QuestionEditor({ question, t, onChange }: EditorProps) {
  const payload = question.payload
  function patch(next: ExamPayload) {
    onChange({ ...question, payload: next })
  }
  return (
    <div className="exam-question-body">
      <label>
        {t("examsPrompt")}
        <textarea value={question.prompt} rows={3} onChange={(event) => onChange({ ...question, prompt: event.target.value })} />
      </label>
      <div className="exam-inline">
        <label>
          {t("examsPoints")}
          <input
            type="number"
            min={0.01}
            max={100}
            step={0.5}
            value={question.points}
            onChange={(event) => onChange({ ...question, points: Number(event.target.value) })}
          />
        </label>
        <label>
          {t("examsFeedback")}
          <input value={question.feedback} onChange={(event) => onChange({ ...question, feedback: event.target.value })} />
        </label>
      </div>
      {question.kind === "choice" || question.kind === "multi" ? (
        <OptionsEditor question={question} t={t} onChange={onChange} />
      ) : null}
      {question.kind === "true_false" ? (
        <label className="exam-check">
          <input
            type="checkbox"
            checked={payload.correct === true}
            onChange={(event) => patch({ correct: event.target.checked })}
          />
          {t("examsTrue")}
        </label>
      ) : null}
      {question.kind === "short" ? <ShortEditor payload={payload} t={t} onChange={patch} /> : null}
      {question.kind === "numerical" ? <NumberEditor payload={payload} t={t} onChange={patch} /> : null}
      {question.kind === "essay" ? (
        <label>
          {t("examsRubric")}
          <textarea value={payload.rubric ?? ""} rows={2} onChange={(event) => patch({ rubric: event.target.value })} />
        </label>
      ) : null}
      {question.kind === "matching" ? <MatchEditor payload={payload} t={t} onChange={patch} /> : null}
      {question.kind === "order" ? <OrderEditor payload={payload} t={t} onChange={patch} /> : null}
      {question.kind === "cloze" ? <ClozeEditor payload={payload} t={t} onChange={patch} /> : null}
      {question.kind === "case" ? <CaseEditor payload={payload} t={t} onChange={patch} /> : null}
    </div>
  )
}

function OptionsEditor({ question, t, onChange }: EditorProps) {
  const options = question.payload.options ?? []
  function setOption(index: number, text: string, correct: boolean) {
    const next = options.map((item, itemIndex) => {
      if (question.kind === "choice" && correct) return { ...item, correct: itemIndex === index, text: itemIndex === index ? text : item.text }
      if (itemIndex !== index) return item
      return { ...item, text, correct }
    })
    onChange({ ...question, payload: { options: next } })
  }
  return (
    <div className="exam-stack">
      {options.map((option, index) => (
        <div className="exam-inline" key={option.id}>
          <label className="exam-check">
            <input
              type={question.kind === "choice" ? "radio" : "checkbox"}
              name={`correct-${question.id}`}
              checked={option.correct === true}
              onChange={(event) => setOption(index, option.text, event.target.checked)}
            />
            {t("examsCorrect")}
          </label>
          <input
            aria-label={t("examsOption")}
            value={option.text}
            onChange={(event) => setOption(index, event.target.value, option.correct === true)}
          />
          <button
            type="button"
            onClick={() => onChange({ ...question, payload: { options: options.filter((_, itemIndex) => itemIndex !== index) } })}
          >
            {t("examsRemove")}
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={() => onChange({ ...question, payload: { options: [...options, { id: nid(), text: "", correct: false }] } })}
      >
        {t("examsAddOption")}
      </button>
    </div>
  )
}

function ShortEditor({ payload, t, onChange }: { payload: ExamPayload; t: EditorProps["t"]; onChange: (next: ExamPayload) => void }) {
  const answers = (payload.answers ?? []) as { text: string; fraction: number }[]
  return (
    <div className="exam-stack">
      <p className="note">{t("examsShortHint")}</p>
      {answers.map((answer, index) => (
        <div className="exam-inline" key={index}>
          <input
            aria-label={t("examsAccepted")}
            value={answer.text}
            onChange={(event) => {
              const next = answers.map((item, itemIndex) => (itemIndex === index ? { ...item, text: event.target.value } : item))
              onChange({ ...payload, answers: next })
            }}
          />
          <button type="button" onClick={() => onChange({ ...payload, answers: answers.filter((_, itemIndex) => itemIndex !== index) })}>
            {t("examsRemove")}
          </button>
        </div>
      ))}
      <button type="button" onClick={() => onChange({ ...payload, answers: [...answers, { text: "", fraction: 100 }] })}>
        {t("examsAddAccepted")}
      </button>
      <label className="exam-check">
        <input
          type="checkbox"
          checked={payload.case_sensitive === true}
          onChange={(event) => onChange({ ...payload, case_sensitive: event.target.checked })}
        />
        {t("examsCaseSensitive")}
      </label>
    </div>
  )
}

function NumberEditor({ payload, t, onChange }: { payload: ExamPayload; t: EditorProps["t"]; onChange: (next: ExamPayload) => void }) {
  const answers = (payload.answers ?? []) as { value: number; tolerance: number; fraction: number }[]
  return (
    <div className="exam-stack">
      {answers.map((answer, index) => (
        <div className="exam-inline" key={index}>
          <label>
            {t("examsValue")}
            <input
              type="number"
              step="any"
              value={answer.value}
              onChange={(event) => {
                const next = answers.map((item, itemIndex) =>
                  itemIndex === index ? { ...item, value: Number(event.target.value) } : item,
                )
                onChange({ ...payload, answers: next })
              }}
            />
          </label>
          <label>
            {t("examsTolerance")}
            <input
              type="number"
              min={0}
              step="any"
              value={answer.tolerance}
              onChange={(event) => {
                const next = answers.map((item, itemIndex) =>
                  itemIndex === index ? { ...item, tolerance: Number(event.target.value) } : item,
                )
                onChange({ ...payload, answers: next })
              }}
            />
          </label>
        </div>
      ))}
    </div>
  )
}

function MatchEditor({ payload, t, onChange }: { payload: ExamPayload; t: EditorProps["t"]; onChange: (next: ExamPayload) => void }) {
  const pairs = payload.pairs ?? []
  return (
    <div className="exam-stack">
      {pairs.map((pair, index) => (
        <div className="exam-inline" key={pair.id}>
          <input
            aria-label={t("examsLeft")}
            value={pair.left}
            onChange={(event) => onChange({ ...payload, pairs: pairs.map((item, itemIndex) => (itemIndex === index ? { ...item, left: event.target.value } : item)) })}
          />
          <input
            aria-label={t("examsRight")}
            value={pair.right}
            onChange={(event) => onChange({ ...payload, pairs: pairs.map((item, itemIndex) => (itemIndex === index ? { ...item, right: event.target.value } : item)) })}
          />
          <button type="button" onClick={() => onChange({ ...payload, pairs: pairs.filter((_, itemIndex) => itemIndex !== index) })}>
            {t("examsRemove")}
          </button>
        </div>
      ))}
      <button type="button" onClick={() => onChange({ ...payload, pairs: [...pairs, { id: nid(), left: "", right: "" }] })}>
        {t("examsAddPair")}
      </button>
    </div>
  )
}

function OrderEditor({ payload, t, onChange }: { payload: ExamPayload; t: EditorProps["t"]; onChange: (next: ExamPayload) => void }) {
  const items = payload.items ?? []
  return (
    <div className="exam-stack">
      <p className="note">{t("examsOrderHint")}</p>
      {items.map((item, index) => (
        <div className="exam-inline" key={item.id}>
          <input
            aria-label={t("examsAddItem")}
            value={item.text}
            onChange={(event) => onChange({ ...payload, items: items.map((row, rowIndex) => (rowIndex === index ? { ...row, text: event.target.value } : row)) })}
          />
          <button type="button" onClick={() => onChange({ ...payload, items: items.filter((_, rowIndex) => rowIndex !== index) })}>
            {t("examsRemove")}
          </button>
        </div>
      ))}
      <button type="button" onClick={() => onChange({ ...payload, items: [...items, { id: nid(), text: "" }] })}>
        {t("examsAddItem")}
      </button>
    </div>
  )
}

function ClozeEditor({ payload, t, onChange }: { payload: ExamPayload; t: EditorProps["t"]; onChange: (next: ExamPayload) => void }) {
  const blanks = payload.blanks ?? []
  return (
    <div className="exam-stack">
      <p className="note">{t("examsClozeHint")}</p>
      <label>
        {t("examsClozeText")}
        <textarea value={payload.text ?? ""} rows={3} onChange={(event) => onChange({ ...payload, text: event.target.value })} />
      </label>
      {blanks.map((blank, index) => (
        <div className="exam-inline" key={blank.id}>
          <input aria-label={t("examsBlankId")} value={blank.id} readOnly />
          <input
            aria-label={t("examsAccepted")}
            value={blank.answers.join(" | ")}
            onChange={(event) => {
              const answers = event.target.value.split("|").map((item) => item.trim()).filter(Boolean)
              const next = blanks.map((item, itemIndex) => (itemIndex === index ? { ...item, answers } : item))
              onChange({ ...payload, blanks: next })
            }}
          />
        </div>
      ))}
      <button
        type="button"
        onClick={() => {
          const id = String(blanks.length + 1)
          onChange({
            ...payload,
            text: `${payload.text ?? ""} {{${id}}}`,
            blanks: [...blanks, { id, answers: [""] }],
          })
        }}
      >
        {t("examsAddBlank")}
      </button>
    </div>
  )
}

function CaseEditor({ payload, t, onChange }: { payload: ExamPayload; t: EditorProps["t"]; onChange: (next: ExamPayload) => void }) {
  const cases = payload.cases ?? []
  return (
    <div className="exam-stack">
      <p className="note">{t("examsCaseNote")}</p>
      <label>
        {t("examsStatement")}
        <textarea value={payload.statement ?? ""} rows={3} onChange={(event) => onChange({ ...payload, statement: event.target.value })} />
      </label>
      <label>
        {t("examsStarter")}
        <textarea value={payload.starter ?? ""} rows={5} spellCheck={false} onChange={(event) => onChange({ ...payload, starter: event.target.value })} />
      </label>
      {cases.map((item, index) => (
        <div className="exam-case" key={`${item.name}-${index}`}>
          <div className="exam-inline">
            <label>
              {t("examsCaseName")}
              <input
                value={item.name}
                onChange={(event) => onChange({ ...payload, cases: cases.map((row, rowIndex) => (rowIndex === index ? { ...row, name: event.target.value } : row)) })}
              />
            </label>
            <label>
              {t("examsCasePoints")}
              <input
                type="number"
                min={0.01}
                step={0.5}
                value={item.points}
                onChange={(event) => onChange({ ...payload, cases: cases.map((row, rowIndex) => (rowIndex === index ? { ...row, points: Number(event.target.value) } : row)) })}
              />
            </label>
            <label className="exam-check">
              <input
                type="checkbox"
                checked={item.hidden}
                onChange={(event) => onChange({ ...payload, cases: cases.map((row, rowIndex) => (rowIndex === index ? { ...row, hidden: event.target.checked } : row)) })}
              />
              {t("examsCaseHidden")}
            </label>
          </div>
          <label>
            {t("examsCaseInputs")}
            <input
              value={item.inputs.join(", ")}
              onChange={(event) => {
                const inputs = event.target.value.split(",").map((piece) => piece.trim()).filter(Boolean)
                onChange({ ...payload, cases: cases.map((row, rowIndex) => (rowIndex === index ? { ...row, inputs } : row)) })
              }}
            />
          </label>
          <label>
            {t("examsCaseExpected")}
            <textarea
              value={item.expected}
              rows={2}
              onChange={(event) => onChange({ ...payload, cases: cases.map((row, rowIndex) => (rowIndex === index ? { ...row, expected: event.target.value } : row)) })}
            />
          </label>
          <button type="button" onClick={() => onChange({ ...payload, cases: cases.filter((_, rowIndex) => rowIndex !== index) })}>
            {t("examsRemove")}
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={() => onChange({ ...payload, cases: [...cases, { name: `caso ${cases.length + 1}`, inputs: [], expected: "", points: 1, hidden: false }] })}
      >
        {t("examsAddCase")}
      </button>
    </div>
  )
}

export function initialAnswer(question: AttemptQuestion): Record<string, unknown> {
  if (question.answer && Object.keys(question.answer).length > 0) return question.answer
  if (question.kind === "case") return { source: question.payload.starter ?? "" }
  if (question.kind === "order") return { order: (question.payload.items ?? []).map((item) => item.id) }
  if (question.kind === "multi") return { options: [] }
  if (question.kind === "matching") return { pairs: {} }
  if (question.kind === "cloze") return { blanks: {} }
  return {}
}

export function AnswerField({
  question,
  t,
  onChange,
}: {
  question: AttemptQuestion
  t: EditorProps["t"]
  onChange: (answer: Record<string, unknown>) => void
}) {
  const answer = question.answer
  if (question.kind === "choice" || question.kind === "multi") {
    const options = question.payload.options ?? []
    const several = question.kind === "multi"
    const picked = new Set(several ? ((answer.options as string[]) ?? []) : [String(answer.option ?? "")])
    return (
      <div className="exam-stack">
        {options.map((option) => (
          <label className="exam-check" key={option.id}>
            <input
              type={several ? "checkbox" : "radio"}
              name={question.id}
              checked={picked.has(option.id)}
              onChange={(event) => {
                if (!several) {
                  onChange({ option: option.id })
                  return
                }
                const next = new Set(picked)
                if (event.target.checked) next.add(option.id)
                else next.delete(option.id)
                next.delete("")
                onChange({ options: [...next] })
              }}
            />
            {option.text}
          </label>
        ))}
      </div>
    )
  }
  if (question.kind === "true_false") {
    return (
      <div className="exam-inline">
        {[true, false].map((value) => (
          <label className="exam-check" key={String(value)}>
            <input type="radio" name={question.id} checked={answer.value === value} onChange={() => onChange({ value })} />
            {value ? t("examsTrue") : t("examsFalse")}
          </label>
        ))}
      </div>
    )
  }
  if (question.kind === "short" || question.kind === "essay" || question.kind === "numerical") {
    const field = question.kind === "numerical" ? "value" : "text"
    return (
      <textarea
        rows={question.kind === "essay" ? 6 : 2}
        value={String(answer[field] ?? "")}
        onChange={(event) => onChange({ [field]: event.target.value })}
      />
    )
  }
  if (question.kind === "matching") {
    const pairs = (answer.pairs as Record<string, string>) ?? {}
    const left = question.payload.left ?? []
    const right = question.payload.right ?? []
    return (
      <div className="exam-stack">
        {left.map((item) => (
          <label key={item.id}>
            {item.text}
            <select
              value={pairs[item.id] ?? ""}
              onChange={(event) => onChange({ pairs: { ...pairs, [item.id]: event.target.value } })}
            >
              <option value="">{t("examsBlank")}</option>
              {right.map((choice) => (
                <option key={choice.id} value={choice.id}>
                  {choice.text}
                </option>
              ))}
            </select>
          </label>
        ))}
      </div>
    )
  }
  if (question.kind === "order") {
    const items = question.payload.items ?? []
    const order = ((answer.order as string[]) ?? items.map((item) => item.id)).slice()
    const labels = new Map(items.map((item) => [item.id, item.text]))
    function move(index: number, delta: number) {
      const target = index + delta
      if (target < 0 || target >= order.length) return
      const next = order.slice()
      const [row] = next.splice(index, 1)
      next.splice(target, 0, row)
      onChange({ order: next })
    }
    return (
      <div className="exam-stack">
        {order.map((id, index) => (
          <div className="exam-inline" key={id}>
            <span>{index + 1}. {labels.get(id) ?? id}</span>
            <button type="button" onClick={() => move(index, -1)}>{t("examsMoveUp")}</button>
            <button type="button" onClick={() => move(index, 1)}>{t("examsMoveDown")}</button>
          </div>
        ))}
      </div>
    )
  }
  if (question.kind === "cloze") {
    const blanks = (answer.blanks as Record<string, string>) ?? {}
    const parts = (question.payload.text ?? "").split(/(\{\{[^}]+\}\})/g)
    return (
      <div className="exam-cloze">
        {parts.map((part, index) => {
          const mark = /^\{\{([^}]+)\}\}$/.exec(part)
          if (!mark) return <span key={index}>{part}</span>
          const id = mark[1]
          return (
            <input
              key={index}
              aria-label={id}
              value={blanks[id] ?? ""}
              onChange={(event) => onChange({ blanks: { ...blanks, [id]: event.target.value } })}
            />
          )
        })}
      </div>
    )
  }
  const cases = question.payload.cases ?? []
  return (
    <div className="exam-stack">
      <p>{question.payload.statement}</p>
      {question.payload.hidden_count ? <p className="note">{t("examsHiddenCases", { count: question.payload.hidden_count })}</p> : null}
      {cases.map((item) => (
        <p className="note" key={item.name}>
          {item.name}
          {item.inputs?.length ? `: ${item.inputs.join(", ")}` : ""}
        </p>
      ))}
      <label>
        {t("examsCode")}
        <textarea
          rows={10}
          spellCheck={false}
          value={String(answer.source ?? "")}
          onChange={(event) => onChange({ source: event.target.value })}
        />
      </label>
    </div>
  )
}

export function describeAnswer(question: AttemptQuestion): string {
  const answer = question.answer ?? {}
  if (question.kind === "choice") {
    const option = (question.payload.options ?? []).find((item) => item.id === answer.option)
    return option?.text ?? ""
  }
  if (question.kind === "multi") {
    const picked = new Set((answer.options as string[]) ?? [])
    return (question.payload.options ?? []).filter((item) => picked.has(item.id)).map((item) => item.text).join(" | ")
  }
  if (question.kind === "true_false") return answer.value === true ? "Verdadero" : answer.value === false ? "Falso" : ""
  if (question.kind === "short" || question.kind === "essay") return String(answer.text ?? "")
  if (question.kind === "numerical") return answer.value == null ? "" : String(answer.value)
  if (question.kind === "matching") {
    const pairs = (answer.pairs as Record<string, string>) ?? {}
    const left = new Map((question.payload.left ?? question.payload.pairs ?? []).map((item) => [item.id, "text" in item ? item.text : item.left]))
    const right = new Map((question.payload.right ?? question.payload.pairs ?? []).map((item) => [item.id, "text" in item ? item.text : item.right]))
    return Object.entries(pairs).map(([key, value]) => `${left.get(key) ?? key} → ${right.get(value) ?? value}`).join("; ")
  }
  if (question.kind === "order") {
    const labels = new Map((question.payload.items ?? []).map((item) => [item.id, item.text]))
    return ((answer.order as string[]) ?? []).map((id) => labels.get(id) ?? id).join(" | ")
  }
  if (question.kind === "cloze") {
    const blanks = (answer.blanks as Record<string, string>) ?? {}
    return Object.entries(blanks).map(([key, value]) => `${key}=${value}`).join(", ")
  }
  return String(answer.source ?? "")
}
