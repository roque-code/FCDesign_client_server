export type ExamKind =
  | "choice"
  | "multi"
  | "true_false"
  | "short"
  | "numerical"
  | "essay"
  | "matching"
  | "order"
  | "cloze"
  | "case"

export type ExamOption = { id: string; text: string; correct?: boolean }
export type ExamPair = { id: string; left: string; right: string }
export type ExamItem = { id: string; text: string }
export type ExamBlank = { id: string; answers: string[] }
export type ExamCase = {
  name: string
  inputs: string[]
  expected: string
  points: number
  hidden: boolean
}
export type ExamTextAnswer = { text: string; fraction: number }
export type ExamNumberAnswer = { value: number; tolerance: number; fraction: number }

export type ExamPayload = {
  options?: ExamOption[]
  correct?: boolean
  answers?: Array<ExamTextAnswer | ExamNumberAnswer>
  case_sensitive?: boolean
  rubric?: string
  pairs?: ExamPair[]
  items?: ExamItem[]
  text?: string
  blanks?: ExamBlank[]
  statement?: string
  starter?: string
  cases?: ExamCase[]
  left?: { id: string; text: string }[]
  right?: { id: string; text: string }[]
  hidden_count?: number
}

export type ExamQuestion = {
  id: string
  kind: ExamKind
  prompt: string
  points: number
  feedback: string
  payload: ExamPayload
}

export type ExamSummary = {
  id: string
  title: string
  subject: string
  community_id: string
  community_name: string
  opens_at: string | null
  closes_at: string | null
  duration_minutes: number | null
  published: boolean
  audience: "all" | "selected"
  question_count: number
  attempt_count: number
  student_count: number
  max_points: number
}

export type ExamDetail = ExamSummary & {
  instructions: string
  attempts_allowed: number
  grading_method: "highest" | "average" | "first" | "last"
  shuffle_questions: boolean
  shuffle_choices: boolean
  navigation: "free" | "sequential"
  one_per_page: boolean
  grade_to_pass: number | null
  show_grade: "immediate" | "after_close"
  student_ids: number[]
  questions: ExamQuestion[]
  notified?: number
}

export type AttemptQuestion = {
  id: string
  kind: ExamKind
  prompt: string
  points: number
  payload: ExamPayload
  answer: Record<string, unknown>
  feedback?: string
  score?: number | null
  pending?: boolean
  comment?: string
  detail?: { cases?: { name?: string; ok?: boolean; hidden?: boolean; output?: string; expected?: string }[] }
}

export type AttemptView = {
  id: string
  exam_id: string
  number: number
  state: "open" | "submitted" | "graded"
  started_at: string
  deadline: string | null
  submitted_at: string | null
  title: string
  instructions: string
  subject: string
  navigation: "free" | "sequential"
  one_per_page: boolean
  graded_visible: boolean
  pending: boolean
  questions: AttemptQuestion[]
  score?: number | null
  max_score?: number | null
  percent?: number | null
  passed?: boolean | null
}

export type ExamCard = {
  id: string
  title: string
  instructions: string
  subject: string
  community_name: string
  opens_at: string | null
  closes_at: string | null
  duration_minutes: number | null
  attempts_allowed: number
  attempts_used: number
  window: "upcoming" | "open" | "closed"
  can_start: boolean
  open_attempt_id: string | null
  latest_attempt_id: string | null
  navigation: "free" | "sequential"
  one_per_page: boolean
  show_grade: "immediate" | "after_close"
  official: {
    percent: number | null
    score: number | null
    max_score: number | null
    passed: boolean | null
    pending: boolean
    attempt_id: string | null
  }
}

export type ExamNotice = {
  id: string
  exam_id: string
  kind: "assigned" | "graded"
  title: string
  subject: string
  group: string
  opens_at: string | null
  closes_at: string | null
  duration_minutes: number | null
  percent: number | null
  created_at: string
  read: boolean
}

export type ExamResultRow = {
  student: { id: number; display_name: string; email: string }
  official: ExamCard["official"]
  attempts: AttemptView[]
}

export type ExamResults = {
  exam: ExamDetail
  questions: ExamQuestion[]
  rows: ExamResultRow[]
}

export type ExamFile = { filename: string; content: string; media_type: string }

export type ExamWrite = {
  title: string
  instructions: string
  subject: string
  community_id: string
  opens_at: string | null
  closes_at: string | null
  duration_minutes: number | null
  attempts_allowed: number
  grading_method: ExamDetail["grading_method"]
  shuffle_questions: boolean
  shuffle_choices: boolean
  navigation: ExamDetail["navigation"]
  one_per_page: boolean
  grade_to_pass: number | null
  show_grade: ExamDetail["show_grade"]
  audience: ExamDetail["audience"]
  student_ids: number[]
  questions: ExamQuestion[]
}
