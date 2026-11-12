import { useCallback, useEffect, useRef, useState } from "react"
import { api, type ExerciseKind, type FocusEvent, type FocusReport } from "../api"
import { useT } from "../i18n"
import { awayClock, enterFullscreen, exitsLeft, fullscreenSupported, inFullscreen, leaveFullscreen } from "./watch"

const SETTLE_MS = 400

/**
 * Avisa al servidor cuando el alumno deja la plataforma y cuando vuelve.
 * Espera un momento antes de decidir para no contar los diálogos propios del navegador.
 */
export function useFocusWatch(active: boolean, send: (event: FocusEvent, reason?: "hidden" | "blur") => void) {
  const sender = useRef(send)
  const [fullscreen, setFullscreen] = useState(inFullscreen)
  const [away, setAway] = useState(false)

  useEffect(() => {
    sender.current = send
  }, [send])

  useEffect(() => {
    if (!active) return
    let out = false
    let timer = 0
    let wasFull = inFullscreen()
    setFullscreen(wasFull)
    const settle = () => {
      timer = 0
      const hidden = document.visibilityState === "hidden"
      const gone = hidden || !document.hasFocus()
      if (gone && !out) {
        out = true
        setAway(true)
        sender.current("leave", hidden ? "hidden" : "blur")
      } else if (!gone && out) {
        out = false
        setAway(false)
        sender.current("back")
      }
    }
    const later = () => {
      if (timer) window.clearTimeout(timer)
      timer = window.setTimeout(settle, SETTLE_MS)
    }
    const pasted = () => sender.current("paste")
    const resized = () => {
      const now = inFullscreen()
      setFullscreen(now)
      if (wasFull && !now) sender.current("fullscreen")
      wasFull = now
    }
    window.addEventListener("blur", later)
    window.addEventListener("focus", later)
    document.addEventListener("visibilitychange", later)
    window.addEventListener("paste", pasted, true)
    document.addEventListener("fullscreenchange", resized)
    document.addEventListener("webkitfullscreenchange", resized)
    return () => {
      if (timer) window.clearTimeout(timer)
      window.removeEventListener("blur", later)
      window.removeEventListener("focus", later)
      document.removeEventListener("visibilitychange", later)
      window.removeEventListener("paste", pasted, true)
      document.removeEventListener("fullscreenchange", resized)
      document.removeEventListener("webkitfullscreenchange", resized)
    }
  }, [active])

  return { fullscreen, away }
}

/**
 * Vigilancia en los editores: cada ejercicio guarda sus propias salidas.
 * El servidor decide si el alumno está vigilado; sin vigilancia devuelve `null` y no se escucha nada.
 */
export function useExerciseFocus(kind: ExerciseKind, exerciseId: string, enabled: boolean) {
  const target = enabled ? exerciseId : ""
  const current = useRef(target)
  const [report, setReport] = useState<FocusReport | null>(null)

  useEffect(() => {
    current.current = target
    if (!target) {
      setReport(null)
      return
    }
    let ignore = false
    void api.exerciseFocus(kind, target, "open").then(
      (payload) => {
        if (ignore) return
        setReport(payload.focus)
        if (payload.focus) enterFullscreen()
      },
      () => undefined,
    )
    return () => {
      ignore = true
    }
  }, [kind, target])

  const send = useCallback(
    (event: FocusEvent, reason?: "hidden" | "blur") => {
      if (!target) return
      void api.exerciseFocus(kind, target, event, reason).then(
        (payload) => {
          if (current.current === target) setReport(payload.focus)
        },
        () => undefined,
      )
    },
    [kind, target],
  )

  const watched = report !== null
  const { fullscreen } = useFocusWatch(watched, send)

  useEffect(() => {
    if (!watched) return
    return () => leaveFullscreen()
  }, [watched])

  return { report, fullscreen }
}

export function FocusNotice({ report, fullscreen }: { report: FocusReport; fullscreen: boolean }) {
  const t = useT()
  const left = exitsLeft(report)
  return (
    <div className="focus-notice" role="status" aria-live="polite">
      <p>{t("focusNotice")}</p>
      <p>
        <strong>
          {report.limit == null
            ? t("focusExits", { count: report.exits })
            : t("focusExitsOf", { count: report.exits, limit: report.limit })}
        </strong>
        {left != null && left > 0 && report.exits > 0 ? ` · ${t("focusExitsLeft", { count: left })}` : ""}
      </p>
      {fullscreenSupported() && !fullscreen ? (
        <button type="button" className="primary" onClick={enterFullscreen}>
          {t(report.exits > 0 ? "focusBackFullscreen" : "focusFullscreen")}
        </button>
      ) : null}
    </div>
  )
}

export function FocusStatus({ report, fullscreen }: { report: FocusReport; fullscreen: boolean }) {
  const t = useT()
  return (
    <span className="focus-status" role="status" title={t("focusNotice")}>
      <strong>{t("focusWatched")}</strong>
      <span>{t("focusExits", { count: report.exits })}</span>
      {fullscreenSupported() && !fullscreen ? (
        <button type="button" onClick={enterFullscreen}>
          {t("focusFullscreen")}
        </button>
      ) : null}
    </span>
  )
}

export function focusSummary(t: ReturnType<typeof useT>, report: FocusReport): string {
  const parts = [
    report.exits === 0
      ? t("focusSummaryNone")
      : t(report.exits === 1 ? "focusSummaryOne" : "focusSummary", {
          count: report.exits,
          time: awayClock(report.away_seconds),
        }),
  ]
  if (report.fullscreen_exits) parts.push(t("focusFullscreenExits", { count: report.fullscreen_exits }))
  if (report.pastes) parts.push(t("focusPastes", { count: report.pastes }))
  if (report.away_now) parts.push(t("focusAwayNow"))
  if (report.auto_submitted) parts.push(t("focusAutoNote"))
  return parts.join(" · ")
}

export function FocusSummary({ report }: { report: FocusReport | null | undefined }) {
  const t = useT()
  if (!report) return null
  return (
    <p className={report.exits > 0 || report.auto_submitted ? "focus-summary is-away" : "focus-summary"}>
      {focusSummary(t, report)}
    </p>
  )
}
