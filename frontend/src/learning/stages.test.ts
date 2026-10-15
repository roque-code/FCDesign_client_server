import { describe, expect, it } from "vitest"

import { blockOnLine, buildLocked, formatClock, formatLimit, stagesFor } from "./trace"

describe("etapas del reto", () => {
  it("clasificar y ordenar no abren el lienzo", () => {
    expect(stagesFor("classify")).not.toContain("construir")
    expect(stagesFor("order")).not.toContain("construir")
  })

  it("construir sigue cerrado hasta terminar el análisis", () => {
    expect(buildLocked("build", "comprender")).toBe(true)
    expect(buildLocked("build", "razonar")).toBe(true)
    expect(buildLocked("build", "construir")).toBe(false)
    expect(buildLocked("classify", "razonar")).toBe(false)
  })

  it("muestra el tiempo configurado en minutos", () => {
    expect(formatLimit(180)).toBe("3 min")
    expect(formatLimit(45)).toBe("45 s")
    expect(formatClock(65)).toBe("1:05")
  })

  it("la predicción ejecuta después de razonar", () => {
    expect(stagesFor("predict")).toEqual(["comprender", "razonar", "comprobar", "explicar"])
  })
})

describe("bloque de la línea", () => {
  it("elige el bloque que empieza la línea", () => {
    const blockId = blockOnLine(
      [
        { block_id: "valor", line: 3, column: 12 },
        { block_id: "asigna", line: 3, column: 5 },
        { block_id: "define", line: 2, column: 5 },
      ],
      3,
    )
    expect(blockId).toBe("asigna")
    expect(blockOnLine([], 1)).toBeNull()
  })
})
