import { closeBrackets, insertBracket } from "@codemirror/autocomplete"
import { EditorState } from "@codemirror/state"
import { describe, expect, it } from "vitest"

import { blockBulkPaste, trustedEdit } from "./editor/pasteGuard"
import { keepTypedText } from "./paste"

function apply(start: string, insert: string, userEvent?: string, trusted = false): string {
  const state = EditorState.create({ doc: start, extensions: blockBulkPaste(true) })
  return state.update({
    changes: { from: start.length, insert },
    ...(userEvent ? { userEvent } : {}),
    ...(trusted ? { annotations: trustedEdit.of(true) } : {}),
  }).state.doc.toString()
}

describe("pegar bloqueado", () => {
  it("acepta una tecla, un salto y la sangría", () => {
    expect(apply("Algoritmo", " ")).toBe("Algoritmo ")
    expect(apply("Algoritmo", "\n    ")).toBe("Algoritmo\n    ")
    expect(apply("", "a")).toBe("a")
  })

  it("rechaza un bloque pegado o escrito de golpe", () => {
    expect(apply("", "docker compose -f compose.servidor.yaml down", "input.paste")).toBe("")
    expect(apply("inicio", "\ndocker compose up", "input.type")).toBe("inicio")
    expect(apply("", "programa completo")).toBe("")
  })

  it("deja deshacer y cargar el fuente guardado", () => {
    expect(apply("hola", " mundo", "undo")).toBe("hola mundo")
    expect(apply("", "Algoritmo saludo", undefined, true)).toBe("Algoritmo saludo")
  })

  it("deja abrir paréntesis, corchetes, llaves y comillas con su cierre automático", () => {
    for (const open of ["(", "[", "{", '"', "'"]) {
      const state = EditorState.create({ doc: "x = ", selection: { anchor: 4 }, extensions: [closeBrackets(), ...blockBulkPaste(true)] })
      const typed = insertBracket(state, open)
      expect(typed?.state.doc.toString()).toBe(`x = ${open}${{ "(": ")", "[": "]", "{": "}" }[open] ?? open}`)
    }
    expect(apply("", '""""', "input.type")).toBe('""""')
    expect(apply("", "(a)", "input.type")).toBe("")
  })

  it("deja las plantillas del editor y una letra en un cuadro", () => {
    expect(apply("", "Mientras condicion Hacer\nFinMientras", "input.complete")).toContain("Mientras")
    expect(keepTypedText("saludo", "saludo!")).toBe("saludo!")
    expect(keepTypedText("saludo", "saludo\ndocker compose")).toBe("saludo")
  })
})
