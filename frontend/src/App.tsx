import { useCallback, useEffect, useState } from "react"

import { api, asAccount, ensureCsrf, type Account } from "./api"
import { AuthScreen } from "./auth/AuthScreen"
import { AdminHome } from "./admin/AdminHome"
import { Composer, type DiagramRequest } from "./compose/Composer"
import { LocaleProvider, readStoredLocale, storeLocale, translate, type Locale } from "./i18n"
import { LearningLab } from "./learning/LearningLab"
import { inInstalledApp, installedLocal, rememberAccess } from "./runtime"
import { AccountOnly } from "./shell/AccountOnly"
import { Workbench } from "./workbench/Workbench"

export function App() {
  const [account, setAccount] = useState<Account | null>(null)
  const [ready, setReady] = useState(false)
  const [screen, setScreen] = useState<"editor" | "lab" | "compose">("editor")
  const [diagramRequest, setDiagramRequest] = useState<DiagramRequest | null>(null)
  const [editorFocus, setEditorFocus] = useState<{ projectId: string; algorithmId: string; token: number } | null>(null)
  const [locale, setLocale] = useState<Locale>(readStoredLocale)
  const applyLocale = useCallback((next: Locale) => {
    storeLocale(next)
    setLocale(next)
  }, [])
  const holdAccount = useCallback((next: Account) => {
    setAccount(asAccount(next))
  }, [])

  useEffect(() => {
    void ensureCsrf()
      .then(() => api.me())
      .then(holdAccount)
      .catch(() => undefined)
      .finally(() => setReady(true))
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
    <AuthScreen onSuccess={holdAccount} />
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
  return <LocaleProvider locale={locale}>{shell}</LocaleProvider>
}
