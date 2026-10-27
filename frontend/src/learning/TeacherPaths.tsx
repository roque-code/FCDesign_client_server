import { FormEvent, useEffect, useState } from "react"

import {
  ApiError,
  api,
  type CommunitySummary,
  type LabAuthoredChallenge,
  type LabAuthoredPath,
  type LabAuthoredSummary,
  type LabCatalogChallenge,
  type LabChallengeDraft,
  type LabConcept,
  type Person,
} from "../api"
import { translatedMessage, useT, type MessageKey } from "../i18n"
import { ChallengeForm } from "./ChallengeForm"
import { WeightFields } from "./WeightFields"
import { parseWeights, weightTotal, type LabWeights } from "./weights"

const ACTIVITY: Record<string, MessageKey> = {
  classify: "classify",
  order: "order",
  build: "build",
  predict: "predict",
}

function messageOf(error: unknown, fallback: string): string {
  return error instanceof ApiError ? translatedMessage(error.message) : fallback
}

function audienceSize(
  communities: { id: string }[],
  students: { id: number }[],
  people: Record<string, Person[]>,
): number {
  const ids = new Set(students.map((item) => item.id))
  for (const community of communities) {
    for (const person of people[community.id] ?? []) ids.add(person.id)
  }
  return ids.size
}

function toLocalInput(iso: string | null): string {
  if (!iso) return ""
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ""
  const pad = (value: number) => String(value).padStart(2, "0")
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function fromLocalInput(value: string): string | null {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return null
  return date.toISOString()
}

function ChallengeSchedule({
  pathId,
  item,
  busy,
  onSaved,
  onError,
}: {
  pathId: string
  item: LabAuthoredChallenge
  busy: boolean
  onSaved: (path: LabAuthoredPath) => void
  onError: (message: string) => void
}) {
  const t = useT()
  const [opens, setOpens] = useState(toLocalInput(item.opens_at))
  const [closes, setCloses] = useState(toLocalInput(item.closes_at))
  const [weights, setWeights] = useState<LabWeights>(() => parseWeights(item.weights, item.activity_type))
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    setOpens(toLocalInput(item.opens_at))
    setCloses(toLocalInput(item.closes_at))
    setWeights(parseWeights(item.weights, item.activity_type))
  }, [item.opens_at, item.closes_at, item.weights, item.activity_type])

  async function save(event: FormEvent) {
    event.preventDefault()
    onError("")
    const rubric = item.activity_type === "build" ? weights : { ...weights, lenguaje: 0 }
    if (weightTotal(rubric) !== 100) {
      onError(t("weightMust100"))
      return
    }
    setSaving(true)
    try {
      onSaved(
        await api.setLabSchedule(pathId, item.id, {
          entry_id: item.entry_id,
          opens_at: fromLocalInput(opens),
          closes_at: fromLocalInput(closes),
          weights: rubric,
        }),
      )
    } catch (caught) {
      onError(messageOf(caught, t("pathSaveError")))
    } finally {
      setSaving(false)
    }
  }

  async function toggleWithdrawn() {
    onError("")
    setSaving(true)
    try {
      onSaved(
        await api.setLabSchedule(pathId, item.id, { entry_id: item.entry_id, withdrawn: !item.withdrawn }),
      )
    } catch (caught) {
      onError(messageOf(caught, t("pathSaveError")))
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="entry-settings" onSubmit={(event) => void save(event)}>
      <div className="schedule-grid">
        <label>
          {t("starts")}
          <input type="datetime-local" value={opens} onChange={(event) => setOpens(event.target.value)} />
        </label>
        <label>
          {t("ends")}
          <input type="datetime-local" value={closes} onChange={(event) => setCloses(event.target.value)} />
        </label>
        <div className="practice-actions">
          <button type="submit" disabled={busy || saving}>
            {t("saveSchedule")}
          </button>
          <button type="button" onClick={() => void toggleWithdrawn()} disabled={busy || saving}>
            {item.withdrawn ? t("offer") : t("withdrawAction")}
          </button>
        </div>
      </div>
      <WeightFields activity={item.activity_type} weights={weights} onChange={setWeights} note={t("pathWeightsNote")} />
    </form>
  )
}

