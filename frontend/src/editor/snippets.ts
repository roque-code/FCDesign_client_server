/** Plantillas de las instrucciones. El campo queda marcado y la palabra reservada sigue en el texto. */

import { snippetCompletion, type Completion, type CompletionResult, type CompletionSource } from "@codemirror/autocomplete"

import { keywordText, type Dialect } from "../dialect"
import { canonicalize } from "../words"

type Place = { es: string; en: string }

const PLACE: Record<"name" | "expr" | "cond" | "body" | "alt" | "param" | "result", Place> = {
  name: { es: "nombre", en: "name" },
  expr: { es: "expresion", en: "expression" },
  cond: { es: "condicion", en: "condition" },
  body: { es: "instruccion", en: "instruction" },
  alt: { es: "alternativa", en: "alternative" },
  param: { es: "parametro", en: "parameter" },
  result: { es: "resultado", en: "result" },
}

export const instructionCanonicals = new Set([
  "algoritmo",
  "funcion",
  "subproceso",
  "definir",
  "dimension",
  "leer",
  "escribir",
  "borrar",
  "esperar",
  "si",
  "segun",
  "mientras",
  "repetir",
  "para",
])

type Offer = {
  keys: { text: string; alias: boolean }[]
  completion: Completion
}

function word(locale: Dialect, canonical: string): string {
  return keywordText(locale, canonical)
}

function field(order: number, text: string): string {
  return "${" + order + ":" + text + "}"
}

function done(block = false): string {
  return (block ? "\n" : "") + "${0}"
}

function place(locale: Dialect, key: keyof typeof PLACE): string {
  return PLACE[key][locale]
}

function keysFor(locale: Dialect, canonical: string): { text: string; alias: boolean }[] {
  const primary = canonicalize(word(locale, canonical))
  const other = canonicalize(word(locale === "es" ? "en" : "es", canonical))
  const keys = [{ text: primary, alias: false }]
  if (other !== primary) keys.push({ text: other, alias: true })
  return keys
}

function offer(
  locale: Dialect,
  canonical: string,
  template: string,
  display: string,
  detail: string,
  extra?: { text: string; alias: boolean }[],
): Offer {
  return {
    keys: [...keysFor(locale, canonical), ...(extra ?? [])],
    completion: snippetCompletion(template, {
      label: word(locale, canonical),
      displayLabel: display,
      detail,
      type: "keyword",
    }),
  }
}

function stop(semicolons: boolean): string {
  return semicolons ? ";" : ""
}

