import { useEffect, useRef, useState, type CSSProperties, type FormEvent, type PointerEvent as ReactPointerEvent } from "react"

import {
  accessOf,
  api,
  ApiError,
  type Account,
  type Algorithm,
  type ClassroomStudent,
  type Diagnostic,
  type Execution,
  type Translation,
  type FlowGraph,
  type Meta,
  type Preferences,
  type Project,
} from "../api"
import { applyConsoleOutput } from "../console/output"
import { FlowView } from "../diagram/FlowView"
import { CodeEditor } from "../editor/CodeEditor"
import { editorKeywords } from "../dialect"
import { GuideButtons } from "../help/Guides"
import { translatedMessage, useLocale, useT, type Locale } from "../i18n"
import { saveDownload } from "../saveFile"
import {
  inInstalledApp,
  localControl,
  localDebug,
  localExecute,
  localExecution,
  localFlowchart,
  localInput,
  localInspect,
  localTranslate,
  localValidate,
  openEditorEvents,
  type LanguageBody,
} from "../runtime"
import { AccountIdentity } from "../shell/Identity"
import { Logo } from "../shell/Logo"
import { CommunitiesPanel } from "./Communities"
import { TranslateDialog } from "./TranslateDialog"
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
  const access = accessOf(account)
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
  const [zone, setZone] = useState<"editor" | "diagram">("editor")
  const [narrow, setNarrow] = useState(() => window.matchMedia("(max-width: 720px)").matches)
  const [consoleHeight, setConsoleHeight] = useState(176)
  const [debugHeight, setDebugHeight] = useState(220)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [functionsOpen, setFunctionsOpen] = useState(false)
  const [communitiesOpen, setCommunitiesOpen] = useState(false)
  const [students, setStudents] = useState<ClassroomStudent[]>([])
  const [reviewId, setReviewId] = useState<number | null>(null)
  const [reviewLoading, setReviewLoading] = useState(false)
  const [catalog, setCatalog] = useState<Record<string, Algorithm[]>>({})
  const reviewIdRef = useRef<number | null>(null)
  reviewIdRef.current = reviewId
  const [reloadToken, setReloadToken] = useState(0)
  const [algorithmName, setAlgorithmName] = useState("")
  const [renaming, setRenaming] = useState<{ kind: "project" | "algorithm"; id: string; name: string } | null>(null)
  const [breakpoints, setBreakpoints] = useState<number[]>([])
  const [slice, setSlice] = useState("")
  const [playing, setPlaying] = useState(false)
  const [translateOpen, setTranslateOpen] = useState(false)
  const [translations, setTranslations] = useState<Translation[]>([])
  const [translateBusy, setTranslateBusy] = useState(false)
  const [translateLocked, setTranslateLocked] = useState(false)
  const [translateFailure, setTranslateFailure] = useState("")
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
  const projectIdRef = useRef("")
  projectIdRef.current = projectId
  const sourceOwner = useRef("")
  const wantedAlgorithm = useRef<string | null>(null)
  const focusRef = useRef(focus)
  focusRef.current = focus
  const marks = useRef<Record<string, number[]>>({})
  const streamRef = useRef<EventSource | null>(null)
  const seen = useRef(0)
  const diagramToken = useRef(0)
  const sourceRef = useRef("")
  const profileKey = useRef("strict")
  const pendingSave = useRef<{ id: string; text: string } | null>(null)
  const consoleRef = useRef<HTMLPreElement>(null)
  const settingsRef = useRef<HTMLDivElement>(null)
  const functionsRef = useRef<HTMLDivElement>(null)
  const workspaceRef = useRef<HTMLDivElement>(null)
  const stageRef = useRef<HTMLElement>(null)
  const insightRef = useRef<HTMLDivElement>(null)
  const localeNotify = useRef(onLocale)
  localeNotify.current = onLocale
  const reviewing = reviewId !== null
  const reviewedStudent = students.find((item) => item.id === reviewId)
  const saveLabel = reviewing
    ? t("readOnlyCode")
    : saveState.kind === "saving"
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
    const query = window.matchMedia("(max-width: 720px)")
    const apply = () => setNarrow(query.matches)
    apply()
    query.addEventListener("change", apply)
    return () => query.removeEventListener("change", apply)
  }, [])

  useEffect(() => {
    if (account.role !== "teacher" || access.features.communities !== true) {
      setCommunitiesOpen(false)
      setStudents([])
    }
  }, [account.role, access.features.communities])

  useEffect(() => {
    let active = true
    function refresh() {
      void api.me().then((next) => {
        if (
          !active ||
          (next.translation_enabled === account.translation_enabled &&
            next.paste_enabled === account.paste_enabled &&
            next.plan?.code === account.plan?.code &&
            next.plan?.status === account.plan?.status &&
            next.plan?.days_remaining === account.plan?.days_remaining &&
            accessOf(next).browser_app === access.browser_app &&
            JSON.stringify(accessOf(next).features) === JSON.stringify(access.features) &&
            JSON.stringify(accessOf(next).limits) === JSON.stringify(access.limits) &&
            next.usage?.projects === account.usage?.projects &&
            next.usage?.algorithms === account.usage?.algorithms)
        ) {
          return
        }
        if (next.role !== "teacher" && !next.translation_enabled) setTranslateOpen(false)
        onAccount(next)
      }).catch(() => undefined)
    }
    function onVisible() {
      if (document.visibilityState === "visible") refresh()
    }
    window.addEventListener("focus", refresh)
    document.addEventListener("visibilitychange", onVisible)
    return () => {
      active = false
      window.removeEventListener("focus", refresh)
      document.removeEventListener("visibilitychange", onVisible)
    }
  }, [account, onAccount])

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
    const seeStudents = account.role === "teacher" && access.features.communities === true
    if (!seeStudents && reviewIdRef.current !== null) {
      setReviewId(null)
      return
    }
    let active = true
    void (async () => {
      const watched = seeStudents ? reviewIdRef.current : null
      const [projectPage, studentWork, preference, info, words] = await Promise.all([
        watched === null ? api.projects() : Promise.resolve(null),
        watched === null ? Promise.resolve(null) : api.studentProjects(watched),
        api.preferences(),
        api.meta(),
        api.keywords(),
      ])
      if (!active || reviewIdRef.current !== watched) return
      const listed = studentWork ? studentWork.projects : (projectPage?.results ?? [])
      setCatalog(
        studentWork
          ? Object.fromEntries(studentWork.projects.map((project) => [project.id, project.algorithms]))
          : {},
      )
      setProjects(listed)
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
      const ids = new Set(listed.map((item) => item.id))
      const wanted = watched === null ? focusRef.current?.projectId : undefined
      const keep = projectIdRef.current
      if (wanted && ids.has(wanted)) setProjectId(wanted)
      else if (keep && ids.has(keep)) setProjectId(keep)
      else setProjectId(listed[0]?.id ?? "")
      setReviewLoading(false)
    })().catch((caught: unknown) => {
      if (!active) return
      setReviewLoading(false)
      setError(messageOf(caught, t("requestError")))
    })
    return () => {
      active = false
    }
  }, [reloadToken, reviewId, account.role, access.features.communities])

  useEffect(() => {
    if (account.role !== "teacher" || access.features.communities !== true) return
    let active = true
    void api
      .classroomStudents()
      .then((page) => {
        if (active) setStudents(page.results)
      })
      .catch(() => {
        if (active) setStudents([])
      })
    return () => {
      active = false
    }
  }, [reloadToken, account.role, access.features.communities])

  useEffect(() => {
    if (!projectId) return
    if (reviewId !== null) {
      const items = catalog[projectId] ?? []
      setAlgorithms(items)
      setAlgorithmId((selected) => {
        const want = wantedAlgorithm.current
        if (want) {
          wantedAlgorithm.current = null
          return want
        }
        return items.some((item) => item.id === selected) ? selected : (items[0]?.id ?? "")
      })
      return
    }
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
  }, [projectId, focus?.token, reloadToken, reviewId, catalog])

  useEffect(() => {
    if (!focus) return
    setReviewId(null)
    wantedAlgorithm.current = focus.algorithmId
    sourceOwner.current = ""
    setDirty(false)
    setProjectId(focus.projectId)
    setAlgorithmId(focus.algorithmId)
  }, [focus])

  function showAlgorithm(algorithm: Algorithm) {
    if (selectedId.current !== algorithm.id) return
    sourceOwner.current = algorithm.id
    sourceRef.current = algorithm.source
    profileKey.current = algorithm.language_profile || "strict"
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
  }

  useEffect(() => {
    if (!algorithmId) return
    selectedId.current = algorithmId
    if (reviewId !== null) {
      const algorithm = Object.values(catalog).flat().find((item) => item.id === algorithmId)
      if (algorithm) showAlgorithm(algorithm)
      return
    }
    void api
      .algorithm(algorithmId)
      .then((algorithm) => {
        showAlgorithm(algorithm)
      })
      .catch((caught: unknown) => setError(messageOf(caught, t("requestError"))))
  }, [algorithmId, focus?.token, reloadToken, reviewId, catalog])

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
    if (reviewIdRef.current !== null || !dirty || !prefs.autosave || !algorithmId || sourceOwner.current !== algorithmId) {
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

  function currentProfile(): LanguageBody {
    return {
      profile_key: profileKey.current,
      require_semicolons: languageChoice.current.requireSemicolons,
      index_base: languageChoice.current.indexBase,
    }
  }

  function loadDiagram(id: string) {
    if (access.features.diagram !== true) {
      setGraph(null)
      setDiagramNote("")
      return Promise.resolve()
    }
    const token = ++diagramToken.current
    const pending = inInstalledApp()
      ? localFlowchart(sourceRef.current, currentProfile())
      : api.flowchart(id)
    return pending
      .then((payload) => {
        if (selectedId.current !== id || token !== diagramToken.current) return
        setGraph(payload.graph)
        const failure = payload.diagnostics.find((item) => item.severity === "error")
        setDiagramNote(payload.graph ? "" : failure?.message ?? t("noDiagram"))
      })
      .catch((caught: unknown) => {
        if (caught instanceof ApiError && caught.code === "plan_forbidden") return
        setError(messageOf(caught, t("requestError")))
      })
  }

  function openStream(id: string) {
    streamRef.current?.close()
    const stream = openEditorEvents(id)
    streamRef.current = stream
    const ready = new Promise<void>((resolve) => {
      const finish = () => resolve()
      stream.addEventListener("open", finish, { once: true })
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
        const read = inInstalledApp() ? localExecution(executionId) : api.execution(executionId)
        void read.then((result) => {
          seen.current = Math.max(seen.current, result.event_cursor ?? cursor)
          setExecution((current) => (current && current.id === executionId ? { ...current, ...result } : current))
        })
      }
      if (["completed", "error", "cancelled", "timeout"].includes(data.status)) stream.close()
    }
    for (const name of ["paused", "output", "input_requested", "finished", "error", "cancelled"]) {
      stream.addEventListener(name, apply)
    }
    return ready
  }

  function chooseAlgorithm(id: string) {
    setAlgorithmId(id)
  }

  function edit(next: string) {
    sourceOwner.current = algorithmId
    sourceRef.current = next
    setSource(next)
    setDirty(true)
  }

  function openReview(next: number | null) {
    const job = pendingSave.current
    pendingSave.current = null
    if (job && reviewIdRef.current === null) {
      void api.saveSource(job.id, job.text).catch((caught: unknown) => {
        setError(messageOf(caught, t("requestError")))
      })
    }
    setDirty(false)
    setCatalog({})
    setProjects([])
    setAlgorithms([])
    clearOpenAlgorithm()
    setProjectId("")
    setReviewLoading(next !== null)
    setReviewId(next)
  }

  async function flushSource() {
    if (!algorithmId || reviewIdRef.current !== null) return
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
    const base = algorithm.name.replace(/[\\/:*?"<>|]+/g, " ").trim() || "algoritmo"
    void saveDownload(`${base}.txt`, new Blob([body], { type: "text/plain;charset=utf-8" }))
  }

  function clearOpenAlgorithm() {
    selectedId.current = ""
    setAlgorithmId("")
    sourceRef.current = ""
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
    const result = inInstalledApp()
      ? await localValidate(source, currentProfile())
      : await api.validate(algorithmId)
    setDiagnostics(result.diagnostics)
  }

  const can = (key: string) => access.features[key] === true
  const translationOn = can("translate") && account.translation_enabled !== false
  const pasteBlocked = !can("paste") || (account.role !== "teacher" && account.paste_enabled === false)
  const projectsLeft = access.limits.max_projects
  const algorithmsLeft = access.limits.max_algorithms
  const canCreateProject = projectsLeft === null || (account.usage?.projects ?? 0) < projectsLeft
  const canCreateAlgorithm = algorithmsLeft === null || (account.usage?.algorithms ?? 0) < algorithmsLeft

  async function translate() {
    if (!translationOn) return
    setError("")
    setTranslateFailure("")
    setTranslateOpen(true)
    setTranslateBusy(true)
    setTranslations([])
    // Disabling the button inside this click makes Chromium and the desktop
    // webview send the same click to the new backdrop, which closes it at once.
    let opened = true
    const arm = window.setTimeout(() => {
      if (opened) setTranslateLocked(true)
    }, 0)
    try {
      await flushSource()
      const result = inInstalledApp()
        ? await localTranslate(source, currentProfile())
        : await api.translate(algorithmId)
      setDiagnostics(result.diagnostics)
      setTranslations(result.translations)
    } catch (caught) {
      setTranslateFailure(messageOf(caught, t("requestError")))
    } finally {
      opened = false
      window.clearTimeout(arm)
      setTranslateBusy(false)
      setTranslateLocked(false)
    }
  }

  async function execute() {
    setError("")
    setInput("")
    setPlaying(true)
    try {
      await flushSource()
      const result = inInstalledApp()
        ? await localExecute(source, currentProfile())
        : await api.execute(algorithmId)
      remember(result)
      if (result.status === "paused") {
        await openStream(result.id)
        const finished = inInstalledApp()
          ? await localControl(result.id, "continue")
          : await api.control(result.id, "continue")
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
      const result = inInstalledApp()
        ? await localDebug(source, currentProfile(), breakpoints)
        : await api.debug(algorithmId, breakpoints)
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
      const result = inInstalledApp()
        ? await localControl(execution.id, action, breakpoints)
        : await api.control(execution.id, action, breakpoints)
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
      void (inInstalledApp() ? localControl(execution.id, "breakpoints", next) : api.control(execution.id, "breakpoints", next)).then(remember).catch((caught: unknown) => {
        setError(messageOf(caught, t("requestError")))
      })
    }
  }

  async function showArray(name: string) {
    if (!execution) return
    const chunk = inInstalledApp()
      ? await localInspect(execution.id, name)
      : await api.inspect(execution.id, name)
    setSlice(`${name} [${chunk.base + chunk.start}…]: ${chunk.values.join(", ")}`)
  }

  async function sendInput(event: FormEvent) {
    event.preventDefault()
    if (!execution) return
    const result = inInstalledApp()
      ? await localInput(execution.id, input)
      : await api.sendInput(execution.id, input)
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
        const algorithm =
          targetId && reviewIdRef.current === null
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
          const checked = inInstalledApp()
            ? await localValidate(source, {
                profile_key: profileKey.current,
                require_semicolons: snapshot.requireSemicolons,
                index_base: snapshot.indexBase,
              })
            : await api.validate(algorithm.id)
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
          <h1><Logo /></h1>
          <AccountIdentity account={account} onAccount={onAccount} />
        </div>
        <div className="actions">
          <button
            className="top-action"
            type="button"
            onClick={() => {
              pendingSave.current = null
              setDirty(false)
              streamRef.current?.close()
              streamRef.current = null
              setReloadToken((token) => token + 1)
            }}
          >
            {t("refresh")}
          </button>
          {(can("editor") || can("diagram")) && (
          <div className="zone-switch" role="tablist" aria-label={t("editor")}>
            {can("editor") && (
            <button type="button" aria-pressed={zone === "editor"} onClick={() => setZone("editor")}>
              {t("editor")}
            </button>
            )}
            {can("diagram") && (
            <button type="button" aria-pressed={zone === "diagram"} onClick={() => setZone("diagram")}>
              {t("diagram")}
            </button>
            )}
          </div>
          )}
          {can("lab") && (
          <button className="top-action" type="button" onClick={onOpenLab}>
            {t("lab")}
          </button>
          )}
          {can("compose") && (
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
          )}
          {account.role === "teacher" && can("communities") && (
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
          {can("editor") && (
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
          )}
          <GuideButtons role={account.role} />
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
                    disabled={reviewing}
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
                    disabled={reviewing}
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
      {communitiesOpen && <CommunitiesPanel key={reloadToken} onClose={() => setCommunitiesOpen(false)} />}
      {meta?.notice && <p className="notice">{meta.notice}</p>}
      <div
        className={["workspace", projectsOpen ? "" : "projects-hidden", diagramOpen && can("diagram") ? "" : "diagram-hidden"].filter(Boolean).join(" ")}
        data-zone={narrow ? zone : "both"}
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
          {account.role === "teacher" && can("communities") && (
            <div className="student-review">
              <h2>{t("studentWork")}</h2>
              {students.length === 0 ? (
                <p className="note">{t("studentWorkEmpty")}</p>
              ) : (
                <label>
                  {t("pickStudent")}
                  <select
                    aria-label={t("pickStudent")}
                    value={reviewId ?? ""}
                    onChange={(event) => {
                      const value = event.target.value
                      openReview(value ? Number(value) : null)
                    }}
                  >
                    <option value="">{t("myProjects")}</option>
                    {students.map((student) => (
                      <option key={student.id} value={student.id}>
                        {student.display_name} · {student.communities.join(", ")}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              {reviewing && reviewedStudent && (
                <p className="note">{t("studentWorkNote", { name: reviewedStudent.display_name })}</p>
              )}
              {reviewing && !reviewLoading && projects.length === 0 && <p className="note">{t("noStudentProjects")}</p>}
            </div>
          )}
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
                {!reviewing && (
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
                )}
              </li>
            ))}
          </ul>
          {!reviewing && canCreateProject && (
            <form onSubmit={(event) => void createProject(event)}>
              <label>
                {t("newProject")}
                <input value={projectName} onChange={(event) => setProjectName(event.target.value)} required />
              </label>
              <button type="submit">{t("createProject")}</button>
            </form>
          )}
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
                {!reviewing && (
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
                )}
                <button
                  type="button"
                  className="mini"
                  aria-label={t("downloadNamed", { name: algorithm.name })}
                  title={t("download")}
                  hidden={!can("download")}
                  onClick={() => downloadAlgorithm(algorithm)}
                >
                  ↓
                </button>
                {!reviewing && (
                  <button
                    type="button"
                    className="mini"
                    aria-label={t("removeNamed", { name: algorithm.name })}
                    title={t("remove")}
                    onClick={() => void removeAlgorithm(algorithm)}
                  >
                    ×
                  </button>
                )}
              </li>
            ))}
          </ul>
          {!reviewing && canCreateAlgorithm && (
            <form onSubmit={(event) => void createAlgorithm(event)}>
              <label>
                {t("newAlgorithm")}
                <input value={algorithmName} onChange={(event) => setAlgorithmName(event.target.value)} required />
              </label>
              <button type="submit">{t("createAlgorithm")}</button>
            </form>
          )}
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
          <div className="toolbar" role="toolbar" aria-label={t("editor")} hidden={!can("editor")}>
            <div className="tool-group">
              {can("validate") && (
              <button type="button" onClick={() => void validate()} disabled={!algorithmId || playing}>
                {t("validate")}
              </button>
              )}
              {can("translate") && (
              <button
                type="button"
                onClick={() => void translate()}
                disabled={!translationOn || !algorithmId || playing || translateLocked}
                title={translationOn ? undefined : t("translationOff")}
              >
                {t("translate")}
              </button>
              )}
              {can("execute") && (
              <button className="primary" type="button" onClick={() => void execute()} disabled={!algorithmId || playing}>
                {t("run")}
              </button>
              )}
              {can("debug") && (
              <button className="tool-debug" type="button" onClick={() => void debug()} disabled={!algorithmId || playing}>
                {t("debug")}
              </button>
              )}
            </div>
            {can("debug") && (
            <>
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
            </>
            )}
            <button className="tool-save" type="button" onClick={() => void saveVersion()} disabled={!algorithmId || reviewing}>
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
            readOnly={reviewing}
            pasteBlocked={pasteBlocked && !reviewing}
            semicolons={requireSemicolons}
          />
          <div className="status-bar">
            <span>{saveLabel}</span>
            {pasteBlocked && !reviewing ? <span>{t("pasteBlockedNote")}</span> : null}
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
      {translateOpen && (
        <TranslateDialog
          translations={translations}
          diagnostics={diagnostics}
          busy={translateBusy}
          failure={translateFailure}
          filename={algorithms.find((item) => item.id === algorithmId)?.name || "algoritmo"}
          onClose={() => setTranslateOpen(false)}
        />
      )}
    </div>
  )
}

function messageOf(caught: unknown, fallback: string): string {
  return caught instanceof ApiError ? translatedMessage(caught.message) : fallback
}
