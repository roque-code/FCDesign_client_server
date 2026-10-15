import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type CSSProperties,
  type FormEvent,
  type PointerEvent as ReactPointerEvent,
} from "react"

import { ApiError, api, type LabPractice, type LabPreview, type LabRun } from "../api"
import { applyConsoleOutput } from "../console/output"
import { editorKeywords, spellText } from "../dialect"
import { useLocale, useT, type MessageKey } from "../i18n"
import { highlightSource } from "../editor/highlight"
import { keywordSet } from "../words"
import { BlockWorkspace } from "./BlockWorkspace"
import { canvasSignature } from "./canvasSignature"
import { blockOnLine, formatWhen } from "./trace"
import "./lab.css"

const PREVIEW_MS = 1000

const STATUS: Record<string, MessageKey> = {
  paused: "statusPaused",
  waiting_input: "statusWaiting",
  completed: "statusDone",
  error: "errorWord",
  cancelled: "statusStopped",
  timeout: "statusTimeout",
}

function messageOf(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback
}

function downloadSource(name: string, source: string) {
  const body = source.endsWith("\n") ? source : `${source}\n`
  const blob = new Blob([body], { type: "text/plain;charset=utf-8" })
  const url = URL.createObjectURL(blob)
  const link = document.createElement("a")
  const base = name.replace(/[\\/:*?"<>|]+/g, " ").trim() || "practica"
  link.href = url
  link.download = `${base}.txt`
  link.click()
  URL.revokeObjectURL(url)
}

function LabSplit({
  axis,
  label,
  value,
  min,
  max,
  className,
  edge = "end",
  onDrag,
  onStep,
}: {
  axis: "x" | "y"
  label: string
  value: number
  min: number
  max: number
  className: string
  edge?: "start" | "end"
  onDrag: (event: ReactPointerEvent<HTMLButtonElement>) => void
  onStep: (delta: number) => void
}) {
  return (
    <button
      type="button"
      className={axis === "y" ? `splitter splitter-row ${className}` : `splitter ${className}`}
      role="separator"
      aria-orientation={axis === "y" ? "horizontal" : "vertical"}
      aria-label={label}
      aria-valuenow={value}
      aria-valuemin={min}
      aria-valuemax={max}
      onPointerDown={onDrag}
      onKeyDown={(event) => {
        const step = event.shiftKey ? 48 : 16
        const grow =
          axis === "y"
            ? event.key === "ArrowUp"
            : edge === "start"
              ? event.key === "ArrowRight"
              : event.key === "ArrowLeft"
        const shrink =
          axis === "y"
            ? event.key === "ArrowDown"
            : edge === "start"
              ? event.key === "ArrowLeft"
              : event.key === "ArrowRight"
        if (!grow && !shrink) return
        event.preventDefault()
        onStep(grow ? step : -step)
      }}
    />
  )
}

const EMPTY_CANVAS = { blocks: { languageVersion: 0, blocks: [] } }
const MAX_FILE_BYTES = 64 * 1024

function fileStem(name: string): string {
  const cut = name.replace(/\.[^.]+$/, "")
  return cut.replace(/[\\/:*?"<>|]+/g, " ").trim().slice(0, 120)
}

export function PracticeLab() {
  const t = useT()
  const locale = useLocale()
  const [count, setCount] = useState(0)
  const [workspace, setWorkspace] = useState<object | null>(null)
  const [preview, setPreview] = useState<LabPreview | null>(null)
  const [previewError, setPreviewError] = useState("")
  const [run, setRun] = useState<LabRun | null>(null)
  const [frozen, setFrozen] = useState("")
  const [busy, setBusy] = useState(false)
  const [playing, setPlaying] = useState(false)
  const [phonePane, setPhonePane] = useState<"construccion" | "codigo" | "ejecucion" | "practicas">("construccion")
  const [runError, setRunError] = useState("")
  const [input, setInput] = useState("")
  const [reserved, setReserved] = useState<Set<string>>(() => keywordSet([]))
  const [practices, setPractices] = useState<LabPractice[]>([])
  const [practiceName, setPracticeName] = useState("")
  const [currentId, setCurrentId] = useState<string | null>(null)
  const [restore, setRestore] = useState<{ key: number; state: object } | null>(null)
  const [saveNote, setSaveNote] = useState("")
  const [saveError, setSaveError] = useState("")
  const [saveBusy, setSaveBusy] = useState(false)
  const [pendingDelete, setPendingDelete] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const layoutRef = useRef<HTMLDivElement>(null)
  const outputRef = useRef<HTMLPreElement>(null)
  const [codeWidth, setCodeWidth] = useState(300)
  const [sideWidth, setSideWidth] = useState(352)
  const [outputHeight, setOutputHeight] = useState(168)
  const restoreKey = useRef(0)
  const seen = useRef(0)
  const streamRef = useRef<EventSource | null>(null)
  const previewSignature = useRef("")
  const inputRef = useRef<HTMLInputElement>(null)

  const sameCanvas = frozen !== "" && JSON.stringify(workspace) === frozen
  const locked = Boolean(run?.id) && sameCanvas
  const stepping = locked && (run?.status === "paused" || run?.status === "waiting_input")
  const source = locked && run?.source ? run.source : preview?.source ?? ""
  const diagnostics =
    run && (locked || (!run.id && sameCanvas)) ? run.diagnostics : (preview?.diagnostics ?? [])
  const activeLine = stepping ? run?.line ?? null : null
  const shownSource = spellText(locale, source.endsWith("\n") ? source.slice(0, -1) : source)
  const colored = useMemo(() => highlightSource(shownSource, reserved), [shownSource, reserved])
  const activeBlockId = activeLine != null && run ? blockOnLine(run.bindings, activeLine) : null
  const blocked = diagnostics.some((item) => item.severity === "error")

  useEffect(() => {
    if (!workspace) return
    const signature = canvasSignature(workspace)
    if (signature === previewSignature.current) return
    let cancelled = false
    const handle = window.setTimeout(() => {
      void api.previewLab(workspace).then(
        (result) => {
          if (cancelled) return
          previewSignature.current = signature
          setPreview(result)
          setPreviewError("")
        },
        (error: unknown) => {
          if (cancelled) return
          setPreviewError(error instanceof ApiError ? error.message : t("previewFailed"))
        },
      )
    }, PREVIEW_MS)
    return () => {
      cancelled = true
      window.clearTimeout(handle)
    }
  }, [workspace])

  useEffect(() => {
    return () => {
      streamRef.current?.close()
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    void api.keywords().then(
      (words) => {
        if (!cancelled) setReserved(keywordSet([...editorKeywords(locale, words.keywords), ...words.stdlib]))
      },
      () => undefined,
    )
    return () => {
      cancelled = true
    }
  }, [locale])

  useEffect(() => {
    let cancelled = false
    void api.practices().then(
      (page) => {
        if (!cancelled) setPractices(page.results)
      },
      () => {
        if (!cancelled) setSaveError(t("practicesLoadError"))
      },
    )
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (run?.status === "waiting_input") inputRef.current?.focus()
  }, [run?.status])

  useEffect(() => {
    const node = outputRef.current
    if (!node) return
    node.scrollTop = node.scrollHeight
  }, [run?.output])

  function paneLimit(kind: "code" | "side" | "output") {
    const box = layoutRef.current?.getBoundingClientRect()
    if (kind === "output") {
      const min = 88
      const max = box ? Math.max(min, Math.round(box.height - 160)) : 420
      return { min, max }
    }
    const min = kind === "code" ? 180 : 220
    const other = kind === "code" ? sideWidth : codeWidth
    const max = box ? Math.max(min, Math.round(box.width - other - 220 - 12)) : 560
    return { min, max }
  }

  function setPane(kind: "code" | "side" | "output", next: number) {
    const { min, max } = paneLimit(kind)
    const size = Math.round(Math.min(Math.max(next, min), max))
    if (kind === "code") setCodeWidth(size)
    else if (kind === "side") setSideWidth(size)
    else setOutputHeight(size)
  }

  function dragPane(kind: "code" | "side" | "output", event: ReactPointerEvent<HTMLButtonElement>) {
    const layout = layoutRef.current
    if (!layout) return
    event.preventDefault()
    const handle = event.currentTarget
    try {
      handle.setPointerCapture(event.pointerId)
    } catch {
      /* El arrastre sigue por los eventos del propio separador. */
    }
    const body = document.body
    const cursor = body.style.cursor
    const select = body.style.userSelect
    body.style.cursor = kind === "output" ? "row-resize" : "col-resize"
    body.style.userSelect = "none"
    const move = (ev: PointerEvent) => {
      const box = layout.getBoundingClientRect()
      if (kind === "output") setPane("output", box.bottom - ev.clientY)
      else if (kind === "side") setPane("side", ev.clientX - box.left)
      else setPane("code", box.right - ev.clientX)
    }
    const stop = () => {
      handle.removeEventListener("pointermove", move)
      handle.removeEventListener("pointerup", stop)
      handle.removeEventListener("pointercancel", stop)
      body.style.cursor = cursor
      body.style.userSelect = select
    }
    handle.addEventListener("pointermove", move)
    handle.addEventListener("pointerup", stop)
    handle.addEventListener("pointercancel", stop)
  }

  function remember(result: LabRun) {
    seen.current = result.event_cursor
    setRun(result)
  }

  function openStream(id: string) {
    streamRef.current?.close()
    const sourceStream = new EventSource(`/api/v1/learning/runs/${id}/events/`)
    streamRef.current = sourceStream
    const ready = new Promise<void>((resolve) => {
      const finish = () => resolve()
      sourceStream.addEventListener("open", finish, { once: true })
      window.setTimeout(finish, 400)
    })
    const apply = (event: Event) => {
      const message = event as MessageEvent
      const cursor = Number(message.lastEventId)
      if (!Number.isFinite(cursor) || cursor <= seen.current) return
      const missed = cursor > seen.current + 1
      seen.current = cursor
      const data = JSON.parse(message.data) as {
        execution_id?: string
        status: string
        output?: string
        text?: string
        output_reset?: boolean
        line?: number | null
        column?: number | null
        variables?: Record<string, string>
        pending_input?: LabRun["pending_input"]
        scope?: string
      }
      setRun((current) =>
        current && current.id === data.execution_id
          ? {
              ...current,
              status: data.status === "running" ? current.status : data.status,
              output: missed ? current.output : applyConsoleOutput(current.output, message.type, data),
              line: data.line ?? null,
              column: data.column ?? null,
              scope: data.scope ?? current.scope,
              variables: data.variables ?? current.variables,
              pending_input: data.pending_input ?? null,
            }
          : current,
      )
      if (missed) {
        void api.labRun(id).then((result) => {
          seen.current = Math.max(seen.current, result.event_cursor ?? cursor)
          setRun((current) => (current && current.id === id ? { ...current, ...result, id } : current))
        })
      }
      if (["completed", "error", "cancelled", "timeout"].includes(data.status)) sourceStream.close()
    }
    for (const name of [
      "paused",
      "output",
      "input_requested",
      "input_rejected",
      "call",
      "return",
      "finished",
      "error",
      "cancelled",
    ]) {
      sourceStream.addEventListener(name, apply)
    }
    return ready
  }

  async function execute() {
    if (!workspace || busy || playing) return
    setPlaying(true)
    setRunError("")
    setInput("")
    const key = JSON.stringify(workspace)
    setFrozen(key)
    try {
      const result = await api.startLab(workspace)
      remember(result)
      if (result.status === "paused" && result.id) {
        await openStream(result.id)
        remember(await api.controlLab(result.id, "continue"))
      } else if (result.id) {
        void openStream(result.id)
      } else {
        streamRef.current?.close()
      }
    } catch (caught) {
      setRunError(messageOf(caught, t("labRunError")))
    } finally {
      setPlaying(false)
    }
  }

  async function control(action: string) {
    if (!run?.id || busy || (playing && action !== "stop")) return
    setBusy(true)
    setRunError("")
    try {
      remember(await api.controlLab(run.id, action))
    } catch (caught) {
      setRunError(messageOf(caught, t("labRunError")))
    } finally {
      setBusy(false)
    }
  }

  async function sendInput(event: FormEvent) {
    event.preventDefault()
    if (!run?.id || busy) return
    setBusy(true)
    setRunError("")
    try {
      remember(await api.inputLab(run.id, input))
      setInput("")
    } catch (caught) {
      setRunError(messageOf(caught, t("labRunError")))
    } finally {
      setBusy(false)
    }
  }

  function stopRun() {
    streamRef.current?.close()
    setRun(null)
    setFrozen("")
    setInput("")
  }

  function loadCanvas(state: object) {
    restoreKey.current += 1
    setRestore({ key: restoreKey.current, state })
  }

  function rememberPractice(saved: LabPractice) {
    setCurrentId(saved.id)
    setPracticeName(saved.name)
    setPractices((current) =>
      [saved, ...current.filter((item) => item.id !== saved.id)].sort((a, b) =>
        b.updated_at.localeCompare(a.updated_at),
      ),
    )
    setSaveNote(t("savedNote"))
    setSaveError("")
    setPendingDelete(null)
  }

  async function savePractice(event: FormEvent) {
    event.preventDefault()
    if (!workspace || saveBusy) return
    const name = practiceName.trim()
    if (!name) {
      setSaveError(t("needPracticeName"))
      return
    }
    setSaveBusy(true)
    setSaveError("")
    try {
      const saved = currentId
        ? await api.updatePractice(currentId, { name, workspace })
        : await api.createPractice(name, workspace)
      rememberPractice(saved)
    } catch (caught) {
      setSaveError(caught instanceof ApiError ? caught.message : t("practiceSaveError"))
    } finally {
      setSaveBusy(false)
    }
  }

  async function openPractice(id: string) {
    setSaveBusy(true)
    setSaveError("")
    try {
      const saved = await api.practice(id)
      stopRun()
      setPracticeName(saved.name)
      setCurrentId(saved.id)
      loadCanvas(saved.workspace ?? EMPTY_CANVAS)
      setSaveNote("")
      setPendingDelete(null)
    } catch (caught) {
      setSaveError(caught instanceof ApiError ? caught.message : t("practiceOpenError"))
    } finally {
      setSaveBusy(false)
    }
  }

  function downloadPractice(item: LabPractice) {
    if (!item.source.trim()) {
      setSaveError(t("noPracticeSource"))
      return
    }
    setSaveError("")
    downloadSource(item.name, item.source)
  }

  async function removePractice(id: string) {
    setSaveBusy(true)
    setSaveError("")
    try {
      await api.deletePractice(id)
      setPractices((current) => current.filter((item) => item.id !== id))
      setPendingDelete(null)
      if (id === currentId) {
        setCurrentId(null)
        setPracticeName("")
        stopRun()
        loadCanvas(EMPTY_CANVAS)
      }
      setSaveNote(t("deletedNote"))
    } catch (caught) {
      setSaveError(caught instanceof ApiError ? caught.message : t("practiceDeleteError"))
    } finally {
      setSaveBusy(false)
    }
  }

  function startNew() {
    stopRun()
    setCurrentId(null)
    setPracticeName("")
    setSaveNote("")
    setSaveError("")
    setPendingDelete(null)
    loadCanvas(EMPTY_CANVAS)
  }

  async function openFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ""
    if (!file || saveBusy) return
    if (file.size > MAX_FILE_BYTES) {
      setSaveError(t("fileTooBig"))
      setSaveNote("")
      return
    }
    setSaveBusy(true)
    setSaveError("")
    try {
      const source = (await file.text()).replace(/^\uFEFF/, "")
      if (source.includes("\0")) {
        setSaveError(t("notPseudocode"))
        setSaveNote("")
        return
      }
      const imported = await api.importLab(source)
      if (!imported.workspace) {
        const text = imported.diagnostics
          .map((item) => item.message)
          .filter(Boolean)
          .slice(0, 3)
          .join(" ")
        setSaveError(text || t("canvasBuildError"))
        setSaveNote("")
        return
      }
      stopRun()
      setCurrentId(null)
      setPracticeName(fileStem(file.name))
      setPendingDelete(null)
      loadCanvas(imported.workspace)
      const warning = imported.diagnostics.find((item) => item.severity !== "error")
      setSaveNote(warning?.message ?? t("builtFromFile"))
    } catch (caught) {
      setSaveError(caught instanceof ApiError ? caught.message : t("fileReadError"))
      setSaveNote("")
    } finally {
      setSaveBusy(false)
    }
  }

  const canStep = Boolean(run?.id) && run?.status === "paused" && sameCanvas && !busy && !playing
  const canStop =
    Boolean(run?.id) &&
    (playing || ((run?.status === "paused" || run?.status === "waiting_input") && !busy))
  const actions = useRef({ execute, control })
  actions.current = { execute, control }
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      const target = event.target
      if (target instanceof HTMLElement) {
        const tag = target.tagName
        if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable) return
      }
      const mod = event.ctrlKey || event.metaKey
      if (mod && event.key === "Enter") {
        event.preventDefault()
        void actions.current.execute()
      } else if (mod && event.key === "." && canStep) {
        event.preventDefault()
        void actions.current.control("step")
      } else if (event.key === "Escape" && canStop && !mod && !event.altKey) {
        event.preventDefault()
        void actions.current.control("stop")
      }
    }
    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [canStep, canStop])

  const entries = Object.entries(run?.variables ?? {})
  const statusText = [
    run ? (STATUS[run.status] ? t(STATUS[run.status]) : run.status) : t("notRun"),
    run?.scope ?? "",
    activeLine != null ? t("lineMark", { line: activeLine }) : "",
    t(count === 1 ? "blockOne" : "blockMany", { count }),
  ]
    .filter(Boolean)
    .join(" · ")

  return (
    <div className="lab-practice">
      <p className="notice">{t("practiceNote")}</p>
      <div className="lab-phone-tabs" role="tablist" aria-label={t("labSections")}>
        {(
          [
            ["construccion", t("construction")],
            ["codigo", t("pseudocode")],
            ["ejecucion", t("execution")],
            ["practicas", t("practices")],
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
      <div
        className="lab-body"
        data-phone={phonePane}
        ref={layoutRef}
        style={
          {
            "--lab-code": `${codeWidth}px`,
            "--lab-side": `${sideWidth}px`,
            "--lab-output": `${outputHeight}px`,
          } as CSSProperties
        }
      >
        <div className="lab-stage">
          <div className="lab-controls">
            <button
              className="primary"
              type="button"
              title={t("runTitle")}
              aria-keyshortcuts="Control+Enter"
              onClick={() => void execute()}
              disabled={
                !workspace ||
                busy ||
                playing ||
                blocked ||
                (sameCanvas && (run?.status === "paused" || run?.status === "waiting_input"))
              }
            >
              {t("run")}
            </button>
            <button type="button" onClick={() => void control("pause")} disabled={!canStep}>
              {t("pause")}
            </button>
            <button type="button" onClick={() => void control("continue")} disabled={!canStep}>
              {t("continue")}
            </button>
            <button
              type="button"
              title={t("oneStepTitle")}
              aria-keyshortcuts="Control+Period"
              onClick={() => void control("step")}
              disabled={!canStep}
            >
              {t("oneStep")}
            </button>
            <button
              type="button"
              title={t("stopTitle")}
              aria-keyshortcuts="Escape"
              onClick={() => void control("stop")}
              disabled={!canStop}
            >
              {t("stop")}
            </button>
            <button type="button" onClick={() => void control("restart")} disabled={!run?.id || !sameCanvas || busy || playing}>
              {t("restart")}
            </button>
          </div>
          <div className="lab-canvas-host">
            <BlockWorkspace
              onCount={setCount}
              onState={setWorkspace}
              activeBlockId={activeBlockId}
              restore={restore}
              onLoadError={(message) => {
                setSaveError(message)
                setSaveNote("")
              }}
            />
          </div>
        </div>
        <div className="lab-run-info" aria-live="polite">
          <p>{statusText}</p>
          {run && !sameCanvas ? <p>{t("canvasChanged")}</p> : null}
        </div>
        <LabSplit
          axis="y"
          className="lab-split-output"
          label={t("adjustOutput")}
          value={outputHeight}
          min={paneLimit("output").min}
          max={paneLimit("output").max}
          onDrag={(event) => dragPane("output", event)}
          onStep={(delta) => setPane("output", outputHeight + delta)}
        />
        <section className="lab-output-pane" aria-label={t("output")}>
          <h2>{t("output")}</h2>
          {runError ? <p className="error">{runError}</p> : null}
          <pre className="lab-output" ref={outputRef}>
            {run?.output || t("noOutput")}
          </pre>
          {run?.status === "waiting_input" && run.pending_input ? (
            <form className="lab-input" onSubmit={(event) => void sendInput(event)}>
              <label>
                {t("readNamed", { name: run.pending_input.name, type: run.pending_input.type })}
                <input
                  ref={inputRef}
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  autoComplete="off"
                />
              </label>
              <button type="submit" disabled={busy}>
                {t("send")}
              </button>
            </form>
          ) : null}
        </section>
        <LabSplit
          axis="x"
          className="lab-split-code"
          label={t("adjustPseudocode")}
          value={codeWidth}
          min={paneLimit("code").min}
          max={paneLimit("code").max}
          onDrag={(event) => dragPane("code", event)}
          onStep={(delta) => setPane("code", codeWidth + delta)}
        />
        <section className="lab-code-pane" aria-label={t("pseudocode")}>
          <h2>{t("pseudocode")}</h2>
          {source ? (
            <pre className="lab-code">
              {colored.map((spans, index) => {
                const number = index + 1
                const current = number === activeLine
                return (
                  <span key={number} className={current ? "lab-line lab-line-active" : "lab-line"} aria-current={current ? "true" : undefined}>
                    <span className="lab-gutter">{number}</span>
                    {spans.map((span, spanIndex) =>
                      span.kind === "keyword" || span.kind === "string" || span.kind === "comment" || span.kind === "number" ? (
                        <span key={spanIndex} className={`tok-${span.kind}`}>
                          {span.text}
                        </span>
                      ) : (
                        <span key={spanIndex}>{span.text}</span>
                      ),
                    )}
                  </span>
                )
              })}
            </pre>
          ) : (
            <p>{previewError || (preview ? t("previewEmpty") : t("translatingCanvas"))}</p>
          )}
          {previewError && source ? <p className="error">{previewError}</p> : null}
          {diagnostics.length > 0 ? (
            <ul className="lab-diagnostics">
              {diagnostics.map((item, index) => (
                <li key={`${item.code}-${item.line}-${index}`} className={item.severity === "error" ? "error" : "warning"}>
                  {item.message}
                </li>
              ))}
            </ul>
          ) : null}
        </section>
        <LabSplit
          axis="y"
          className="lab-split-vars"
          label={t("adjustDebugger")}
          value={outputHeight}
          min={paneLimit("output").min}
          max={paneLimit("output").max}
          onDrag={(event) => dragPane("output", event)}
          onStep={(delta) => setPane("output", outputHeight + delta)}
        />
        <section className="lab-vars-pane" aria-label={t("variables")}>
          <h2>{t("variables")}</h2>
          {entries.length > 0 ? (
            <ul className="lab-vars">
              {entries.map(([name, value]) => (
                <li key={name}>
                  <code>{name}</code> = {value}
                </li>
              ))}
            </ul>
          ) : (
            <p>{t("noValuesYet")}</p>
          )}
        </section>
        <LabSplit
          axis="x"
          className="lab-split-side"
          edge="start"
          label={t("adjustPractices")}
          value={sideWidth}
          min={paneLimit("side").min}
          max={paneLimit("side").max}
          onDrag={(event) => dragPane("side", event)}
          onStep={(delta) => setPane("side", sideWidth + delta)}
        />
        <aside className="lab-side">
          <section className="practice-save">
            <h2>{t("savedPractices")}</h2>
            <form onSubmit={(event) => void savePractice(event)}>
              <label>
                {t("nameWord")}
                <input
                  value={practiceName}
                  onChange={(event) => setPracticeName(event.target.value)}
                  maxLength={120}
                  placeholder={t("reviewPlaceholder")}
                  autoComplete="off"
                />
              </label>
              <button type="submit" disabled={!workspace || saveBusy || !practiceName.trim()}>
                {t("save")}
              </button>
              <button type="button" onClick={startNew} disabled={saveBusy}>
                {t("newPractice")}
              </button>
              <button type="button" onClick={() => fileRef.current?.click()} disabled={saveBusy}>
                {t("openFile")}
              </button>
              <input
                ref={fileRef}
                type="file"
                accept=".txt,text/plain"
                hidden
                aria-label={t("sourceFile")}
                onChange={(event) => void openFile(event)}
              />
            </form>
            {saveNote ? <p>{saveNote}</p> : null}
            {saveError ? <p className="error">{saveError}</p> : null}
            {practices.length > 0 ? (
              <ul className="practice-list">
                {practices.map((item) => (
                  <li key={item.id} className={item.id === currentId ? "practice-row is-open" : "practice-row"}>
                    <strong>{item.name}</strong>
                    <span>{formatWhen(item.updated_at)}</span>
                    <div className="practice-actions">
                      <button type="button" onClick={() => void openPractice(item.id)} disabled={saveBusy}>
                        {t("open")}
                      </button>
                      <button type="button" onClick={() => downloadPractice(item)} disabled={saveBusy}>
                        {t("download")}
                      </button>
                      {pendingDelete === item.id ? (
                        <>
                          <button type="button" className="danger" onClick={() => void removePractice(item.id)} disabled={saveBusy}>
                            {t("yesDelete")}
                          </button>
                          <button type="button" onClick={() => setPendingDelete(null)} disabled={saveBusy}>
                            {t("noWord")}
                          </button>
                        </>
                      ) : (
                        <button type="button" className="danger" onClick={() => setPendingDelete(item.id)} disabled={saveBusy}>
                          {t("remove")}
                        </button>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p>{t("noPractices")}</p>
            )}
          </section>
        </aside>
      </div>
    </div>
  )
}
