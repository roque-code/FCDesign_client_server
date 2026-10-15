import { describe, expect, it } from "vitest"

import { canvasSignature } from "./canvasSignature"

describe("canvasSignature", () => {
  it("ignora un arrastre que no cambia el programa", () => {
    const left = { blocks: { blocks: [{ type: "traza_definir", id: "d", x: 10, y: 20 }] } }
    const right = { blocks: { blocks: [{ type: "traza_definir", id: "d", x: 80, y: 40 }] } }
    expect(canvasSignature(left)).toBe(canvasSignature(right))
  })

  it("cambia cuando cambia un bloque", () => {
    const before = { blocks: { blocks: [{ type: "traza_definir", id: "d", fields: { NOMBRE: "a" } }] } }
    const after = { blocks: { blocks: [{ type: "traza_definir", id: "d", fields: { NOMBRE: "b" } }] } }
    expect(canvasSignature(before)).not.toBe(canvasSignature(after))
  })
})
