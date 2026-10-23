import { Component, StrictMode, type ErrorInfo, type ReactNode } from "react"
import { createRoot } from "react-dom/client"

import { App } from "./App"
import { readStoredLocale, translate } from "./i18n"
import { Logo } from "./shell/Logo"
import "./styles.css"

class RootError extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null }

  static getDerivedStateFromError(error: Error) {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(error, info.componentStack)
  }

  render() {
    if (!this.state.error) return this.props.children
    return (
      <div className="app-frame">
        <main className="auth">
          <section className="card">
            <h1><Logo /></h1>
            <p>{this.state.error.message}</p>
            <button type="button" onClick={() => window.location.reload()}>
              Reintentar
            </button>
          </section>
        </main>
        <footer className="app-legal">
          {translate(readStoredLocale(), "rights", { year: new Date().getFullYear() })}
        </footer>
      </div>
    )
  }
}

const root = document.getElementById("root")
if (!root) throw new Error("No está el contenedor de la aplicación.")
createRoot(root).render(
  <StrictMode>
    <RootError>
      <App />
    </RootError>
  </StrictMode>,
)
