import { useEffect, useRef, useState, type CSSProperties, type FormEvent, type PointerEvent as ReactPointerEvent } from "react"

import {
  api,
  ApiError,
  type Account,
  type Algorithm,
  type Diagnostic,
  type Execution,
  type FlowGraph,
  type Meta,
  type Preferences,
  type Project,
} from "../api"
import { applyConsoleOutput } from "../console/output"
import { FlowView } from "../diagram/FlowView"
import { CodeEditor } from "../editor/CodeEditor"
import { editorKeywords } from "../dialect"
import { useLocale, useT, type Locale } from "../i18n"
import { AccountIdentity } from "../shell/Identity"
import { CommunitiesPanel } from "./Communities"
import { stdlibHelp } from "./stdlibHelp"

const AUTOSAVE_MS = 3000

const EMPTY_PREFS: Preferences = {
  theme: "light",
  font_size: 16,
  keymap: "default",
  indent_size: 4,
  autosave: true,
  locale: "es",
  require_semicolons: true,
  index_base: 1,
}

type SaveState = { kind: "idle" | "saving" | "saved" | "version"; number?: number }

export function Workbench({
  account,
  onAccount,
  onLogout,
  onOpenLab,
  onOpenCompose,
  focus,
  onLocale,
}: {
  account: Account
  onAccount: (account: Account) => void
  onLogout: () => void
  onOpenLab: () => void
  onOpenCompose: (payload: { name?: string; source?: string; semicolons: boolean }) => void
  focus: { projectId: string; algorithmId: string; token: number } | null
  onLocale: (locale: Locale) => void
}) {
  const t = useT()
  const locale = useLocale()
  const [projects, setProjects] = useState<Project[]>([])
  const [projectId, setProjectId] = useState("")
  const [algorithms, setAlgorithms] = useState<Algorithm[]>([])
  const [algorithmId, setAlgorithmId] = useState("")
  const [source, setSource] = useState("")
  const [dirty, setDirty] = useState(false)
  const [saveState, setSaveState] = useState<SaveState>({ kind: "idle" })
  const [keywords, setKeywords] = useState<string[]>([])
  const [stdlib, setStdlib] = useState<string[]>([])
  const [prefs, setPrefs] = useState<Preferences>(EMPTY_PREFS)
  const [meta, setMeta] = useState<Meta | null>(null)
  const [diagnostics, setDiagnostics] = useState<Diagnostic[]>([])
  const [execution, setExecution] = useState<Execution | null>(null)
  const [input, setInput] = useState("")
  const [jump, setJump] = useState<{ line: number; token: number } | null>(null)
  const [activeLine, setActiveLine] = useState<number | null>(null)
  const [error, setError] = useState("")
  const [projectName, setProjectName] = useState("")
  const [projectsOpen, setProjectsOpen] = useState(true)
  const [projectsWidth, setProjectsWidth] = useState(256)
  const [diagramOpen, setDiagramOpen] = useState(true)
  const [diagramWidth, setDiagramWidth] = useState(448)
  const [consoleHeight, setConsoleHeight] = useState(176)
  const [debugHeight, setDebugHeight] = useState(220)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [functionsOpen, setFunctionsOpen] = useState(false)
  const [communitiesOpen, setCommunitiesOpen] = useState(false)
  const [algorithmName, setAlgorithmName] = useState("")
  const [renaming, setRenaming] = useState<{ kind: "project" | "algorithm"; id: string; name: string } | null>(null)
  const [breakpoints, setBreakpoints] = useState<number[]>([])
  const [slice, setSlice] = useState("")
  const [playing, setPlaying] = useState(false)
  const [graph, setGraph] = useState<FlowGraph | null>(null)
  const [diagramNote, setDiagramNote] = useState("")
  const [requireSemicolons, setRequireSemicolons] = useState(true)
  const skipRename = useRef(false)
  const renamingLock = useRef(false)
  const [indexBase, setIndexBase] = useState<0 | 1>(1)
  const languageChoice = useRef({ requireSemicolons: true, indexBase: 1 as 0 | 1 })
  const savedLanguage = useRef({ requireSemicolons: true, indexBase: 1 as 0 | 1 })
  const savingChoice = useRef(false)
  const selectedId = useRef("")
  const sourceOwner = useRef("")
  const wantedAlgorithm = useRef<string | null>(null)
  const focusRef = useRef(focus)
  focusRef.current = focus
  const marks = useRef<Record<string, number[]>>({})
  const streamRef = useRef<EventSource | null>(null)
  const seen = useRef(0)
  const diagramToken = useRef(0)
  const pendingSave = useRef<{ id: string; text: string } | null>(null)
  const consoleRef = useRef<HTMLPreElement>(null)
  const settingsRef = useRef<HTMLDivElement>(null)
  const functionsRef = useRef<HTMLDivElement>(null)
  const workspaceRef = useRef<HTMLDivElement>(null)
  const stageRef = useRef<HTMLElement>(null)
  const insightRef = useRef<HTMLDivElement>(null)
  const localeNotify = useRef(onLocale)
  localeNotify.current = onLocale
  const saveLabel =
    saveState.kind === "saving"
      ? t("saving")
      : saveState.kind === "saved"
        ? t("saved")
        : saveState.kind === "version"
          ? t("version", { number: saveState.number ?? 0 })
          : t("unchanged")

  useEffect(() => {
    document.documentElement.dataset.theme = prefs.theme
  }, [prefs.theme])

  useEffect(() => {
    if (account.role !== "teacher") setCommunitiesOpen(false)
  }, [account.role])

  useEffect(() => {
    if (!settingsOpen && !functionsOpen) return
    function close(event: MouseEvent) {
      const target = event.target as Node
      if (settingsRef.current?.contains(target) || functionsRef.current?.contains(target)) return
      setSettingsOpen(false)
      setFunctionsOpen(false)
    }
    function onKey(event: KeyboardEvent) {
      if (event.key !== "Escape") return
      setSettingsOpen(false)
      setFunctionsOpen(false)
    }
    document.addEventListener("mousedown", close)
    document.addEventListener("keydown", onKey)
    return () => {
      document.removeEventListener("mousedown", close)
      document.removeEventListener("keydown", onKey)
    }
  }, [settingsOpen, functionsOpen])

  useEffect(() => {
    const node = consoleRef.current
    if (!node) return
    node.scrollTop = node.scrollHeight
  }, [execution?.output])

  useEffect(() => {
    void (async () => {
      const [projectPage, preference, info, words] = await Promise.all([
        api.projects(),
        api.preferences(),
        api.meta(),
        api.keywords(),
      ])
      setProjects(projectPage.results)
      setPrefs(preference)
      savedLanguage.current = {
        requireSemicolons: preference.require_semicolons,
        indexBase: preference.index_base === 0 ? 0 : 1,
      }
      if (!selectedId.current) {
        languageChoice.current = savedLanguage.current
        setRequireSemicolons(savedLanguage.current.requireSemicolons)
        setIndexBase(savedLanguage.current.indexBase)
      }
      localeNotify.current(preference.locale === "en" ? "en" : "es")
      setMeta(info)
      setKeywords(words.keywords)
      setStdlib(words.stdlib)
      const first = projectPage.results[0]
      const wanted = focusRef.current?.projectId
      if (wanted) setProjectId(wanted)
      else if (first) setProjectId(first.id)
    })().catch((caught: unknown) => setError(messageOf(caught, t("requestError"))))
  }, [])

  useEffect(() => {
    if (!projectId) return
    let current = true
    setAlgorithms([])
    void api
      .algorithms(projectId)
      .then((page) => {
        if (!current) return
        setAlgorithms(page.results)
        setAlgorithmId((selected) => {
          const want = wantedAlgorithm.current
          if (want) {
            wantedAlgorithm.current = null
            return want
          }
          return page.results.some((item) => item.id === selected) ? selected : (page.results[0]?.id ?? "")
        })
      })
      .catch((caught: unknown) => {
        if (current) setError(messageOf(caught, t("requestError")))
      })
    return () => {
      current = false
    }
  }, [projectId, focus?.token])

  useEffect(() => {
    if (!focus) return
    wantedAlgorithm.current = focus.algorithmId
    sourceOwner.current = ""
    setDirty(false)
    setProjectId(focus.projectId)
    setAlgorithmId(focus.algorithmId)
  }, [focus])

  useEffect(() => {
    if (!algorithmId) return
    selectedId.current = algorithmId
    void api
      .algorithm(algorithmId)
      .then((algorithm) => {
        if (selectedId.current !== algorithm.id) return
        sourceOwner.current = algorithm.id
        setSource(algorithm.source)
        languageChoice.current = {
          requireSemicolons: algorithm.require_semicolons,
          indexBase: algorithm.index_base,
        }
        setRequireSemicolons(algorithm.require_semicolons)
        setIndexBase(algorithm.index_base)
        setDirty(false)
        setSaveState({ kind: "saved" })
        setDiagnostics([])
        setExecution(null)
        setActiveLine(null)
        setBreakpoints(marks.current[algorithm.id] ?? [])
        setSlice("")
        setGraph(null)
        streamRef.current?.close()
        streamRef.current = null
        void loadDiagram(algorithm.id)
      })
      .catch((caught: unknown) => setError(messageOf(caught, t("requestError"))))
  }, [algorithmId, focus?.token])

  function flushPending() {
    const job = pendingSave.current
    if (!job) return
    pendingSave.current = null
    void api
      .saveSource(job.id, job.text, { keepalive: true })
      .then(() => {
        if (selectedId.current === job.id) {
          setSaveState({ kind: "saved" })
          void loadDiagram(job.id)
        }
      })
      .catch((caught: unknown) => setError(messageOf(caught, t("requestError"))))
  }

  useEffect(() => {
    const onHide = () => flushPending()
    window.addEventListener("pagehide", onHide)
    return () => {
      window.removeEventListener("pagehide", onHide)
      flushPending()
    }
  }, [])

  useEffect(() => {
    const previous = pendingSave.current
    if (previous && previous.id !== algorithmId) {
      pendingSave.current = null
      void api.saveSource(previous.id, previous.text, { keepalive: true }).catch((caught: unknown) => {
        setError(messageOf(caught, t("requestError")))
      })
    }
    if (!dirty || !prefs.autosave || !algorithmId || sourceOwner.current !== algorithmId) {
      if (!previous || previous.id === algorithmId) pendingSave.current = null
      return
    }
    const id = algorithmId
    const text = source
    pendingSave.current = { id, text }
    setSaveState({ kind: "saving" })
    const handle = window.setTimeout(() => {
      if (pendingSave.current?.id === id && pendingSave.current.text === text) pendingSave.current = null
      void api
        .saveSource(id, text)
        .then(() => {
          if (selectedId.current === id) {
            setSaveState({ kind: "saved" })
            void loadDiagram(id)
          }
        })
        .catch((caught: unknown) => setError(messageOf(caught, t("requestError"))))
    }, AUTOSAVE_MS)
    return () => window.clearTimeout(handle)
  }, [dirty, source, algorithmId, prefs.autosave])

  useEffect(() => {
    return () => {
      streamRef.current?.close()
    }
  }, [])

  function remember(result: Execution) {
    seen.current = result.event_cursor ?? seen.current
    setExecution(result)
    setDiagnostics(result.diagnostics)
  }

  function loadDiagram(id: string) {
    const token = ++diagramToken.current
    return api
      .flowchart(id)
      .then((payload) => {
        if (selectedId.current !== id || token !== diagramToken.current) return
        setGraph(payload.graph)
        const failure = payload.diagnostics.find((item) => item.severity === "error")
        setDiagramNote(payload.graph ? "" : failure?.message ?? t("noDiagram"))
      })
      .catch((caught: unknown) => setError(messageOf(caught, t("requestError"))))
  }

  function openStream(id: string) {
    streamRef.current?.close()
    const source = new EventSource(`/api/v1/executions/${id}/events/`)
    streamRef.current = source
    const ready = new Promise<void>((resolve) => {
      const finish = () => resolve()
      source.addEventListener("open", finish, { once: true })
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
        variables?: Record<string, string>
        call_stack?: Execution["call_stack"]
        last_condition?: string | null
        pending_input?: Execution["pending_input"]
      }
      setExecution((current) =>
        current && current.id === data.execution_id
          ? {
              ...current,
              status: data.status,
              output: missed ? current.output : applyConsoleOutput(current.output, message.type, data),
              line: data.line,
              variables: data.variables ?? current.variables,
              call_stack: data.call_stack ?? current.call_stack,
              last_condition: data.last_condition,
              pending_input: data.pending_input ?? null,
            }
          : current,
      )
      if (missed && data.execution_id) {
        const executionId = data.execution_id
        void api.execution(executionId).then((result) => {
          seen.current = Math.max(seen.current, result.event_cursor ?? cursor)
          setExecution((current) => (current && current.id === executionId ? { ...current, ...result } : current))
        })
      }
      if (["completed", "error", "cancelled", "timeout"].includes(data.status)) source.close()
    }
    for (const name of ["paused", "output", "input_requested", "finished", "error", "cancelled"]) {
      source.addEventListener(name, apply)
    }
    return ready
  }

  function chooseAlgorithm(id: string) {
    setAlgorithmId(id)
  }

  function edit(next: string) {
    sourceOwner.current = algorithmId
    setSource(next)
    setDirty(true)
  }

  async function flushSource() {
    if (!algorithmId) return
    await api.saveSource(algorithmId, source)
    setDirty(false)
    setSaveState({ kind: "saved" })
  }

  async function createProject(event: FormEvent) {
    event.preventDefault()
    const project = await api.createProject(projectName)
    setProjects((current) => [...current, project].sort((a, b) => a.name.localeCompare(b.name, prefs.locale)))
    setProjectId(project.id)
    setProjectName("")
  }

  async function createAlgorithm(event: FormEvent) {
    event.preventDefault()
    const algorithm = await api.createAlgorithm(projectId, algorithmName)
    setAlgorithms((current) => [...current, algorithm].sort((a, b) => a.name.localeCompare(b.name, prefs.locale)))
    setAlgorithmId(algorithm.id)
    setAlgorithmName("")
  }

  function beginRename(kind: "project" | "algorithm", id: string, name: string) {
    skipRename.current = false
    setRenaming({ kind, id, name })
  }

  function cancelRename() {
    skipRename.current = true
    setRenaming(null)
    setError("")
  }

  async function commitRename() {
    if (skipRename.current) {
      skipRename.current = false
      return
    }
    if (renamingLock.current || !renaming) return
    renamingLock.current = true
    const draft = renaming
    const next = draft.name.trim()
    const previous =
      draft.kind === "project"
        ? projects.find((item) => item.id === draft.id)?.name
        : algorithms.find((item) => item.id === draft.id)?.name
    const stillThis = (current: { kind: "project" | "algorithm"; id: string; name: string } | null) =>
      current !== null && current.kind === draft.kind && current.id === draft.id
    if (!next || next === previous) {
      setRenaming((current) => (stillThis(current) ? null : current))
      renamingLock.current = false
      return
    }
    setError("")
    try {
      if (draft.kind === "project") {
        const project = await api.renameProject(draft.id, next)
        setProjects((current) =>
          current.map((item) => (item.id === project.id ? project : item)).sort((a, b) => a.name.localeCompare(b.name, prefs.locale)),
        )
      } else {
        const algorithm = await api.renameAlgorithm(draft.id, next)
        setAlgorithms((current) =>
          current
            .map((item) => (item.id === algorithm.id ? { ...item, name: algorithm.name } : item))
            .sort((a, b) => a.name.localeCompare(b.name, prefs.locale)),
        )
      }
      setRenaming((current) => (stillThis(current) ? null : current))
    } catch (caught) {
      setError(messageOf(caught, t("requestError")))
    } finally {
      renamingLock.current = false
    }
  }

  function downloadAlgorithm(algorithm: Algorithm) {
    const text = algorithm.id === algorithmId ? source : algorithm.source
    const body = text.endsWith("\n") ? text : `${text}\n`
    const blob = new Blob([body], { type: "text/plain;charset=utf-8" })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    const base = algorithm.name.replace(/[\\/:*?"<>|]+/g, " ").trim() || "algoritmo"
    link.href = url
    link.download = `${base}.txt`
    link.click()
    URL.revokeObjectURL(url)
  }

  function clearOpenAlgorithm() {
    selectedId.current = ""
    setAlgorithmId("")
    setSource("")
    setDirty(false)
    setSaveState({ kind: "idle" })
    languageChoice.current = savedLanguage.current
    setRequireSemicolons(savedLanguage.current.requireSemicolons)
    setIndexBase(savedLanguage.current.indexBase)
    setDiagnostics([])
    setExecution(null)
    setGraph(null)
    setDiagramNote("")
    setActiveLine(null)
    setBreakpoints([])
    setSlice("")
    streamRef.current?.close()
    streamRef.current = null
  }

  async function removeAlgorithm(algorithm: Algorithm) {
    if (!window.confirm(t("deleteConfirm", { name: algorithm.name }))) return
    setError("")
    try {
      await api.deleteAlgorithm(algorithm.id)
    } catch (caught) {
      setError(messageOf(caught, t("requestError")))
      return
    }
    const rest = algorithms.filter((item) => item.id !== algorithm.id)
    setAlgorithms(rest)
    if (algorithm.id !== algorithmId) return
    const next = rest[0]
    if (next) setAlgorithmId(next.id)
    else clearOpenAlgorithm()
  }

  async function validate() {
    setError("")
    await flushSource()
    const result = await api.validate(algorithmId)
    setDiagnostics(result.diagnostics)
  }

  async function execute() {
    setError("")
    setInput("")
    setPlaying(true)
    try {
      await flushSource()
      const result = await api.execute(algorithmId)
      remember(result)
      if (result.status === "paused") {
        await openStream(result.id)
        const finished = await api.control(result.id, "continue")
        remember(finished)
      }
    } catch (caught) {
      setError(messageOf(caught, t("requestError")))
    } finally {
      setPlaying(false)
    }
  }

  async function debug() {
    setError("")
    setInput("")
    setSlice("")
    try {
      await flushSource()
      const result = await api.debug(algorithmId, breakpoints)
      remember(result)
      openStream(result.id)
    } catch (caught) {
      setError(messageOf(caught, t("requestError")))
    }
  }

  async function control(action: string) {
    if (!execution) return
    setError("")
    try {
      const result = await api.control(execution.id, action, breakpoints)
      remember(result)
    } catch (caught) {
      setError(messageOf(caught, t("requestError")))
    }
  }

  function toggleBreakpoint(line: number) {
    const next = breakpoints.includes(line)
      ? breakpoints.filter((item) => item !== line)
      : [...breakpoints, line].sort((left, right) => left - right)
    setBreakpoints(next)
    if (algorithmId) marks.current[algorithmId] = next
    if (execution?.debug && execution.status === "paused") {
      void api.control(execution.id, "breakpoints", next).then(remember).catch((caught: unknown) => {
        setError(messageOf(caught, t("requestError")))
      })
    }
  }

  async function showArray(name: string) {
    if (!execution) return
    const chunk = await api.inspect(execution.id, name)
    setSlice(`${name} [${chunk.base + chunk.start}…]: ${chunk.values.join(", ")}`)
  }

  async function sendInput(event: FormEvent) {
    event.preventDefault()
    if (!execution) return
    const result = await api.sendInput(execution.id, input)
    setExecution(result)
    setDiagnostics(result.diagnostics)
    setInput("")
  }

  async function saveVersion() {
    if (dirty) await api.saveSource(algorithmId, source)
    const version = await api.saveVersion(algorithmId)
    setDirty(false)
    setSaveState({ kind: "version", number: version.number })
  }

  async function configure(patch: { requireSemicolons?: boolean; indexBase?: 0 | 1 }) {
    const targetId = algorithmId
    languageChoice.current = { ...languageChoice.current, ...patch }
    savedLanguage.current = { ...languageChoice.current }
    setRequireSemicolons(languageChoice.current.requireSemicolons)
    setIndexBase(languageChoice.current.indexBase)
    if (savingChoice.current) return
    savingChoice.current = true
    setError("")
    try {
      let pending = true
      while (pending) {
        const snapshot = { ...languageChoice.current }
        const updated = await api.updatePreferences({
          require_semicolons: snapshot.requireSemicolons,
          index_base: snapshot.indexBase,
        })
        setPrefs(updated)
        const algorithm = targetId
          ? await api.saveLanguageOptions(targetId, {
              require_semicolons: snapshot.requireSemicolons,
              index_base: snapshot.indexBase,
            })
          : null
        pending =
          snapshot.requireSemicolons !== languageChoice.current.requireSemicolons ||
          snapshot.indexBase !== languageChoice.current.indexBase
        if (!pending && algorithm && selectedId.current === algorithm.id) {
          languageChoice.current = {
            requireSemicolons: algorithm.require_semicolons,
            indexBase: algorithm.index_base,
          }
          savedLanguage.current = { ...languageChoice.current }
          setRequireSemicolons(algorithm.require_semicolons)
          setIndexBase(algorithm.index_base)
          const checked = await api.validate(algorithm.id)
          setDiagnostics(checked.diagnostics)
          await loadDiagram(algorithm.id)
        }
      }
    } catch (caught) {
      setError(messageOf(caught, t("requestError")))
    } finally {
      savingChoice.current = false
    }
  }

  async function chooseLocale(locale: Locale) {
    const updated = await api.updatePreferences({ locale })
    setPrefs(updated)
    onLocale(locale)
  }

  async function chooseTheme(theme: "light" | "dark") {
    const updated = await api.updatePreferences({ theme })
    setPrefs(updated)
  }

  function jumpTo(diagnostic: Diagnostic) {
    setActiveLine(diagnostic.line)
    setJump({ line: diagnostic.line, token: Date.now() })
  }

  function paneLimit(kind: "projects" | "diagram") {
    const box = workspaceRef.current?.getBoundingClientRect()
    const min = kind === "projects" ? 168 : 200
    if (!box) return { min, max: kind === "projects" ? 560 : 900 }
    const other = kind === "projects" ? (diagramOpen ? diagramWidth : 136) : projectsOpen ? projectsWidth : 136
    const max = Math.max(min, Math.round(box.width - other - 280 - 12))
    return { min, max }
  }

  function setPane(kind: "projects" | "diagram", next: number) {
    const { min, max } = paneLimit(kind)
    const width = Math.round(Math.min(Math.max(next, min), max))
    if (kind === "projects") setProjectsWidth(width)
    else setDiagramWidth(width)
  }

  function dragPane(kind: "projects" | "diagram", event: ReactPointerEvent<HTMLElement>) {
    const workspace = workspaceRef.current
    if (!workspace) return
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
    body.style.cursor = "col-resize"
    body.style.userSelect = "none"
    const move = (ev: PointerEvent) => {
      const box = workspace.getBoundingClientRect()
      const next = kind === "projects" ? ev.clientX - box.left : box.right - ev.clientX
      setPane(kind, next)
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

  function rowLimit(kind: "console" | "debug") {
    const box = (kind === "console" ? stageRef.current : insightRef.current)?.getBoundingClientRect()
    const min = kind === "console" ? 72 : 96
    const reserved = kind === "console" ? 180 : 96
    const max = box ? Math.max(min, Math.round(box.height - reserved)) : 480
    return { min, max }
  }

  function setRow(kind: "console" | "debug", next: number) {
    const { min, max } = rowLimit(kind)
    const height = Math.round(Math.min(Math.max(next, min), max))
    if (kind === "console") setConsoleHeight(height)
    else setDebugHeight(height)
  }

  function dragRow(kind: "console" | "debug", event: ReactPointerEvent<HTMLButtonElement>) {
    const parent = kind === "console" ? stageRef.current : insightRef.current
    if (!parent) return
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
    body.style.cursor = "row-resize"
    body.style.userSelect = "none"
    const move = (ev: PointerEvent) => {
      const box = parent.getBoundingClientRect()
      setRow(kind, box.bottom - ev.clientY)
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

  return (
    <div className="shell">
      <header className="topbar topbar-editor">
        <div className="brand">
          <h1>Traza</h1>
          <AccountIdentity account={account} />
        </div>
        <div className="actions">
          <button className="top-action" type="button" onClick={onOpenLab}>
            {t("lab")}
          </button>
          <button
            className="top-action"
            type="button"
            onClick={() => {
              const current = algorithms.find((item) => item.id === algorithmId)
              onOpenCompose({
                semicolons: requireSemicolons,
                ...(algorithmId ? { name: current?.name ?? t("diagramFallback"), source } : {}),
              })
            }}
          >
            {t("compose")}
          </button>
          {account.role === "teacher" && (
            <button
              className="top-action"
              type="button"
              aria-expanded={communitiesOpen}
              onClick={() => {
                setSettingsOpen(false)
                setFunctionsOpen(false)
                setCommunitiesOpen(true)
              }}
            >
              {t("communities")}
            </button>
          )}
          <div className="functions" ref={functionsRef}>
            <button
              className="top-action"
              type="button"
              aria-expanded={functionsOpen}
              aria-controls="funciones"
              onClick={() => {
                setSettingsOpen(false)
                setFunctionsOpen((open) => !open)
              }}
            >
              {t("functions")}
            </button>
            {functionsOpen && (
              <div className="functions-menu" id="funciones" role="dialog" aria-label={t("includedFunctions")}>
                <h2>{t("includedFunctions")}</h2>
                <p className="note">{t("functionsNote")}</p>
                <ul>
                  {stdlib.map((name) => {
                    const help = stdlibHelp(prefs.locale, name)
                    return (
                      <li key={name}>
                        <code>{help?.signature ?? name}</code>
                        {help && <p>{help.summary}</p>}
                      </li>
                    )
                  })}
                </ul>
              </div>
            )}
          </div>
          <div className="settings" ref={settingsRef}>
            <button
              className="top-action"
              type="button"
              aria-expanded={settingsOpen}
              aria-controls="configuracion"
              onClick={() => {
                setFunctionsOpen(false)
                setSettingsOpen((open) => !open)
              }}
            >
              {t("settings")}
            </button>
            {settingsOpen && (
              <div className="settings-menu" id="configuracion">
                <label>
                  {t("language")}
                  <select
                    aria-label={t("language")}
                    value={prefs.locale}
                    onChange={(event) => {
                      const locale = event.target.value === "en" ? "en" : "es"
                      void chooseLocale(locale).catch((caught: unknown) => {
                        setError(messageOf(caught, t("requestError")))
                      })
                    }}
                  >
                    <option value="es">{t("spanish")}</option>
                    <option value="en">{t("english")}</option>
                  </select>
                </label>
                <label>
                  {t("profile")}
                  <select
                    aria-label={t("profile")}
                    value={account.role}
                    onChange={(event) => {
                      const role = event.target.value === "teacher" ? "teacher" : "student"
                      void api.updateAccount({ role }).then(onAccount).catch((caught: unknown) => {
                        setError(messageOf(caught, t("profileError")))
                      })
                    }}
                  >
                    <option value="student">{t("student")}</option>
                    <option value="teacher">{t("teacher")}</option>
                  </select>
                </label>
                <label>
                  {t("body")}
                  <select
                    aria-label={t("body")}
                    value={prefs.font_size}
                    onChange={(event) => {
                      const font_size = Number(event.target.value)
                      setPrefs({ ...prefs, font_size })
                      void api.updatePreferences({ font_size }).catch((caught: unknown) => {
                        setError(messageOf(caught, t("requestError")))
                      })
                    }}
                  >
                    {[14, 16, 18, 20, 22].map((size) => (
                      <option key={size} value={size}>
                        {size}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  {t("mode")}
                  <select
                    aria-label={t("mode")}
                    value={prefs.theme}
                    onChange={(event) => {
                      const theme = event.target.value === "dark" ? "dark" : "light"
                      void chooseTheme(theme).catch((caught: unknown) => {
                        setError(messageOf(caught, t("requestError")))
                      })
                    }}
                  >
                    <option value="light">{t("light")}</option>
                    <option value="dark">{t("dark")}</option>
                  </select>
                </label>
                <label>
                  {t("semicolons")}
                  <select
                    aria-label={t("semicolons")}
                    value={requireSemicolons ? "si" : "no"}
                    onChange={(event) => void configure({ requireSemicolons: event.target.value === "si" })}
                  >
                    <option value="si">{t("required")}</option>
                    <option value="no">{t("optional")}</option>
                  </select>
                </label>
                <label>
                  {t("arrayIndex")}
                  <select
                    aria-label={t("arrayIndex")}
                    value={String(indexBase)}
                    onChange={(event) => void configure({ indexBase: event.target.value === "0" ? 0 : 1 })}
                  >
                    <option value="1">{t("startsAt1")}</option>
                    <option value="0">{t("startsAt0")}</option>
                  </select>
                </label>
                <p className="note">{t("settingsNote")}</p>
              </div>
            )}
          </div>
          <button className="top-leave" type="button" onClick={onLogout}>
            {t("leave")}
          </button>
        </div>
      </header>
      {communitiesOpen && <CommunitiesPanel onClose={() => setCommunitiesOpen(false)} />}
      {meta?.notice && <p className="notice">{meta.notice}</p>}
      <div
        className={["workspace", projectsOpen ? "" : "projects-hidden", diagramOpen ? "" : "diagram-hidden"].filter(Boolean).join(" ")}
        ref={workspaceRef}
        style={{ "--projects-width": `${projectsWidth}px`, "--diagram-width": `${diagramWidth}px` } as CSSProperties}
      >
        <aside className="sidebar" id="proyectos">
          <div className="sidebar-head">
            <h2>{t("projects")}</h2>
            <button
              type="button"
              className="fold"
              aria-expanded={projectsOpen}
              aria-controls="proyectos-contenido"
              aria-label={projectsOpen ? t("hideProjects") : t("showProjects")}
              onClick={() => setProjectsOpen((open) => !open)}
            >
              {projectsOpen ? "−" : "+"}
            </button>
          </div>
          <div className="sidebar-body" id="proyectos-contenido">
          <ul>
            {projects.map((project) => (
              <li key={project.id} className="name-row">
                {renaming?.kind === "project" && renaming.id === project.id ? (
                  <input
                    className="rename-input"
                    autoFocus
                    aria-label={t("projectName")}
                    value={renaming.name}
                    onFocus={(event) => event.currentTarget.select()}
                    onChange={(event) => setRenaming({ kind: "project", id: project.id, name: event.target.value })}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") {
                        event.preventDefault()
                        void commitRename()
                      }
                      if (event.key === "Escape") {
                        event.preventDefault()
                        cancelRename()
                      }
                    }}
                    onBlur={() => void commitRename()}
                  />
                ) : (
                  <button
                    type="button"
                    aria-current={project.id === projectId ? "page" : undefined}
                    onClick={() => setProjectId(project.id)}
                  >
                    {project.name}
                  </button>
                )}
                <button
                  type="button"
                  className="mini"
                  aria-label={t("renameNamed", { name: project.name })}
                  title={t("rename")}
                  onClick={() => {
                    if (renaming?.kind === "project" && renaming.id === project.id) return
                    beginRename("project", project.id, project.name)
                  }}
                >
                  ✎
                </button>
              </li>
            ))}
          </ul>
          <form onSubmit={(event) => void createProject(event)}>
            <label>
              {t("newProject")}
              <input value={projectName} onChange={(event) => setProjectName(event.target.value)} required />
            </label>
            <button type="submit">{t("createProject")}</button>
          </form>
          <h2>{t("algorithms")}</h2>
          <ul>
            {algorithms.map((algorithm) => (
              <li key={algorithm.id} className="name-row">
                {renaming?.kind === "algorithm" && renaming.id === algorithm.id ? (
                  <input
                    className="rename-input"
                    autoFocus
                    aria-label={t("algorithmName")}
                    value={renaming.name}
                    onFocus={(event) => event.currentTarget.select()}
                    onChange={(event) => setRenaming({ kind: "algorithm", id: algorithm.id, name: event.target.value })}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") {
                        event.preventDefault()
                        void commitRename()
                      }
                      if (event.key === "Escape") {
                        event.preventDefault()
                        cancelRename()
                      }
                    }}
                    onBlur={() => void commitRename()}
                  />
                ) : (
                  <button
                    type="button"
                    aria-current={algorithm.id === algorithmId ? "true" : undefined}
                    onClick={() => chooseAlgorithm(algorithm.id)}
                  >
                    {algorithm.name}
                  </button>
                )}
                <button
                  type="button"
                  className="mini"
                  aria-label={t("renameNamed", { name: algorithm.name })}
                  title={t("rename")}
                  onClick={() => {
                    if (renaming?.kind === "algorithm" && renaming.id === algorithm.id) return
                    beginRename("algorithm", algorithm.id, algorithm.name)
                  }}
                >
                  ✎
                </button>
                <button
                  type="button"
                  className="mini"
                  aria-label={t("downloadNamed", { name: algorithm.name })}
                  title={t("download")}
                  onClick={() => downloadAlgorithm(algorithm)}
                >
                  ↓
                </button>
                <button
                  type="button"
                  className="mini"
                  aria-label={t("removeNamed", { name: algorithm.name })}
                  title={t("remove")}
                  onClick={() => void removeAlgorithm(algorithm)}
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
          <form onSubmit={(event) => void createAlgorithm(event)}>
            <label>
              {t("newAlgorithm")}
              <input value={algorithmName} onChange={(event) => setAlgorithmName(event.target.value)} required />
            </label>
            <button type="submit">{t("createAlgorithm")}</button>
          </form>
          </div>
        </aside>
        {projectsOpen && (
          <button
            type="button"
            className="splitter"
            role="separator"
            aria-orientation="vertical"
            aria-label={t("adjustProjects")}
            aria-valuenow={projectsWidth}
            aria-valuemin={168}
            aria-valuemax={paneLimit("projects").max}
            onPointerDown={(event) => dragPane("projects", event)}
            onKeyDown={(event) => {
              const step = event.shiftKey ? 48 : 16
              if (event.key === "ArrowRight") {
                event.preventDefault()
                setPane("projects", projectsWidth + step)
              }
              if (event.key === "ArrowLeft") {
                event.preventDefault()
                setPane("projects", projectsWidth - step)
              }
            }}
          />
        )}
        <section
          className="stage"
          ref={stageRef}
          style={{ "--console-height": `${consoleHeight}px` } as CSSProperties}
        >
          <div className="toolbar" role="toolbar" aria-label={t("editor")}>
            <div className="tool-group">
              <button type="button" onClick={() => void validate()} disabled={!algorithmId || playing}>
                {t("validate")}
              </button>
              <button className="primary" type="button" onClick={() => void execute()} disabled={!algorithmId || playing}>
                {t("run")}
              </button>
              <button className="tool-debug" type="button" onClick={() => void debug()} disabled={!algorithmId || playing}>
                {t("debug")}
              </button>
            </div>
            <div className="tool-group">
              <button type="button" onClick={() => void control("step")} disabled={playing || execution?.status !== "paused"}>
                {t("step")}
              </button>
              <button type="button" onClick={() => void control("step_in")} disabled={playing || execution?.status !== "paused"}>
                {t("stepIn")}
              </button>
              <button type="button" onClick={() => void control("step_out")} disabled={playing || execution?.status !== "paused"}>
                {t("stepOut")}
              </button>
              <button type="button" onClick={() => void control("continue")} disabled={playing || execution?.status !== "paused"}>
                {t("continue")}
              </button>
            </div>
            <div className="tool-group">
              <button type="button" onClick={() => void control("pause")} disabled={!execution?.debug}>
                {t("pause")}
              </button>
              <button type="button" onClick={() => void control("stop")} disabled={!playing && !execution?.debug}>
                {t("stop")}
              </button>
              <button type="button" onClick={() => void control("restart")} disabled={!execution?.debug}>
                {t("restart")}
              </button>
            </div>
            <button className="tool-save" type="button" onClick={() => void saveVersion()} disabled={!algorithmId}>
              {t("saveVersion")}
            </button>
          </div>
          <CodeEditor
            source={source}
            keywords={editorKeywords(locale, keywords)}
            stdlib={stdlib}
            fontSize={prefs.font_size}
            indentSize={prefs.indent_size}
            theme={prefs.theme}
            jump={jump}
            breakpoints={breakpoints}
            currentLine={execution?.debug ? (execution.line ?? null) : null}
            onToggleBreakpoint={toggleBreakpoint}
            onChange={edit}
            onCursor={setActiveLine}
          />
          <div className="status-bar">
            <span>{saveLabel}</span>
            {activeLine !== null && <span>{t("cursorLine", { line: activeLine })}</span>}
          </div>
          <button
            type="button"
            className="splitter splitter-row"
            role="separator"
            aria-orientation="horizontal"
            aria-label={t("adjustConsole")}
            aria-valuenow={consoleHeight}
            aria-valuemin={rowLimit("console").min}
            aria-valuemax={rowLimit("console").max}
            onPointerDown={(event) => dragRow("console", event)}
            onKeyDown={(event) => {
              const step = event.shiftKey ? 48 : 16
              if (event.key === "ArrowUp") {
                event.preventDefault()
                setRow("console", consoleHeight + step)
              }
              if (event.key === "ArrowDown") {
                event.preventDefault()
                setRow("console", consoleHeight - step)
              }
            }}
          />
          <div className="console-dock">
            <pre className="console" aria-label={t("console")} ref={consoleRef}>
              {execution?.output || t("emptyConsole")}
            </pre>
            {execution?.status === "waiting_input" && execution.pending_input && (
              <form className="input-row" onSubmit={(event) => void sendInput(event)}>
                <label htmlFor="dato">
                  {execution.pending_input.name} ({execution.pending_input.type})
                  <input id="dato" value={input} onChange={(event) => setInput(event.target.value)} autoFocus />
                </label>
                <button className="primary" type="submit">
                  {t("send")}
                </button>
              </form>
            )}
          </div>
        </section>
        <button
          type="button"
          className="splitter"
          role="separator"
          aria-orientation="vertical"
          aria-label={t("adjustDiagram")}
          aria-valuenow={diagramWidth}
          aria-valuemin={200}
          aria-valuemax={paneLimit("diagram").max}
          onPointerDown={(event) => dragPane("diagram", event)}
          onKeyDown={(event) => {
            const step = event.shiftKey ? 48 : 16
            if (event.key === "ArrowLeft") {
              event.preventDefault()
              setPane("diagram", diagramWidth + step)
            }
            if (event.key === "ArrowRight") {
              event.preventDefault()
              setPane("diagram", diagramWidth - step)
            }
          }}
        />
        <div
          className="insight"
          ref={insightRef}
          style={{ "--debug-height": `${debugHeight}px` } as CSSProperties}
        >
          <FlowView
            open={diagramOpen}
            onToggle={() => setDiagramOpen((open) => !open)}
            graph={graph}
            focusLine={execution?.debug && execution.line ? execution.line : activeLine}
            theme={prefs.theme}
            dirty={dirty}
            note={diagramNote}
            filename={algorithms.find((item) => item.id === algorithmId)?.name ?? t("diagramFallback")}
            onSelectLine={(line) => {
              setActiveLine(line)
              setJump({ line, token: Date.now() })
            }}
          />
          <button
            type="button"
            className="splitter splitter-row"
            role="separator"
            aria-orientation="horizontal"
            aria-label={t("adjustDebugger")}
            aria-valuenow={debugHeight}
            aria-valuemin={rowLimit("debug").min}
            aria-valuemax={rowLimit("debug").max}
            onPointerDown={(event) => dragRow("debug", event)}
            onKeyDown={(event) => {
              const step = event.shiftKey ? 48 : 16
              if (event.key === "ArrowUp") {
                event.preventDefault()
                setRow("debug", debugHeight + step)
              }
              if (event.key === "ArrowDown") {
                event.preventDefault()
                setRow("debug", debugHeight - step)
              }
            }}
          />
          <aside className="panel">
            <section>
              <h2>{t("debugger")}</h2>
              {execution?.debug ? (
                <div className="debug-grid">
                  <p className="note">
                    {execution.scope || t("algorithm")}
                    {execution.line ? ` · ${t("lineMark", { line: execution.line })}` : ""}
                    {execution.last_condition ? ` · ${t("condition", { value: execution.last_condition })}` : ""}
                  </p>
                  <h3>{t("stack")}</h3>
                  <ul className="stack">
                    {(execution.call_stack ?? []).map((frame, index) => (
                      <li key={`${frame.name}-${index}`}>
                        <button type="button" onClick={() => frame.line && jumpTo({ line: frame.line, column: 1, code: "", message: "", severity: "info", suggestion: null })}>
                          {frame.name}
                          {frame.line ? `:${frame.line}` : ""}
                        </button>
                      </li>
                    ))}
                  </ul>
                  <h3>{t("variables")}</h3>
                  <ul className="variables">
                    {Object.entries(execution.variables ?? {}).map(([name, value]) => (
                      <li key={name}>
                        <span>
                          {name} = {value}
                        </span>
                        {value.includes("celdas") && (
                          <button type="button" onClick={() => void showArray(name)}>
                            {t("see")}
                          </button>
                        )}
                      </li>
                    ))}
                  </ul>
                  {slice && <p className="note">{slice}</p>}
                  {Object.keys(execution.variables ?? {}).length === 0 && <p className="note">{t("noVariables")}</p>}
                </div>
              ) : (
                <p className="note">{t("debugHint")}</p>
              )}
            </section>
            <section>
              <h2>{t("diagnostics")}</h2>
              {error && <p className="error">{error}</p>}
              {diagnostics.length === 0 && <p className="note">{t("noDiagnostics")}</p>}
              <ul className="diagnostics">
                {diagnostics.map((item) => (
                  <li key={`${item.code}-${item.line}-${item.column}-${item.message}`}>
                    <button type="button" onClick={() => jumpTo(item)}>
                      {item.severity === "warning" ? t("warning") : t("errorWord")} {item.code}
                      <small>
                        {t("lineColumn", { line: item.line, column: item.column ?? "", message: item.message })}
                      </small>
                      {item.suggestion && <small>{item.suggestion}</small>}
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          </aside>
        </div>
      </div>
    </div>
  )
}

function messageOf(caught: unknown, fallback: string): string {
  return caught instanceof ApiError ? caught.message : fallback
}
