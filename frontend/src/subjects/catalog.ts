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
