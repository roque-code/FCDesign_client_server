import { useState } from "react"

import { accessOf, type Account } from "../api"
import { useT } from "../i18n"
import { AccountIdentity } from "../shell/Identity"
import { Logo } from "../shell/Logo"
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
  const access = accessOf(account)
  const [mode, setMode] = useState<Mode>("path")
  const [challengeId, setChallengeId] = useState<string | null>(null)
  const [pathId, setPathId] = useState<string | null>(null)
  const [reloadToken, setReloadToken] = useState(0)

  return (
    <div className="shell lab">
      <header className="topbar topbar-editor">
        <div className="brand">
          <h1><Logo mark />{t("lab")}</h1>
          <AccountIdentity account={account} onAccount={onAccount} />
        </div>
        <div className="actions">
          <button
            className="top-action"
            type="button"
            aria-current={mode === "path" || mode === "challenge" ? "page" : undefined}
            hidden={!access.features.lab_route}
            onClick={() => setMode("path")}
          >
            {t("route")}
          </button>
          <button
            className="top-action"
            type="button"
            aria-current={mode === "practice" ? "page" : undefined}
            hidden={!access.features.lab_practice}
            onClick={() => setMode("practice")}
          >
            {t("freePractice")}
          </button>
          {account.role === "teacher" && access.features.lab_bank ? (
            <button
              className="top-action"
              type="button"
              aria-current={mode === "bank" ? "page" : undefined}
              onClick={() => setMode("bank")}
            >
              {t("bank")}
            </button>
          ) : null}
          {account.role === "teacher" && access.features.lab_routes ? (
            <button
              className="top-action"
              type="button"
              aria-current={mode === "routes" ? "page" : undefined}
              onClick={() => setMode("routes")}
            >
              {t("routes")}
            </button>
          ) : null}
          {account.role === "teacher" && access.features.lab_progress ? (
            <button
              className="top-action"
              type="button"
              aria-current={mode === "roster" ? "page" : undefined}
              onClick={() => setMode("roster")}
            >
              {t("progress")}
            </button>
          ) : null}
          <button className="top-action" type="button" onClick={() => setReloadToken((token) => token + 1)}>
            {t("refresh")}
          </button>
          <button className="top-leave" type="button" onClick={onBack}>
            {t("backToEditor")}
          </button>
        </div>
      </header>
      {mode === "practice" ? <PracticeLab key={reloadToken} /> : null}
      {mode === "challenge" && challengeId ? (
        <ChallengePlay
          key={`${challengeId}-${reloadToken}`}
          challengeId={challengeId}
          pathId={pathId ?? undefined}
          onStanding={(standing) => onAccount({ ...account, ...standing })}
          pasteBlocked={account.role !== "teacher" && account.paste_enabled === false}
          onDone={() => {
            setChallengeId(null)
            setMode("path")
          }}
        />
      ) : null}
      {mode === "roster" && account.role === "teacher" ? <TeacherRoster key={reloadToken} /> : null}
      {mode === "routes" && account.role === "teacher" ? <TeacherPaths key={reloadToken} /> : null}
      {mode === "bank" && account.role === "teacher" ? <BankView key={reloadToken} /> : null}
      {mode === "path" ? (
        <PathHome
          key={reloadToken}
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