export function TeacherPaths() {
  const t = useT()
  const [paths, setPaths] = useState<LabAuthoredSummary[] | null>(null)
  const [catalog, setCatalog] = useState<LabCatalogChallenge[]>([])
  const [concepts, setConcepts] = useState<LabConcept[]>([])
  const [editor, setEditor] = useState<string | null>(null)
  const [current, setCurrent] = useState<LabAuthoredPath | null>(null)
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [draftName, setDraftName] = useState("")
  const [draftDescription, setDraftDescription] = useState("")
  const [published, setPublished] = useState(false)
  const [pick, setPick] = useState("")
  const [kind, setKind] = useState("")
  const [communities, setCommunities] = useState<CommunitySummary[]>([])
  const [communityPeople, setCommunityPeople] = useState<Record<string, Person[]>>({})
  const [communityIds, setCommunityIds] = useState<string[]>([])
  const [students, setStudents] = useState<LabAuthoredPath["students"]>([])
  const [groupId, setGroupId] = useState("")
  const [members, setMembers] = useState<Person[]>([])
  const [studentId, setStudentId] = useState("")
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [savedNote, setSavedNote] = useState("")

  async function reload() {
    const result = await api.authoredPaths()
    setPaths(result.results)
  }

  useEffect(() => {
    let cancelled = false
    void api.authoredPaths().then(
      (result) => {
        if (!cancelled) setPaths(result.results)
      },
      (caught: unknown) => {
        if (!cancelled) setError(messageOf(caught, t("pathSaveError")))
      },
    )
    return () => {
      cancelled = true
    }
  }, [])

  function show(path: LabAuthoredPath, groups: CommunitySummary[]) {
    setCurrent(path)
    setDraftName(path.name)
    setDraftDescription(path.description)
    setPublished(path.is_published)
    setCommunityIds(path.communities.map((item) => item.id))
    setStudents(path.students)
    setCommunities(groups)
    setGroupId("")
    setMembers([])
    setStudentId("")
    setConfirmDelete(false)
    setPick("")
    setSavedNote("")
    setEditor(null)
  }

  async function openPath(id: string) {
    setBusy(true)
    setError("")
    try {
      const [path, groups, available] = await Promise.all([
        api.labAuthored(id),
        api.communities(),
        api.labCatalog(),
      ])
      const details = await Promise.all(groups.results.map((group) => api.community(group.id)))
      setCatalog(available.results)
      setConcepts(available.concepts)
      setCommunityPeople(Object.fromEntries(details.map((item) => [item.id, item.students])))
      show(path, groups.results)
    } catch (caught) {
      setError(messageOf(caught, t("pathSaveError")))
    } finally {
      setBusy(false)
    }
  }

  async function createPath(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError("")
    try {
      const created = await api.createLabPath(name.trim(), description.trim())
      setName("")
      setDescription("")
      await reload()
      await openPath(created.id)
    } catch (caught) {
      setError(messageOf(caught, t("pathSaveError")))
    } finally {
      setBusy(false)
    }
  }

  async function saveDetails(event: FormEvent) {
    event.preventDefault()
    if (!current) return
    setBusy(true)
    setError("")
    try {
      const saved = await api.updateLabPath(current.id, {
        name: draftName.trim(),
        description: draftDescription.trim(),
        is_published: published,
      })
      setCurrent(saved)
      setDraftName(saved.name)
      setDraftDescription(saved.description)
      setPublished(saved.is_published)
      await reload()
    } catch (caught) {
      setError(messageOf(caught, t("pathSaveError")))
    } finally {
      setBusy(false)
    }
  }

  async function storeRows(rows: { id: string; entry_id: string | null }[]) {
    if (!current) return
    setBusy(true)
    setError("")
    try {
      const saved = await api.setLabChallenges(
        current.id,
        rows.map((row) => row.id),
        rows.map((row) => row.entry_id),
      )
      setCurrent(saved)
      await reload()
    } catch (caught) {
      setError(messageOf(caught, t("pathSaveError")))
    } finally {
      setBusy(false)
    }
  }

  function addChallenge() {
    if (!current || !pick) return
    void storeRows([
      ...current.challenges.map((item) => ({ id: item.id, entry_id: item.entry_id })),
      { id: pick, entry_id: null },
    ])
  }

  async function placeChallenge(draft: LabChallengeDraft) {
    if (!current) return
    setBusy(true)
    setError("")
    try {
      const available = await api.labCatalog()
      setCatalog(available.results)
      setConcepts(available.concepts)
      const rows = current.challenges.map((item) => ({ id: item.id, entry_id: item.entry_id }))
      const next = rows.some((row) => row.id === draft.id) ? rows : [...rows, { id: draft.id, entry_id: null }]
      const saved = await api.setLabChallenges(
        current.id,
        next.map((row) => row.id),
        next.map((row) => row.entry_id),
      )
      setCurrent(saved)
      setEditor(null)
      await reload()
    } catch (caught) {
      setError(messageOf(caught, t("pathSaveError")))
    } finally {
      setBusy(false)
    }
  }

  function moveChallenge(index: number, delta: number) {
    if (!current) return
    const next = current.challenges.slice()
    const target = index + delta
    if (target < 0 || target >= next.length) return
    const [item] = next.splice(index, 1)
    next.splice(target, 0, item)
    void storeRows(next.map((row) => ({ id: row.id, entry_id: row.entry_id })))
  }

  async function saveAssignments(event: FormEvent) {
    event.preventDefault()
    if (!current) return
    setBusy(true)
    setError("")
    try {
      const saved = await api.setLabAssignments(
        current.id,
        communityIds,
        students.map((item) => item.id),
      )
      setCurrent(saved)
      setPublished(saved.is_published)
      setCommunityIds(saved.communities.map((item) => item.id))
      setStudents(saved.students)
      const groups = saved.communities.map((item) => item.name)
      const people = saved.students.map((item) => item.display_name)
      const who = [...groups, ...people]
      setSavedNote(
        who.length > 0 ? t("assignSaved", { who: who.join(", ") }) : t("assignCleared"),
      )
      await reload()
    } catch (caught) {
      setError(messageOf(caught, t("pathSaveError")))
    } finally {
      setBusy(false)
    }
  }

  async function loadMembers(id: string) {
    setGroupId(id)
    setStudentId("")
    setMembers([])
    if (!id) return
    setBusy(true)
    setError("")
    try {
      const detail = await api.community(id)
      setMembers(detail.students)
    } catch (caught) {
      setError(messageOf(caught, t("pathSaveError")))
    } finally {
      setBusy(false)
    }
  }

  function addStudent() {
    const person = members.find((item) => item.id === Number(studentId))
    if (!person || students.some((item) => item.id === person.id)) return
    setStudents((currentStudents) => [
      ...currentStudents,
      { id: person.id, display_name: person.display_name, email: person.email },
    ])
  }

  async function removePath() {
    if (!current) return
    setBusy(true)
    setError("")
    try {
      await api.deleteLabPath(current.id)
      setCurrent(null)
      await reload()
    } catch (caught) {
      setError(messageOf(caught, t("pathSaveError")))
    } finally {
      setBusy(false)
    }
  }

  if (current) {
    return (
      <>
        <section className="enunciado path-intro">
          <div>
            <p className="enunciado-kicker">{t("teacherPath")}</p>
            <h2>{current.name}</h2>
            <p className="path-stats">
              <span className={current.is_published ? "roster-state roster-state-completed" : "roster-state roster-state-locked"}>
                {current.is_published ? t("published") : t("draft")}
              </span>
              <span>{t(current.challenges.length === 1 ? "countChallenge" : "countChallenges", { count: current.challenges.length })}</span>
              <span>{t(current.communities.length === 1 ? "countCommunity" : "countCommunities", { count: current.communities.length })}</span>
              <span>
                {t(audienceSize(current.communities, current.students, communityPeople) === 1 ? "countStudent" : "countStudents", {
                  count: audienceSize(current.communities, current.students, communityPeople),
                })}
              </span>
            </p>
          </div>
          <button type="button" className="path-btn" onClick={() => setCurrent(null)}>
            {t("backToList")}
          </button>
        </section>
        <main className="lab-main path-editor">
          {error ? <p className="error">{error}</p> : null}
          <form className="stage-form path-panel path-tone-1" onSubmit={(event) => void saveDetails(event)}>
              <h2>{t("dataWord")}</h2>
              <label>
                {t("nameWord")}
                <input value={draftName} onChange={(event) => setDraftName(event.target.value)} maxLength={120} required />
              </label>
              <label>
                {t("description")}
                <textarea
                  value={draftDescription}
                  onChange={(event) => setDraftDescription(event.target.value)}
                  rows={3}
                  maxLength={2000}
                />
              </label>
              <label className="check-line">
                <input
                  type="checkbox"
                  checked={published}
                  onChange={(event) => setPublished(event.target.checked)}
                />
                {t("publishedNote")}
              </label>
              <div className="practice-actions">
                <button type="submit" className="primary" disabled={busy}>
                  {t("saveData")}
                </button>
              </div>
          </form>
          <section className="path-section">
            <div className="stage-form path-panel path-tone-2">
              <h2>{t("challenges")}</h2>
              <p>{t("scheduleNote")}</p>
              <p>{t("repeatChallengeNote")}</p>
              {current.challenges.length === 0 ? <p className="roster-empty">{t("pathHasNone")}</p> : null}
              <div className="path-pick">
                <label>
                  {t("kindWord")}
                  <select
                    value={kind}
                    onChange={(event) => {
                      const next = event.target.value
                      setKind(next)
                      if (pick && catalog.find((item) => item.id === pick)?.activity_type !== next && next) {
                        setPick("")
                      }
                    }}
                  >
                    <option value="">{t("all")}</option>
                    {Object.entries(ACTIVITY).map(([id, label]) => (
                      <option key={id} value={id}>
                        {t(label)}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  {t("fromCatalog")}
                  <select value={pick} onChange={(event) => setPick(event.target.value)}>
                    <option value="">{t("pickChallenge")}</option>
                    {(
                      [
                        { label: t("yourChallenges"), owned: true },
                        { label: t("catalog"), owned: false },
                      ] as const
                    ).map(({ label, owned }) => {
                      const rows = catalog.filter(
                        (item) => Boolean(item.owned) === owned && (!kind || item.activity_type === kind),
                      )
                      if (rows.length === 0) return null
                      return (
                        <optgroup key={label} label={label}>
                          {rows.map((item) => (
                            <option key={item.id} value={item.id}>
                              {item.title} · {ACTIVITY[item.activity_type] ? t(ACTIVITY[item.activity_type]) : item.activity_type} · {t("pointsCount", { count: item.points })}
                            </option>
                          ))}
                        </optgroup>
                      )
                    })}
                  </select>
                </label>
              </div>
              <div className="practice-actions">
                <button type="button" onClick={addChallenge} disabled={busy || !pick}>
                  {t("add")}
                </button>
              </div>
            </div>
            {editor ? (
              <div className="path-panel path-tone-editor">
                <ChallengeForm
                  challengeId={editor === "new" ? null : editor}
                  concepts={concepts}
                  onCancel={() => setEditor(null)}
                  onSaved={(draft) => void placeChallenge(draft)}
                />
              </div>
            ) : null}
            <ol className="path-list">
              {current.challenges.map((item, index) => (
                <li key={item.entry_id} className={`path-panel path-tone-entry entry-item${item.withdrawn ? " entry-withdrawn" : ""}`}>
                  <div className="entry-head">
                    <span className="path-index">{index + 1}</span>
                    <div className="path-copy">
                      <strong>{item.title}</strong>
                      <p>
                        <span>{ACTIVITY[item.activity_type] ? t(ACTIVITY[item.activity_type]) : item.activity_type}</span>
                        <span>{item.concept}</span>
                        <span>{t("pointsCount", { count: item.points })}</span>
                        {item.withdrawn ? <span className="roster-state roster-state-locked">{t("withdrawn")}</span> : null}
                      </p>
                    </div>
                  </div>
                  <ChallengeSchedule
                    pathId={current.id}
                    item={item}
                    busy={busy}
                    onSaved={(saved) => {
                      setCurrent(saved)
                      void reload()
                    }}
                    onError={setError}
                  />
                  <div className="practice-actions">
                    {item.owned ? (
                      <button type="button" onClick={() => setEditor(item.id)} disabled={busy}>
                        {t("edit")}
                      </button>
                    ) : null}
                    <button type="button" onClick={() => moveChallenge(index, -1)} disabled={busy || index === 0}>
                      {t("moveUp")}
                    </button>
                    <button
                      type="button"
                      onClick={() => moveChallenge(index, 1)}
                      disabled={busy || index === current.challenges.length - 1}
                    >
                      {t("moveDown")}
                    </button>
                    <button
                      type="button"
                      className="danger"
                      onClick={() =>
                        void storeRows(
                          current.challenges
                            .filter((row) => row.entry_id !== item.entry_id)
                            .map((row) => ({ id: row.id, entry_id: row.entry_id })),
                        )
                      }
                      disabled={busy}
                    >
                      {t("removeMember")}
                    </button>
                  </div>
                </li>
              ))}
            </ol>
          </section>
          <form className="stage-form path-panel path-tone-3" onSubmit={(event) => void saveAssignments(event)}>
              <h2>{t("assignment")}</h2>
              <p>{t("assignNote")}</p>
              {savedNote ? <p className="path-note">{savedNote}</p> : null}
              {communities.length === 0 ? <p>{t("needCommunity")}</p> : null}
              {communities.map((community) => {
                const people = communityPeople[community.id] ?? []
                return (
                  <div key={community.id} className="community-block">
                    <label className="check-line">
                      <input
                        type="checkbox"
                        checked={communityIds.includes(community.id)}
                        onChange={() =>
                          setCommunityIds((currentIds) =>
                            currentIds.includes(community.id)
                              ? currentIds.filter((item) => item !== community.id)
                              : [...currentIds, community.id],
                          )
                        }
                      />
                      <span className="community-block-name">
                        <strong>{community.name}</strong>
                        <span>{t(people.length === 1 ? "countStudent" : "countStudents", { count: people.length })}</span>
                      </span>
                    </label>
                    {people.length > 0 ? (
                      <ul className="community-members">
                        {people.map((person) => (
                          <li key={person.id}>
                            <strong>{person.display_name}</strong>
                            <span>{person.email}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="community-members-empty">{t("communityHasNoStudents")}</p>
                    )}
                  </div>
                )
              })}
              {students.length > 0 ? (
                <ul className="assign-people">
                  {students.map((person) => (
                    <li key={person.id} className="assign-person">
                      <span>
                        <strong>{person.display_name}</strong>
                        <span className="roster-meta">{person.email}</span>
                      </span>
                      <button
                        type="button"
                        className="danger"
                        onClick={() => setStudents((currentStudents) => currentStudents.filter((item) => item.id !== person.id))}
                      >
                        {t("removeMember")}
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>{t("nobodyAssigned")}</p>
              )}
              <div className="assign-row">
                <label>
                  {t("communityWord")}
                  <select value={groupId} onChange={(event) => void loadMembers(event.target.value)}>
                    <option value="">{t("pickCommunityShort")}</option>
                    {communities.map((community) => (
                      <option key={community.id} value={community.id}>
                        {community.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  {t("studentWord")}
                  <select value={studentId} onChange={(event) => setStudentId(event.target.value)}>
                    <option value="">{t("pickStudent")}</option>
                    {members.map((person) => (
                      <option key={person.id} value={person.id}>
                        {person.display_name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="practice-actions">
                <button type="button" onClick={addStudent} disabled={!studentId}>
                  {t("assignStudent")}
                </button>
                <button type="submit" className="primary" disabled={busy}>
                  {t("saveAssignment")}
                </button>
              </div>
          </form>
          <section className="path-panel path-tone-danger">
            <h2>{t("deleteWord")}</h2>
            <p>{t("deletePathNote")}</p>
            <div className="practice-actions">
              {confirmDelete ? (
                <>
                  <button type="button" className="danger" onClick={() => void removePath()} disabled={busy}>
                    {t("confirmDeletePath")}
                  </button>
                  <button type="button" onClick={() => setConfirmDelete(false)} disabled={busy}>
                    {t("cancel")}
                  </button>
                </>
              ) : (
                <button type="button" className="danger" onClick={() => setConfirmDelete(true)} disabled={busy}>
                  {t("deletePath")}
                </button>
              )}
            </div>
          </section>
        </main>
      </>
    )
  }

  return (
    <>
      <section className="enunciado path-intro">
        <div>
          <p className="enunciado-kicker">{t("routes")}</p>
          <h2>{t("createAndAssign")}</h2>
          <p>{t("pathIntro")}</p>
        </div>
      </section>
      <main className="lab-main path-editor">
        {error ? <p className="error">{error}</p> : null}
        <form className="stage-form path-panel path-tone-1" onSubmit={(event) => void createPath(event)}>
          <h2>{t("newPath")}</h2>
          <p>{t("pathNameNote")}</p>
          <label>
            {t("nameWord")}
            <input value={name} onChange={(event) => setName(event.target.value)} maxLength={120} required />
          </label>
          <label>
            {t("description")}
            <textarea value={description} onChange={(event) => setDescription(event.target.value)} rows={3} maxLength={2000} />
          </label>
          <div className="practice-actions">
            <button type="submit" className="primary" disabled={busy || !name.trim()}>
              {t("createPath")}
            </button>
          </div>
        </form>
        <section className="path-panel path-tone-2">
          <h2>{t("yourPaths")}</h2>
          {paths && paths.length === 0 ? <p className="roster-empty">{t("noPathsYet")}</p> : null}
          <div className="path-board">
            {paths?.map((path) => (
              <button key={path.id} type="button" className="path-card" onClick={() => void openPath(path.id)} disabled={busy}>
                <span className="path-card-copy">
                  <span className="path-card-title">
                    <strong>{path.name}</strong>
                    <span className={path.is_published ? "roster-state roster-state-completed" : "roster-state roster-state-locked"}>
                      {path.is_published ? t("published") : t("draft")}
                    </span>
                  </span>
                  {path.description ? <span className="path-card-desc">{path.description}</span> : null}
                  <span className="path-stats">
                    <span>{t(path.challenge_count === 1 ? "countChallenge" : "countChallenges", { count: path.challenge_count })}</span>
                    <span>{t(path.community_count === 1 ? "countCommunity" : "countCommunities", { count: path.community_count })}</span>
                    <span>{t(path.student_count === 1 ? "countStudent" : "countStudents", { count: path.student_count })}</span>
                  </span>
                </span>
                <span className="path-card-go">{t("edit")}</span>
              </button>
            ))}
          </div>
        </section>
      </main>
    </>
  )
}
