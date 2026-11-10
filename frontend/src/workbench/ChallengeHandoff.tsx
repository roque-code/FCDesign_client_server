import { useEffect, useState, type CSSProperties, type FormEvent } from "react"

import { ApiError, api, bumpRunUsage, type Account, type LabPath } from "../api"
import { translatedMessage, useT } from "../i18n"
import { inInstalledApp, localImport } from "../runtime"
import { handoffBlock, handoffResult, handoffTargets } from "./handoffRules"

const BLOCK_NOTE = {
  analysis: "pseudoAnalysisFirst",
  noCode: "pseudoNoCode",
  built: "pseudoAlreadyBuilt",
} as const

export function ChallengeHandoff({
  account,
  onAccount,
  source,
  beforeSend,
  style,
}: {
  account: Account
  onAccount: (account: Account) => void
  source: string
  beforeSend: () => Promise<void>
  style?: CSSProperties
}) {
  const t = useT()
  const [paths, setPaths] = useState<LabPath[] | null>(null)
  const [routeId, setRouteId] = useState("")
  const [challengeId, setChallengeId] = useState("")
  const [busy, setBusy] = useState(false)
  const [note, setNote] = useState("")
  const [failure, setFailure] = useState("")

  useEffect(() => {
    let alive = true
    void api.labPaths().then(
      (payload) => {
        if (alive) setPaths(payload.results)
      },
      (caught: unknown) => {
        if (alive) setFailure(caught instanceof ApiError ? translatedMessage(caught.message) : t("requestError"))
      },
    )
    return () => {
      alive = false
    }
  }, [])

  const route = paths?.find((item) => item.id === routeId) ?? null
  const targets = handoffTargets(route?.challenges ?? [])
  const target = targets.find((item) => item.id === challengeId) ?? null

  async function send(event: FormEvent) {
    event.preventDefault()
    if (!routeId || !target) {
      setFailure(t("languageChoose"))
      return
    }
    setNote("")
    setFailure("")
    if (!target.in_progress) {
      setNote(t("pseudoAnalysisFirst"))
      return
    }
    setBusy(true)
    try {
      await beforeSend()
      const session = await api.startAttempt(target.id, routeId)
      const block = handoffBlock(session)
      if (block) {
        setNote(t(BLOCK_NOTE[block]))
        return
      }
      const imported = inInstalledApp() ? await localImport(source) : await api.importLab(source)
      if (!imported.workspace) {
        const error = imported.diagnostics.find((item) => item.severity === "error")
        setNote(error ? translatedMessage(error.message) : t("notYetMatch"))
        return
      }
      const checked = await api.checkAttempt(session.attempt.id, imported.workspace, "codigo")
      if ((checked.cases ?? []).length > 0) onAccount(bumpRunUsage(account))
      const outcome = handoffResult(checked)
      setNote(
        outcome.kind === "passed"
          ? t("pseudoPassed")
          : outcome.kind === "cases"
            ? t("casesNeedAll", { done: outcome.done, total: outcome.total })
            : outcome.kind === "error"
              ? translatedMessage(outcome.message)
              : t("notYetMatch"),
      )
    } catch (caught) {
      setFailure(caught instanceof ApiError ? translatedMessage(caught.message) : t("requestError"))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="functions-menu challenge-handoff" role="dialog" aria-label={t("languageAttach")} style={style} onSubmit={(event) => void send(event)}>
      <h2>{t("languageAttach")}</h2>
      <p>{t("pseudoAttachNote")}</p>
      <label>
        {t("languageRoute")}
        <select
          value={routeId}
          onChange={(event) => {
            setRouteId(event.target.value)
            setChallengeId("")
            setNote("")
            setFailure("")
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
        <select
          value={challengeId}
          onChange={(event) => {
            setChallengeId(event.target.value)
            setNote("")
            setFailure("")
          }}
        >
          <option value="">{t("choose")}</option>
          {targets.map((item) => (
            <option key={item.id} value={item.id}>
              {item.title}
            </option>
          ))}
        </select>
      </label>
      {routeId && targets.length === 0 ? <p>{t("languageNoBuild")}</p> : null}
      {note ? <p role="status">{note}</p> : null}
      {failure ? <p className="error">{failure}</p> : null}
      <button className="primary" type="submit" disabled={busy || !challengeId}>
        {busy ? t("foreignRunning") : t("languageAttach")}
      </button>
    </form>
  )
}
