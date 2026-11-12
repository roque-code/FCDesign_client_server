import { useEffect, useRef, useState, type CSSProperties, type PointerEvent as ReactPointerEvent } from "react"

import {
  ApiError,
  accessOf,
  api,
  bumpRunUsage,
  canExecuteToday,
  withRunUsage,
  type Account,
  type ClassroomStudent,
  type LabPath,
  type LanguageProgram,
} from "../api"
import { FeedbackForm, FeedbackNotes, GradesDownload, useMyFeedback } from "../feedback/Feedback"
import { FocusNotice, useExerciseFocus } from "../focus/FocusWatch"
import { translatedMessage, useT } from "../i18n"
import {
  installedLocal,
  localForeignCheck,
  localForeignClose,
  localForeignInput,
  localForeignOpen,
  localForeignPoll,
  localForeignStatus,
  type ForeignCheck,
  type ForeignDiagnostic,
  type ForeignRun,
} from "../runtime"
import { browserStorage, clamp, followPointer, readLayout, writeLayout } from "../panes"
import { pasteBlockedFor } from "../paste"
import { saveDownload } from "../saveFile"
import { AccountIdentity } from "../shell/Identity"
import { Logo } from "../shell/Logo"
import { Splitter } from "../shell/Splitter"
import { LeaveSubjectButton } from "../subjects/leave"
import { groupNames, studentLabel, studentsIn } from "../workbench/studentGroups"
import { AlgorithmPeek } from "./AlgorithmPeek"
import { runLanguageCases } from "./cases"
import { ForeignEditor } from "./ForeignEditor"
import { FOREIGN_LANGUAGES, LANGUAGE_LABELS, type ForeignLanguage } from "./keywords"
import { isForeignLanguage, sortPrograms, withProgram } from "./programs"

const EXTENSIONS: Record<ForeignLanguage, string> = {
  python: "py",
  javascript: "js",
  typescript: "ts",
  java: "java",
  c: "c",
  cpp: "cpp",
  csharp: "cs",
}

const STARTERS: Record<ForeignLanguage, string> = {
  python: 'print("hola")\n',
  javascript: 'console.log("hola")\n',
  typescript: 'console.log("hola")\n',
  java: 'public class Programa {\n    public static void main(String[] args) {\n        System.out.println("hola");\n    }\n}\n',
  c: '#include <stdio.h>\n\nint main(void) {\n    printf("hola\\n");\n    return 0;\n}\n',
  cpp: '#include <iostream>\n\nint main() {\n    std::cout << "hola\\n";\n    return 0;\n}\n',
  csharp: 'Console.WriteLine("hola");\n',
}

type Link = { id: string; name: string; saved: string }
type SaveJob = { id: string; language: ForeignLanguage; text: string }

const AUTOSAVE_MS = 3000
const SYNTAX_ONLY = new Set<ForeignLanguage>(["python", "javascript", "typescript"])

const NARROW = "(max-width: 980px)"
const PANES_KEY = "traza.foreign.panes"
const DEFAULT_PANES = { programs: 256, peek: 340, output: 144, students: 220 }
type Panes = typeof DEFAULT_PANES
const FOLDED = 44
const MIN_CODE = 340

const drafts = new Map<ForeignLanguage, string>()
const links = new Map<ForeignLanguage, Link>()

function draftOf(language: ForeignLanguage): string {
  return drafts.get(language) ?? STARTERS[language]
}

function languageLabel(language: string): string {
  return isForeignLanguage(language) ? LANGUAGE_LABELS[language] : language
}

