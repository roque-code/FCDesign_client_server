import { request, type FocusEvent } from "../api"
import type {
  AttemptView,
  ExamCard,
  ExamDetail,
  ExamFile,
  ExamNotice,
  ExamResults,
  ExamSummary,
  ExamWrite,
} from "./types"

export function examList(subject = "") {
  const query = subject ? `?subject=${encodeURIComponent(subject)}` : ""
  return request<{ results: ExamSummary[] }>(`/api/v1/exams/${query}`)
}

export function examMine() {
  return request<{ results: ExamCard[] }>("/api/v1/exams/mine/")
}

export function examNotices() {
  return request<{ unread: number; results: ExamNotice[] }>("/api/v1/exams/notices/")
}

export function examReadNotices() {
  return request<{ unread: number; results: ExamNotice[] }>("/api/v1/exams/notices/", { method: "POST", body: "{}" })
}

export function examCreate(body: ExamWrite) {
  return request<ExamDetail>("/api/v1/exams/", { method: "POST", body: JSON.stringify(body) })
}

export function examOpen(id: string) {
  return request<ExamDetail>(`/api/v1/exams/${id}/`)
}

export function examUpdate(id: string, body: Partial<ExamWrite>) {
  return request<ExamDetail>(`/api/v1/exams/${id}/`, { method: "PATCH", body: JSON.stringify(body) })
}

export function examRemove(id: string) {
  return request<void>(`/api/v1/exams/${id}/`, { method: "DELETE" })
}

export function examPublish(id: string) {
  return request<ExamDetail>(`/api/v1/exams/${id}/publish/`, { method: "POST", body: "{}" })
}

export function examClose(id: string) {
  return request<ExamDetail>(`/api/v1/exams/${id}/close/`, { method: "POST", body: "{}" })
}

export function examImport(body: { format?: string; text: string; subject: string; community_id: string; title?: string }) {
  return request<ExamDetail>("/api/v1/exams/import/", { method: "POST", body: JSON.stringify(body) })
}

export function examExport(id: string, format: "json" | "moodle" | "gift") {
  return request<ExamFile>(`/api/v1/exams/${id}/export/?as=${format}`)
}

export function examResults(id: string) {
  return request<ExamResults>(`/api/v1/exams/${id}/results/`)
}

export function examGrades(id: string) {
  return request<ExamFile>(`/api/v1/exams/${id}/grades/`)
}

export function examStart(id: string) {
  return request<AttemptView>(`/api/v1/exams/${id}/attempts/`, { method: "POST", body: "{}" })
}

export function examAttempt(id: string) {
  return request<AttemptView>(`/api/v1/exams/attempts/${id}/`)
}

export function examSave(id: string, answers: { question_id: string; answer: Record<string, unknown> }[]) {
  return request<AttemptView>(`/api/v1/exams/attempts/${id}/`, {
    method: "PATCH",
    body: JSON.stringify({ answers }),
  })
}

export function examSubmit(id: string, answers: { question_id: string; answer: Record<string, unknown> }[]) {
  return request<AttemptView>(`/api/v1/exams/attempts/${id}/submit/`, {
    method: "POST",
    body: JSON.stringify({ answers }),
  })
}

export function examFocus(id: string, body: { event: FocusEvent; reason?: string; answers?: { question_id: string; answer: Record<string, unknown> }[] }) {
  const text = JSON.stringify(body)
  return request<AttemptView>(`/api/v1/exams/attempts/${id}/focus/`, {
    method: "POST",
    body: text,
    keepalive: text.length < 60_000,
  })
}

export function examGrade(id: string, scores: { question_id: string; score: number; comment: string }[]) {
  return request<AttemptView>(`/api/v1/exams/attempts/${id}/grade/`, {
    method: "POST",
    body: JSON.stringify({ scores }),
  })
}
