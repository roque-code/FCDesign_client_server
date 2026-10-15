import { describe, expect, it } from "vitest"

import { applyConsoleOutput } from "./output"

describe("applyConsoleOutput", () => {
  it("agrega solo el texto nuevo", () => {
    expect(applyConsoleOutput("Hola\n", "output", { text: "Listo\n" })).toBe("Hola\nListo\n")
  })

  it("vacía la consola cuando el programa borra la pantalla", () => {
    expect(applyConsoleOutput("Hola\n", "output", { output_reset: true, text: "" })).toBe("")
  })

  it("usa la consola completa si el servidor la reenvía tras un corte", () => {
    expect(applyConsoleOutput("trozo", "paused", { output: "Hola\nListo\n" })).toBe("Hola\nListo\n")
  })

  it("deja la consola quieta en una pausa sin texto nuevo", () => {
    expect(applyConsoleOutput("Hola\n", "paused", {})).toBe("Hola\n")
  })
})
