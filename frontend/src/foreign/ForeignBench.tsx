import { useEffect, useState } from "react"

import { ApiError, type Account } from "../api"
import { translatedMessage, useT } from "../i18n"
import { installedLocal, localForeignRun, localForeignStatus, type ForeignRun } from "../runtime"
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
  const [copied, setCopied] = useState(false)
  const [failure, setFailure] = useState("")
  const [result, setResult] = useState<ForeignRun | null>(null)
  const [ready, setReady] = useState<Record<string, string>>({})
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

  function choose(next: ForeignLanguage) {
    drafts.set(language, source)
    setLanguage(next)
    setSource(draftOf(next))
    setCopied(false)
    setResult(null)
    setFailure("")
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
    setBusy(true)
    setFailure("")
    setResult(null)
    try {
      const payload = await localForeignRun(language, source, stdin)
      setResult(payload)
      if (payload.via === "cached" || payload.via === "system") {
        setReady((current) => ({ ...current, [language]: payload.via }))
      }
    } catch (caught) {
      setFailure(caught instanceof ApiError ? translatedMessage(caught.message) : t("foreignFailed"))
    } finally {
      setBusy(false)
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
          <label>
            {t("foreignInput")}
            <textarea
              value={stdin}
              spellCheck={false}
              rows={2}
              onChange={(event) => setStdin(event.target.value)}
            />
          </label>
          <button type="button" onClick={() => void copy()}>
            {copied ? t("copied") : t("copy")}
          </button>
          <button className="primary" type="button" onClick={() => void run()} disabled={!local || busy}>
            {busy ? t("foreignRunning") : t("run")}
          </button>
          {runtimeNote && <p>{runtimeNote}</p>}
        </div>
        {failure && <p className="error">{failure}</p>}
        {result?.message && <p className="error">{translatedMessage(result.message)}</p>}
        <pre className="foreign-output" aria-label={t("console")}>
          {result ? `${result.stderr}${result.stdout}` : ""}
        </pre>
      </div>
    </div>
  )
}
