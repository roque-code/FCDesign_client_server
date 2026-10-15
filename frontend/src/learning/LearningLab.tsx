import { useState } from "react"

import { type Account } from "../api"
import { useT } from "../i18n"
import { AccountIdentity } from "../shell/Identity"
import { BankView } from "./BankView"
import { ChallengePlay } from "./ChallengePlay"
import { PathHome } from "./PathHome"
import { PracticeLab } from "./PracticeLab"
import { TeacherPaths } from "./TeacherPaths"
import { TeacherRoster } from "./TeacherRoster"
import "./lab.css"

type Mode = "path" | "practice" | "challenge" | "roster" | "routes" | "bank"

export function LearningLab({
  account,
  onAccount,
  onBack,
}: {
  account: Account
  onAccount: (account: Account) => void
  onBack: () => void
}) {
  const t = useT()
  const [mode, setMode] = useState<Mode>("path")
  const [challengeId, setChallengeId] = useState<string | null>(null)
  const [pathId, setPathId] = useState<string | null>(null)

  return (
    <div className="shell lab">
      <header className="topbar topbar-editor">
        <div className="brand">
          <h1>{t("lab")}</h1>
          <AccountIdentity account={account} />
        </div>
        <div className="actions">
          <button
            className="top-action"
            type="button"
            aria-current={mode === "path" || mode === "challenge" ? "page" : undefined}
            onClick={() => setMode("path")}
          >
            {t("route")}
          </button>
          <button
            className="top-action"
            type="button"
            aria-current={mode === "practice" ? "page" : undefined}
            onClick={() => setMode("practice")}
          >
            {t("freePractice")}
          </button>
          {account.role === "teacher" ? (
            <button
              className="top-action"
              type="button"
              aria-current={mode === "bank" ? "page" : undefined}
              onClick={() => setMode("bank")}
            >
              {t("bank")}
            </button>
          ) : null}
          {account.role === "teacher" ? (
            <button
              className="top-action"
              type="button"
              aria-current={mode === "routes" ? "page" : undefined}
              onClick={() => setMode("routes")}
            >
              {t("routes")}
            </button>
          ) : null}
          {account.role === "teacher" ? (
            <button
              className="top-action"
              type="button"
              aria-current={mode === "roster" ? "page" : undefined}
              onClick={() => setMode("roster")}
            >
              {t("progress")}
            </button>
          ) : null}
          <button className="top-leave" type="button" onClick={onBack}>
            {t("backToEditor")}
          </button>
        </div>
      </header>
      {mode === "practice" ? <PracticeLab /> : null}
      {mode === "challenge" && challengeId ? (
        <ChallengePlay
          key={challengeId}
          challengeId={challengeId}
          pathId={pathId ?? undefined}
          onStanding={(standing) => onAccount({ ...account, ...standing })}
          onDone={() => {
            setChallengeId(null)
            setMode("path")
          }}
        />
      ) : null}
      {mode === "roster" && account.role === "teacher" ? <TeacherRoster /> : null}
      {mode === "routes" && account.role === "teacher" ? <TeacherPaths /> : null}
      {mode === "bank" && account.role === "teacher" ? <BankView /> : null}
      {mode === "path" ? (
        <PathHome
          initialPathId={pathId}
          onOpen={(id, selectedPath) => {
            setChallengeId(id)
            setPathId(selectedPath)
            setMode("challenge")
          }}
        />
      ) : null}
    </div>
  )
}