export function ForeignBench({
  account,
  onAccount,
  onBack,
}: {
  account: Account
  onAccount: (account: Account) => void
  onBack: () => void
}) {
  const t = useT()
  const [language, setLanguage] = useState<ForeignLanguage>("python")
  const [source, setSource] = useState(() => draftOf("python"))
  const [stdin, setStdin] = useState("")
  const [busy, setBusy] = useState(false)
  const [waiting, setWaiting] = useState(false)
  const [copied, setCopied] = useState(false)
  const [failure, setFailure] = useState("")
  const [result, setResult] = useState<ForeignRun | null>(null)
  const [checking, setChecking] = useState(false)
  const [marks, setMarks] = useState<ForeignDiagnostic[]>([])
  const [ready, setReady] = useState<Record<string, string>>({})
  const [paths, setPaths] = useState<LabPath[] | null>(null)
  const [routeId, setRouteId] = useState("")
  const [challengeId, setChallengeId] = useState("")
  const [attachOpen, setAttachOpen] = useState(false)
  const [attachNote, setAttachNote] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)
  const bodyRef = useRef<HTMLDivElement>(null)
  const layoutRef = useRef<HTMLDivElement>(null)
  const sideRef = useRef<HTMLDivElement>(null)
  const [panes, setPanes] = useState(() => readLayout(browserStorage(), PANES_KEY, DEFAULT_PANES))
  const [peekOpen, setPeekOpen] = useState(true)
  const [narrow, setNarrow] = useState(() => window.matchMedia(NARROW).matches)
  const [zone, setZone] = useState<"programs" | "code" | "algorithm">("code")
  const fileRef = useRef<HTMLInputElement>(null)
  const outputRef = useRef<HTMLPreElement>(null)
  const sessionRef = useRef("")
  const busyRef = useRef(false)
  const runTicket = useRef(0)
  const onThisMachine = installedLocal() !== null
  const pasteBlocked = pasteBlockedFor(account)
  const seeStudents = account.role === "teacher" && accessOf(account).features.communities === true
  const [panelOpen, setPanelOpen] = useState(true)
  const [programs, setPrograms] = useState<LanguageProgram[] | null>(null)
  const [link, setLink] = useState<Link | null>(() => links.get("python") ?? null)
  const [programName, setProgramName] = useState("")
  const [programNote, setProgramNote] = useState("")
  const [saving, setSaving] = useState(false)
  const [students, setStudents] = useState<ClassroomStudent[]>([])
  const [group, setGroup] = useState("")
  const [studentId, setStudentId] = useState<number | null>(null)
  const [studentRows, setStudentRows] = useState<LanguageProgram[] | null>(null)
  const [viewing, setViewing] = useState<{ program: LanguageProgram; student: string } | null>(null)
  const shownSource = viewing ? (viewing.program.source ?? "") : source
  const dirty = link !== null && !viewing && source !== link.saved
  const myFeedback = useMyFeedback(account.role === "student", "program", link?.id ?? "")
  const watch = useExerciseFocus("program", link?.id ?? "", account.role === "student" && !viewing)
  const [autoState, setAutoState] = useState<"idle" | "saving" | "saved">("idle")
  const pendingSave = useRef<SaveJob | null>(null)
  const saveQueue = useRef<Promise<unknown>>(Promise.resolve())
  const flushRef = useRef<(keepalive?: boolean) => void>(() => undefined)

  useEffect(() => {
    const query = window.matchMedia(NARROW)
    const apply = () => setNarrow(query.matches)
    apply()
    query.addEventListener("change", apply)
    return () => query.removeEventListener("change", apply)
  }, [])

  useEffect(() => {
    const timer = window.setTimeout(() => writeLayout(browserStorage(), PANES_KEY, panes), 300)
    return () => window.clearTimeout(timer)
  }, [panes])

  useEffect(() => {
    let ignore = false
    void api
      .programs()
      .then((payload) => {
        if (!ignore) setPrograms(sortPrograms(payload.results))
      })
      .catch((caught) => {
        if (ignore) return
        setPrograms([])
        setProgramNote(caught instanceof ApiError ? translatedMessage(caught.message) : t("programsFailed"))
      })
    return () => {
      ignore = true
    }
  }, [])

  useEffect(() => {
    if (!seeStudents) return
    let ignore = false
    void api
      .classroomStudents()
      .then((payload) => {
        if (!ignore) setStudents(payload.results)
      })
      .catch(() => {
        if (!ignore) setStudents([])
      })
    return () => {
      ignore = true
    }
  }, [seeStudents])

  useEffect(() => {
    setStudentRows(null)
    if (studentId === null) return
    let ignore = false
    void api
      .studentPrograms(studentId)
      .then((payload) => {
        if (!ignore) setStudentRows(sortPrograms(payload.programs))
      })
      .catch((caught) => {
        if (ignore) return
        setStudentRows([])
        setProgramNote(caught instanceof ApiError ? translatedMessage(caught.message) : t("programsFailed"))
      })
    return () => {
      ignore = true
    }
  }, [studentId])

  useEffect(() => {
    let ignore = false
    void localForeignStatus()
      .then((payload) => {
        if (ignore) return
        const next: Record<string, string> = {}
        for (const item of payload.languages) next[item.language] = item.via
        setReady(next)
      })
      .catch(() => {
        if (!ignore) setReady({})
      })
    return () => {
      ignore = true
    }
  }, [])

  useEffect(() => {
    if (!waiting) return
    setStdin("")
    const focus = window.requestAnimationFrame(() => inputRef.current?.focus())
    return () => window.cancelAnimationFrame(focus)
  }, [waiting])

  useEffect(() => {
    const node = outputRef.current
    if (node) node.scrollTop = node.scrollHeight
  }, [result?.stdout, result?.stderr])

  useEffect(() => {
    if (!waiting || !sessionRef.current) return
    let ignore = false
    const timer = window.setInterval(() => {
      const current = sessionRef.current
      if (!current || busyRef.current || ignore) return
      void localForeignPoll(current)
        .then((payload) => {
          if (!ignore && sessionRef.current === current) show(payload)
        })
        .catch(() => {
          if (!ignore) {
            sessionRef.current = ""
            setWaiting(false)
          }
        })
    }, 400)
    return () => {
      ignore = true
      window.clearInterval(timer)
    }
  }, [waiting])

  useEffect(() => {
    return () => {
      runTicket.current += 1
      const current = sessionRef.current
      sessionRef.current = ""
      if (current) void localForeignClose(current)
    }
  }, [])

  // Un guardado sale cuando terminó el anterior: si dos viajan a la vez, el
  // servidor puede quedarse con el texto viejo.
  function persist(job: SaveJob, keepalive = false): Promise<void> {
    const sent = saveQueue.current.then(() => api.saveProgram(job.id, { source: job.text }, keepalive))
    saveQueue.current = sent.catch(() => undefined)
    return sent.then((saved) => {
      setPrograms((current) => withProgram(current ?? [], saved))
      const current = links.get(job.language)
      if (current?.id !== job.id) return
      const next = { ...current, name: saved.name, saved: job.text }
      links.set(job.language, next)
      setLink((shown) => (shown?.id === job.id ? next : shown))
    })
  }

  function flushSave(keepalive = false) {
    const job = pendingSave.current
    if (!job) return
    pendingSave.current = null
    persist(job, keepalive).catch((caught: unknown) => setProgramNote(problem(caught)))
  }
  flushRef.current = flushSave

  useEffect(() => {
    const onHide = () => flushRef.current(true)
    window.addEventListener("pagehide", onHide)
    return () => {
      window.removeEventListener("pagehide", onHide)
      flushRef.current(true)
    }
  }, [])

  useEffect(() => {
    pendingSave.current = null
    if (!link || viewing || source === link.saved) return
    const job = { id: link.id, language, text: source }
    pendingSave.current = job
    const timer = window.setTimeout(() => {
      if (pendingSave.current !== job) return
      pendingSave.current = null
      setAutoState("saving")
      persist(job).then(
        () => setAutoState("saved"),
        (caught: unknown) => {
          setAutoState("idle")
          setProgramNote(problem(caught))
        },
      )
    }, AUTOSAVE_MS)
    return () => window.clearTimeout(timer)
  }, [source, link, viewing, language])

  function show(payload: ForeignRun) {
    setResult(payload)
    sessionRef.current = payload.session
    setWaiting(payload.status === "waiting")
    if (payload.via === "cached" || payload.via === "system") {
      setReady((current) => ({ ...current, [language]: payload.via }))
    }
  }

  function dropSession() {
    const current = sessionRef.current
    sessionRef.current = ""
    setWaiting(false)
    if (current) void localForeignClose(current)
  }

  function cancelRun() {
    runTicket.current += 1
    dropSession()
    busyRef.current = false
    setBusy(false)
    setChecking(false)
    setMarks([])
  }

  function stopRun() {
    cancelRun()
    setFailure("")
    setResult((current) =>
      current
        ? { ...current, status: "error", session: "", message: t("runStopped") }
        : {
            status: "error",
            via: "system",
            exit_code: null,
            stdout: "",
            stderr: "",
            message: t("runStopped"),
            session: "",
          },
    )
  }

  function choose(next: ForeignLanguage) {
    flushSave()
    setAutoState("idle")
    drafts.set(language, source)
    cancelRun()
    setViewing(null)
    setLanguage(next)
    setSource(draftOf(next))
    setLink(links.get(next) ?? null)
    setCopied(false)
    setResult(null)
    setFailure("")
    setStdin("")
  }

  function edit(next: string) {
    drafts.set(language, next)
    setSource(next)
  }

  function linkTo(target: ForeignLanguage, next: Link | null) {
    if (next) links.set(target, next)
    else links.delete(target)
    setLink(next)
  }

  function problem(caught: unknown): string {
    return caught instanceof ApiError ? translatedMessage(caught.message) : t("foreignFailed")
  }

  async function openProgram(item: LanguageProgram) {
    if (!isForeignLanguage(item.language)) return
    const target = item.language
    const queued = pendingSave.current?.language === target ? pendingSave.current.text : null
    const kept = queued ?? links.get(target)?.saved ?? STARTERS[target]
    const draft = target === language ? source : draftOf(target)
    if (draft !== kept && !window.confirm(t("programDiscard", { language: LANGUAGE_LABELS[target] }))) return
    setProgramNote("")
    flushSave()
    try {
      await saveQueue.current
      const full = await api.program(item.id)
      const text = full.source ?? ""
      choose(target)
      drafts.set(target, text)
      setSource(text)
      linkTo(target, { id: full.id, name: full.name, saved: text })
      setZone("code")
    } catch (caught) {
      setProgramNote(problem(caught))
    }
  }

  async function saveChanges() {
    if (!link) return
    pendingSave.current = null
    setSaving(true)
    setProgramNote("")
    try {
      const saved = await api.saveProgram(link.id, { source })
      linkTo(language, { id: saved.id, name: saved.name, saved: saved.source ?? source })
      setPrograms((current) => withProgram(current ?? [], saved))
      setProgramNote(t("programSaved"))
    } catch (caught) {
      setProgramNote(problem(caught))
    } finally {
      setSaving(false)
    }
  }

  async function saveNew(event: { preventDefault: () => void }) {
    event.preventDefault()
    const name = programName.trim()
    if (!name) {
      setProgramNote(t("programNeedsName"))
      return
    }
    setSaving(true)
    setProgramNote("")
    try {
      const saved = await api.createProgram({ name, language, source })
      linkTo(language, { id: saved.id, name: saved.name, saved: saved.source ?? source })
      setPrograms((current) => withProgram(current ?? [], saved))
      setProgramName("")
      setProgramNote(t("programSaved"))
    } catch (caught) {
      setProgramNote(problem(caught))
    } finally {
      setSaving(false)
    }
  }

  async function removeProgram(item: LanguageProgram) {
    if (!window.confirm(t("programDeleteConfirm", { name: item.name }))) return
    setProgramNote("")
    try {
      if (pendingSave.current?.id === item.id) pendingSave.current = null
      await api.deleteProgram(item.id)
      setPrograms((current) => (current ?? []).filter((row) => row.id !== item.id))
      for (const [key, value] of links) if (value.id === item.id) links.delete(key)
      if (link?.id === item.id) setLink(null)
    } catch (caught) {
      setProgramNote(problem(caught))
    }
  }

  function newProgram() {
    flushSave()
    setAutoState("idle")
    setMarks([])
    edit(STARTERS[language])
    linkTo(language, null)
    setProgramNote("")
  }

  function view(item: LanguageProgram) {
    if (!isForeignLanguage(item.language)) return
    const student = students.find((row) => row.id === studentId)
    choose(item.language)
    setViewing({ program: item, student: student?.display_name ?? "" })
    setZone("code")
  }

  function leaveView() {
    cancelRun()
    setViewing(null)
    setResult(null)
    setFailure("")
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(shownSource)
      setCopied(true)
    } catch {
      setCopied(false)
    }
  }

  async function saveFile() {
    await saveDownload(`programa.${EXTENSIONS[language]}`, shownSource)
  }

  function openPicked(file: File | undefined) {
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      if (typeof reader.result === "string") edit(reader.result)
    }
    reader.readAsText(file)
  }

  async function showAttach() {
    if (viewing) return
    setAttachOpen(true)
    setAttachNote("")
    if (paths) return
    try {
      const payload = await api.labPaths()
      setPaths(payload.results)
    } catch (caught) {
      setFailure(caught instanceof ApiError ? translatedMessage(caught.message) : t("foreignFailed"))
    }
  }

  async function passCode() {
    if (!routeId || !challengeId) {
      setFailure(t("languageChoose"))
      return
    }
    setBusy(true)
    setFailure("")
    setAttachNote("")
    try {
      const session = await api.startAttempt(challengeId, routeId)
      const spec = session.challenge.task.cases ?? []
      const outputs = await runLanguageCases(language, source, spec)
      const graded = await api.submitLanguage(session.attempt.id, { language, source, outputs })
      const percent = graded.percent ?? 0
      setAttachNote(graded.passed ? t("languagePassedOn", { percent }) : t("languageHeld", { percent }))
    } catch (caught) {
      setFailure(caught instanceof ApiError ? translatedMessage(caught.message) : t("foreignFailed"))
    } finally {
      setBusy(false)
    }
  }

  function checkReport(checked: ForeignCheck): string {
    const found = checked.diagnostics
    if (checked.status === "ok" && found.length === 0) {
      return `${t(SYNTAX_ONLY.has(language) ? "foreignCheckSyntaxClean" : "foreignCheckClean")}\n`
    }
    if (found.length === 0) return `${checked.stderr}${checked.stdout}`
    const lines = found.map((item) =>
      item.line ? `${t("foreignCheckLine", { line: item.line })}: ${item.message}` : item.message,
    )
    return `${t("foreignCheckFound", { count: found.length })}\n${lines.join("\n")}\n`
  }

  async function validate() {
    const ticket = ++runTicket.current
    dropSession()
    setBusy(true)
    busyRef.current = true
    setChecking(true)
    setFailure("")
    setResult(null)
    setMarks([])
    try {
      const checked = await localForeignCheck(language, shownSource)
      if (runTicket.current !== ticket) return
      if (checked.via === "cached" || checked.via === "system") {
        setReady((current) => ({ ...current, [language]: checked.via }))
      }
      setMarks(checked.diagnostics)
      setResult({ ...checked, session: "", stdout: "", stderr: checkReport(checked) })
    } catch (caught) {
      if (runTicket.current !== ticket) return
      setFailure(caught instanceof ApiError ? translatedMessage(caught.message) : t("foreignCheckFailed"))
    } finally {
      if (runTicket.current === ticket) {
        busyRef.current = false
        setBusy(false)
        setChecking(false)
      }
    }
  }

  async function run() {
    const ticket = ++runTicket.current
    dropSession()
    setBusy(true)
    busyRef.current = true
    setFailure("")
    setResult(null)
    setMarks([])
    setStdin("")
    try {
      if (onThisMachine) {
        const quota = await api.consumeExecution()
        onAccount(withRunUsage(account, quota.used))
      }
      const payload = await localForeignOpen(language, shownSource)
      if (runTicket.current !== ticket) {
        if (payload.session) void localForeignClose(payload.session)
        return
      }
      show(payload)
      if (!onThisMachine) onAccount(bumpRunUsage(account))
    } catch (caught) {
      if (runTicket.current !== ticket) return
      setFailure(caught instanceof ApiError ? translatedMessage(caught.message) : t("foreignFailed"))
    } finally {
      if (runTicket.current === ticket) {
        busyRef.current = false
        setBusy(false)
      }
    }
  }

  async function send(event: { preventDefault: () => void }) {
    event.preventDefault()
    const current = sessionRef.current
    if (!current || busyRef.current) return
    const text = stdin
    setStdin("")
    setBusy(true)
    busyRef.current = true
    setFailure("")
    try {
      show(await localForeignInput(current, text))
    } catch (caught) {
      setWaiting(false)
      sessionRef.current = ""
      setFailure(caught instanceof ApiError ? translatedMessage(caught.message) : t("foreignFailed"))
    } finally {
      busyRef.current = false
      setBusy(false)
      window.requestAnimationFrame(() => inputRef.current?.focus())
    }
  }

  function paneLimit(kind: keyof Panes) {
    if (kind === "programs" || kind === "peek") {
      const min = kind === "programs" ? 180 : 220
      const box = layoutRef.current?.getBoundingClientRect()
      if (!box) return { min, max: 640 }
      const other = kind === "programs" ? (peekOpen ? panes.peek : FOLDED) : panelOpen ? panes.programs : FOLDED
      return { min, max: Math.round(box.width - other - MIN_CODE - 12) }
    }
    const box = (kind === "output" ? bodyRef.current : sideRef.current)?.getBoundingClientRect()
    const min = kind === "output" ? 72 : 96
    const reserved = kind === "output" ? 220 : 140
    return { min, max: box ? Math.round(box.height - reserved) : 480 }
  }

  function resize(kind: keyof Panes, next: number) {
    const { min, max } = paneLimit(kind)
    setPanes((current) => ({ ...current, [kind]: clamp(next, min, max) }))
  }

  function dragPane(kind: keyof Panes, event: ReactPointerEvent<HTMLButtonElement>) {
    const parent = kind === "output" ? bodyRef.current : kind === "students" ? sideRef.current : layoutRef.current
    if (!parent) return
    const padding = Number.parseFloat(getComputedStyle(parent).paddingBottom) || 0
    followPointer(event, kind === "output" || kind === "students" ? "y" : "x", (position) => {
      const box = parent.getBoundingClientRect()
      if (kind === "programs") resize(kind, position - box.left)
      else if (kind === "peek") resize(kind, box.right - position)
      else resize(kind, box.bottom - padding - position)
    })
  }

  function splitter(kind: keyof Panes, label: string, sign = 1) {
    const { min, max } = paneLimit(kind)
    return (
      <Splitter
        axis={kind === "output" || kind === "students" ? "y" : "x"}
        label={label}
        value={panes[kind]}
        min={min}
        max={max}
        onPointerDown={(event) => dragPane(kind, event)}
        onStep={(delta) => resize(kind, panes[kind] + sign * delta)}
      />
    )
  }

  const showPrograms = narrow || panelOpen
  const showPeek = narrow || peekOpen
  const columns = [
    showPrograms ? `${panes.programs}px 6px` : "auto",
    "minmax(0, 1fr)",
    showPeek ? `6px ${panes.peek}px` : "auto",
  ].join(" ")

  const route = paths?.find((item) => item.id === routeId) ?? null
  const builds = (route?.challenges ?? []).filter(
    (item) => item.activity_type === "build" && item.state === "available",
  )
  const via = ready[language]
  const runtimeNote =
    via === "system" ? t("foreignReadySystem") : via === "cached" ? t("foreignReadyCached") : via === "missing" ? t("foreignReadyMissing") : ""

  return (
    <div className="shell foreign-screen">
      <header className="topbar topbar-editor">
        <div className="brand">
          <h1><Logo mark />{t("foreignOpen")}</h1>
          <AccountIdentity account={account} onAccount={onAccount} />
        </div>
        <div className="actions">
          <div className="zone-switch" role="group" aria-label={t("foreignOpen")}>
            <button type="button" aria-pressed={zone === "programs"} onClick={() => setZone("programs")}>
              {t("zonePrograms")}
            </button>
            <button type="button" aria-pressed={zone === "code"} onClick={() => setZone("code")}>
              {t("zoneCode")}
            </button>
            <button type="button" aria-pressed={zone === "algorithm"} onClick={() => setZone("algorithm")}>
              {t("algorithm")}
            </button>
          </div>
          <LeaveSubjectButton />
          <button className="top-leave" type="button" onClick={onBack}>
            {t("backToEditor")}
          </button>
        </div>
      </header>
      <div
        ref={layoutRef}
        className={["foreign-layout", showPrograms ? "" : "programs-hidden", showPeek ? "" : "peek-hidden"].filter(Boolean).join(" ")}
        data-zone={narrow ? zone : "all"}
        style={{ "--foreign-columns": columns, "--students-height": `${panes.students}px` } as CSSProperties}
      >
        <aside className="sidebar foreign-programs" id="programas">
          <div className="sidebar-head">
            <h2>{t("programsTitle")}</h2>
            <button
              type="button"
              className="fold"
              aria-expanded={panelOpen}
              aria-controls="programas-contenido"
              aria-label={panelOpen ? t("hidePrograms") : t("showPrograms")}
              onClick={() => setPanelOpen((open) => !open)}
            >
              {panelOpen ? "−" : "+"}
            </button>
          </div>
          <div
            ref={sideRef}
            className={seeStudents ? "sidebar-body programs-split" : "sidebar-body"}
            id="programas-contenido"
          >
            <div className="programs-own">
              {programs !== null && programs.length === 0 && <p className="note">{t("programsEmpty")}</p>}
              <ul>
                {(programs ?? []).map((item) => (
                  <li key={item.id} className="name-row">
                    <button
                      type="button"
                      aria-current={!viewing && link?.id === item.id ? "page" : undefined}
                      onClick={() => void openProgram(item)}
                    >
                      <span className="program-language">{languageLabel(item.language)}</span>
                      {item.name}
                    </button>
                    <button
                      type="button"
                      className="mini"
                      aria-label={t("removeNamed", { name: item.name })}
                      title={t("removeNamed", { name: item.name })}
                      onClick={() => void removeProgram(item)}
                    >
                      ×
                    </button>
                  </li>
                ))}
              </ul>
              {!viewing && (
                <>
                  {link && (
                    <div className="program-current">
                      <p>
                        {t("programOpenNamed", { name: link.name })}
                        {autoState === "saving" ? (
                          <span> · {t("saving")}</span>
                        ) : dirty ? (
                          <strong> · {t("programUnsaved")}</strong>
                        ) : autoState === "saved" ? (
                          <span> · {t("saved")}</span>
                        ) : null}
                      </p>
                      <button type="button" disabled={saving || !dirty} onClick={() => void saveChanges()}>
                        {t("programSave")}
                      </button>
                    </div>
                  )}
                  {link && account.role === "student" && (
                    <FeedbackNotes items={myFeedback} kind="program" exerciseId={link.id} />
                  )}
                  <form onSubmit={(event) => void saveNew(event)}>
                    <label>
                      {t("programName")}
                      <input value={programName} maxLength={120} onChange={(event) => setProgramName(event.target.value)} />
                    </label>
                    <button type="submit" disabled={saving}>
                      {t("programSaveNew")}
                    </button>
                  </form>
                  <button type="button" onClick={newProgram}>
                    {t("programNew")}
                  </button>
                </>
              )}
              {programNote && (
                <p className="note" role="status">
                  {programNote}
                </p>
              )}
            </div>
            {seeStudents && splitter("students", t("adjustStudents"))}
            {seeStudents && (
              <div className="student-review program-students">
                <h2>{t("studentPrograms")}</h2>
                {students.length === 0 ? (
                  <p className="note">{t("studentWorkEmpty")}</p>
                ) : (
                  <>
                    <label>
                      {t("reviewGroup")}
                      <select
                        value={group}
                        onChange={(event) => {
                          setGroup(event.target.value)
                          setStudentId(null)
                        }}
                      >
                        <option value="">{t("pickGroup")}</option>
                        {groupNames(students).map((name) => (
                          <option key={name} value={name}>
                            {name}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      {t("reviewStudent")}
                      <select
                        value={studentId ?? ""}
                        disabled={!group}
                        onChange={(event) => setStudentId(event.target.value ? Number(event.target.value) : null)}
                      >
                        <option value="">{group ? t("pickStudent") : t("pickGroupFirst")}</option>
                        {studentsIn(students, group).map((student, _index, list) => (
                          <option key={student.id} value={student.id}>
                            {studentLabel(student, list)}
                          </option>
                        ))}
                      </select>
                    </label>
                    {studentRows !== null &&
                      (studentRows.length === 0 ? (
                        <p className="note">{t("studentProgramsEmpty")}</p>
                      ) : (
                        <ul>
                          {studentRows.map((item) => (
                            <li key={item.id} className="name-row">
                              <button
                                type="button"
                                aria-current={viewing?.program.id === item.id ? "page" : undefined}
                                onClick={() => view(item)}
                              >
                                <span className="program-language">{languageLabel(item.language)}</span>
                                {item.name}
                              </button>
                            </li>
                          ))}
                        </ul>
                      ))}
                    {viewing && (
                      <FeedbackForm kind="program" exerciseId={viewing.program.id} exerciseName={viewing.program.name} />
                    )}
                    <GradesDownload group={group} />
                  </>
                )}
              </div>
            )}
          </div>
        </aside>
        {showPrograms && splitter("programs", t("adjustPrograms"))}
        <div className="foreign-body" ref={bodyRef}>
          <div className="foreign-tabs" role="tablist" aria-label={t("foreignTitle")}>
            {FOREIGN_LANGUAGES.map((item) => (
              <button
                key={item}
                type="button"
                role="tab"
                aria-selected={item === language}
                onClick={() => choose(item)}
              >
                {LANGUAGE_LABELS[item]}
              </button>
            ))}
          </div>
          {viewing ? (
            <div className="foreign-viewing" role="status">
              <p>{t("viewingProgram", { name: viewing.program.name, student: viewing.student })}</p>
              <button type="button" onClick={leaveView}>
                {t("backToMyCode")}
              </button>
            </div>
          ) : (
            <p className="note">{onThisMachine ? t("foreignNote") : t("foreignServerNote")}</p>
          )}
          {watch.report ? <FocusNotice report={watch.report} fullscreen={watch.fullscreen} /> : null}
          <ForeignEditor
            key={language}
            language={language}
            source={shownSource}
            onChange={viewing ? () => undefined : edit}
            pasteBlocked={pasteBlocked}
            readOnly={viewing !== null}
            marks={marks}
          />
          <div className="foreign-actions">
            <button type="button" onClick={() => void copy()}>
              {copied ? t("copied") : t("copy")}
            </button>
            <button type="button" onClick={() => void saveFile()}>
              {t("languageSave")}
            </button>
            <button type="button" onClick={() => fileRef.current?.click()} disabled={pasteBlocked || viewing !== null}>
              {t("languageOpen")}
            </button>
            <input
              ref={fileRef}
              type="file"
              accept=".py,.js,.ts,.java,.c,.cpp,.cs,.h,.txt"
              hidden
              onChange={(event) => {
                openPicked(event.target.files?.[0])
                event.target.value = ""
              }}
            />
            <button type="button" onClick={() => void showAttach()} disabled={viewing !== null}>
              {t("languageAttach")}
            </button>
            <button type="button" onClick={() => void validate()} disabled={busy} title={t("foreignCheckTitle")}>
              {busy && checking ? t("foreignChecking") : t("validate")}
            </button>
            <button
              className="primary"
              type="button"
              onClick={() => void run()}
              disabled={busy || !canExecuteToday(account)}
              title={!canExecuteToday(account) ? t("executionsGone") : undefined}
            >
              {busy && !waiting && !checking ? t("foreignRunning") : t("run")}
            </button>
            <button
              type="button"
              title={t("stopTitle")}
              onClick={stopRun}
              disabled={!busy && !waiting && !sessionRef.current}
            >
              {t("stop")}
            </button>
            {runtimeNote && <p>{runtimeNote}</p>}
            {pasteBlocked ? <p>{t("pasteBlockedNote")}</p> : null}
          </div>
          {attachOpen && !viewing && (
            <form
              className="foreign-attach"
              onSubmit={(event) => {
                event.preventDefault()
                void passCode()
              }}
            >
              <label>
                {t("languageRoute")}
                <select
                  value={routeId}
                  onChange={(event) => {
                    setRouteId(event.target.value)
                    setChallengeId("")
                    setAttachNote("")
                  }}
                >
                  <option value="">{t("choose")}</option>
                  {(paths ?? []).map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                {t("languageChallenge")}
                <select value={challengeId} onChange={(event) => setChallengeId(event.target.value)}>
                  <option value="">{t("choose")}</option>
                  {builds.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.title}
                    </option>
                  ))}
                </select>
              </label>
              <button className="primary" type="submit" disabled={busy || !challengeId}>
                {t("languageAttach")}
              </button>
              {routeId && builds.length === 0 ? <p>{t("languageNoBuild")}</p> : null}
              {attachNote ? <p>{attachNote}</p> : null}
            </form>
          )}
          {waiting && (
            <form className="foreign-actions" onSubmit={(event) => void send(event)}>
              <label>
                {t("foreignInput")}
                <input
                  ref={inputRef}
                  value={stdin}
                  spellCheck={false}
                  autoFocus
                  disabled={busy}
                  onChange={(event) => setStdin(event.target.value)}
                />
              </label>
              <button className="primary" type="submit" disabled={busy}>
                {t("send")}
              </button>
            </form>
          )}
          {failure && <p className="error">{failure}</p>}
          {result?.message && <p className="error">{translatedMessage(result.message)}</p>}
          {splitter("output", t("adjustConsole"))}
          <pre
            className="foreign-output"
            aria-label={t("console")}
            ref={outputRef}
            style={{ height: panes.output }}
          >
            {result ? `${result.stderr}${result.stdout}` : ""}
          </pre>
        </div>
        {showPeek && splitter("peek", t("adjustAlgorithms"), -1)}
        <aside className="sidebar foreign-peek" id="algoritmos">
          <div className="sidebar-head">
            <h2>{t("algorithms")}</h2>
            <button
              type="button"
              className="fold"
              aria-expanded={peekOpen}
              aria-controls="algoritmos-contenido"
              aria-label={peekOpen ? t("hideAlgorithms") : t("showAlgorithms")}
              onClick={() => setPeekOpen((open) => !open)}
            >
              {peekOpen ? "−" : "+"}
            </button>
          </div>
          <div className="sidebar-body peek-body" id="algoritmos-contenido">
            <AlgorithmPeek students={students} seeStudents={seeStudents} />
          </div>
        </aside>
      </div>
    </div>
  )
}
