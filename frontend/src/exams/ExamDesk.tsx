import { useEffect, useMemo, useRef, useState } from "react"

import { accessOf, api, ApiError, type Account, type CommunitySummary, type Person } from "../api"
import { translatedMessage, useLocale, useT, type MessageKey } from "../i18n"
import { saveDownload } from "../saveFile"
import { AccountIdentity } from "../shell/Identity"
import { Logo } from "../shell/Logo"
import { subjectsForMenu, type SubjectId, type SubjectSpec } from "../subjects/catalog"
import {
  examAttempt,
  examClose,
  examCreate,
  examExport,
  examGrade,
  examGrades,
  examImport,
  examList,
  examMine,
  examNotices,
  examOpen,
  examPublish,
  examReadNotices,
  examRemove,
  examResults,
  examSave,
  examStart,
  examSubmit,
  examUpdate,
} from "./api"
import { AnswerField, QuestionEditor, blankQuestion, describeAnswer, initialAnswer, kindKey, KINDS } from "./questions"
import type { AttemptQuestion, AttemptView, ExamCard, ExamDetail, ExamKind, ExamNotice, ExamQuestion, ExamResults, ExamWrite } from "./types"
import "./exam.css"

const SUBJECT_KEY: Record<string, MessageKey> = {
  fundamentos: "subjectFundamentos",
  bases: "subjectBases",
  objetos: "subjectObjects",
  software: "subjectSoftware",
}

function subjectName(t: (key: MessageKey) => string, id: string) {
  const key = SUBJECT_KEY[id]
  return key ? t(key) : id
}

