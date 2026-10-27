import { useEffect, useId, useRef, useState } from "react"

import { api, type LabPath } from "../api"
import { useT } from "../i18n"
import { acknowledge, noticeDiff, type ChallengeNotice, type SeenMark } from "./challengeNotices"

const STORAGE = "aulivana.challenge-notices."

export function ChallengeBell({ userId }: { userId: number }) {
  const t = useT()
  const panelId = useId()
  const rootRef = useRef<HTMLSpanElement>(null)
  const seenRef = useRef<Record<string, SeenMark> | null>(null)
  const pathsRef = useRef<LabPath[]>([])
  const [open, setOpen] = useState(false)
  const [notices, setNotices] = useState<ChallengeNotice[]>([])

  useEffect(() => {
    let cancelled = false
    async function refresh() {
      try {
        const payload = await api.labPaths()
        if (cancelled) return
        const result = noticeDiff(readSeen(userId), payload.results)
        writeSeen(userId, result.seen)
        seenRef.current = result.seen
        pathsRef.current = payload.results
        setNotices(result.notices)
      } catch {
        if (!cancelled) setNotices([])
      }
    }
    void refresh()
    const timer = window.setInterval(() => void refresh(), 60_000)
    const onFocus = () => {
      if (document.visibilityState === "hidden") return
      void refresh()
    }
    window.addEventListener("focus", onFocus)
    document.addEventListener("visibilitychange", onFocus)
    return () => {
      cancelled = true
      window.clearInterval(timer)
      window.removeEventListener("focus", onFocus)
      document.removeEventListener("visibilitychange", onFocus)
    }
  }, [userId])

  useEffect(() => {
    if (!open) return
    function onPointer(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false)
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false)
    }
    document.addEventListener("mousedown", onPointer)
    document.addEventListener("keydown", onKey)
    return () => {
      document.removeEventListener("mousedown", onPointer)
      document.removeEventListener("keydown", onKey)
    }
  }, [open])

  function markRead() {
    const next = acknowledge(pathsRef.current, seenRef.current ?? {})
    writeSeen(userId, next)
    seenRef.current = next
    setNotices([])
    setOpen(false)
  }

  const count = notices.length
  return (
    <span className="notice-bell" ref={rootRef}>
      <button
        type="button"
        className={count > 0 ? "has-notices" : ""}
        aria-label={count > 0 ? t("noticeBellCount", { count }) : t("noticeBell")}
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((value) => !value)}
      >
        <BellMark />
        {count > 0 ? <span className="notice-badge">{count > 9 ? "9+" : count}</span> : null}
      </button>
      {open ? (
        <div className="notice-panel" id={panelId} role="region" aria-label={t("noticeBell")}>
          {count === 0 ? <p>{t("noticeEmpty")}</p> : null}
          {count > 0 ? (
            <ul>
              {notices.map((item) => (
                <li key={item.id}>
                  <strong>{item.title}</strong>
                  <span>{item.kind === "new" ? t("noticeNew") : t("noticeEnabled")}</span>
                  <span>{t("noticeOnPath", { path: item.pathName })}</span>
                </li>
              ))}
            </ul>
          ) : null}
          {count > 0 ? (
            <button type="button" onClick={markRead}>
              {t("noticeMarkRead")}
            </button>
          ) : null}
        </div>
      ) : null}
    </span>
  )
}

function BellMark() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 3.1a4.8 4.8 0 0 0-4.8 4.8v2.6c0 .8-.3 1.6-.8 2.2L5 15.4h14l-1.4-2.7a3.4 3.4 0 0 1-.8-2.2V7.9A4.8 4.8 0 0 0 12 3.1Z" />
      <path d="M9.5 16.2a2.5 2.5 0 0 0 5 0H9.5Z" />
    </svg>
  )
}

function readSeen(userId: number): Record<string, SeenMark> | null {
  try {
    const raw = localStorage.getItem(STORAGE + userId)
    if (!raw) return null
    const parsed = JSON.parse(raw) as unknown
    if (!parsed || typeof parsed !== "object") return null
    return parsed as Record<string, SeenMark>
  } catch {
    return null
  }
}

function writeSeen(userId: number, seen: Record<string, SeenMark>) {
  try {
    localStorage.setItem(STORAGE + userId, JSON.stringify(seen))
  } catch {
    // El aviso se vuelve a calcular en la siguiente visita.
  }
}
