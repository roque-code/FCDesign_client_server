import { type LabRosterRoute } from "../api"
import { useLocale, useT } from "../i18n"
import { formatWhen } from "./trace"

type BoardRoute = {
  id: string
  name: string
  completed: number
  total: number
}

type BoardStudent = {
  id: number
  display_name: string
  communities: string[]
  points: number
  rank: number
  last_activity: string | null
  routes: BoardRoute[]
}

function percent(completed: number, total: number): number {
  if (total <= 0) return 0
  return Math.min(100, Math.round((completed / total) * 100))
}

function studentsOf(routes: LabRosterRoute[], locale: "es" | "en"): BoardStudent[] {
  const grouped = new Map<number, BoardStudent>()
  for (const route of routes) {
    for (const student of route.students) {
      const current = grouped.get(student.id) ?? {
        id: student.id,
        display_name: student.display_name,
        communities: student.communities,
        points: student.points,
        rank: student.rank,
        last_activity: student.last_activity,
        routes: [],
      }
      if (student.last_activity && (!current.last_activity || student.last_activity > current.last_activity)) {
        current.last_activity = student.last_activity
      }
      current.routes.push({
        id: route.id,
        name: route.name,
        completed: student.completed,
        total: student.total,
      })
      grouped.set(student.id, current)
    }
  }
  return [...grouped.values()].sort((left, right) => left.display_name.localeCompare(right.display_name, locale))
}

function totals(student: BoardStudent): { done: number; total: number; percent: number } {
  const done = student.routes.reduce((sum, route) => sum + route.completed, 0)
  const total = student.routes.reduce((sum, route) => sum + route.total, 0)
  return { done, total, percent: percent(done, total) }
}

function focusRoute(student: BoardStudent): string {
  let chosen = student.routes[0]
  for (const route of student.routes) {
    if (!chosen || percent(route.completed, route.total) < percent(chosen.completed, chosen.total)) chosen = route
  }
  return chosen?.id ?? ""
}

function Ring({ value, label }: { value: number; label: string }) {
  const radius = 28
  const turn = 2 * Math.PI * radius
  const drawn = (value / 100) * turn
  return (
    <svg className="board-ring" viewBox="0 0 72 72" role="img" aria-label={label}>
      <circle className="board-ring-track" cx="36" cy="36" r={radius} />
      {value > 0 ? (
        <circle
          className="board-ring-value"
          cx="36"
          cy="36"
          r={radius}
          strokeDasharray={`${drawn} ${turn - drawn}`}
          transform="rotate(-90 36 36)"
        />
      ) : null}
      <text x="36" y="40" textAnchor="middle">
        {value}%
      </text>
    </svg>
  )
}

export function TeacherBoard({
  routes,
  busy,
  onOpen,
}: {
  routes: LabRosterRoute[]
  busy: boolean
  onOpen: (userId: number, routeId: string) => void
}) {
  const t = useT()
  const locale = useLocale()
  const students = studentsOf(routes, locale)
  if (students.length === 0) return null
  const average = Math.round(students.reduce((sum, student) => sum + totals(student).percent, 0) / students.length)
  const idle = students.filter((student) => student.last_activity == null).length
  const ranked = [...students].sort(
    (left, right) => totals(right).percent - totals(left).percent || left.display_name.localeCompare(right.display_name, locale),
  )

  return (
    <section className="teacher-board">
      <header>
        <div>
          <p className="enunciado-kicker">{t("progress")}</p>
          <h2>{t("dashboard")}</h2>
          <p>{t("dashboardNote")}</p>
        </div>
      </header>
      <div className="board-summary">
        <article>
          <strong>{students.length}</strong>
          <span>{t(students.length === 1 ? "studentWord" : "students")}</span>
        </article>
        <article>
          <strong>{average}%</strong>
          <span>{t("averageProgress")}</span>
        </article>
        <article>
          <strong>{idle}</strong>
          <span>{t("idleStudents")}</span>
        </article>
      </div>
      <ol className="board-chart">
        {ranked.map((student) => {
          const progress = totals(student)
          return (
            <li key={student.id}>
              <button type="button" onClick={() => onOpen(student.id, focusRoute(student))} disabled={busy}>
                <span className="board-name">{student.display_name}</span>
                <span className="board-track" aria-hidden="true">
                  <span style={{ width: `${progress.percent}%` }} />
                </span>
                <span className="board-percent">{progress.percent}%</span>
              </button>
            </li>
          )
        })}
      </ol>
      <div className="board-cards">
        {students.map((student) => {
          const progress = totals(student)
          return (
            <article key={student.id} className="board-card">
              <button type="button" className="board-card-main" onClick={() => onOpen(student.id, focusRoute(student))} disabled={busy}>
                <Ring value={progress.percent} label={t("progressLabel", { name: student.display_name })} />
                <span className="board-card-copy">
                  <strong>{student.display_name}</strong>
                  {student.communities.length > 0 ? <span className="roster-meta">{student.communities.join(" · ")}</span> : null}
                  <span className="roster-meta">
                    {progress.total === 0 ? t("noChallengesShort") : t("progressCount", { done: progress.done, total: progress.total })}
                    {student.last_activity ? ` · ${formatWhen(student.last_activity, locale)}` : ""}
                  </span>
                  <span className="roster-meta">{t("placeLine", { points: student.points, rank: student.rank })}</span>
                </span>
              </button>
              <ul>
                {student.routes.map((route) => {
                  const done = percent(route.completed, route.total)
                  return (
                    <li key={route.id}>
                      <button type="button" onClick={() => onOpen(student.id, route.id)} disabled={busy}>
                        <span>{route.name}</span>
                        <span className="board-track" aria-hidden="true">
                          <span style={{ width: `${done}%` }} />
                        </span>
                        <span>{route.total === 0 ? "0%" : `${done}%`}</span>
                      </button>
                    </li>
                  )
                })}
              </ul>
            </article>
          )
        })}
      </div>
    </section>
  )
}