function localInput(iso: string | null): string {
  if (!iso) return ""
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ""
  const pad = (value: number) => String(value).padStart(2, "0")
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function fromLocal(value: string): string | null {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return null
  return date.toISOString()
}

function stamp(iso: string | null, locale: string): string {
  if (!iso) return "—"
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return "—"
  return date.toLocaleString(locale === "en" ? "en" : "es", { dateStyle: "medium", timeStyle: "short" })
}

function remain(deadline: string | null): string {
  if (!deadline) return ""
  const ms = new Date(deadline).getTime() - Date.now()
  const total = Math.max(0, Math.floor(ms / 1000))
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const seconds = total % 60
  const pad = (value: number) => String(value).padStart(2, "0")
  return hours > 0 ? `${hours}:${pad(minutes)}:${pad(seconds)}` : `${pad(minutes)}:${pad(seconds)}`
}

function prepare(view: AttemptView): AttemptView {
  return { ...view, questions: view.questions.map((question) => ({ ...question, answer: initialAnswer(question) })) }
}

function packet(questions: AttemptQuestion[]) {
  return questions.map((question) => ({ question_id: question.id, answer: question.answer }))
}

function whole(value: string): number | null {
  if (!value.trim()) return null
  const number = Number(value)
  return Number.isInteger(number) ? number : null
}

function writeOf(detail: ExamDetail): ExamWrite {
  return {
    title: detail.title,
    instructions: detail.instructions,
    subject: detail.subject,
    community_id: detail.community_id,
    opens_at: detail.opens_at,
    closes_at: detail.closes_at,
    duration_minutes: detail.duration_minutes,
    attempts_allowed: detail.attempts_allowed,
    grading_method: detail.grading_method,
    shuffle_questions: detail.shuffle_questions,
    shuffle_choices: detail.shuffle_choices,
    navigation: detail.navigation,
    one_per_page: detail.one_per_page,
    grade_to_pass: detail.grade_to_pass,
    show_grade: detail.show_grade,
    audience: detail.audience,
    student_ids: detail.student_ids,
    questions: detail.questions,
  }
}

export function ExamDesk({
  account,
  onAccount,
  onBack,
}: {
  account: Account
  onAccount: (account: Account) => void
  onBack: () => void
}) {
  const t = useT()
  const locale = useLocale()
  const teacher = account.role === "teacher"
  const subjects = subjectsForMenu(accessOf(account).features, "exams")
  const [error, setError] = useState("")
  const [info, setInfo] = useState("")
  const [loading, setLoading] = useState(true)
  const [summaries, setSummaries] = useState<ExamDetail["id"][]>([])
  const [owned, setOwned] = useState<Awaited<ReturnType<typeof examList>>["results"]>([])
  const [cards, setCards] = useState<ExamCard[]>([])
  const [notices, setNotices] = useState<ExamNotice[]>([])
  const [communities, setCommunities] = useState<CommunitySummary[]>([])
  const [editing, setEditing] = useState<ExamDetail | null>(null)
  const [draftId, setDraftId] = useState("")
  const [playing, setPlaying] = useState<AttemptView | null>(null)
  const [results, setResults] = useState<ExamResults | null>(null)
  const [page, setPage] = useState(0)
  const [clock, setClock] = useState("")
  const expired = useRef("")

  function fail(caught: unknown) {
    setError(caught instanceof ApiError ? translatedMessage(caught.message) : t("examsLoadError"))
  }

  async function reload() {
    setError("")
    if (teacher) {
      const [list, notes] = await Promise.all([examList(), examNotices()])
      setOwned(list.results)
      setSummaries(list.results.map((item) => item.id))
      setNotices(notes.results)
      try {
        setCommunities((await api.communities()).results)
      } catch {
        setCommunities([])
      }
    } else {
      const [mine, notes] = await Promise.all([examMine(), examNotices()])
      setCards(mine.results)
      setNotices(notes.results)
    }
  }

  useEffect(() => {
    let alive = true
    void reload()
      .catch((caught: unknown) => {
        if (alive) fail(caught)
      })
      .finally(() => {
        if (alive) setLoading(false)
      })
    return () => {
      alive = false
    }
  }, [teacher])

  useEffect(() => {
    if (!playing || playing.state !== "open" || !playing.deadline) return
    const tick = () => setClock(remain(playing.deadline))
    tick()
    const timer = window.setInterval(tick, 1000)
    return () => window.clearInterval(timer)
  }, [playing?.id, playing?.deadline, playing?.state])

  useEffect(() => {
    if (!playing || playing.state !== "open" || clock !== "00:00") return
    if (expired.current === playing.id) return
    expired.current = playing.id
    void submit(true)
  }, [clock, playing?.id, playing?.state])

  const total = useMemo(
    () => (editing ? editing.questions.reduce((sum, question) => sum + Number(question.points || 0), 0) : 0),
    [editing],
  )

  async function openEditor(id?: string) {
    setError("")
    setInfo("")
    setPlaying(null)
    setResults(null)
    if (!id) {
      const subject = (subjects.find((item) => item.id === communities[0]?.subject)?.id ??
        subjects[0]?.id ??
        "fundamentos") as SubjectId
      const group = communities.find((item) => item.subject === subject)
      setDraftId("")
      setEditing({
        id: "",
        title: "",
        instructions: "",
        subject,
        community_id: group?.id ?? "",
        community_name: group?.name ?? "",
        opens_at: null,
        closes_at: null,
        duration_minutes: 50,
        attempts_allowed: 1,
        grading_method: "highest",
        shuffle_questions: false,
        shuffle_choices: true,
        navigation: "free",
        one_per_page: false,
        grade_to_pass: 60,
        show_grade: "immediate",
        audience: "all",
        student_ids: [],
        published: false,
        question_count: 1,
        attempt_count: 0,
        student_count: group?.student_count ?? 0,
        max_points: 1,
        questions: [blankQuestion("choice")],
        notified: 0,
      })
      return
    }
    try {
      const detail = await examOpen(id)
      setDraftId(detail.id)
      setEditing(detail)
    } catch (caught) {
      fail(caught)
    }
  }

  async function saveDraft(publish: boolean) {
    if (!editing) return
    setError("")
    setInfo("")
    const body = writeOf({
      ...editing,
      opens_at: editing.opens_at,
      closes_at: editing.closes_at,
    })
    try {
      let saved = draftId ? await examUpdate(draftId, editing.attempt_count > 0 ? {
        opens_at: body.opens_at,
        closes_at: body.closes_at,
        show_grade: body.show_grade,
        grade_to_pass: body.grade_to_pass,
      } : body) : await examCreate(body)
      if (publish) saved = await examPublish(saved.id)
      setDraftId(saved.id)
      setEditing(saved)
      setInfo(publish ? t("examsPublished") : t("examsSaved"))
      await reload()
    } catch (caught) {
      fail(caught)
    }
  }

  async function removeExam() {
    if (!draftId || !editing) return
    if (!window.confirm(t("examsDeleteConfirm", { title: editing.title || t("examsTitle") }))) return
    try {
      await examRemove(draftId)
      setEditing(null)
      setDraftId("")
      await reload()
    } catch (caught) {
      fail(caught)
    }
  }

  async function download(format: "json" | "moodle" | "gift") {
    if (!draftId) return
    try {
      const file = await examExport(draftId, format)
      await saveDownload(file.filename, file.content)
    } catch (caught) {
      fail(caught)
    }
  }

  async function begin(card: ExamCard) {
    setError("")
    try {
      const view = card.open_attempt_id ? await examAttempt(card.open_attempt_id) : await examStart(card.id)
      setPlaying(prepare(view))
      setPage(0)
      setResults(null)
    } catch (caught) {
      fail(caught)
    }
  }

  async function review(id: string) {
    setError("")
    try {
      setPlaying(prepare(await examAttempt(id)))
      setPage(0)
    } catch (caught) {
      fail(caught)
    }
  }

  function updateAnswer(questionId: string, answer: Record<string, unknown>) {
    setPlaying((current) =>
      current
        ? { ...current, questions: current.questions.map((question) => (question.id === questionId ? { ...question, answer } : question)) }
        : current,
    )
  }

  async function persist() {
    if (!playing) return
    setError("")
    try {
      const view = await examSave(playing.id, packet(playing.questions))
      setPlaying(prepare(view))
      setInfo(t("examsSaved"))
    } catch (caught) {
      fail(caught)
    }
  }

  async function submit(auto = false) {
    if (!playing) return
    if (!auto && !window.confirm(t("examsSubmitConfirm"))) return
    setError("")
    try {
      const view = await examSubmit(playing.id, packet(playing.questions))
      setPlaying(prepare(view))
      await reload()
    } catch (caught) {
      fail(caught)
    }
  }

  async function openGrades(id: string) {
    setError("")
    setEditing(null)
    setPlaying(null)
    try {
      setResults(await examResults(id))
    } catch (caught) {
      fail(caught)
    }
  }

  async function downloadGrades() {
    if (!results) return
    try {
      const file = await examGrades(results.exam.id)
      await saveDownload(file.filename, file.content)
    } catch (caught) {
      fail(caught)
    }
  }

  async function closeWindow() {
    if (!results) return
    try {
      await examClose(results.exam.id)
      setResults(await examResults(results.exam.id))
      await reload()
    } catch (caught) {
      fail(caught)
    }
  }

  const screen = editing ? "edit" : playing ? "play" : results ? "grades" : "list"
  return (
    <div className="shell exam-shell">
      <header className="topbar topbar-editor">
        <div className="brand">
          <h1>
            <Logo mark />
            {t("exams")}
          </h1>
          <AccountIdentity account={account} onAccount={onAccount} stats="days" />
        </div>
        <div className="actions">
          {screen !== "list" ? (
            <button
              className="top-leave"
              type="button"
              onClick={() => {
                setEditing(null)
                setPlaying(null)
                setResults(null)
                setInfo("")
                setError("")
              }}
            >
              {t("examsBack")}
            </button>
          ) : null}
          <button className="top-leave" type="button" onClick={onBack}>
            {t("backToSubjects")}
          </button>
        </div>
      </header>
      <div className="exam-body">
        {error ? <p className="error">{error}</p> : null}
        {info ? <p className="note">{info}</p> : null}
        {loading && screen === "list" ? <p className="note">{t("examsLoading")}</p> : null}
        {screen === "list" && teacher ? (
          <TeacherList
            exams={owned.filter((item) => summaries.includes(item.id))}
            communities={communities}
            subjects={subjects}
            t={t}
            locale={locale}
            onNew={() => void openEditor()}
            onOpen={(id) => void openEditor(id)}
            onGrades={(id) => void openGrades(id)}
            onImported={(detail) => {
              setDraftId(detail.id)
              setEditing(detail)
              void reload()
            }}
            onFail={fail}
          />
        ) : null}
        {screen === "list" && !teacher ? (
          <StudentList
            cards={cards}
            notices={notices}
            t={t}
            locale={locale}
            onStart={(card) => void begin(card)}
            onReview={(id) => void review(id)}
            onRead={() => {
              void examReadNotices().then((page) => setNotices(page.results)).catch(fail)
            }}
          />
        ) : null}
        {editing ? (
          <Editor
            exam={editing}
            communities={communities}
            subjects={subjectsForMenu(accessOf(account).features, "exams", editing.subject)}
            total={total}
            t={t}
            locked={editing.attempt_count > 0}
            onChange={setEditing}
            onSave={() => void saveDraft(false)}
            onPublish={() => {
              if (window.confirm(t("examsPublishConfirm"))) void saveDraft(true)
            }}
            onDelete={() => void removeExam()}
            onExport={(format) => void download(format)}
          />
        ) : null}
        {playing ? (
          <Player
            attempt={playing}
            page={page}
            clock={clock}
            t={t}
            locale={locale}
            onPage={setPage}
            onAnswer={updateAnswer}
            onSave={() => void persist()}
            onSubmit={() => void submit(false)}
          />
        ) : null}
        {results ? (
          <Grades
            results={results}
            t={t}
            locale={locale}
            onDownload={() => void downloadGrades()}
            onClose={() => void closeWindow()}
            onGraded={() => void openGrades(results.exam.id)}
            onFail={fail}
          />
        ) : null}
      </div>
    </div>
  )
}

function TeacherList({
  exams,
  communities,
  subjects,
  t,
  locale,
  onNew,
  onOpen,
  onGrades,
  onImported,
  onFail,
}: {
  exams: Awaited<ReturnType<typeof examList>>["results"]
  communities: CommunitySummary[]
  subjects: readonly SubjectSpec[]
  t: ReturnType<typeof useT>
  locale: string
  onNew: () => void
  onOpen: (id: string) => void
  onGrades: (id: string) => void
  onImported: (detail: ExamDetail) => void
  onFail: (caught: unknown) => void
}) {
  const [subject, setSubject] = useState<SubjectId>(subjects[0]?.id ?? "fundamentos")
  const [communityId, setCommunityId] = useState("")
  const [format, setFormat] = useState("")
  const [text, setText] = useState("")
  const [title, setTitle] = useState("")
  const groups = communities.filter((item) => item.subject === subject)
  useEffect(() => {
    setCommunityId(groups[0]?.id ?? "")
  }, [subject, communities])
  return (
    <div className="exam-home">
      <div className="exam-toolbar">
        <div>
          <h2>{t("examsTitle")}</h2>
          <p className="note">{t("examsLead")}</p>
        </div>
        <button className="primary" type="button" onClick={onNew}>{t("examsNew")}</button>
      </div>
      {exams.length === 0 ? <p className="note">{t("examsEmpty")}</p> : null}
      <div className="exam-grid">
        {exams.map((exam) => (
          <article className="exam-card" key={exam.id}>
            <strong>{exam.title}</strong>
            <span>{subjectName(t, exam.subject)} · {exam.community_name}</span>
            <span>{exam.published ? t("examsAssigned") : t("examsDraft")}</span>
            <span>
              {t("examsQuestionsShort", { count: exam.question_count })} · {t("examsStudents", { count: exam.student_count })}
            </span>
            <span>{stamp(exam.opens_at, locale)} — {stamp(exam.closes_at, locale)}</span>
            <div className="exam-inline">
              <button type="button" onClick={() => onOpen(exam.id)}>{t("examsOpen")}</button>
              <button type="button" onClick={() => onGrades(exam.id)}>{t("examsGrades")}</button>
            </div>
          </article>
        ))}
      </div>
      <form
        className="exam-panel"
        onSubmit={(event) => {
          event.preventDefault()
          void examImport({
            format: format || undefined,
            text,
            subject,
            community_id: communityId,
            title,
          }).then(onImported).catch(onFail)
        }}
      >
        <h3>{t("examsImport")}</h3>
        <p className="note">{t("examsExportNote")}</p>
        <div className="exam-inline">
          <label>
            {t("examsSubject")}
            <select value={subject} onChange={(event) => setSubject(event.target.value as SubjectId)}>
              {subjects.map((item) => (
                <option key={item.id} value={item.id}>{t(item.nameKey)}</option>
              ))}
            </select>
          </label>
          <label>
            {t("examsGroup")}
            <select value={communityId} onChange={(event) => setCommunityId(event.target.value)}>
              {groups.map((item) => (
                <option key={item.id} value={item.id}>{item.name}</option>
              ))}
            </select>
          </label>
          <label>
            {t("examsFormat")}
            <select value={format} onChange={(event) => setFormat(event.target.value)}>
              <option value="">{t("examsFormatAuto")}</option>
              <option value="json">JSON</option>
              <option value="moodle">Moodle XML</option>
              <option value="gift">GIFT</option>
              <option value="csv">CSV</option>
              <option value="forms">Microsoft Forms</option>
            </select>
          </label>
        </div>
        <label>
          {t("examsTitleField")}
          <input value={title} onChange={(event) => setTitle(event.target.value)} />
        </label>
        <label>
          {t("examsImportText")}
          <textarea value={text} rows={6} onChange={(event) => setText(event.target.value)} />
        </label>
        <label className="exam-file">
          {t("examsImportFile")}
          <input
            type="file"
            accept=".json,.xml,.txt,.csv,.gift"
            onChange={(event) => {
              const file = event.target.files?.[0]
              if (!file) return
              void file.text().then(setText)
            }}
          />
        </label>
        <button className="primary" type="submit" disabled={!communityId || !text.trim()}>{t("examsImport")}</button>
      </form>
    </div>
  )
}

function StudentList({
  cards,
  notices,
  t,
  locale,
  onStart,
  onReview,
  onRead,
}: {
  cards: ExamCard[]
  notices: ExamNotice[]
  t: ReturnType<typeof useT>
  locale: string
  onStart: (card: ExamCard) => void
  onReview: (id: string) => void
  onRead: () => void
}) {
  return (
    <div className="exam-home">
      <h2>{t("examsTitle")}</h2>
      <p className="note">{t("examsStudentLead")}</p>
      {notices.length ? (
        <div className="exam-panel">
          <div className="exam-toolbar">
            <h3>{t("examsNotices")}</h3>
            <button type="button" onClick={onRead}>{t("examsMarkRead")}</button>
          </div>
          <ul className="exam-notices">
            {notices.map((notice) => (
              <li key={notice.id} data-read={notice.read}>
                {notice.kind === "assigned"
                  ? t("examsNoticeAssigned", { title: notice.title, group: notice.group, subject: subjectName(t, notice.subject) })
                  : notice.percent == null
                    ? t("examsNoticeGradedHidden", { title: notice.title })
                    : t("examsNoticeGraded", { title: notice.title, percent: notice.percent })}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {cards.length === 0 ? <p className="note">{t("examsEmptyStudent")}</p> : null}
      <div className="exam-grid">
        {cards.map((card) => {
          const reviewId = card.latest_attempt_id || card.official.attempt_id
          return (
            <article className="exam-card" key={card.id}>
              <strong>{card.title}</strong>
              <span>{subjectName(t, card.subject)} · {card.community_name}</span>
              <span>
                {card.window === "upcoming" ? t("examsUpcoming") : card.window === "closed" ? t("examsClosed") : t("examsOpenNow")}
                {card.duration_minutes ? ` · ${t("examsMinutes", { count: card.duration_minutes })}` : ` · ${t("examsUnlimited")}`}
              </span>
              <span>{stamp(card.opens_at, locale)} — {stamp(card.closes_at, locale)}</span>
              <span>{t("examsAttemptsUsed", { used: card.attempts_used, total: card.attempts_allowed })}</span>
              {card.official.pending ? <span>{t("examsPending")}</span> : null}
              {card.official.percent != null ? (
                <span>{t("examsYourGrade")}: {card.official.percent}%</span>
              ) : null}
              <div className="exam-inline">
                {card.open_attempt_id ? (
                  <button className="primary" type="button" onClick={() => onStart(card)}>{t("examsContinue")}</button>
                ) : null}
                {card.can_start ? (
                  <button className="primary" type="button" onClick={() => onStart(card)}>{t("examsStart")}</button>
                ) : null}
                {reviewId ? (
                  <button type="button" onClick={() => onReview(reviewId)}>{t("examsReview")}</button>
                ) : null}
              </div>
            </article>
          )
        })}
      </div>
    </div>
  )
}

function Editor({
  exam,
  communities,
  subjects,
  total,
  t,
  locked,
  onChange,
  onSave,
  onPublish,
  onDelete,
  onExport,
}: {
  exam: ExamDetail
  communities: CommunitySummary[]
  subjects: readonly SubjectSpec[]
  total: number
  t: ReturnType<typeof useT>
  locked: boolean
  onChange: (exam: ExamDetail) => void
  onSave: () => void
  onPublish: () => void
  onDelete: () => void
  onExport: (format: "json" | "moodle" | "gift") => void
}) {
  const groups = communities.filter((item) => item.subject === exam.subject)
  const [students, setStudents] = useState<Person[]>([])
  useEffect(() => {
    if (!exam.community_id) {
      setStudents([])
      return
    }
    let alive = true
    void api.community(exam.community_id).then((detail) => {
      if (alive) setStudents(detail.students)
    }).catch(() => {
      if (alive) setStudents([])
    })
    return () => {
      alive = false
    }
  }, [exam.community_id])
  function setQuestion(index: number, question: ExamQuestion) {
    onChange({ ...exam, questions: exam.questions.map((item, itemIndex) => (itemIndex === index ? question : item)) })
  }
  return (
    <form
      className="exam-editor"
      onSubmit={(event) => {
        event.preventDefault()
        onSave()
      }}
    >
      <h2>{exam.title || t("examsNew")}</h2>
      {locked ? <p className="note">{t("examsLocked")}</p> : null}
      <div className="exam-inline">
        <label>
          {t("examsSubject")}
          <select
            disabled={locked}
            value={exam.subject}
            onChange={(event) => {
              const subject = event.target.value
              const group = communities.find((item) => item.subject === subject)
              onChange({ ...exam, subject, community_id: group?.id ?? "", community_name: group?.name ?? "", student_ids: [] })
            }}
          >
            {subjects.map((item) => (
              <option key={item.id} value={item.id}>{t(item.nameKey)}</option>
            ))}
          </select>
        </label>
        <label>
          {t("examsGroup")}
          <select
            disabled={locked}
            value={exam.community_id}
            onChange={(event) => {
              const group = groups.find((item) => item.id === event.target.value)
              onChange({ ...exam, community_id: event.target.value, community_name: group?.name ?? "", student_ids: [] })
            }}
          >
            {groups.map((item) => (
              <option key={item.id} value={item.id}>{item.name}</option>
            ))}
          </select>
        </label>
      </div>
      {groups.length === 0 ? <p className="note">{t("examsNoGroups")}</p> : null}
      <label>
        {t("examsTitleField")}
        <input disabled={locked} value={exam.title} required onChange={(event) => onChange({ ...exam, title: event.target.value })} />
      </label>
      <label>
        {t("examsInstructions")}
        <textarea disabled={locked} rows={3} value={exam.instructions} onChange={(event) => onChange({ ...exam, instructions: event.target.value })} />
      </label>
      <fieldset disabled={locked}>
        <legend>{t("examsAudience")}</legend>
        <p className="note">{t("examsAudienceHint")}</p>
        <label className="exam-check">
          <input type="radio" checked={exam.audience === "all"} onChange={() => onChange({ ...exam, audience: "all", student_ids: [] })} />
          {t("examsAudienceAll")}
        </label>
        <label className="exam-check">
          <input type="radio" checked={exam.audience === "selected"} onChange={() => onChange({ ...exam, audience: "selected" })} />
          {t("examsAudienceSelected")}
        </label>
        {exam.audience === "selected" ? (
          students.length === 0 ? <p className="note">{t("examsNoStudents")}</p> : (
            <div className="exam-students">
              {students.map((student) => (
                <label className="exam-check" key={student.id}>
                  <input
                    type="checkbox"
                    checked={exam.student_ids.includes(student.id)}
                    onChange={(event) => {
                      const ids = event.target.checked
                        ? [...exam.student_ids, student.id]
                        : exam.student_ids.filter((id) => id !== student.id)
                      onChange({ ...exam, student_ids: ids })
                    }}
                  />
                  {student.display_name} · {student.email}
                </label>
              ))}
            </div>
          )
        ) : null}
      </fieldset>
      <div className="exam-inline">
        <label>
          {t("examsOpens")}
          <input type="datetime-local" value={localInput(exam.opens_at)} onChange={(event) => onChange({ ...exam, opens_at: fromLocal(event.target.value) })} />
        </label>
        <label>
          {t("examsCloses")}
          <input type="datetime-local" value={localInput(exam.closes_at)} onChange={(event) => onChange({ ...exam, closes_at: fromLocal(event.target.value) })} />
        </label>
        <label>
          {t("examsDuration")}
          <input
            type="number"
            min={1}
            max={480}
            disabled={locked}
            value={exam.duration_minutes ?? ""}
            placeholder={t("examsUnlimited")}
            onChange={(event) => onChange({ ...exam, duration_minutes: whole(event.target.value) })}
          />
        </label>
        <label>
          {t("examsAttempts")}
          <input
            type="number"
            min={1}
            max={20}
            disabled={locked}
            value={exam.attempts_allowed}
            onChange={(event) => onChange({ ...exam, attempts_allowed: whole(event.target.value) ?? 1 })}
          />
        </label>
      </div>
      <p className="note">{t("examsDurationHint")}</p>
      <div className="exam-inline">
        <label>
          {t("examsMethod")}
          <select disabled={locked} value={exam.grading_method} onChange={(event) => onChange({ ...exam, grading_method: event.target.value as ExamDetail["grading_method"] })}>
            <option value="highest">{t("examsMethodHighest")}</option>
            <option value="average">{t("examsMethodAverage")}</option>
            <option value="first">{t("examsMethodFirst")}</option>
            <option value="last">{t("examsMethodLast")}</option>
          </select>
        </label>
        <label>
          {t("examsNavigation")}
          <select disabled={locked} value={exam.navigation} onChange={(event) => onChange({ ...exam, navigation: event.target.value as ExamDetail["navigation"] })}>
            <option value="free">{t("examsNavFree")}</option>
            <option value="sequential">{t("examsNavSequential")}</option>
          </select>
        </label>
        <label>
          {t("examsShowGrade")}
          <select value={exam.show_grade} onChange={(event) => onChange({ ...exam, show_grade: event.target.value as ExamDetail["show_grade"] })}>
            <option value="immediate">{t("examsShowNow")}</option>
            <option value="after_close">{t("examsShowAfterClose")}</option>
          </select>
        </label>
        <label>
          {t("examsPass")}
          <input
            type="number"
            min={0}
            max={100}
            value={exam.grade_to_pass ?? ""}
            onChange={(event) => onChange({ ...exam, grade_to_pass: event.target.value === "" ? null : Number(event.target.value) })}
          />
        </label>
      </div>
      <p className="note">{t("examsPassHint")}</p>
      <div className="exam-inline">
        <label className="exam-check">
          <input type="checkbox" disabled={locked} checked={exam.shuffle_questions} onChange={(event) => onChange({ ...exam, shuffle_questions: event.target.checked })} />
          {t("examsShuffleQuestions")}
        </label>
        <label className="exam-check">
          <input type="checkbox" disabled={locked} checked={exam.shuffle_choices} onChange={(event) => onChange({ ...exam, shuffle_choices: event.target.checked })} />
          {t("examsShuffleChoices")}
        </label>
        <label className="exam-check">
          <input type="checkbox" disabled={locked} checked={exam.one_per_page} onChange={(event) => onChange({ ...exam, one_per_page: event.target.checked })} />
          {t("examsOnePerPage")}
        </label>
      </div>
      <div className="exam-toolbar">
        <h3>{t("examsQuestions")}</h3>
        <span>{t("examsPointsTotal", { count: total })}</span>
      </div>
      {exam.questions.map((question, index) => (
        <article className="exam-question" key={question.id}>
          <div className="exam-toolbar">
            <strong>{index + 1}</strong>
            <select
              disabled={locked}
              value={question.kind}
              onChange={(event) => setQuestion(index, { ...blankQuestion(event.target.value as ExamKind), id: question.id, prompt: question.prompt, points: question.points })}
            >
              {KINDS.map((kind) => (
                <option key={kind} value={kind}>{t(kindKey(kind))}</option>
              ))}
            </select>
            <button type="button" disabled={locked || index === 0} onClick={() => {
              const questions = exam.questions.slice()
              const [row] = questions.splice(index, 1)
              questions.splice(index - 1, 0, row)
              onChange({ ...exam, questions })
            }}>{t("examsMoveUp")}</button>
            <button type="button" disabled={locked} onClick={() => onChange({ ...exam, questions: exam.questions.filter((_, itemIndex) => itemIndex !== index) })}>
              {t("examsRemove")}
            </button>
          </div>
          <fieldset disabled={locked}>
            <QuestionEditor question={question} t={t} onChange={(next) => setQuestion(index, next)} />
          </fieldset>
        </article>
      ))}
      <button type="button" disabled={locked} onClick={() => onChange({ ...exam, questions: [...exam.questions, blankQuestion("choice")] })}>
        {t("examsAddQuestion")}
      </button>
      <div className="exam-inline">
        <button className="primary" type="submit">{locked ? t("examsSaveDates") : t("examsSave")}</button>
        <button type="button" onClick={onPublish}>{exam.published ? t("examsNotify") : t("examsPublish")}</button>
        {exam.id ? <button type="button" onClick={onDelete}>{t("examsDelete")}</button> : null}
        {exam.id ? <button type="button" onClick={() => onExport("json")}>{t("examsExportJson")}</button> : null}
        {exam.id ? <button type="button" onClick={() => onExport("moodle")}>{t("examsExportMoodle")}</button> : null}
        {exam.id ? <button type="button" onClick={() => onExport("gift")}>{t("examsExportGift")}</button> : null}
      </div>
      <p className="note">{t("examsExportNote")}</p>
    </form>
  )
}

function Player({
  attempt,
  page,
  clock,
  t,
  locale,
  onPage,
  onAnswer,
  onSave,
  onSubmit,
}: {
  attempt: AttemptView
  page: number
  clock: string
  t: ReturnType<typeof useT>
  locale: string
  onPage: (page: number) => void
  onAnswer: (questionId: string, answer: Record<string, unknown>) => void
  onSave: () => void
  onSubmit: () => void
}) {
  const paged = attempt.one_per_page || attempt.navigation === "sequential"
  const current = Math.min(page, Math.max(0, attempt.questions.length - 1))
  const visible = paged ? attempt.questions.slice(current, current + 1) : attempt.questions
  const done = attempt.state !== "open"
  return (
    <div className="exam-player">
      <div className="exam-toolbar">
        <div>
          <h2>{attempt.title}</h2>
          <p className="note">{attempt.instructions}</p>
        </div>
        {attempt.state === "open" && clock ? <p className="exam-timer" aria-live="polite">{t("examsTimeLeft", { time: clock })}</p> : null}
      </div>
      {done && attempt.graded_visible ? (
        <p className="exam-score">
          {t("examsYourGrade")}: {attempt.percent}% ({attempt.score}/{attempt.max_score})
          {attempt.passed == null ? "" : attempt.passed ? ` · ${t("examsPassed")}` : ` · ${t("examsFailed")}`}
        </p>
      ) : null}
      {done && attempt.pending ? <p className="note">{t("examsPending")}</p> : null}
      {done && !attempt.graded_visible ? <p className="note">{t("examsResultHidden")}</p> : null}
      {visible.map((question, index) => (
        <article className="exam-question" key={question.id}>
          <h3>{paged ? t("examsQuestionOf", { index: current + 1, total: attempt.questions.length }) : `${index + 1}.`} {question.prompt}</h3>
          <p className="note">{t(kindKey(question.kind))} · {t("examsPointsTotal", { count: question.points })}</p>
          {done ? (
            <div className="exam-review">
              <p><strong>{t("examsYourAnswer")}</strong> {describeAnswer(question) || "—"}</p>
              {attempt.graded_visible && question.score != null ? <p>{t("examsScore")}: {question.score}/{question.points}</p> : null}
              {question.pending ? <p>{t("examsManual")}</p> : null}
              {question.comment ? <p>{question.comment}</p> : null}
              {question.feedback && attempt.graded_visible ? <p>{question.feedback}</p> : null}
              {question.detail?.cases?.map((item, caseIndex) => (
                <p key={caseIndex}>{item.name}: {item.ok ? t("examsOk") : t("examsFail")}</p>
              ))}
            </div>
          ) : (
            <AnswerField question={question} t={t} onChange={(answer) => onAnswer(question.id, answer)} />
          )}
        </article>
      ))}
      {paged && !done ? (
        <div className="exam-inline">
          <button type="button" disabled={current === 0} onClick={() => onPage(current - 1)}>{t("examsPrevious")}</button>
          <button
            type="button"
            disabled={current >= attempt.questions.length - 1 || (attempt.navigation === "sequential" && !hasAnswer(attempt.questions[current]))}
            onClick={() => onPage(current + 1)}
          >
            {t("examsNext")}
          </button>
        </div>
      ) : null}
      {done ? <p className="note">{stamp(attempt.submitted_at, locale)}</p> : (
        <div className="exam-inline">
          <button type="button" onClick={onSave}>{t("examsSaveAnswers")}</button>
          <button className="primary" type="button" onClick={onSubmit}>{t("examsSubmit")}</button>
        </div>
      )}
    </div>
  )
}

function hasAnswer(question: AttemptQuestion | undefined): boolean {
  if (!question) return false
  const answer = question.answer
  if (question.kind === "choice") return typeof answer.option === "string" && answer.option !== ""
  if (question.kind === "multi") return Array.isArray(answer.options) && answer.options.length > 0
  if (question.kind === "true_false") return typeof answer.value === "boolean"
  if (question.kind === "short" || question.kind === "essay") return String(answer.text ?? "").trim() !== ""
  if (question.kind === "numerical") return String(answer.value ?? "").trim() !== ""
  if (question.kind === "case") return String(answer.source ?? "").trim() !== ""
  if (question.kind === "order") return Array.isArray(answer.order) && answer.order.length > 0
  if (question.kind === "matching") return Object.keys((answer.pairs as object) ?? {}).length > 0
  if (question.kind === "cloze") return Object.values((answer.blanks as Record<string, string>) ?? {}).some((value) => value.trim())
  return false
}

function Grades({
  results,
  t,
  locale,
  onDownload,
  onClose,
  onGraded,
  onFail,
}: {
  results: ExamResults
  t: ReturnType<typeof useT>
  locale: string
  onDownload: () => void
  onClose: () => void
  onGraded: () => void
  onFail: (caught: unknown) => void
}) {
  const [openId, setOpenId] = useState("")
  return (
    <div className="exam-grades">
      <div className="exam-toolbar">
        <div>
          <h2>{results.exam.title}</h2>
          <p className="note">{subjectName(t, results.exam.subject)} · {results.exam.community_name}</p>
        </div>
        <div className="exam-inline">
          <button type="button" onClick={onDownload}>{t("examsDownload")}</button>
          <button type="button" onClick={onClose}>{t("examsClose")}</button>
        </div>
      </div>
      <table className="exam-table">
        <thead>
          <tr>
            <th>{t("examsStudentColumn")}</th>
            <th>{t("examsEmailColumn")}</th>
            <th>{t("examsScore")}</th>
            <th>{t("examsStatus")}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {results.rows.map((row) => (
            <tr key={row.student.id}>
              <td>{row.student.display_name}</td>
              <td>{row.student.email}</td>
              <td>{row.official.percent == null ? "—" : `${row.official.percent}%`}</td>
              <td>{row.attempts.length === 0 ? t("examsNotStarted") : row.official.pending ? t("examsPending") : t("examsAssigned")}</td>
              <td>
                {row.attempts.length ? (
                  <button type="button" onClick={() => setOpenId(openId === String(row.student.id) ? "" : String(row.student.id))}>
                    {openId === String(row.student.id) ? t("examsHideAnswers") : t("examsSeeAnswers")}
                  </button>
                ) : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {results.rows.filter((row) => String(row.student.id) === openId).map((row) => (
        <div key={row.student.id}>
          {row.attempts.map((attempt) => (
            <AttemptGrade key={attempt.id} attempt={attempt} t={t} locale={locale} onGraded={onGraded} onFail={onFail} />
          ))}
        </div>
      ))}
    </div>
  )
}

function AttemptGrade({
  attempt,
  t,
  locale,
  onGraded,
  onFail,
}: {
  attempt: AttemptView
  t: ReturnType<typeof useT>
  locale: string
  onGraded: () => void
  onFail: (caught: unknown) => void
}) {
  const [scores, setScores] = useState<Record<string, string>>({})
  const [comments, setComments] = useState<Record<string, string>>({})
  return (
    <article className="exam-question">
      <h3>{t("examsAttempt", { count: attempt.number })} · {stamp(attempt.submitted_at, locale)}</h3>
      <p>{attempt.percent == null ? t("examsPending") : `${attempt.score}/${attempt.max_score} · ${attempt.percent}%`}</p>
      {attempt.questions.map((question) => (
        <div key={question.id} className="exam-review">
          <p><strong>{question.prompt}</strong></p>
          <p>{t("examsYourAnswer")}: {describeAnswer(question) || "—"}</p>
          <p>{t("examsScore")}: {question.score ?? "—"} / {question.points}</p>
          <label>
            {t("examsScore")}
            <input
              type="number"
              min={0}
              max={question.points}
              step={0.5}
              value={scores[question.id] ?? (question.score ?? "")}
              onChange={(event) => setScores({ ...scores, [question.id]: event.target.value })}
            />
          </label>
          <label>
            {t("examsComment")}
            <input value={comments[question.id] ?? question.comment ?? ""} onChange={(event) => setComments({ ...comments, [question.id]: event.target.value })} />
          </label>
        </div>
      ))}
      <button
        type="button"
        onClick={() => {
          const body = attempt.questions
            .filter((question) => scores[question.id] != null && scores[question.id] !== "")
            .map((question) => ({
              question_id: question.id,
              score: Number(scores[question.id]),
              comment: comments[question.id] ?? question.comment ?? "",
            }))
          if (!body.length) return
          void examGrade(attempt.id, body).then(() => onGraded()).catch(onFail)
        }}
      >
        {t("examsApplyGrade")}
      </button>
    </article>
  )
}
