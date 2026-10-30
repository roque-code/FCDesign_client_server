import { describe, expect, it } from "vitest"
import { indentText } from "./indent"

describe("tabulador del cuadro de código", () => {
  it("escribe un tabulador donde está el cursor", () => {
    expect(indentText("if x:\nprint(x)", 6, 6, false)).toEqual({ value: "if x:\n\tprint(x)", start: 7, end: 7 })
  })

  it("sangra y quita la sangría de varias líneas", () => {
    const source = "a\nb\nc"
    const shifted = indentText(source, 0, 3, false)
    expect(shifted.value).toBe("\ta\n\tb\nc")
    expect(indentText(shifted.value, shifted.start, shifted.end, true).value).toBe(source)
  })

  it("Shift+Tab quita cuatro espacios o un tabulador de la línea", () => {
    expect(indentText("    x = 1", 6, 6, true)).toEqual({ value: "x = 1", start: 2, end: 2 })
    expect(indentText("\tx = 1", 1, 1, true)).toEqual({ value: "x = 1", start: 0, end: 0 })
  })
})
