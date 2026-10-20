import { useCallback, useEffect, useState } from "react"

import { api, ApiError, asAccount, ensureCsrf, isAccount, type Account } from "./api"
import { AuthScreen } from "./auth/AuthScreen"
import { AdminHome } from "./admin/AdminHome"
import { Composer, type DiagramRequest } from "./compose/Composer"
import { LocaleProvider, readStoredLocale, storeLocale, translate, translatedMessage, type Locale } from "./i18n"
import { LearningLab } from "./learning/LearningLab"
import { inInstalledApp, installedLocal, launchSearch, rememberAccess } from "./runtime"
import { AccountOnly } from "./shell/AccountOnly"
import { Workbench } from "./workbench/Workbench"

export function App() {
  const [account, setAccount] = useState<Account | null>(null)
  const [ready, setReady] = useState(false)
  const [screen, setScreen] = useState<"editor" | "lab" | "compose">("editor")
  const [diagramRequest, setDiagramRequest] = useState<DiagramRequest | null>(null)
  const [editorFocus, setEditorFocus] = useState<{ projectId: string; algorithmId: string; token: number } | null>(null)
  const [locale, setLocale] = useState<Locale>(readStoredLocale)
  const [notice, setNotice] = useState("")
  const applyLocale = useCallback((next: Locale) => {
    storeLocale(next)
    setLocale(next)
  }, [])
  const holdAccount = useCallback((next: Account) => {
    setAccount(asAccount(next))
  }, [])

  useEffect(() => {
    function onEnd(event: Event) {
      const detail = (event as CustomEvent<string>).detail
      setAccount(null)
      setNotice(
        typeof detail === "string" && detail
          ? translatedMessage(detail)
          : translate(readStoredLocale(), "sessionIdle"),
      )
      setReady(true)
      setScreen("editor")
    }
    window.addEventListener("traza-session-end", onEnd)
    return () => window.removeEventListener("traza-session-end", onEnd)
  }, [])

  useEffect(() => {
    let ignore = false
    async function start(search: string) {
      const params = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search)
      const uid = params.get("confirmar")
      const token = params.get("token")
      if (params.get("correo") === "confirmado") {
        window.history.replaceState({}, "", window.location.pathname)
        if (!ignore) setNotice(translate(readStoredLocale(), "emailConfirmedAnywhere"))
      }
      if (params.get("sesion") === "abierta") {
        window.history.replaceState({}, "", window.location.pathname)
        if (!ignore) setNotice(translate(readStoredLocale(), "sessionOpen"))
      }
      try {
        await ensureCsrf()
        if (uid && token) {
          const result = await api.confirmEmail(uid, token)
          window.history.replaceState({}, "", window.location.pathname)
          if (isAccount(result)) {
            if (!ignore) holdAccount(result)
            return
          }
          if (!ignore) setNotice(translatedMessage(result.message))
        }
        const current = await api.me()
        if (!ignore) holdAccount(current)
      } catch (caught) {
        if (!ignore && uid && token) {
          window.history.replaceState({}, "", window.location.pathname)
          const failure = caught instanceof ApiError ? caught : null
          setNotice(translatedMessage(failure?.message ?? translate(readStoredLocale(), "confirmError")))
          try {
            const current = await api.me()
            if (!ignore) holdAccount(current)
          } catch {
            /* sin sesión: la pantalla de entrada muestra el aviso */
          }
        }
      } finally {
        if (!ignore) setReady(true)
      }
    }
    void start(launchSearch())
    function onLaunch() {
      const search = launchSearch()
      if (!search.includes("confirmar=")) return
      void start(search)
    }
    window.addEventListener("traza-launch", onLaunch)
    return () => {
      ignore = true
      window.removeEventListener("traza-launch", onLaunch)
    }
  }, [holdAccount])

  useEffect(() => {
    if (!account || !installedLocal()) return
    void rememberAccess(account.access).catch(() => undefined)
  }, [account])

  async function logout() {
    await api.logout()
    setAccount(null)
    setDiagramRequest(null)
    setEditorFocus(null)
    setScreen("editor")
  }

  function backToEditor() {
    setScreen("editor")
    requestAnimationFrame(() => window.dispatchEvent(new Event("resize")))
  }

function openCompose(payload: { name?: string; source?: string; semicolons: boolean }) {
  setDiagramRequest({ ...payload, token: Date.now() })
  setScreen("compose")
}

  function openInEditor(target: { projectId: string; algorithmId: string }) {
    setEditorFocus({ ...target, token: Date.now() })
    backToEditor()
  }

  const shell = !ready ? (
    <main className="auth"><p>{translate(locale, "loading")}</p></main>
  ) : !account ? (
    <AuthScreen
      onSuccess={(next) => {
        setNotice("")
        holdAccount(next)
      }}
      notice={notice}
    />
  ) : account.role === "admin" ? (
    <AdminHome account={account} onAccount={holdAccount} onLogout={() => void logout()} />
  ) : !inInstalledApp() && !account.access?.browser_app ? (
    <AccountOnly account={account} onAccount={holdAccount} onLogout={() => void logout()} />
  ) : (
    <>
      <div className="screen-slot" hidden={screen !== "editor"}>
        <Workbench
          key={account.id}
          account={account}
          onAccount={holdAccount}
          onLogout={() => void logout()}
          onOpenLab={() => setScreen("lab")}
          onOpenCompose={openCompose}
          focus={editorFocus}
          onLocale={applyLocale}
        />
      </div>
      {screen === "lab" && (
        <LearningLab account={account} onAccount={holdAccount} onBack={backToEditor} />
      )}
      <div className="screen-slot" hidden={screen !== "compose"}>
        <Composer account={account} onAccount={holdAccount} active={screen === "compose"} incoming={diagramRequest} onBack={backToEditor} onOpenInEditor={openInEditor} />
      </div>
    </>
  )
  return (
    <LocaleProvider locale={locale}>
      {account && notice ? (
        <p className="confirm-banner" role="status">
          {notice}
        </p>
      ) : null}
      {shell}
    </LocaleProvider>
  )
}
