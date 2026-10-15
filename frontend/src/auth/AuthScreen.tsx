import { useEffect, useState, type FormEvent } from "react"

import { api, ApiError, type Account, type PendingConfirmation, type Role } from "../api"
import { useT } from "../i18n"

type Mode = "entrar" | "crear" | "recuperar"

function isPending(value: Account | PendingConfirmation): value is PendingConfirmation {
  return "pending_confirmation" in value && value.pending_confirmation
}

export function AuthScreen({ onSuccess }: { onSuccess: (account: Account) => void }) {
  const t = useT()
  const [mode, setMode] = useState<Mode>("entrar")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [displayName, setDisplayName] = useState("")
  const [role, setRole] = useState<Role>("student")
  const [message, setMessage] = useState("")
  const [error, setError] = useState("")
  const [pendingEmail, setPendingEmail] = useState("")
  const [confirming, setConfirming] = useState(false)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const uid = params.get("confirmar")
    const token = params.get("token")
    if (!uid || !token) return
    setConfirming(true)
    setError("")
    void api
      .confirmEmail(uid, token)
      .then((account) => {
        window.history.replaceState({}, "", window.location.pathname)
        onSuccess(account)
      })
      .catch((caught: unknown) => {
        const failure = caught instanceof ApiError ? caught : null
        if (failure?.code === "already_confirmed") {
          window.history.replaceState({}, "", window.location.pathname)
          setMode("entrar")
          setMessage(failure.message)
        } else {
          setError(failure?.message ?? t("confirmError"))
        }
      })
      .finally(() => setConfirming(false))
  }, [onSuccess])

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
    setError("")
    setMessage("")
    setPendingEmail("")
    try {
      if (mode === "entrar") onSuccess(await api.login({ email, password }))
      if (mode === "crear") {
        const created = await api.register({ email, password, display_name: displayName, role })
        if (isPending(created)) {
          setPendingEmail(email)
          setMessage(created.message)
          return
        }
        onSuccess(created)
      }
      if (mode === "recuperar") {
        const result = await api.reset(email)
        setMessage(result.message)
      }
    } catch (caught) {
      if (caught instanceof ApiError && caught.code === "email_unconfirmed") {
        setPendingEmail(email)
      }
      setError(caught instanceof ApiError ? caught.message : t("requestError"))
    }
  }

  return (
    <main className="auth">
      <section className="card">
        <h1>Traza</h1>
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
          {confirming && <p className="note">{t("confirming")}</p>}
          {error && <p className="error">{error}</p>}
          {message && <p className="note">{message}</p>}
          {pendingEmail && (
            <button type="button" onClick={() => void resend()}>
              {t("resend")}
            </button>
          )}
          <button className="primary" type="submit">
            {mode === "entrar" ? t("signIn") : mode === "crear" ? t("createAccount") : t("sendInstructions")}
          </button>
        </form>
      </section>
    </main>
  )
}
