import { useEffect, useState } from "react"

import { ApiError, api, type Algorithm, type ClassroomStudent, type Preferences } from "../api"
import { editorKeywords } from "../dialect"
import { CodeEditor } from "../editor/CodeEditor"
import { translatedMessage, useLocale, useT } from "../i18n"
import { groupNames, studentLabel, studentsIn } from "../workbench/studentGroups"

type PeekProject = { id: string; name: string; count: number; algorithms?: Algorithm[] }

const VIEW: Pick<Preferences, "indent_size" | "theme"> = { indent_size: 4, theme: "light" }
const ignore = () => undefined

export function AlgorithmPeek({ students, seeStudents }: { students: ClassroomStudent[]; seeStudents: boolean }) {
  const t = useT()
  const locale = useLocale()
  const [group, setGroup] = useState("")
  const [studentId, setStudentId] = useState<number | null>(null)
  const [projects, setProjects] = useState<PeekProject[] | null>(null)
  const [projectId, setProjectId] = useState("")
  const [algorithms, setAlgorithms] = useState<Algorithm[] | null>(null)
  const [algorithmId, setAlgorithmId] = useState("")
  const [words, setWords] = useState<{ keywords: string[]; stdlib: string[] }>({ keywords: [], stdlib: [] })
  const [view, setView] = useState(VIEW)
  const [note, setNote] = useState("")
  const waitingStudent = seeStudents && group !== "" && studentId === null

  useEffect(() => {
    let active = true
    void Promise.allSettled([api.keywords(), api.preferences()]).then(([found, prefs]) => {
      if (!active) return
      if (found.status === "fulfilled") setWords(found.value)
      if (prefs.status === "fulfilled") {
        const { indent_size, theme } = prefs.value
        setView({ indent_size, theme })
      }
    })
    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    setProjects(null)
    setProjectId("")
    setNote("")
    if (waitingStudent) return
    let active = true
    const load =
      studentId === null
        ? api.projects().then((page) =>
            page.results.map((item) => ({ id: item.id, name: item.name, count: item.algorithm_count ?? 0 })),
          )
        : api.studentProjects(studentId).then((work) =>
            work.projects.map((item) => ({ id: item.id, name: item.name, count: item.algorithms.length, algorithms: item.algorithms })),
          )
    void load
      .then((rows) => {
        if (!active) return
        setProjects(rows)
        setProjectId((rows.find((item) => item.count > 0) ?? rows[0])?.id ?? "")
      })
      .catch((caught) => {
        if (!active) return
        setProjects([])
        setNote(caught instanceof ApiError ? translatedMessage(caught.message) : t("projectsLoadError"))
      })
    return () => {
      active = false
    }
  }, [studentId, waitingStudent])

  useEffect(() => {
    setAlgorithms(null)
    setAlgorithmId("")
    if (!projectId) return
    const known = projects?.find((item) => item.id === projectId)?.algorithms
    let active = true
    const load = known ? Promise.resolve(known) : api.algorithms(projectId).then((page) => page.results)
    void load
      .then((rows) => {
        if (!active) return
        setAlgorithms(rows)
        setAlgorithmId(rows[0]?.id ?? "")
      })
      .catch((caught) => {
        if (!active) return
        setAlgorithms([])
        setNote(caught instanceof ApiError ? translatedMessage(caught.message) : t("algorithmsLoadError"))
      })
    return () => {
      active = false
    }
  }, [projectId, projects])

  const algorithm = algorithms?.find((item) => item.id === algorithmId) ?? null
  const groupStudents = studentsIn(students, group)

  return (
    <>
      <div className="peek-pick">
        {seeStudents && students.length > 0 && (
          <>
            <label>
              {t("reviewGroup")}
              <select
                value={group}
                onChange={(event) => {
                  setGroup(event.target.value)
                  setStudentId(null)
                }}
              >
                <option value="">{t("myProjects")}</option>
                {groupNames(students).map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
            </label>
            {group && (
              <label>
                {t("reviewStudent")}
                <select
                  value={studentId ?? ""}
                  onChange={(event) => setStudentId(event.target.value ? Number(event.target.value) : null)}
                >
                  <option value="">{t("pickStudent")}</option>
                  {groupStudents.map((student) => (
                    <option key={student.id} value={student.id}>
                      {studentLabel(student, groupStudents)}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </>
        )}
        {!waitingStudent && (
          <>
            <label>
              {t("project")}
              <select value={projectId} disabled={!projects?.length} onChange={(event) => setProjectId(event.target.value)}>
                {!projects?.length && <option value="">{studentId === null ? t("peekNoProjects") : t("noStudentProjects")}</option>}
                {(projects ?? []).map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              {t("algorithm")}
              <select value={algorithmId} disabled={!algorithms?.length} onChange={(event) => setAlgorithmId(event.target.value)}>
                {!algorithms?.length && <option value="">{t("peekNoAlgorithms")}</option>}
                {(algorithms ?? []).map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
          </>
        )}
        {note && <p className="error">{note}</p>}
      </div>
      <div className="peek-code" aria-label={t("readOnlyCode")}>
        {algorithm ? (
          <CodeEditor
            key={algorithm.id}
            source={algorithm.source}
            keywords={editorKeywords(locale, words.keywords)}
            stdlib={words.stdlib}
            indentSize={view.indent_size}
            theme={view.theme}
            jump={null}
            breakpoints={[]}
            currentLine={null}
            onToggleBreakpoint={ignore}
            onChange={ignore}
            onCursor={ignore}
            readOnly
            semicolons={algorithm.require_semicolons}
          />
        ) : (
          <p className="note">{waitingStudent ? t("pickStudent") : t("peekEmpty")}</p>
        )}
      </div>
    </>
  )
}
