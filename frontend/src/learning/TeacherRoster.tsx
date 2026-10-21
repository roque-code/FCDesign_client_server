import { useEffect, useState } from "react"

import { ApiError, api, type LabMemberProgress, type LabMemberWork, type LabRosterRoute } from "../api"
import { spellText } from "../dialect"
import { translatedMessage, useLocale, useT, type MessageKey } from "../i18n"
import { saveDownload } from "../saveFile"
import { SolutionCard } from "./SolutionCard"
import { TeacherBoard } from "./TeacherBoard"
import { formatClock, formatWhen } from "./trace"

const STATE: Record<string, MessageKey> = {
  completed: "stateCompleted",
  available: "stateAvailable",
  locked: "stateLocked",
  scheduled: "stateScheduled",
  closed: "stateClosed",
}

const ACTIVITY: Record<string, MessageKey> = {
  classify: "classify",
  order: "order",
  build: "build",
  predict: "predict",
}

function messageOf(error: unknown, fallback: string): string {
  return error instanceof ApiError ? translatedMessage(error.message) : fallback
}

function percent(completed: number, total: number): number {
  if (total <= 0) return 0
  return Math.min(100, Math.round((completed / total) * 100))
}

function StudentWork({
  work,
  points,
  rank,
}: {
  work: LabMemberWork
  points: number
  rank: number
}) {
  const t = useT()
  const locale = useLocale()
  const { challenge, attempt } = work
  const finished = attempt?.status === "completed"
  const timedOut = attempt?.status === "abandoned"
  const readSource = challenge.activity_type === "predict" ? challenge.task.source ?? "" : ""
  return (
    <div className="review-sheet">
      <article className="enunciado">
        <div className="enunciado-body">
          <p className="enunciado-kicker">
            {t("promptKicker")} · {ACTIVITY[challenge.activity_type] ? t(ACTIVITY[challenge.activity_type]) : challenge.activity_type} · {challenge.concept}
          </p>
          <h2>{challenge.title}</h2>
          <p className="enunciado-text">{challenge.prompt}</p>
        </div>
      </article>
      {finished && attempt ? (
        <div className="result-layout">
          <article className="result-card">
            <p className="enunciado-kicker">{t("resultWord")}</p>
            <h2>{t("challengeDone")}</h2>
            {attempt.score != null ? <p className="result-score">{attempt.score}</p> : null}
            <p>
              {t("teacherScore", { points: challenge.points, total: points, rank })}
            </p>
            {attempt.elapsed_seconds != null ? <p>{t("answeredIn", { time: formatClock(attempt.elapsed_seconds) })}</p> : null}
            {attempt.finished_at ? <p>{formatWhen(attempt.finished_at, locale)}</p> : null}
            <p>{attempt.summary || t("alreadyClosed")}</p>
            {attempt.prediction ? <p>{t("answerIs", { answer: attempt.prediction.answer })}</p> : null}
            {attempt.reflection ? <blockquote>{attempt.reflection}</blockquote> : null}
          </article>
          {attempt.solution ? <SolutionCard solution={attempt.solution} title={challenge.title} kicker="studentBuild" /> : null}
        </div>
      ) : null}
      {!finished && attempt?.solution ? (
        <SolutionCard solution={attempt.solution} title={challenge.title} kicker="studentBuild" />
      ) : null}
      {timedOut && attempt ? (
        <article className="result-card">
          <p className="enunciado-kicker">{t("timeWord")}</p>
          <h2>{t("timeUp")}</h2>
          {attempt.elapsed_seconds != null ? <p>{t("usedTime", { time: formatClock(attempt.elapsed_seconds) })}</p> : null}
          {attempt.finished_at ? <p>{formatWhen(attempt.finished_at, locale)}</p> : null}
          <p>{t("savedAgain")}</p>
        </article>
      ) : null}
      {attempt && attempt.answer.length > 0 ? (
        <section className="review-block">
          <h2>{t("reply")}</h2>
          {challenge.task.question ? <p>{challenge.task.question}</p> : null}
          <ul className="review-answers">
            {attempt.answer.map((item) => (
              <li key={`${item.label}-${item.value}`}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {readSource ? (
        <section className="review-block">
          <h2>{t("codeOfChallenge")}</h2>
          <pre className="lab-code">{spellText(locale, readSource)}</pre>
        </section>
      ) : null}
      {attempt && attempt.source && !attempt.solution ? (
        <section className="review-block">
          <h2>{t("studentCode")}</h2>
          <pre className="lab-code">{spellText(locale, attempt.source)}</pre>
        </section>
      ) : null}
      {attempt && attempt.cases.length > 0 ? (
        <section className="review-block">
          <h2>{t("casesWord")}</h2>
          <ul className="case-list">
            {attempt.cases.map((item) => (
              <li key={item.name}>
                {item.passed ? t("passed") : t("mismatch")} · {item.name}
                <pre className="lab-output">{item.output}</pre>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {attempt == null ? <p className="roster-empty">{t("noAttemptYet")}</p> : null}
      {attempt && !finished && !timedOut && attempt.answer.length === 0 && attempt.source === "" ? (
        <p className="roster-empty">{t("noAnswerYet")}</p>
      ) : null}
    </div>
  )
}

function initialOf(name: string, locale: "es" | "en"): string {
  const letter = name.trim().charAt(0)
  return letter ? letter.toLocaleUpperCase(locale === "en" ? "en" : "es") : "?"
}

function progressFilename(name: string): string {
  const folded = name.normalize("NFKD").replace(/[\u0300-\u036f]/g, "")
  const cleaned = folded.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60)
  return `progreso-${cleaned || "ruta"}.csv`
}

export function TeacherRoster() {
  const t = useT()
  const locale = useLocale()
  const [routes, setRoutes] = useState<LabRosterRoute[] | null>(null)
  const [opened, setOpened] = useState<{ routeId: string; detail: LabMemberProgress } | null>(null)
  const [review, setReview] = useState<LabMemberWork | null>(null)
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let cancelled = false
    void api.labRoster().then(
      (result) => {
        if (!cancelled) setRoutes(result.routes)
      },
      (caught: unknown) => {
        if (!cancelled) setError(messageOf(caught, t("rosterLoadError")))
      },
    )
    return () => {
      cancelled = true
    }
  }, [])

  async function downloadProgress(route: LabRosterRoute) {
    setBusy(true)
    setError("")
    try {
      const csv = await api.labProgressCsv(route.id, locale)
      const body = csv.charCodeAt(0) === 0xfeff ? csv : `\ufeff${csv}`
      await saveDownload(progressFilename(route.name), new Blob([body], { type: "text/csv;charset=utf-8" }))
    } catch (caught) {
      setError(messageOf(caught, t("studentProgressError")))
    } finally {
      setBusy(false)
    }
  }

  async function openPerson(userId: number, routeId: string) {
    setBusy(true)
    setError("")
    setReview(null)
    try {
      setOpened({ routeId, detail: await api.labMember(userId) })
    } catch (caught) {
      setError(messageOf(caught, t("rosterLoadError")))
    } finally {
      setBusy(false)
    }
  }

  async function openWork(userId: number, challengeId: string) {
    setBusy(true)
    setError("")
    try {
      setReview(await api.labMemberWork(userId, challengeId))
    } catch (caught) {
      setError(messageOf(caught, t("rosterLoadError")))
    } finally {
      setBusy(false)
    }
  }

  if (opened) {
    const path = opened.detail.paths.find((item) => item.id === opened.routeId) ?? null
    const done = path ? percent(path.completed, path.total) : 0
    return (
      <>
        <section className="enunciado path-intro">
          <div>
            <p className="enunciado-kicker">{path?.name || t("route")}</p>
            <h2>{opened.detail.person.display_name}</h2>
            <p className="roster-meta">
              {t("placeLine", { points: opened.detail.person.points, rank: opened.detail.person.rank })}
              {opened.detail.person.communities.length > 0
                ? ` · ${opened.detail.person.communities.join(", ")}`
                : ""}
            </p>
          </div>
          <div className="roster-heading-side">
            {path ? (
              <p className="path-count">
                <strong>{done}%</strong>
                <span>{path.total === 0 ? t("noChallengesWord") : t("progressCount", { done: path.completed, total: path.total })}</span>
              </p>
            ) : null}
            <button
              type="button"
              onClick={() => {
                if (review) setReview(null)
                else setOpened(null)
              }}
            >
              {review ? t("backToProgress") : t("backToRoutes")}
            </button>
          </div>
        </section>
        <main className="lab-main">
          {error ? <p className="error">{error}</p> : null}
          {review ? (
            <StudentWork work={review} points={opened.detail.person.points} rank={opened.detail.person.rank} />
          ) : null}
          {!review && path == null ? <p className="roster-empty">{t("noSuchPath")}</p> : null}
          {!review && path && path.total > 0 ? (
            <div className="roster-banner">
              <div
                className="roster-meter"
                role="meter"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={done}
                aria-label={t("pathProgress")}
              >
                <span style={{ width: `${done}%` }} />
              </div>
            </div>
          ) : null}
          {opened.detail.mastery.length > 0 && !review ? (
            <ul className="roster-mastery">
              {opened.detail.mastery.map((item) => (
                <li key={item.concept}>
                  {item.concept}
                  <span>{t("levelWord", { level: item.level })}</span>
                </li>
              ))}
            </ul>
          ) : null}
          {path && !review ? (
            <div className="route-groups">
              {[
                {
                  key: "open",
                  title: t("openChallenges"),
                  note: t("openChallengesNote"),
                  items: path.challenges.filter((item) => item.opens_at != null || item.closes_at != null),
                },
                {
                  key: "linked",
                  title: t("linkedChallenges"),
                  note: t("linkedChallengesNote"),
                  items: path.challenges.filter((item) => item.opens_at == null && item.closes_at == null),
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
                        <li key={item.id} className={`path-item path-${item.state}`}>
                          <span className="path-index">{item.position}</span>
                          <div className="path-copy">
                            <strong>{item.title}</strong>
                            <p>
                              <span>{item.concept}</span>
                              <span>{t("pointsCount", { count: item.points })}</span>
                              {item.opens_at ? <span>{t("fromDate", { when: formatWhen(item.opens_at, locale) })}</span> : null}
                              {item.closes_at ? <span>{t("untilDate", { when: formatWhen(item.closes_at, locale) })}</span> : null}
                              {item.withdrawn ? <span className="roster-state roster-state-locked">{t("withdrawn")}</span> : null}
                              {item.state === "completed" && item.score != null ? <span>{t("scoreNote", { score: item.score })}</span> : null}
                            </p>
                          </div>
                          <div className="roster-actions">
                            <span className={`roster-state roster-state-${item.state}`}>{STATE[item.state] ? t(STATE[item.state]) : item.state}</span>
                            <button type="button" onClick={() => void openWork(opened.detail.person.id, item.id)} disabled={busy}>
                              {t("seeWord")}
                            </button>
                          </div>
                        </li>
                      ))}
                    </ol>
                  </section>
                ),
              )}
            </div>
          ) : null}
        </main>
      </>
    )
  }

  return (
    <>
      <section className="enunciado path-intro">
        <div>
          <p className="enunciado-kicker">{t("progress")}</p>
          <h2>{t("assignedPaths")}</h2>
        </div>
        {routes ? (
          <p className="path-count">
            <strong>{routes.length}</strong>
            <span>{routes.length === 1 ? t("routeOne") : t("routeMany")}</span>
          </p>
        ) : null}
      </section>
      <main className="lab-main roster-routes">
        {error ? <p className="error">{error}</p> : null}
        {routes && routes.length > 0 ? (
          <TeacherBoard routes={routes} busy={busy} onOpen={(userId, routeId) => void openPerson(userId, routeId)} />
        ) : null}
        {routes && routes.length === 0 ? (
          <p className="roster-empty">{t("noStudentsOnPath")}</p>
        ) : null}
        {routes?.map((route) => {
          const completed = route.students.reduce((sum, student) => sum + student.completed, 0)
          const total = route.students.reduce((sum, student) => sum + student.total, 0)
          const done = percent(completed, total)
          return (
            <section key={route.id} className="roster-route">
              <header>
                <div>
                  <h2>{route.name}</h2>
                  {route.description ? <p>{route.description}</p> : null}
                </div>
                <div className="roster-download">
                  <button
                    type="button"
                    title={t("studentProgressNote")}
                    onClick={() => void downloadProgress(route)}
                    disabled={busy}
                  >
                    {t("studentProgress")}
                  </button>
                  <p className="path-count">
                    <strong>{route.students.length}</strong>
                    <span>{t(route.students.length === 1 ? "countStudent" : "countStudents", { count: route.students.length })}</span>
                  </p>
                </div>
              </header>
              <div className="roster-route-progress">
                <div
                  className="roster-meter"
                  role="meter"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={done}
                  aria-label={t("progressLabel", { name: route.name })}
                >
                  <span style={{ width: `${done}%` }} />
                </div>
                <p>{total === 0 ? t("emptyPath") : t("completedOf", { done: completed, total })}</p>
              </div>
              <ul className="roster-list">
                {route.students.map((student) => {
                  const studentDone = percent(student.completed, student.total)
                  return (
                    <li key={student.id}>
                      <button type="button" onClick={() => void openPerson(student.id, route.id)} disabled={busy}>
                        <span className="roster-avatar" aria-hidden="true">{initialOf(student.display_name, locale)}</span>
                        <span className="roster-person">
                          <strong>{student.display_name}</strong>
                          {student.communities.length > 0 ? (
                            <span className="roster-tags">
                              {student.communities.map((community) => (
                                <span key={community} className="roster-chip">{community}</span>
                              ))}
                            </span>
                          ) : null}
                          <span className="roster-meter" aria-hidden="true">
                            <span style={{ width: `${studentDone}%` }} />
                          </span>
                          <span className="roster-meta">
                            {student.total === 0 ? t("noChallengesShort") : t("progressCount", { done: student.completed, total: student.total })}
                            {student.last_activity ? ` · ${formatWhen(student.last_activity, locale)}` : ""}
                          </span>
                        </span>
                        <span className="roster-score">
                          <strong>{student.points}</strong>
                          <span>{t("placeRank", { rank: student.rank })}</span>
                        </span>
                      </button>
                    </li>
                  )
                })}
              </ul>
            </section>
          )
        })}
      </main>
    </>
  )
}
