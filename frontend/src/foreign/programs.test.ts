import { describe, expect, it } from "vitest"

import type { LanguageProgram } from "../api"
import { isForeignLanguage, sortPrograms, withProgram } from "./programs"

const row = (id: string, language: string, name: string): LanguageProgram => ({
  id,
  name,
  language,
  updated_at: "2026-11-05T00:00:00Z",
})

describe("programas guardados", () => {
  it("reconoce solo los lenguajes de las pestañas", () => {
    expect(isForeignLanguage("python")).toBe(true)
    expect(isForeignLanguage("cobol")).toBe(false)
  })

  it("ordena por pestaña y luego por nombre", () => {
    const sorted = sortPrograms([row("1", "java", "b"), row("2", "python", "z"), row("3", "java", "a"), row("4", "python", "Programa 10"), row("5", "python", "Programa 9")])
    expect(sorted.map((item) => item.id)).toEqual(["5", "4", "2", "3", "1"])
  })

  it("reemplaza el programa guardado sin conservar el código en la lista", () => {
    const list = [row("1", "python", "a"), row("2", "c", "b")]
    const next = withProgram(list, { ...row("2", "c", "renombrado"), source: "int main(){}" })
    expect(next.map((item) => item.name)).toEqual(["a", "renombrado"])
    expect(next[1]).not.toHaveProperty("source")
    expect(withProgram(list, row("3", "javascript", "nuevo")).map((item) => item.id)).toEqual(["1", "3", "2"])
  })
})
