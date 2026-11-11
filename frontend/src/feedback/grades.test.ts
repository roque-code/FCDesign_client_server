import { describe, expect, it } from "vitest"

import { feedbackQuery, type ExerciseFeedback } from "../api"
import { feedbackOn, formatDay, formatGrade, gradeInput, withBom } from "./grades"

function item(kind: "algorithm" | "program", exerciseId: string): ExerciseFeedback {
  return {
    id: `${kind}-${exerciseId}`,
    kind,
    exercise_id: exerciseId,
    exercise_name: "Ejercicio",
    context: "Proyecto",
    grade: 9.5,
    comment: "",
    teacher: { id: 1, display_name: "Profe" },
    student_id: 2,
    updated_at: "2026-11-11T10:00:00Z",
  }
}

describe("calificaciones", () => {
  it("escribe la nota con el separador del idioma", () => {
    expect(formatGrade("es", 9.5)).toBe("9.5")
    expect(formatGrade("en", 100)).toBe("100")
    expect(formatGrade("es", 8.25)).toBe("8.25")
  })

  it("elige solo las notas del ejercicio abierto", () => {
    const rows = [item("algorithm", "a"), item("program", "a"), item("algorithm", "b")]
    expect(feedbackOn(rows, "algorithm", "a").map((row) => row.id)).toEqual(["algorithm-a"])
    expect(feedbackOn(rows, "program", "z")).toEqual([])
  })

  it("deja vacío el campo sin nota y pone la marca de Excel una vez", () => {
    expect(gradeInput(null)).toBe("")
    expect(gradeInput(7)).toBe("7")
    expect(withBom("a,b")).toBe("\ufeffa,b")
    expect(withBom("\ufeffa,b")).toBe("\ufeffa,b")
  })

  it("arma la consulta de la lista solo con los filtros puestos", () => {
    expect(feedbackQuery({})).toBe("")
    expect(feedbackQuery({ kind: "", page: 1 })).toBe("")
    expect(feedbackQuery({ kind: "program", language: "cpp", page: 3, pageSize: 10 })).toBe(
      "?kind=program&language=cpp&page=3&page_size=10",
    )
    expect(feedbackQuery({ kind: "algorithm", exercise: "a-1" })).toBe("?kind=algorithm&exercise=a-1")
  })

  it("muestra la fecha de la calificación en el idioma elegido", () => {
    expect(formatDay("en", "2026-11-11T18:00:00Z")).toContain("2026")
    expect(formatDay("es", "no es fecha")).toBe("")
  })
})
