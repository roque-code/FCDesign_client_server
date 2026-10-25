import { useEffect, useRef, useState } from "react"

import { ApiError, api, type Account, type LabPath } from "../api"
import { translatedMessage, useT } from "../i18n"
import {
  languageHost,
  localForeignClose,
  localForeignInput,
  localForeignOpen,
  localForeignPoll,
  localForeignStatus,
  type ForeignRun,
} from "../runtime"
import { pasteBlockedFor } from "../paste"
import { saveDownload } from "../saveFile"
import { AccountIdentity } from "../shell/Identity"
import { Logo } from "../shell/Logo"
import { runLanguageCases } from "./cases"
import { ForeignEditor } from "./ForeignEditor"
import { FOREIGN_LANGUAGES, LANGUAGE_LABELS, type ForeignLanguage } from "./keywords"

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

const drafts = new Map<ForeignLanguage, string>()

function draftOf(language: ForeignLanguage): string {
  return drafts.get(language) ?? STARTERS[language]
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
  const [ready, setReady] = useState<Record<string, string>>({})
  const [paths, setPaths] = useState<LabPath[] | null>(null)
  const [routeId, setRouteId] = useState("")
  const [challengeId, setChallengeId] = useState("")
  const [attachOpen, setAttachOpen] = useState(false)
  const [attachNote, setAttachNote] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const outputRef = useRef<HTMLPreElement>(null)
  const sessionRef = useRef("")
  const busyRef = useRef(false)
  const local = languageHost() !== null
  const pasteBlocked = pasteBlockedFor(account)

  useEffect(() => {
    if (!local) return
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
  }, [local])

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
      const current = sessionRef.current
      sessionRef.current = ""
      if (current) void localForeignClose(current)
    }
  }, [])

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

  function choose(next: ForeignLanguage) {
    drafts.set(language, source)
    dropSession()
    setLanguage(next)
    setSource(draftOf(next))
    setCopied(false)
    setResult(null)
    setFailure("")
    setStdin("")
  }

  function edit(next: string) {
    drafts.set(language, next)
    setSource(next)
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(source)
      setCopied(true)
    } catch {
      setCopied(false)
    }
  }

  async function saveFile() {
    await saveDownload(`programa.${EXTENSIONS[language]}`, source)
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

  async function run() {
    dropSession()
    setBusy(true)
    busyRef.current = true
    setFailure("")
    setResult(null)
    setStdin("")
    try {
      show(await localForeignOpen(language, source))
    } catch (caught) {
      setFailure(caught instanceof ApiError ? translatedMessage(caught.message) : t("foreignFailed"))
    } finally {
      busyRef.current = false
      setBusy(false)
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
          <button className="top-leave" type="button" onClick={onBack}>
            {t("backToEditor")}
          </button>
        </div>
      </header>
      <div className="foreign-body">
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
        <p className="note">{t("foreignNote")}</p>
        {!local && <p className="error">{t("foreignDesktop")}</p>}
        <ForeignEditor key={language} language={language} source={source} onChange={edit} pasteBlocked={pasteBlocked} />
        <div className="foreign-actions">
          <button type="button" onClick={() => void copy()}>
            {copied ? t("copied") : t("copy")}
          </button>
          <button type="button" onClick={() => void saveFile()}>
            {t("languageSave")}
          </button>
          <button type="button" onClick={() => fileRef.current?.click()} disabled={pasteBlocked}>
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
          <button type="button" onClick={() => void showAttach()} disabled={!local}>
            {t("languageAttach")}
          </button>
          <button className="primary" type="button" onClick={() => void run()} disabled={!local || busy}>
            {busy && !waiting ? t("foreignRunning") : t("run")}
          </button>
          {runtimeNote && <p>{runtimeNote}</p>}
          {pasteBlocked ? <p>{t("pasteBlockedNote")}</p> : null}
        </div>
        {attachOpen && (
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
            <button className="primary" type="submit" disabled={!local || busy || !challengeId}>
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
        <pre className="foreign-output" aria-label={t("console")} ref={outputRef}>
          {result ? `${result.stderr}${result.stdout}` : ""}
        </pre>
      </div>
    </div>
  )
}
