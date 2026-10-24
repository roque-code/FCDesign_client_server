import { useEffect, useRef, useState, type MouseEvent } from "react"

import { ApiError } from "../api"
import { translatedMessage, useT } from "../i18n"
import { installedLocal, localForeignRun, localForeignStatus, type ForeignRun } from "../runtime"
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

export function ForeignBench({ onClose }: { onClose: () => void }) {
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
  const armed = useRef(false)

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose()
    }
    function arm() {
      armed.current = true
    }
    window.addEventListener("keydown", onKey)
    window.addEventListener("pointerup", arm)
    window.addEventListener("pointercancel", arm)
    return () => {
      window.removeEventListener("keydown", onKey)
      window.removeEventListener("pointerup", arm)
      window.removeEventListener("pointercancel", arm)
    }
  }, [onClose])

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

  function dismissBackdrop(event: MouseEvent<HTMLDivElement>) {
    if (!armed.current || event.target !== event.currentTarget) return
    onClose()
  }

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
    <div className="foreign-backdrop" role="presentation" onMouseDown={dismissBackdrop} onClick={dismissBackdrop}>
      <section
        className="foreign-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="foreign-title"
        onMouseDown={(event) => event.stopPropagation()}
        onClick={(event) => event.stopPropagation()}
      >
        <header>
          <h2 id="foreign-title">{t("foreignTitle")}</h2>
          <button type="button" onClick={onClose}>
            {t("close")}
          </button>
        </header>
        <p>{t("foreignNote")}</p>
        {!local && <p className="error">{t("foreignDesktop")}</p>}
        <div className="foreign-tabs" role="tablist">
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
        </div>
        {runtimeNote && <p>{runtimeNote}</p>}
        {failure && <p className="error">{failure}</p>}
        {result?.message && <p className="error">{translatedMessage(result.message)}</p>}
        {result && (result.stdout || result.stderr) && (
          <pre className="foreign-output" aria-label={t("console")}>
            {result.stderr}
            {result.stdout}
          </pre>
        )}
      </section>
    </div>
  )
}
