import type { ExerciseFeedback, ExerciseKind } from "../api"

export function formatGrade(locale: string, grade: number): string {
  return new Intl.NumberFormat(locale === "en" ? "en-US" : "es-MX", { maximumFractionDigits: 2 }).format(grade)
}

export function formatDay(locale: string, iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ""
  return new Intl.DateTimeFormat(locale === "en" ? "en-US" : "es-MX", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(date)
}

export function feedbackOn(items: ExerciseFeedback[], kind: ExerciseKind, exerciseId: string): ExerciseFeedback[] {
  return items.filter((item) => item.kind === kind && item.exercise_id === exerciseId)
}

export function gradeInput(grade: number | null): string {
  return grade === null ? "" : String(grade)
}

export function withBom(csv: string): string {
  return csv.charCodeAt(0) === 0xfeff ? csv : `\ufeff${csv}`
}
