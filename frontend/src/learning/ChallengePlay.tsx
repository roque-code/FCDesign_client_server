import {
  FormEvent,
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type KeyboardEvent as ReactKeyboardEvent,
  type PointerEvent as ReactPointerEvent,
} from "react"

import { ApiError, api, type Diagnostic, type FocusEvent, type LabAttemptRecord, type LabCase, type LabSession } from "../api"
import { editorKeywords, spellText, starterSource } from "../dialect"
import { translatedMessage, useLocale, useT, type MessageKey } from "../i18n"
import { Composer } from "../compose/Composer"
import { CodeEditor } from "../editor/CodeEditor"
import { FocusNotice, useFocusWatch } from "../focus/FocusWatch"
import { enterFullscreen, leaveFullscreen } from "../focus/watch"
import { runLanguageCases } from "../foreign/cases"
import { ForeignEditor } from "../foreign/ForeignEditor"
import { FOREIGN_LANGUAGES, LANGUAGE_LABELS, type ForeignLanguage } from "../foreign/keywords"
import { inInstalledApp, localImport } from "../runtime"
import { BlockWorkspace } from "./BlockWorkspace"
import { PromptText } from "./PromptText"
import { SolutionCard } from "./SolutionCard"
import { formatClock, formatWhen, stagesFor, type StageName } from "./trace"

const ACTIVITY: Record<string, MessageKey> = {
  classify: "classify",
  order: "order",
  build: "build",
  predict: "predict",
}

const TOOL_LABEL: Record<string, MessageKey> = {
  codigo: "writeCode",
  diagrama: "composeTitle",
  bloques: "blocksTool",
}

const STAGE: Record<StageName, MessageKey> = {
  comprender: "understand",
  razonar: "reason",
  construir: "build",
  comprobar: "check",
  lenguaje: "languageStage",
  explicar: "explain",
}

function AttemptHistory({ records }: { records: LabAttemptRecord[] }) {
  const t = useT()
  const locale = useLocale()
  if (records.length === 0) return null
  return (
    <section className="attempt-history">
      <h2>{t("attempts")}</h2>
      <ol className="attempt-list">
        {records.map((item) => (
          <li key={item.id}>
            <strong>{t("attemptN", { number: item.number })}</strong>
            <span>{item.status === "completed" ? t("attemptFinished") : t("attemptOpen")}</span>
            {item.score != null ? <span>{t("scorePoints", { count: item.score })}</span> : null}
            {item.elapsed_seconds != null ? <span>{formatClock(item.elapsed_seconds)}</span> : null}
            {item.finished_at ? <time dateTime={item.finished_at}>{formatWhen(item.finished_at, locale)}</time> : null}
          </li>
        ))}
      </ol>
    </section>
  )
}

function messageOf(error: unknown, fallback: string): string {
  return error instanceof ApiError ? translatedMessage(error.message) : fallback
}

const NARROW_QUERY = "(max-width: 980px)"
const PANELS_KEY = "traza.build-panels"

type BuildPanels = { brief: boolean; cases: boolean; mentor: boolean }

function readBuildPanels(): BuildPanels {
  const open: BuildPanels = { brief: true, cases: true, mentor: true }
  try {
    const saved: unknown = JSON.parse(localStorage.getItem(PANELS_KEY) ?? "null")
    if (!saved || typeof saved !== "object") return open
    const value = saved as Record<string, unknown>
    return {
      brief: value.brief !== false,
      cases: value.cases !== false,
      mentor: value.mentor !== false,
    }
  } catch {
    return open
  }
}

function storeBuildPanels(panels: BuildPanels) {
  try {
    localStorage.setItem(PANELS_KEY, JSON.stringify(panels))
  } catch {
    /* El navegador puede bloquear el almacenamiento; los paneles quedan como están en esta pantalla. */
  }
}

function clampIn(value: number, box: Element | null, fallback: number, min: number, reserve: number, axis: "width" | "height") {
  const size = box?.getBoundingClientRect()[axis] || fallback
  return Math.round(Math.min(Math.max(value, min), Math.max(min, size - reserve)))
}

