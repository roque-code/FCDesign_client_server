import { useEffect, useRef, useState } from "react"

import { accessOf, api, ApiError, type Account } from "../api"
import { translatedMessage, useT } from "../i18n"
import { AccountIdentity } from "../shell/Identity"
import { Logo } from "../shell/Logo"
import { SUBJECTS, type SubjectId } from "./catalog"
import "./subject.css"

export function SubjectHome({
  account,
  onAccount,
  onLogout,
  onOpenCommunities,
  onEnter,
}: {
  account: Account
  onAccount: (account: Account) => void
  onLogout: () => void
  onOpenCommunities: () => void
  onEnter: (id: SubjectId) => void
}) {
  const t = useT()
  const access = accessOf(account)
  const joinRef = useRef<HTMLDivElement>(null)
  const [joinOpen, setJoinOpen] = useState(false)
  const [joinCode, setJoinCode] = useState("")
  const [joinError, setJoinError] = useState("")
  const [joinMessage, setJoinMessage] = useState("")
  const canJoin = account.role === "student" || account.role === "teacher"
  const canManage = account.role === "teacher" && access.features.communities === true

  useEffect(() => {
    if (!joinOpen) return
    function close(event: MouseEvent) {
      if (joinRef.current?.contains(event.target as Node)) return
      setJoinOpen(false)
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setJoinOpen(false)
    }
    document.addEventListener("mousedown", close)
    document.addEventListener("keydown", onKey)
    return () => {
      document.removeEventListener("mousedown", close)
      document.removeEventListener("keydown", onKey)
    }
  }, [joinOpen])

  return (
    <div className="shell subject-shell">
      <header className="topbar topbar-editor">
        <div className="brand">
          <h1>
            <Logo />
          </h1>
          <AccountIdentity account={account} onAccount={onAccount} />
        </div>
        <div className="actions">
          {canJoin ? (
            <div className="functions" ref={joinRef}>
              <button
                className="top-action"
                type="button"
                aria-expanded={joinOpen}
                onClick={() => {
                  setJoinError("")
                  setJoinMessage("")
                  setJoinOpen((open) => !open)
                }}
              >
                {t("joinCommunity")}
              </button>
              {joinOpen ? (
                <form
                  className="functions-menu"
                  role="dialog"
                  aria-label={t("joinCommunityTitle")}
                  onSubmit={(event) => {
                    event.preventDefault()
                    setJoinError("")
                    setJoinMessage("")
                    void api
                      .joinCommunity(joinCode.trim())
                      .then((joined) => {
                        setJoinMessage(t("joinedCommunity", { name: joined.name }))
                        setJoinCode("")
                      })
                      .catch((caught: unknown) => {
                        setJoinError(caught instanceof ApiError ? translatedMessage(caught.message) : t("joinFailed"))
                      })
                  }}
                >
                  <h2>{t("joinCommunityTitle")}</h2>
                  <p className="note">{t("joinCommunityNote")}</p>
                  <label>
                    {t("joinCode")}
                    <input
                      value={joinCode}
                      autoComplete="off"
                      spellCheck={false}
                      maxLength={12}
                      onChange={(event) => setJoinCode(event.target.value)}
                      required
                    />
                  </label>
                  {joinMessage ? <p className="note">{joinMessage}</p> : null}
                  {joinError ? <p className="error">{joinError}</p> : null}
                  <button className="primary" type="submit">
                    {t("joinCommunity")}
                  </button>
                </form>
              ) : null}
            </div>
          ) : null}
          {canManage ? (
            <button className="top-action" type="button" onClick={onOpenCommunities}>
              {t("communities")}
            </button>
          ) : null}
          <button className="top-leave" type="button" onClick={onLogout}>
            {t("leave")}
          </button>
        </div>
      </header>
      <div className="subject-home">
        <div className="subject-home-inner">
          <h2>{t("subjectsTitle")}</h2>
          <p className="note">{t("subjectsLead")}</p>
          <div className="subject-grid">
            {SUBJECTS.map((item) =>
              item.open ? (
                <button key={item.id} className="subject-card" type="button" onClick={() => onEnter(item.id)}>
                  <strong>{t(item.nameKey)}</strong>
                  {item.noteKey ? <span>{t(item.noteKey)}</span> : null}
                  <span className="subject-enter">{t("subjectEnter")}</span>
                </button>
              ) : (
                <article key={item.id} className="subject-card subject-card-quiet">
                  <strong>{t(item.nameKey)}</strong>
                  <span>{t("subjectClosed")}</span>
                </article>
              ),
            )}
          </div>
          <p className="note">{t("subjectsAside")}</p>
        </div>
      </div>
    </div>
  )
}
