export type SubjectId = "fundamentos" | "bases" | "objetos" | "software"

export type SubjectNameKey =
  | "subjectFundamentos"
  | "subjectBases"
  | "subjectObjects"
  | "subjectSoftware"

export type SubjectSpec = {
  id: SubjectId
  nameKey: SubjectNameKey
  noteKey?: "subjectFundamentosNote" | "subjectBasesNote"
  open: boolean
}

export const SUBJECTS: readonly SubjectSpec[] = [
  {
    id: "fundamentos",
    nameKey: "subjectFundamentos",
    noteKey: "subjectFundamentosNote",
    open: true,
  },
  { id: "bases", nameKey: "subjectBases", noteKey: "subjectBasesNote", open: true },
  { id: "objetos", nameKey: "subjectObjects", open: false },
  { id: "software", nameKey: "subjectSoftware", open: false },
]

export function openSubject(id: SubjectId): SubjectSpec | null {
  const subject = SUBJECTS.find((item) => item.id === id)
  return subject?.open ? subject : null
}

export function subjectsFor(
  features: Record<string, boolean> | undefined,
  current?: string,
): SubjectSpec[] {
  const flags = features ?? {}
  return SUBJECTS.filter((item) => flags[`subject_${item.id}`] === true || item.id === current)
}

export type MenuKind = "exams" | "chat"

export function menuOn(
  features: Record<string, boolean> | undefined,
  menu: MenuKind,
  subject?: string,
): boolean {
  const flags = features ?? {}
  if (subject) return flags[`${menu}_${subject}`] === true
  return SUBJECTS.some((item) => flags[`${menu}_${item.id}`] === true)
}

export function subjectsForMenu(
  features: Record<string, boolean> | undefined,
  menu: MenuKind,
  current?: string,
): SubjectSpec[] {
  const flags = features ?? {}
  return SUBJECTS.filter((item) => flags[`${menu}_${item.id}`] === true || item.id === current)
}