function sideWidth(share: number, min: number, max: number) {
  return Math.round(Math.min(max, Math.max(min, window.innerWidth * share)))
}
export function ChallengePlay({
  challengeId,
  pathId,
  onDone,
  onStanding,
  pasteBlocked = false,
}: {
  challengeId: string
  pathId?: string
  onDone: () => void
  onStanding?: (standing: { points: number; rank: number }) => void
  pasteBlocked?: boolean
}) {
  const t = useT()
  const locale = useLocale()
  const [session, setSession] = useState<LabSession | null>(null)
  const [error, setError] = useState("")
  const [note, setNote] = useState("")
  const [busy, setBusy] = useState(false)
  const [text, setText] = useState("")
  const [choices, setChoices] = useState<Record<string, string>>({})
  const [order, setOrder] = useState<string[]>([])
  const [reflection, setReflection] = useState("")
  const [workspace, setWorkspace] = useState<object | null>(null)
  const [cases, setCases] = useState<LabCase[] | null>(null)
  const [diagnostics, setDiagnostics] = useState<Diagnostic[]>([])
  const [output, setOutput] = useState("")
  const [left, setLeft] = useState<number | null>(null)
  const [phonePane, setPhonePane] = useState<"problema" | "construccion" | "ayuda">("problema")
  const [mode, setMode] = useState<string | null>(null)
  const [code, setCode] = useState(() => starterSource(locale))
  const [diagramSource, setDiagramSource] = useState("")
  const [langId, setLangId] = useState<ForeignLanguage>("python")
  const [langSource, setLangSource] = useState("")
  const [langCases, setLangCases] = useState<LabCase[] | null>(null)
  const [grade, setGrade] = useState<number | null>(null)
  const [promptHeight, setPromptHeight] = useState<number | null>(168)
  const [mentorWidth, setMentorWidth] = useState(() => sideWidth(0.22, 220, 320))
  const [panels, setPanels] = useState<BuildPanels>(readBuildPanels)
  const [briefWidth, setBriefWidth] = useState(() => sideWidth(0.26, 240, 380))
  const [briefHeight, setBriefHeight] = useState(340)
  const [mentorHeight, setMentorHeight] = useState(300)
  const [resultsHeight, setResultsHeight] = useState(180)
  const [narrow, setNarrow] = useState(() => window.matchMedia(NARROW_QUERY).matches)
  const frameRef = useRef<HTMLDivElement>(null)
  const enunciadoRef = useRef<HTMLElement>(null)
  const leftRef = useRef<HTMLDivElement>(null)
  const rightRef = useRef<HTMLDivElement>(null)
  const centerRef = useRef<HTMLElement>(null)
  const [keywords, setKeywords] = useState<string[]>([])
  const [stdlib, setStdlib] = useState<string[]>([])
  const expiredOnce = useRef(false)
  const attemptClock = session?.attempt.seconds_left ?? null
  const attemptStatus = session?.attempt.status ?? ""
  const attemptId = session?.attempt.id ?? ""
  const prompt = session?.challenge.prompt ?? ""
  const watched = attemptStatus === "open" && Boolean(session?.attempt.focus)
  const { fullscreen } = useFocusWatch(watched, sendFocus)

  function sendFocus(event: FocusEvent, reason?: string) {
    if (!attemptId) return
    const id = attemptId
    void api.focusAttempt(id, event, reason).then(
      (result) => {
        if (result.attempt.status !== "open") {
          apply(result)
          return
        }
        setSession((current) =>
          current && current.attempt.id === id
            ? { ...current, attempt: { ...current.attempt, focus: result.attempt.focus } }
            : current,
        )
      },
      () => undefined,
    )
  }

  useEffect(() => {
    if (attemptStatus && attemptStatus !== "open") leaveFullscreen()
  }, [attemptStatus])

  useEffect(() => () => leaveFullscreen(), [])

  useEffect(() => {
    const query = window.matchMedia(NARROW_QUERY)
    const apply = () => setNarrow(query.matches)
    query.addEventListener("change", apply)
    return () => query.removeEventListener("change", apply)
  }, [])

  useEffect(() => {
    storeBuildPanels(panels)
    const frame = requestAnimationFrame(() => window.dispatchEvent(new Event("resize")))
    return () => cancelAnimationFrame(frame)
  }, [panels])

  useEffect(() => {
    if (prompt.includes("![") || prompt.includes("\n#") || prompt.length > 700) {
      setPromptHeight((current) => (current === 168 ? 380 : current))
    }
  }, [prompt])

  useEffect(() => {
    let cancelled = false
    void api.startAttempt(challengeId, pathId).then(
      (result) => {
        if (cancelled) return
        if (result.attempt.status === "open" && result.attempt.focus) enterFullscreen()
        setSession(result)
        if (result.attempt.cases?.length) setCases(result.attempt.cases)
        const saved = result.attempt.language
        if (saved && (FOREIGN_LANGUAGES as readonly string[]).includes(saved.language)) {
          setLangId(saved.language as ForeignLanguage)
          setLangSource(saved.source)
          setGrade(saved.percent)
          if (saved.cases?.length) setLangCases(saved.cases)
        }
        const items = result.challenge.task.items ?? []
        if (result.challenge.activity_type === "order") setOrder(items.map((item) => item.id))
      },
      (caught: unknown) => {
        if (!cancelled) setError(messageOf(caught, t("challengeContinueError")))
      },
    )
    return () => {
      cancelled = true
    }
  }, [challengeId, pathId])

  useEffect(() => {
    if (session?.challenge.activity_type !== "build") return
    let cancelled = false
    void api.keywords().then(
      (words) => {
        if (cancelled) return
        setKeywords(editorKeywords(locale, words.keywords))
        setStdlib(words.stdlib)
      },
      () => undefined,
    )
    return () => {
      cancelled = true
    }
  }, [session?.challenge.activity_type, locale])

  useEffect(() => {
    expiredOnce.current = false
    if (attemptClock == null || attemptStatus !== "open") {
      setLeft(attemptClock)
      return
    }
    const endsAt = Date.now() + attemptClock * 1000
    const tick = () => setLeft(Math.max(0, Math.ceil((endsAt - Date.now()) / 1000)))
    tick()
    const handle = window.setInterval(tick, 250)
    return () => window.clearInterval(handle)
  }, [attemptId, attemptClock, attemptStatus])

  useEffect(() => {
    if (!session || left !== 0 || attemptStatus !== "open" || session.attempt.time_limit_seconds == null) return
    if (expiredOnce.current) return
    expiredOnce.current = true
    void run(() => api.expireAttempt(session.attempt.id))
  }, [left, attemptId, attemptStatus, session])

  function apply(result: LabSession) {
    const rows = result.cases ?? []
    const incomplete = result.passed === false || rows.some((item) => !item.passed)
    const settled =
      incomplete && result.attempt.next_stage === "explicar"
        ? { ...result, passed: false, attempt: { ...result.attempt, next_stage: "comprobar" } }
        : result
    const done = rows.filter((item) => item.passed).length
    setSession(settled)
    setError("")
    if (rows.length > 0) {
      setNote(incomplete ? t("casesNeedAll", { done, total: rows.length }) : t("casesAllMatch"))
    } else if (settled.passed === true) {
      setNote(t("programReady"))
    } else {
      setNote(settled.correct === false || settled.passed === false ? t("notYetMatch") : "")
    }
    if (settled.cases) setCases(settled.cases)
    if (settled.diagnostics) setDiagnostics(settled.diagnostics)
    if (typeof settled.output === "string") setOutput(settled.output)
    if (typeof settled.percent === "number") {
      setGrade(settled.percent)
      if (settled.cases) setLangCases(settled.cases)
    }
    if (typeof settled.points === "number" && typeof settled.rank === "number") {
      onStanding?.({ points: settled.points, rank: settled.rank })
    }
  }

  async function run(action: () => Promise<LabSession>) {
    setBusy(true)
    setError("")
    try {
      apply(await action())
    } catch (caught) {
      setError(messageOf(caught, t("challengeContinueError")))
    } finally {
      setBusy(false)
    }
  }

  if (!session) {
    return (
      <div className="lab-challenge">
        <div className="challenge-leave">
          <button type="button" onClick={onDone}>
            {t("backToRoute")}
          </button>
        </div>
        <p className="notice">{t("openingChallenge")}</p>
        <main className="lab-main">
          {error ? <p className="error">{error}</p> : null}
        </main>
      </div>
    )
  }

  const { challenge, attempt } = session
  const activity = challenge.activity_type
  const stages = stagesFor(activity)
  const current = attempt.next_stage
  const finished = attempt.status === "completed"
  const timedOut = attempt.status === "abandoned" || (attempt.time_limit_seconds != null && left === 0)
  const items = challenge.task.items ?? []
  const itemText = new Map(items.map((item) => [item.id, item.text]))
  const showCanvas = activity === "build" && (current === "construir" || current === "comprobar")
  const tools = challenge.task.tools?.length ? challenge.task.tools : ["bloques"]
  const specCases = challenge.task.cases ?? []
  const buildMode = mode && tools.includes(mode) ? mode : (tools[0] ?? "bloques")

  function move(index: number, delta: number) {
    setOrder((currentOrder) => {
      const next = currentOrder.slice()
      const target = index + delta
      if (target < 0 || target >= next.length) return currentOrder
      const [item] = next.splice(index, 1)
      next.splice(target, 0, item)
      return next
    })
  }

  function submitReason(event: FormEvent) {
    event.preventDefault()
    if (activity === "classify") {
      void run(() => api.saveStage(attempt.id, "razonar", { choices }))
      return
    }
    if (activity === "order") {
      void run(() => api.saveStage(attempt.id, "razonar", { order }))
      return
    }
    void run(() => api.saveStage(attempt.id, "razonar", { text }))
  }

  async function prove() {
    if (buildMode === "bloques") {
      await run(() => api.checkAttempt(attempt.id, workspace ?? {}, buildMode))
      return
    }
    const source = buildMode === "codigo" ? code : diagramSource
    setBusy(true)
    setError("")
    try {
      const imported = inInstalledApp() ? await localImport(source) : await api.importLab(source)
      if (!imported.workspace) {
        setDiagnostics(imported.diagnostics)
        setNote(t("notYetMatch"))
        return
      }
      apply(await api.checkAttempt(attempt.id, imported.workspace, buildMode))
    } catch (caught) {
      setError(messageOf(caught, t("challengeContinueError")))
    } finally {
      setBusy(false)
    }
  }

  async function proveLanguage() {
    const spec = challenge.task.cases ?? []
    setBusy(true)
    setError("")
    try {
      const body: { language: string; source: string; outputs?: string[] } = {
        language: langId,
        source: langSource,
      }
      if (inInstalledApp()) body.outputs = await runLanguageCases(langId, langSource, spec)
      apply(await api.submitLanguage(attempt.id, body))
    } catch (caught) {
      setError(messageOf(caught, t("challengeContinueError")))
    } finally {
      setBusy(false)
    }
  }

  function clampPrompt(value: number) {
    const height = frameRef.current?.getBoundingClientRect().height ?? 640
    return Math.round(Math.min(Math.max(value, 72), Math.max(72, height - 180)))
  }

  function clampMentor(value: number) {
    const width = frameRef.current?.getBoundingClientRect().width ?? 960
    return Math.round(Math.min(Math.max(value, 160), Math.max(160, width - 280)))
  }

  const clampBriefWidth = (value: number) => clampIn(value, frameRef.current, 1200, 220, 420 + (panels.mentor ? mentorWidth : 0), "width")
  const clampBriefHeight = (value: number) => clampIn(value, leftRef.current, 640, 96, 110, "height")
  const clampMentorHeight = (value: number) => clampIn(value, rightRef.current, 640, 120, 110, "height")
  const clampResults = (value: number) => clampIn(value, centerRef.current, 640, 72, 260, "height")

  const timer =
    attempt.status === "open" && left != null ? (
      <p className={left <= 30 ? "timer timer-low" : "timer"} aria-live="polite">
        <span>{t("timeWord")}</span>
        {formatClock(left)}
      </p>
    ) : null

  const promptBody = (
    <div className="enunciado-body">
      <p className="enunciado-kicker">
        {t("promptKicker")} · {ACTIVITY[activity] ? t(ACTIVITY[activity]) : activity} · {challenge.concept}
      </p>
      <h2>{challenge.title}</h2>
      <PromptText text={challenge.prompt} />
    </div>
  )

  const stageHead = (
    <div className="stage-head">
      {!finished && !timedOut && attempt.score != null ? (
        <p className="note">{t("currentScore", { score: attempt.score })}</p>
      ) : null}
      <div className="stage-pills" aria-label={t("stages")}>
        {stages.map((stage) => {
          const index = stages.indexOf(stage)
          const currentIndex = stages.indexOf(current as StageName)
          const state = finished || index < currentIndex ? "done" : index === currentIndex ? "current" : "ahead"
          return (
            <span key={stage} className={`stage-pill stage-${state}`}>
              {t(STAGE[stage])}
            </span>
          )
        })}
      </div>
    </div>
  )

  function mentorPanel(style?: CSSProperties) {
    return (
      <aside className="mentor" style={style}>
        <p className="enunciado-kicker">{t("help")}</p>
        <h2>{t("mentor")}</h2>
        <p>
          {attempt.hints_left} {attempt.hints_left === 1 ? t("hintOne") : t("hintMany")}
        </p>
        {attempt.hints.length === 0 ? <p>{t("noHelpYet")}</p> : null}
        <ol className="hint-list">
          {attempt.hints.map((hint, index) => (
            <li key={`${hint.level}-${index}`} className={hint.solution ? "hint-solution" : undefined}>
              {hint.body}
            </li>
          ))}
        </ol>
        <button
          type="button"
          disabled={busy || finished || timedOut || attempt.hints_left === 0}
          onClick={() => void run(() => api.revealHint(attempt.id))}
        >
          {attempt.hints_left === 0
            ? t("noHints")
            : attempt.hints_left === 1 && attempt.solution_next
              ? t("seeSolution")
              : t("askHint")}
        </button>
      </aside>
    )
  }

  const diagnosticsList =
    diagnostics.length > 0 && !finished && !timedOut ? (
      <ul className="lab-diagnostics">
        {diagnostics.map((item, index) => (
          <li key={`${item.code}-${item.line}-${index}`} className={item.severity === "error" ? "error" : "warning"}>
            {item.message}
          </li>
        ))}
      </ul>
    ) : null

  const phoneTabs = (
    <div className="lab-phone-tabs" role="tablist" aria-label={t("challengeSections")}>
      {(
        [
          ["problema", t("problemTab")],
          ["construccion", t("construction")],
          ["ayuda", t("help")],
        ] as const
      ).map(([id, label]) => (
        <button
          key={id}
          type="button"
          role="tab"
          aria-selected={phonePane === id}
          onClick={() => setPhonePane(id)}
        >
          {label}
        </button>
      ))}
    </div>
  )

  if (showCanvas && !finished && !timedOut) {
    const history = session.history ?? []
    const showBrief = narrow || panels.brief
    const showCases = narrow || panels.cases
    const showMentor = narrow || panels.mentor
    const leftOpen = showBrief || showCases
    const rightOpen = showMentor || history.length > 0
    const hasResults = Boolean(cases) || Boolean(note) || diagnostics.length > 0 || Boolean(error)
    const columns = [
      leftOpen ? `${briefWidth}px 10px` : "",
      "minmax(0, 1fr)",
      rightOpen ? `10px ${mentorWidth}px` : "",
    ]
      .filter(Boolean)
      .join(" ")
    const toggles = [
      ["brief", t("promptKicker")],
      ["cases", t("casesWord")],
      ["mentor", t("mentor")],
    ] as const

    return (
      <div className="lab-challenge build-layout" data-phone={phonePane}>
        <div className="challenge-leave build-toolbar">
          <div className="panel-toggles" role="group" aria-label={t("buildPanels")}>
            {toggles.map(([id, label]) => (
              <button
                key={id}
                type="button"
                aria-pressed={panels[id]}
                title={t(panels[id] ? "hidePanel" : "showPanel", { name: label })}
                onClick={() => setPanels((open) => ({ ...open, [id]: !open[id] }))}
              >
                {label}
              </button>
            ))}
          </div>
          {timer}
          <button type="button" onClick={onDone}>
            {t("backToRoute")}
          </button>
        </div>
        {watched && attempt.focus ? <FocusNotice report={attempt.focus} fullscreen={fullscreen} /> : null}
        {phoneTabs}
        <div className="build-board" ref={frameRef} style={{ gridTemplateColumns: columns }}>
          {leftOpen ? (
            <div className="build-left" ref={leftRef}>
              {showBrief ? (
                <section
                  className="enunciado build-brief"
                  style={showCases ? { height: briefHeight, flex: "0 0 auto" } : undefined}
                >
                  {promptBody}
                </section>
              ) : null}
              {showBrief && showCases ? (
                <PanelSplitter
                  row
                  label={t("adjustPrompt")}
                  value={briefHeight}
                  min={96}
                  max={clampBriefHeight(10_000)}
                  onChange={(next) => setBriefHeight(clampBriefHeight(next))}
                />
              ) : null}
              {showCases ? (
                <aside className="build-cases" aria-label={t("testCases")}>
                  <h3>{t("howToAdvance")}</h3>
                  {specCases.length > 0 ? (
                    <ul className="build-spec">
                      <li>{t("proveAll")}</li>
                      <li>{t("outputExact")}</li>
                      <li>{t("explainGate")}</li>
                      <li>{t("languageAfterCheck")}</li>
                      <li>{t("stayCheck")}</li>
                    </ul>
                  ) : (
                    <ul className="build-spec">
                      <li>{t("proveProgram")}</li>
                      <li>{t("noCaseThenLanguage")}</li>
                      <li>{t("explainAfterOpen")}</li>
                    </ul>
                  )}
                  {specCases.length > 0 ? (
                    <>
                      <h3>{t("casesWord")}</h3>
                      <ul className="case-list">
                        {specCases.map((item) => (
                          <li key={item.name}>
                            <strong>{item.name}</strong>
                            <span>
                              {item.inputs.length > 0 ? t("caseInputs", { values: item.inputs.join(", ") }) : t("noInputs")}
                            </span>
                            <pre className="lab-output">{item.expected_output}</pre>
                          </li>
                        ))}
                      </ul>
                    </>
                  ) : null}
                </aside>
              ) : null}
            </div>
          ) : null}
          {leftOpen ? (
            <PanelSplitter
              before
              label={t("adjustBrief")}
              value={briefWidth}
              min={220}
              max={clampBriefWidth(10_000)}
              onChange={(next) => setBriefWidth(clampBriefWidth(next))}
            />
          ) : null}
          <section className="build-center" ref={centerRef}>
            {stageHead}
            <div className="build-work">
              <div className="build-work-head">
                <h2>{current === "construir" ? t("build") : t("check")}</h2>
                {tools.length > 1 ? (
                  <div className="practice-actions" role="tablist" aria-label={t("tools")}>
                    {tools.map((tool) => (
                      <button
                        key={tool}
                        type="button"
                        className={buildMode === tool ? "primary" : ""}
                        aria-pressed={buildMode === tool}
                        onClick={() => setMode(tool)}
                      >
                        {TOOL_LABEL[tool] ? t(TOOL_LABEL[tool]) : tool}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
              {tools.includes("codigo") ? (
                <div className="stage-canvas is-build" hidden={buildMode !== "codigo"}>
                  <CodeEditor
                    source={code}
                    keywords={keywords}
                    stdlib={stdlib}
                    indentSize={4}
                    theme="light"
                    jump={null}
                    breakpoints={[]}
                    currentLine={null}
                    onToggleBreakpoint={() => undefined}
                    onChange={setCode}
                    onCursor={() => undefined}
                    pasteBlocked={pasteBlocked}
                  />
                  {pasteBlocked ? <p className="note">{t("pasteBlockedNote")}</p> : null}
                </div>
              ) : null}
              {tools.includes("diagrama") ? (
                <div className="stage-canvas is-build" hidden={buildMode !== "diagrama"}>
                  <Composer
                    embedded
                    isolated
                    active={buildMode === "diagrama"}
                    incoming={null}
                    allowedBlocks={challenge.allowed_blocks}
                    pasteBlocked={pasteBlocked}
                    onBack={() => undefined}
                    onOpenInEditor={() => undefined}
                    onSource={setDiagramSource}
                  />
                  {pasteBlocked ? <p className="note">{t("pasteBlockedNote")}</p> : null}
                </div>
              ) : null}
              {tools.includes("bloques") ? (
                <div className="stage-canvas is-build" hidden={buildMode !== "bloques"}>
                  <BlockWorkspace onCount={() => undefined} onState={setWorkspace} allowed={challenge.allowed_blocks} />
                </div>
              ) : null}
              <button
                type="button"
                className="primary build-prove"
                disabled={
                  busy ||
                  (buildMode === "bloques" && !workspace) ||
                  (buildMode === "codigo" && code.trim() === "") ||
                  (buildMode === "diagrama" && diagramSource.trim() === "")
                }
                onClick={() => void prove()}
              >
                {t("prove")}
              </button>
              {hasResults ? (
                <PanelSplitter
                  row
                  before={false}
                  label={t("adjustEditor")}
                  value={resultsHeight}
                  min={72}
                  max={clampResults(10_000)}
                  onChange={(next) => setResultsHeight(clampResults(next))}
                />
              ) : null}
              {hasResults ? (
                <div className="build-results" style={{ height: resultsHeight }}>
                  {note && cases ? <p className={cases.some((item) => !item.passed) ? "error" : "note"}>{note}</p> : null}
                  {cases ? (
                    <ul className="case-list">
                      {cases.map((item) => (
                        <li key={item.name}>
                          {item.passed ? t("passed") : t("mismatch")} · {item.name}
                          <pre className="lab-output">{item.output}</pre>
                        </li>
                      ))}
                    </ul>
                  ) : null}
                  {diagnosticsList}
                  {error ? <p className="error">{error}</p> : null}
                </div>
              ) : null}
            </div>
          </section>
          {rightOpen ? (
            <PanelSplitter
              label={t("adjustHelp")}
              value={mentorWidth}
              min={200}
              max={clampMentor(10_000)}
              onChange={(next) => setMentorWidth(clampMentor(next))}
            />
          ) : null}
          {rightOpen ? (
            <div className="build-right" ref={rightRef}>
              {showMentor ? mentorPanel(history.length > 0 ? { height: mentorHeight, flex: "0 0 auto" } : undefined) : null}
              {showMentor && history.length > 0 ? (
                <PanelSplitter
                  row
                  label={t("adjustMentorSplit")}
                  value={mentorHeight}
                  min={120}
                  max={clampMentorHeight(10_000)}
                  onChange={(next) => setMentorHeight(clampMentorHeight(next))}
                />
              ) : null}
              {history.length > 0 ? (
                <div className="build-attempts">
                  <AttemptHistory records={history} />
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    )
  }

  return (
    <div className="lab-challenge" data-phone={phonePane}>
      <div className="challenge-leave">
        <button type="button" onClick={onDone}>
          {t("backToRoute")}
        </button>
      </div>
      {watched && attempt.focus ? <FocusNotice report={attempt.focus} fullscreen={fullscreen} /> : null}
      {phoneTabs}
      <div className="lab-split" ref={frameRef}>
      <section
        className="enunciado"
        ref={enunciadoRef}
        style={promptHeight == null ? undefined : { height: promptHeight }}
      >
        {promptBody}
        {timer}
      </section>
      <PanelSplitter
        label={t("adjustPrompt")}
        row
        value={promptHeight ?? 168}
        min={72}
        max={clampPrompt(10_000)}
        onChange={(next) => setPromptHeight(clampPrompt(next))}
      />
      <div className="lab-main path-play" style={{ "--mentor-width": `${mentorWidth}px` } as CSSProperties}>
        <section className="stage-column">
          {stageHead}
          <div className="stage-panel">
            {timedOut ? (
              <article className="result-card">
                <p className="enunciado-kicker">{t(attempt.focus?.auto_submitted ? "resultWord" : "timeWord")}</p>
                <h2>
                  {attempt.focus?.auto_submitted
                    ? t("focusAutoSubmitted", { count: attempt.focus.exits })
                    : t("timeUp")}
                </h2>
                {attempt.elapsed_seconds != null ? (
                  <p>{t("usedTime", { time: formatClock(attempt.elapsed_seconds) })}</p>
                ) : null}
                {attempt.finished_at ? <p>{formatWhen(attempt.finished_at, locale)}</p> : null}
                {attempt.score != null ? <p className="result-score">{attempt.score}</p> : null}
                {attempt.summary ? <p>{attempt.summary}</p> : null}
                <p>{t("savedAgain")}</p>
                <button type="button" className="primary" onClick={onDone}>
                  {t("backToRoute")}
                </button>
              </article>
            ) : null}
            {finished ? (
              <div className="result-layout">
                <article className="result-card">
                  <p className="enunciado-kicker">{t("resultWord")}</p>
                  <h2>{t("challengeDone")}</h2>
                  {attempt.score != null ? <p className="result-score">{attempt.score}</p> : null}
                  {session.points != null && session.rank != null ? (
                    <p>
                      {t("scoreLine", { points: session.challenge.points, total: session.points, rank: session.rank })}
                    </p>
                  ) : null}
                  {attempt.elapsed_seconds != null ? (
                    <p>{t("answeredIn", { time: formatClock(attempt.elapsed_seconds) })}</p>
                  ) : null}
                  {attempt.finished_at ? <p>{formatWhen(attempt.finished_at, locale)}</p> : null}
                  <p>{attempt.summary || t("alreadyClosed")}</p>
                  {attempt.prediction ? <p>{t("answerIs", { answer: attempt.prediction.answer })}</p> : null}
                  {attempt.reflection ? <blockquote>{attempt.reflection}</blockquote> : null}
                  <button type="button" className="primary" onClick={onDone}>
                    {t("backToRoute")}
                  </button>
                </article>
                {attempt.solution ? <SolutionCard solution={attempt.solution} title={challenge.title} /> : null}
              </div>
            ) : null}
            {!finished && !timedOut && current === "comprender" ? (
              <>
                <h2>{t("understand")}</h2>
                <p>{t("understandNote")}</p>
                <button
                  type="button"
                  className="primary"
                  disabled={busy}
                  onClick={() => void run(() => api.saveStage(attempt.id, "comprender", { ack: true }))}
                >
                  {t("gotIt")}
                </button>
              </>
            ) : null}
            {!finished && !timedOut && current === "razonar" ? (
              <form className="stage-form" onSubmit={submitReason}>
                <h2>{t("reason")}</h2>
                {challenge.task.question ? <p>{challenge.task.question}</p> : null}
                {activity === "classify"
                  ? items.map((item) => (
                      <label key={item.id}>
                        {item.text}
                        <select
                          value={choices[item.id] ?? ""}
                          onChange={(event) =>
                            setChoices((currentChoices) => ({ ...currentChoices, [item.id]: event.target.value }))
                          }
                        >
                          <option value="">{t("choose")}</option>
                          {(challenge.task.categories ?? []).map((category) => (
                            <option key={category} value={category}>
                              {category}
                            </option>
                          ))}
                        </select>
                      </label>
                    ))
                  : null}
                {activity === "order" ? (
                  <ol className="order-list">
                    {order.map((id, index) => (
                      <li key={id} className="order-row">
                        <span>{itemText.get(id) ?? id}</span>
                        <button type="button" onClick={() => move(index, -1)} disabled={index === 0}>
                          {t("moveUp")}
                        </button>
                        <button type="button" onClick={() => move(index, 1)} disabled={index === order.length - 1}>
                          {t("moveDown")}
                        </button>
                      </li>
                    ))}
                  </ol>
                ) : null}
                {activity === "build" || activity === "predict" ? (
                  <label>
                    {t("yourAnswer")}
                    <input value={text} onChange={(event) => setText(event.target.value)} autoComplete="off" />
                  </label>
                ) : null}
                {activity === "predict" && challenge.task.source ? (
                  <pre className="lab-code">{spellText(locale, challenge.task.source)}</pre>
                ) : null}
                {note ? <p>{note}</p> : null}
                <button
                  type="submit"
                  className="primary"
                  disabled={busy || (activity === "classify" && items.some((item) => !choices[item.id]))}
                >
                  {activity === "build" || activity === "predict" ? t("reply") : t("check")}
                </button>
              </form>
            ) : null}
            {!finished && !timedOut && activity === "predict" && current === "comprobar" ? (
              <>
                <h2>{t("check")}</h2>
                <p>{t("predicted", { answer: attempt.prediction?.answer ?? "" })}</p>
                {challenge.task.source ? <pre className="lab-code">{spellText(locale, challenge.task.source)}</pre> : null}
                <button type="button" className="primary" disabled={busy} onClick={() => void run(() => api.runAttempt(attempt.id))}>
                  {t("run")}
                </button>
              </>
            ) : null}
            {!finished && !timedOut && current === "lenguaje" ? (
              <form
                className="stage-form"
                onSubmit={(event) => {
                  event.preventDefault()
                  void proveLanguage()
                }}
              >
                <h2>{t("languageStage")}</h2>
                <p>
                  {specCases.length === 0
                    ? t("languageNoteOpen")
                    : inInstalledApp()
                      ? t("languageNoteApp")
                      : t("languageNote")}
                </p>
                <label>
                  {t("foreignTitle")}
                  <select value={langId} onChange={(event) => setLangId(event.target.value as ForeignLanguage)}>
                    {FOREIGN_LANGUAGES.map((item) => (
                      <option key={item} value={item}>
                        {LANGUAGE_LABELS[item]}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="language-field">
                  <span>{t("languagePaste")}</span>
                  <ForeignEditor
                    language={langId}
                    source={langSource}
                    onChange={setLangSource}
                    pasteBlocked={pasteBlocked}
                    label={t("languagePaste")}
                  />
                </div>
                {pasteBlocked ? <p className="note">{t("pasteBlockedNote")}</p> : null}
                <button type="submit" className="primary" disabled={busy || langSource.trim() === ""}>
                  {t("prove")}
                </button>
                {grade != null ? (
                  <p className={specCases.length === 0 || grade === 100 ? "note" : "error"}>
                    {specCases.length === 0 ? t("languageDelivered") : t("languageGrade", { percent: grade })}
                  </p>
                ) : null}
                {langCases && langCases.length > 0 ? (
                  <ul className="case-list">
                    {langCases.map((item) => (
                      <li key={item.name}>
                        {item.passed ? t("passed") : t("mismatch")} · {item.name}
                        <pre className="lab-output">{item.output}</pre>
                      </li>
                    ))}
                  </ul>
                ) : null}
                {specCases.length > 0 ? (
                  <>
                  <h3>{t("casesWord")}</h3>
                  <ul className="case-list">
                    {specCases.map((item) => (
                      <li key={item.name}>
                        <strong>{item.name}</strong>
                        <span>
                          {item.inputs.length > 0
                            ? t("caseInputs", { values: item.inputs.join(", ") })
                            : t("noInputs")}
                        </span>
                        <pre className="lab-output">{item.expected_output}</pre>
                      </li>
                    ))}
                  </ul>
                  </>
                ) : null}
              </form>
            ) : null}
            {!finished && !timedOut && current === "explicar" ? (
              <form
                className="stage-form"
                onSubmit={(event) => {
                  event.preventDefault()
                  void run(() => api.closeAttempt(attempt.id, reflection))
                }}
              >
                <h2>{t("explain")}</h2>
                {output && !(cases && cases.length > 0) ? <pre className="lab-output">{output}</pre> : null}
                {cases && cases.length > 0 ? (
                  <>
                    <p className={cases.every((item) => item.passed) ? "note" : "error"}>
                      {cases.every((item) => item.passed)
                        ? t("casesAllMatch")
                        : t("casesNeedAll", {
                            done: cases.filter((item) => item.passed).length,
                            total: cases.length,
                          })}
                    </p>
                    <ul className="case-list">
                      {cases.map((item) => (
                        <li key={item.name}>
                          {item.passed ? t("passed") : t("mismatch")} · {item.name}
                          <pre className="lab-output">{item.output}</pre>
                        </li>
                      ))}
                    </ul>
                  </>
                ) : null}
                <label>
                  {t("whatHappened")}
                  <textarea value={reflection} onChange={(event) => setReflection(event.target.value)} rows={4} />
                </label>
                <button type="submit" className="primary" disabled={busy || reflection.trim().length < 12}>
                  {t("finish")}
                </button>
              </form>
            ) : null}
            {diagnosticsList}
            {error ? <p className="error">{error}</p> : null}
            <AttemptHistory records={session.history ?? []} />
          </div>
        </section>
        <PanelSplitter
          label={t("adjustHelp")}
          value={mentorWidth}
          min={160}
          max={clampMentor(10_000)}
          onChange={(next) => setMentorWidth(clampMentor(next))}
        />
        {mentorPanel()}
      </div>
      </div>
    </div>
  )
}

function PanelSplitter({
  label,
  row = false,
  before = row,
  value,
  min,
  max,
  onChange,
}: {
  label: string
  row?: boolean
  /** El panel que cambia de tamaño está antes del separador: arriba o a la izquierda. */
  before?: boolean
  value: number
  min: number
  max: number
  onChange: (value: number) => void
}) {
  function drag(event: ReactPointerEvent<HTMLButtonElement>) {
    event.preventDefault()
    const handle = event.currentTarget
    try {
      handle.setPointerCapture(event.pointerId)
    } catch {
      /* the pointer still moves while the button stays under it */
    }
    const page = document.body
    const cursor = page.style.cursor
    const select = page.style.userSelect
    page.style.cursor = row ? "row-resize" : "col-resize"
    page.style.userSelect = "none"
    const origin = row ? event.clientY : event.clientX
    const start = value
    const sign = before ? 1 : -1
    const move = (ev: PointerEvent) => {
      const point = row ? ev.clientY : ev.clientX
      onChange(start + sign * (point - origin))
    }
    const stop = () => {
      page.style.cursor = cursor
      page.style.userSelect = select
      handle.removeEventListener("pointermove", move)
      handle.removeEventListener("pointerup", stop)
      handle.removeEventListener("pointercancel", stop)
    }
    handle.addEventListener("pointermove", move)
    handle.addEventListener("pointerup", stop)
    handle.addEventListener("pointercancel", stop)
  }

  function nudge(event: ReactKeyboardEvent<HTMLButtonElement>) {
    const step = event.shiftKey ? 48 : 16
    const forward = row ? event.key === "ArrowDown" : event.key === "ArrowRight"
    const back = row ? event.key === "ArrowUp" : event.key === "ArrowLeft"
    const grow = before ? forward : back
    const shrink = before ? back : forward
    if (!grow && !shrink) return
    event.preventDefault()
    onChange(value + (grow ? step : -step))
  }

  return (
    <button
      type="button"
      className={row ? "splitter splitter-row" : "splitter"}
      role="separator"
      aria-orientation={row ? "horizontal" : "vertical"}
      aria-label={label}
      aria-valuenow={value}
      aria-valuemin={min}
      aria-valuemax={max}
      onPointerDown={drag}
      onKeyDown={nudge}
    />
  )
}
