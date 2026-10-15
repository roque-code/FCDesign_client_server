import { describe, expect, it } from "vitest"

import { highlightSource } from "./highlight"
import { keywordSet } from "../words"

const reserved = keywordSet(["Algoritmo", "Definir", "Como", "Escribir", "FinAlgoritmo"])

function kinds(line: string) {
  return highlightSource(line, reserved)[0].filter((span) => span.text.trim() !== "").map((span) => [span.text, span.kind])
}

describe("highlightSource", () => {
  it("colorea palabras clave, textos, números y comentarios como el editor", () => {
    expect(kinds('Escribir "hola"')).toEqual([
      ["Escribir", "keyword"],
      ['"hola"', "string"],
    ])
    expect(kinds("n <- 12.5")).toEqual([
      ["n", "variableName"],
      [" <- ", null],
      ["12.5", "number"],
    ])
    expect(kinds("area // nota")).toEqual([
      ["area", "variableName"],
      ["// nota", "comment"],
    ])
  })

  it("mantiene un comentario de bloque entre líneas", () => {
    const lines = highlightSource("a /*\nnota\n*/ b", reserved)
    expect(lines[0].at(-1)?.kind).toBe("comment")
    expect(lines[1][0]).toEqual({ text: "nota", kind: "comment" })
    expect(lines[2][0]?.kind).toBe("comment")
    expect(lines[2].at(-1)).toEqual({ text: "b", kind: "variableName" })
  })
})