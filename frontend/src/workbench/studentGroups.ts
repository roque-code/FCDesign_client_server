import type { ClassroomStudent } from "../api"

const byName = new Intl.Collator("es", { sensitivity: "base", numeric: true })

export function groupNames(students: ClassroomStudent[]): string[] {
  return [...new Set(students.flatMap((student) => student.communities))].sort(byName.compare)
}

export function studentsIn(students: ClassroomStudent[], group: string): ClassroomStudent[] {
  return students
    .filter((student) => student.communities.includes(group))
    .sort((a, b) => byName.compare(a.display_name, b.display_name) || byName.compare(a.email, b.email))
}

/** Dos alumnos del grupo con el mismo nombre se distinguen por el correo. */
export function studentLabel(student: ClassroomStudent, group: ClassroomStudent[]): string {
  const twin = group.some((other) => other.id !== student.id && byName.compare(other.display_name, student.display_name) === 0)
  return twin ? `${student.display_name} · ${student.email}` : student.display_name
}
