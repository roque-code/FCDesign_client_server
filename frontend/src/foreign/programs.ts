import type { LanguageProgram } from "../api"
import { FOREIGN_LANGUAGES, type ForeignLanguage } from "./keywords"

const byName = new Intl.Collator("es", { sensitivity: "base", numeric: true })

export function isForeignLanguage(value: string): value is ForeignLanguage {
  return (FOREIGN_LANGUAGES as readonly string[]).includes(value)
}

/** Agrupa por lenguaje en el orden de las pestañas y, dentro, por nombre. */
export function sortPrograms(programs: LanguageProgram[]): LanguageProgram[] {
  const order = (item: LanguageProgram) => (FOREIGN_LANGUAGES as readonly string[]).indexOf(item.language)
  return [...programs].sort((a, b) => order(a) - order(b) || byName.compare(a.name, b.name))
}

/** La lista lateral no guarda el código: solo los datos para mostrarlo. */
export function withProgram(programs: LanguageProgram[], program: LanguageProgram): LanguageProgram[] {
  const { source: _source, ...row } = program
  return sortPrograms([...programs.filter((item) => item.id !== program.id), row])
}
