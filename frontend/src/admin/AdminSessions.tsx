import { useEffect, useRef, useState } from "react"

import { ApiError, api, type AccountRole, type ConnectedAccount } from "../api"
import { useT } from "../i18n"

export function AdminSessions() {
  const t = useT()
  const [rows, setRows] = useState<ConnectedAccount[]>([])
  const [count, setCount] = useState(0)
  const [fetchedAt, setFetchedAt] = useState(Date.now())
  const [now, setNow] = useState(Date.now())
  const [error, setError] = useState("")
  const origins = useRef(new Map<number, number>())

  async function refresh() {
    try {
      const listed = await api.connectedAccounts()
      setRows(listed.results)
      setCount(listed.count)
      setFetchedAt(Date.now())
      setError("")
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t("requestError"))
    }
  }

  useEffect(() => {
    void refresh()
    const pull = window.setInterval(() => void refresh(), 15000)
    const tick = window.setInterval(() => setNow(Date.now()), 1000)
    return () => {
      window.clearInterval(pull)
      window.clearInterval(tick)
    }
  }, [])

  useEffect(() => {
    const live = new Set(rows.map((row) => row.id))
    for (const id of origins.current.keys()) {
      if (!live.has(id)) origins.current.delete(id)
    }
  }, [rows])

  return (
    <section className="session-board">
      <header className="admin-head">
        <div>
          <h2>{t("connected")}</h2>
          <p className="note">{t("connectedHint")}</p>
          <p className="note">{count === 1 ? t("connectedCountOne") : t("connectedCount", { count })}</p>
        </div>
        <button type="button" onClick={() => void refresh()}>
          {t("refresh")}
        </button>
      </header>
      {error ? <p className="error">{error}</p> : null}
      {rows.length === 0 ? (
        <p className="note">{t("nobodyConnected")}</p>
      ) : (
        <div className="table-scroll">
          <table className="account-table">
            <thead>
              <tr>
                <th>{t("nameWord")}</th>
                <th>{t("email")}</th>
                <th>{t("accountType")}</th>
                <th>{t("sessionSince")}</th>
                <th>{t("sessionLength")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const origin = sessionOrigin(row, fetchedAt, origins.current)
                const elapsed = Math.max(0, Math.floor((now - origin) / 1000))
                const clock = new Date(origin).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
                return (
                  <tr key={row.id}>
                    <td>{row.display_name}</td>
                    <td>{row.email}</td>
                    <td>{roleLabel(row.role, t)}</td>
                    <td>{clock}</td>
                    <td className="session-time">{formatSession(elapsed, t)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

function sessionOrigin(
  row: ConnectedAccount,
  fetchedAt: number,
  origins: Map<number, number>,
): number {
  const parsed = new Date(row.started_at).getTime()
  const inferred = fetchedAt - row.seconds * 1000
  let candidate = Number.isFinite(parsed) ? parsed : inferred
  if (Number.isFinite(inferred)) candidate = Math.min(candidate, inferred)
  const known = origins.get(row.id)
  const origin = known === undefined ? candidate : Math.min(known, candidate)
  origins.set(row.id, origin)
  return origin
}

function roleLabel(role: AccountRole, t: ReturnType<typeof useT>): string {
  if (role === "teacher") return t("teacher")
  if (role === "admin") return t("administrator")
  return t("student")
}

function formatSession(total: number, t: ReturnType<typeof useT>): string {
  const seconds = Math.max(0, total)
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (hours > 0) return t("sessionHours", { hours, minutes })
  if (minutes > 0) return t("sessionMinutes", { minutes })
  return t("sessionSeconds", { seconds })
}
