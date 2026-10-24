import { useEffect, useRef, useState } from "react"

import { ApiError, type Account } from "../api"
import { translatedMessage, useT } from "../i18n"
import {
  installedLocal,
  localForeignClose,
  localForeignInput,
  localForeignOpen,
  localForeignPoll,
  localForeignStatus,
  type ForeignRun,
} from "../runtime"
import { AccountIdentity } from "../shell/Identity"
import { Logo } from "../shell/Logo"
import { ForeignEditor } from "./ForeignEditor"
import { FOREIGN_LANGUAGES, type ForeignLanguage } from "./keywords"

const LABELS: Record<ForeignLanguage, string> = {
  python: "Python",
  javascript: "JavaScript",
  typescript: "TypeScript",
  java: "Java",
  c: "C",
  cpp: "C++",
  csharp: "C#",
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
  const inputRef = useRef<HTMLInputElement>(null)
  const outputRef = useRef<HTMLPreElement>(null)
  const sessionRef = useRef("")
  const busyRef = useRef(false)
  const local = installedLocal() !== null

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
              {LABELS[item]}
            </button>
          ))}
        </div>
        <p className="note">{t("foreignNote")}</p>
        {!local && <p className="error">{t("foreignDesktop")}</p>}
        <ForeignEditor key={language} language={language} source={source} onChange={edit} />
        <div className="foreign-actions">
          <button type="button" onClick={() => void copy()}>
            {copied ? t("copied") : t("copy")}
          </button>
          <button className="primary" type="button" onClick={() => void run()} disabled={!local || busy}>
            {busy && !waiting ? t("foreignRunning") : t("run")}
          </button>
          {runtimeNote && <p>{runtimeNote}</p>}
        </div>
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
