import { describe, expect, it } from "vitest"

import { nextIndent, opensBlock } from "./indent"

describe("sangría automática", () => {
  it("Python sangra después de los dos puntos aunque haya un comentario", () => {
    expect(nextIndent("def suma(a, b):", "", "python", 4, 4)).toBe(4)
    expect(nextIndent("\tif a > b:  # mayor", "", "python", 4, 4)).toBe(8)
    expect(nextIndent("\treturn a", "", "python", 4, 4)).toBe(4)
  })

  it("las llaves abren y cierran el bloque", () => {
    expect(nextIndent("public static void main(String[] args) {", "", "java", 4, 4)).toBe(4)
    expect(nextIndent("\tint x = 1;", "}", "java", 4, 4)).toBe(0)
    expect(nextIndent("if (x) { // abre", "}", "c", 4, 4)).toBe(0)
  })

  it("los dos puntos o las llaves dentro de un texto no abren bloque", () => {
    expect(opensBlock('print("hora:")', "python")).toBe(false)
    expect(opensBlock('const s = "{"', "javascript")).toBe(false)
    expect(opensBlock("case 1:", "java")).toBe(false)
  })
})
