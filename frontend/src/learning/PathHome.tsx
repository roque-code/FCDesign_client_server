import { useEffect, useState } from "react"

import { ApiError, api, type LabPath, type LabPathChallenge } from "../api"
import { useT, type MessageKey } from "../i18n"
import { formatLimit, formatWhen } from "./trace"

const ACTIVITY: Record<string, MessageKey> = {
  classify: "classify",
  order: "order",
  build: "build",
  predict: "predict",
}

const STATE: Record<string, MessageKey> = {
  locked: "stateLocked",
  available: "stateOpen",
  completed: "stateDone",
  scheduled: "stateScheduled",
  closed: "stateClosed",
}

function messageOf(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback
}

function percent(completed: number, total: number): number {
  if (total <= 0) return 0
  return Math.min(100, Math.round((completed / total) * 100))
}

function hasSchedule(item: LabPathChallenge): boolean {
  return item.opens_at != null || item.closes_at != null
}

function ChallengeRow({
  item,
  onOpen,
}: {
  item: LabPathChallenge
  onOpen: () => void
}) {
  const t = useT()
  return (
    <li className={`path-item path-${item.state}`}>
      <span className="path-index">{item.position}</span>
      <div className="path-copy">
        <strong>{item.title}</strong>
        <p>
          <span className={`activity-chip activity-${item.activity_type}`}>
            {ACTIVITY[item.activity_type] ? t(ACTIVITY[item.activity_type]) : item.activity_type}
          </span>
          <span>{item.concept}</span>
          <span>{item.points} pts</span>
          {item.opens_at ? <span>{t("fromDate", { when: formatWhen(item.opens_at) })}</span> : null}
          {item.closes_at ? <span>{t("untilDate", { when: formatWhen(item.closes_at) })}</span> : null}
          {item.withdrawn ? <span className="roster-state roster-state-locked">{t("withdrawn")}</span> : null}
          {item.time_limit_seconds ? <span>{formatLimit(item.time_limit_seconds)}</span> : null}
          {item.attempt_count > 0 ? (
            <span>{item.attempt_count === 1 ? t("attemptOne") : t("attemptMany", { count: item.attempt_count })}</span>
          ) : null}
        </p>
      </div>
      <button
        type="button"
        className={item.state === "available" ? "primary" : undefined}
        disabled={item.state === "locked" || item.state === "scheduled" || item.state === "closed"}
        onClick={onOpen}
      >
        {STATE[item.state] ? t(STATE[item.state]) : t("stateOpen")}
      </button>
    </li>
  )
}

function progressOf(path: LabPath): { done: number; total: number } {
  return {
    done: path.challenges.filter((item) => item.state === "completed").length,
    total: path.challenges.length,
  }
}

export function PathHome({
  initialPathId = null,
  onOpen,
}: {
  initialPathId?: string | null
  onOpen: (challengeId: string, pathId: string) => void
}) {
  const t = useT()
  const [paths, setPaths] = useState<LabPath[] | null>(null)
  const [pathId, setPathId] = useState<string | null>(initialPathId)
  const [error, setError] = useState("")

  useEffect(() => {
    let cancelled = false
    async function load() {
      if (document.visibilityState === "hidden") return
      const result = await api.labPaths()
      if (cancelled) return
      setPaths(result.results)
      setPathId((current) => (current && result.results.some((item) => item.id === current) ? current : null))
    }
    void load().catch((caught: unknown) => {
      if (!cancelled) setError(messageOf(caught, t("pathLoadError")))
    })
    const timer = window.setInterval(() => {
      void load().catch(() => undefined)
    }, 5000)
    const onShow = () => {
      void load().catch(() => undefined)
    }
    document.addEventListener("visibilitychange", onShow)
    return () => {
      cancelled = true
      window.clearInterval(timer)
      document.removeEventListener("visibilitychange", onShow)
    }
  }, [])

  const path = paths?.find((item) => item.id === pathId) ?? null

  if (path) {
    const { done, total } = progressOf(path)
    const ratio = percent(done, total)
    return (
      <>
        <section className="enunciado path-intro">
          <div>
            <p className="enunciado-kicker">{t("route")}</p>
            <h2>{path.name}</h2>
            {path.description ? <p className="roster-meta">{path.description}</p> : null}
          </div>
          <div className="roster-heading-side">
            <p className="path-count">
              <strong>{total === 0 ? "—" : `${ratio}%`}</strong>
              <span>{total === 0 ? t("noChallengesWord") : t("progressCount", { done, total })}</span>
            </p>
            <button type="button" onClick={() => setPathId(null)}>
              {t("backToRoutes")}
            </button>
          </div>
        </section>
        <main className="lab-main">
          {error ? <p className="error">{error}</p> : null}
          {total > 0 ? (
            <div className="roster-banner">
              <div
                className="roster-meter"
                role="meter"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={ratio}
                aria-label={t("progressLabel", { name: path.name })}
              >
                <span style={{ width: `${ratio}%` }} />
              </div>
            </div>
          ) : (
            <p className="roster-empty">{t("emptyPath")}</p>
          )}
          <div className="route-groups">
            {[
              {
                key: "open",
                title: t("openChallenges"),
                note: t("openChallengesNote"),
                items: path.challenges.filter(hasSchedule),
              },
              {
                key: "linked",
                title: t("linkedChallenges"),
                note: t("linkedChallengesNote"),
                items: path.challenges.filter((item) => !hasSchedule(item)),
              },
            ].map((group) =>
              group.items.length === 0 ? null : (
                <section key={group.key} className="route-group">
                  <header>
                    <h3>{group.title}</h3>
                    <p>{group.note}</p>
                  </header>
                  <ol className="path-list">
                    {group.items.map((item) => (
                      <ChallengeRow key={item.id} item={item} onOpen={() => onOpen(item.id, path.id)} />
                    ))}
                  </ol>
                </section>
              ),
            )}
          </div>
        </main>
      </>
    )
  }

  return (
    <>
      <section className="enunciado path-intro">
        <div>
          <p className="enunciado-kicker">{t("route")}</p>
          <h2>{t("assignedRoutes")}</h2>
        </div>
        {paths ? (
          <p className="path-count">
            <strong>{paths.length}</strong>
            <span>{paths.length === 1 ? t("routeOne") : t("routeMany")}</span>
          </p>
        ) : null}
      </section>
      <main className="lab-main route-board">
        {error ? <p className="error">{error}</p> : null}
        {paths && paths.length === 0 ? <p className="roster-empty">{t("noAssigned")}</p> : null}
        {paths?.map((item) => {
          const { done, total } = progressOf(item)
          const ratio = percent(done, total)
          return (
            <button key={item.id} type="button" className="route-card" onClick={() => setPathId(item.id)}>
              <span className="route-card-copy">
                <strong>{item.name}</strong>
                {item.description ? <span>{item.description}</span> : null}
                <span className="roster-meter" aria-hidden="true">
                  <span style={{ width: `${ratio}%` }} />
                </span>
                <span className="roster-meta">{total === 0 ? t("noChallengesShort") : t("challengesOf", { done, total })}</span>
              </span>
              <span className="roster-score">
                <strong>{total === 0 ? "—" : `${ratio}%`}</strong>
                <span>{t("seeChallenges")}</span>
              </span>
            </button>
          )
        })}
      </main>
    </>
  )
}
