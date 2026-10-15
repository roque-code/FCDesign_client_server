import { describe, expect, it } from "vitest"

import { canonicalize, keywordSet } from "./words"

describe("canonicalize", () => {
  it("pliega acentos y mayúsculas como el lexer", () => {
    expect(canonicalize("Lógico")).toBe("logico")
    expect(canonicalize("Función")).toBe("funcion")
    expect(canonicalize("NO")).toBe("no")
    expect(canonicalize("Carácter")).toBe("caracter")
  })

  it("arma el conjunto que resalta el editor", () => {
    const words = keywordSet(["Algoritmo", "Según"])
    expect(words.has("algoritmo")).toBe(true)
    expect(words.has("segun")).toBe(true)
    expect(words.has("Según")).toBe(false)
  })
})
