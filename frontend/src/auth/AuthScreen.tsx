import { useEffect, useState, type FormEvent } from "react"

import { api, ApiError, type Account, type PendingConfirmation, type Role } from "../api"
import { useT, translatedMessage } from "../i18n"
import { launchSearch } from "../runtime"
import { Logo } from "../shell/Logo"

type Mode = "entrar" | "crear" | "recuperar" | "nueva"

const PENDING_KEY = "traza-pending-confirmation"

function isPending(value: Account | PendingConfirmation): value is PendingConfirmation {
  return "pending_confirmation" in value && value.pending_confirmation
}

function readPending(): { email: string; message: string } | null {
  try {
    const raw = sessionStorage.getItem(PENDING_KEY)
    if (!raw) return null
    const data = JSON.parse(raw) as { email?: string; message?: string }
    if (!data.email || !data.message) return null
    return { email: data.email, message: data.message }
  } catch {
    return null
  }
}

function readLaunch(): URLSearchParams {
  const raw = launchSearch()
  return new URLSearchParams(raw.startsWith("?") ? raw.slice(1) : raw)
}

export function AuthScreen({
  onSuccess,
  notice = "",
  locked = false,
}: {
  onSuccess: (account: Account) => void
  notice?: string
  locked?: boolean
}) {
  const t = useT()
  const launch = readLaunch()
  const resetUid = launch.get("restablecer")
  const resetToken = launch.get("token")
  const storedPending = readPending()
  const [mode, setMode] = useState<Mode>(resetUid && resetToken ? "nueva" : "entrar")
  const [email, setEmail] = useState(storedPending?.email ?? "")
  const [password, setPassword] = useState("")
  const [displayName, setDisplayName] = useState("")
  const [role, setRole] = useState<Role>("student")
  const [message, setMessage] = useState(storedPending?.message || notice)
  const [error, setError] = useState("")
  const [pendingEmail, setPendingEmail] = useState(storedPending?.email ?? "")
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (notice) setMessage(notice)
  }, [notice])

  async function resend() {
    setError("")
    try {
      const result = await api.resendConfirmation(pendingEmail || email)
      setMessage(result.message)
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t("resendError"))
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (busy) return
    setBusy(true)
    setError("")
    setMessage("")
    setPendingEmail("")
    try {
      if (mode === "nueva") {
        if (!resetUid || !resetToken) return
        await api.confirmReset(resetUid, resetToken, password)
        window.history.replaceState({}, "", window.location.pathname)
        setPassword("")
        setMode("entrar")
        setMessage(t("passwordUpdated"))
        return
      }
      if (mode === "entrar") {
        const account = await api.login({ email, password })
        sessionStorage.removeItem(PENDING_KEY)
        onSuccess(account)
      } else if (mode === "crear") {
        const created = await api.register({ email, password, display_name: displayName, role })
        if (isPending(created)) {
          sessionStorage.setItem(PENDING_KEY, JSON.stringify({ email, message: created.message }))
          setPendingEmail(email)
          setMessage(created.message)
          return
        }
        sessionStorage.removeItem(PENDING_KEY)
        onSuccess(created)
      } else if (mode === "recuperar") {
        const result = await api.reset(email)
        setMessage(result.message)
      }
    } catch (caught) {
      if (caught instanceof ApiError && caught.code === "email_unconfirmed") {
        const text = translatedMessage(caught.message)
        sessionStorage.setItem(PENDING_KEY, JSON.stringify({ email, message: text }))
        setPendingEmail(email)
        setMessage(text)
        return
      }
      const detail = caught instanceof Error ? caught.message : ""
      setError(caught instanceof ApiError ? translatedMessage(caught.message) : detail || t("requestError"))
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="auth">
      <section className="card">
        <h1><Logo /></h1>
        {locked ? (
          message ? <p className="note" role="status">{message}</p> : null
        ) : pendingEmail ? (
        <>
        <p className="note" role="status">{message}</p>
        <p className="note">{pendingEmail}</p>
        <button type="button" onClick={() => void resend()}>
          {t("resend")}
        </button>
        <button className="primary" type="button" onClick={() => { setPendingEmail(""); setMode("entrar") }}>
          {t("signIn")}
        </button>
        </>
        ) : (
        <>
        <p className="note">{t("authNote")}</p>
        <div className="tabs" role="tablist">
          <button type="button" aria-selected={mode === "entrar"} onClick={() => setMode("entrar")}>
            {t("signIn")}
          </button>
          <button type="button" aria-selected={mode === "crear"} onClick={() => setMode("crear")}>
            {t("createAccount")}
          </button>
          <button type="button" aria-selected={mode === "recuperar"} onClick={() => setMode("recuperar")}>
            {t("recover")}
          </button>
        </div>
        <form onSubmit={submit}>
          {mode === "crear" && (
            <>
              <label>
                {t("visibleName")}
                <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
              </label>
              <label>
                {t("profile")}
                <select aria-label={t("profile")} value={role} onChange={(event) => setRole(event.target.value as Role)}>
                  <option value="student">{t("student")}</option>
                  <option value="teacher">{t("teacher")}</option>
                </select>
              </label>
            </>
          )}
          {mode !== "nueva" && (
          <label>
            {t("email")}
            <input
              type="email"
              autoComplete="username"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>
          )}
          {mode !== "recuperar" && (
            <label>
              {t("password")}
              <input
                type="password"
                autoComplete={mode === "crear" ? "new-password" : "current-password"}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </label>
          )}
          {error && <p className="error">{error}</p>}
          {message && <p className="note">{message}</p>}
          {pendingEmail && (
            <button type="button" onClick={() => void resend()}>
              {t("resend")}
            </button>
          )}
          <button className="primary" type="submit" disabled={busy}>
            {busy ? "…" : mode === "entrar" ? t("signIn") : mode === "crear" ? t("createAccount") : mode === "nueva" ? t("password") : t("sendInstructions")}
          </button>
        </form>
        </>
        )}
      </section>
    </main>
  )
}