export function instructionOffers(locale: Dialect, semicolons = true): Offer[] {
  const name = place(locale, "name")
  const expr = place(locale, "expr")
  const cond = place(locale, "cond")
  const body = place(locale, "body")
  const alt = place(locale, "alt")
  const param = place(locale, "param")
  const result = place(locale, "result")
  const typeName = word(locale, "entero")
  const es = locale === "es"
  const assignLabel = es ? "asignar" : "assign"
  const end = stop(semicolons)

  return [
    offer(
      locale,
      "algoritmo",
      `${word(locale, "algoritmo")} ${field(1, name)}\n\t${field(2, body)}\n${word(locale, "finalgoritmo")}${done(true)}`,
      es ? "Algoritmo nombre … FinAlgoritmo" : "Algorithm name … EndAlgorithm",
      es ? "programa" : "program",
    ),
    offer(
      locale,
      "definir",
      `${word(locale, "definir")} ${field(1, name)} ${word(locale, "como")} ${field(2, typeName)}${end}${done()}`,
      es ? "Definir nombre Como Entero" : "Declare name As Integer",
      es ? "variable" : "variable",
    ),
    {
      keys: [
        { text: assignLabel, alias: false },
        { text: es ? "assign" : "asignar", alias: true },
      ],
      completion: snippetCompletion(`${field(1, name)} <- ${field(2, expr)}${end}${done()}`, {
        label: assignLabel,
        displayLabel: es ? "nombre <- expresion" : "name <- expression",
        detail: es ? "asignación" : "assignment",
        type: "keyword",
      }),
    },
    offer(
      locale,
      "dimension",
      `${word(locale, "dimension")} ${field(1, name)}[${field(2, "10")}] ${word(locale, "como")} ${field(3, typeName)}${end}${done()}`,
      es ? "Dimension nombre[10] Como Entero" : "Dimension name[10] As Integer",
      es ? "arreglo" : "array",
    ),
    offer(
      locale,
      "leer",
      `${word(locale, "leer")} ${field(1, name)}${end}${done()}`,
      es ? "Leer nombre" : "Read name",
      es ? "entrada" : "input",
    ),
    offer(
      locale,
      "escribir",
      `${word(locale, "escribir")} ${field(1, expr)}${end}${done()}`,
      es ? "Escribir expresion" : "Write expression",
      es ? "salida" : "output",
    ),
    offer(
      locale,
      "escribir",
      `${word(locale, "escribir")} ${field(1, expr)} ${word(locale, "sin")} ${word(locale, "saltar")}${end}${done()}`,
      es ? "Escribir expresion Sin Saltar" : "Write expression Without Newline",
      es ? "misma línea" : "same line",
    ),
    offer(
      locale,
      "borrar",
      `${word(locale, "borrar")} ${word(locale, "pantalla")}${end}${done()}`,
      es ? "Borrar Pantalla" : "Clear Screen",
      es ? "pantalla" : "screen",
    ),
    offer(
      locale,
      "esperar",
      `${word(locale, "esperar")} ${field(1, "2")} ${word(locale, "segundos")}${end}${done()}`,
      es ? "Esperar 2 Segundos" : "Wait 2 Seconds",
      es ? "pausa" : "pause",
    ),
    offer(
      locale,
      "si",
      `${word(locale, "si")} ${field(1, cond)} ${word(locale, "entonces")}\n\t${field(2, body)}\n${word(locale, "sino")}\n\t${field(3, alt)}\n${word(locale, "finsi")}${done(true)}`,
      es ? "Si condicion Entonces … FinSi" : "If condition Then … EndIf",
      es ? "decisión" : "decision",
    ),
    offer(
      locale,
      "segun",
      `${word(locale, "segun")} ${field(1, expr)} ${word(locale, "hacer")}\n\t${field(2, "1")}:\n\t\t${field(3, body)}\n\t${field(4, "2")}:\n\t\t${field(5, alt)}\n\t${word(locale, "de")} ${word(locale, "otro")} ${word(locale, "modo")}:\n\t\t${field(6, body)}\n${word(locale, "finsegun")}${done(true)}`,
      es ? "Según expresion Hacer … FinSegun" : "Switch expression Do … EndSwitch",
      es ? "casos" : "cases",
    ),
    offer(
      locale,
      "mientras",
      `${word(locale, "mientras")} ${field(1, cond)} ${word(locale, "hacer")}\n\t${field(2, body)}\n${word(locale, "finmientras")}${done(true)}`,
      es ? "Mientras condicion Hacer … FinMientras" : "While condition Do … EndWhile",
      es ? "ciclo" : "loop",
    ),
    offer(
      locale,
      "repetir",
      `${word(locale, "repetir")}\n\t${field(1, body)}\n${word(locale, "hasta")} ${word(locale, "que")} ${field(2, cond)}${done(true)}`,
      es ? "Repetir … Hasta Que condicion" : "Repeat … Until That condition",
      es ? "ciclo" : "loop",
    ),
    offer(
      locale,
      "para",
      `${word(locale, "para")} ${field(1, "i")} <- ${field(2, "1")} ${word(locale, "hasta")} ${field(3, "n")} ${word(locale, "con")} ${word(locale, "paso")} ${field(4, "1")} ${word(locale, "hacer")}\n\t${field(5, body)}\n${word(locale, "finpara")}${done(true)}`,
      es ? "Para i <- 1 Hasta n Con Paso 1 … FinPara" : "For i <- 1 Until n With Step 1 … EndFor",
      es ? "ciclo contado" : "counted loop",
    ),
    offer(
      locale,
      "funcion",
      `${word(locale, "funcion")} ${field(1, result)} <- ${field(2, name)}(${field(3, param)})\n\t${field(4, body)}\n${word(locale, "finfuncion")}${done(true)}`,
      es ? "Función resultado <- nombre() … FinFunción" : "Function result <- name() … EndFunction",
      es ? "función" : "function",
    ),
    offer(
      locale,
      "subproceso",
      `${word(locale, "subproceso")} ${field(1, name)}(${field(2, param)})\n\t${field(3, body)}\n${word(locale, "finsubproceso")}${done(true)}`,
      es ? "SubProceso nombre() … FinSubProceso" : "SubProcedure name() … EndSubProcedure",
      es ? "procedimiento" : "procedure",
    ),
  ]
}

function matches(keys: Offer["keys"], typed: string): boolean {
  if (!typed) return true
  return keys.some((key) => {
    if (!key.text.startsWith(typed)) return false
    return !key.alias || typed.length >= 2
  })
}

export function instructionSource(locale: Dialect, semicolons = true): CompletionSource {
  const offers = instructionOffers(locale, semicolons)
  return (context): CompletionResult | null => {
    const word = context.matchBefore(/[\p{L}\p{N}_]*/u)
    if (!word || (word.from === word.to && !context.explicit)) return null
    const typed = canonicalize(word.text)
    const options = offers.filter((item) => matches(item.keys, typed)).map((item) => item.completion)
    if (options.length === 0) return null
    return { from: word.from, options, filter: false }
  }
}
