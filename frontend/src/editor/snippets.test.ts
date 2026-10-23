import { CompletionContext, snippet } from "@codemirror/autocomplete"
import { EditorState } from "@codemirror/state"
import { describe, expect, it } from "vitest"

import { allKeywordDisplays } from "../dialect"
import { highlightSource } from "./highlight"
import { instructionOffers, instructionSource } from "./snippets"
import { canonicalize, keywordSet } from "../words"

const reserved = keywordSet(allKeywordDisplays())

function inserted(apply: (editor: never, completion: never, from: number, to: number) => void, completion: never): string {
  let text = ""
  apply(
    {
      state: EditorState.create({ doc: "" }),
      dispatch(value: { newDoc?: { toString(): string } } | readonly { newDoc?: { toString(): string } }[]) {
        const tr = Array.isArray(value) ? value[0] : value
        text = tr?.newDoc?.toString() ?? text
      },
    } as never,
    completion,
    0,
    0,
  )
  return text
}

function expand(template: string): string {
  return inserted(snippet(template) as never, null as never)
}

function templateOf(locale: "es" | "en", display: string, semicolons = true): string {
  const offer = instructionOffers(locale, semicolons).find((item) => item.completion.displayLabel === display)
  const apply = offer?.completion.apply
  if (!offer || typeof apply !== "function") throw new Error(display)
  return inserted(apply as never, offer.completion as never)
}

function wordsOf(source: string, kind: "keyword" | "variableName"): string[] {
  return highlightSource(source, reserved)
    .flat()
    .filter((span) => span.kind === kind)
    .map((span) => span.text)
}

describe("instruction snippets", () => {
  it("completa cada instrucción y deja las palabras reservadas para el resaltado", () => {
    const si = templateOf("es", "Si condicion Entonces … FinSi")
    expect(si).toBe("Si condicion Entonces\n  instruccion\nSino\n  alternativa\nFinSi\n")
    expect(wordsOf(si, "keyword")).toEqual(["Si", "Entonces", "Sino", "FinSi"])
    expect(wordsOf(si, "variableName")).toEqual(["condicion", "instruccion", "alternativa"])

    const definir = templateOf("es", "Definir nombre Como Entero")
    expect(definir).toBe("Definir nombre Como Entero;")
    expect(wordsOf(definir, "keyword")).toEqual(["Definir", "Como", "Entero"])
    expect(wordsOf(definir, "variableName")).toEqual(["nombre"])

    expect(templateOf("es", "Escribir expresion Sin Saltar")).toBe("Escribir expresion Sin Saltar;")
    expect(templateOf("es", "Borrar Pantalla")).toBe("Borrar Pantalla;")
    expect(templateOf("es", "Según expresion Hacer … FinSegun")).toContain("De Otro Modo:")
    expect(templateOf("es", "Según expresion Hacer … FinSegun")).toContain("FinSegun")
    expect(templateOf("es", "Para i <- 1 Hasta n Con Paso 1 … FinPara")).toContain("Con Paso 1")
    expect(templateOf("es", "Repetir … Hasta Que condicion")).toContain("Hasta Que condicion")
    expect(templateOf("es", "Función resultado <- nombre() … FinFunción")).toContain("FinFunción")
    expect(templateOf("en", "If condition Then … EndIf")).toBe("If condition Then\n  instruction\nElse\n  alternative\nEndIf\n")
    expect(wordsOf(templateOf("en", "While condition Do … EndWhile"), "keyword")).toEqual(["While", "Do", "EndWhile"])
  })

  it("los nombres de los campos no son palabras reservadas", () => {
    for (const locale of ["es", "en"] as const) {
      for (const item of instructionOffers(locale)) {
        const apply = item.completion.apply
        if (typeof apply !== "function") continue
        const text = inserted(apply as never, item.completion as never)
        const fields = wordsOf(text, "variableName")
        for (const field of fields) expect(reserved.has(canonicalize(field))).toBe(false)
      }
    }
  })

  it("al escribir la instrucción ofrece la estructura, también con la otra grafía", () => {
    const spanish = EditorState.create({ doc: "Si" })
    const result = instructionSource("es")(new CompletionContext(spanish, 2, false))
    expect(result && "options" in result ? result.options.map((item) => item.displayLabel) : []).toEqual([
      "Si condicion Entonces … FinSi",
    ])

    const alias = EditorState.create({ doc: "If" })
    const fromEnglish = instructionSource("es")(new CompletionContext(alias, 2, false))
    expect(fromEnglish && "options" in fromEnglish ? fromEnglish.options[0]?.displayLabel : "").toBe(
      "Si condicion Entonces … FinSi",
    )

    const partial = EditorState.create({ doc: "Esc" })
    const writes = instructionSource("es")(new CompletionContext(partial, 3, false))
    expect(writes && "options" in writes ? writes.options.map((item) => item.displayLabel) : []).toEqual([
      "Escribir expresion",
      "Escribir expresion Sin Saltar",
    ])

    expect(instructionSource("es")(new CompletionContext(EditorState.create({ doc: "x" }), 1, false))).toBeNull()
    expect(expand("${1:nombre}")).toBe("nombre")
  })

  it("omite el punto y coma cuando la configuración es opcional", () => {
    expect(templateOf("es", "Definir nombre Como Entero", false)).toBe("Definir nombre Como Entero")
    expect(templateOf("es", "nombre <- expresion", false)).toBe("nombre <- expresion")
    expect(templateOf("es", "Dimension nombre[10] Como Entero", false)).toBe("Dimension nombre[10] Como Entero")
    expect(templateOf("es", "Leer nombre", false)).toBe("Leer nombre")
    expect(templateOf("es", "Escribir expresion", false)).toBe("Escribir expresion")
    expect(templateOf("es", "Escribir expresion Sin Saltar", false)).toBe("Escribir expresion Sin Saltar")
    expect(templateOf("es", "Borrar Pantalla", false)).toBe("Borrar Pantalla")
    expect(templateOf("es", "Esperar 2 Segundos", false)).toBe("Esperar 2 Segundos")
    expect(templateOf("es", "Si condicion Entonces … FinSi", false)).toBe(
      "Si condicion Entonces\n  instruccion\nSino\n  alternativa\nFinSi\n",
    )
    expect(templateOf("es", "Repetir … Hasta Que condicion", true)).not.toContain(";")
    expect(templateOf("en", "Declare name As Integer", false)).toBe("Declare name As Integer")
    expect(templateOf("en", "Declare name As Integer", true)).toBe("Declare name As Integer;")
  })
})
