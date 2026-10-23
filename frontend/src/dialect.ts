/** Grafías de las palabras reservadas. El texto guardado no se reescribe. */

import { canonicalize, isIdentContinue, isIdentStart } from "./words"

export type Dialect = "es" | "en"

const ROWS: ReadonlyArray<readonly [string, string, string]> = [
  ["algoritmo", "Algoritmo", "Algorithm"],
  ["finalgoritmo", "FinAlgoritmo", "EndAlgorithm"],
  ["funcion", "Función", "Function"],
  ["finfuncion", "FinFunción", "EndFunction"],
  ["subproceso", "SubProceso", "SubProcedure"],
  ["finsubproceso", "FinSubProceso", "EndSubProcedure"],
  ["definir", "Definir", "Declare"],
  ["como", "Como", "As"],
  ["dimension", "Dimension", "Dimension"],
  ["por", "Por", "By"],
  ["valor", "Valor", "Value"],
  ["referencia", "Referencia", "Reference"],
  ["leer", "Leer", "Read"],
  ["escribir", "Escribir", "Write"],
  ["sin", "Sin", "Without"],
  ["saltar", "Saltar", "Newline"],
  ["borrar", "Borrar", "Clear"],
  ["pantalla", "Pantalla", "Screen"],
  ["esperar", "Esperar", "Wait"],
  ["segundos", "Segundos", "Seconds"],
  ["si", "Si", "If"],
  ["entonces", "Entonces", "Then"],
  ["sino", "Sino", "Else"],
  ["finsi", "FinSi", "EndIf"],
  ["segun", "Según", "Switch"],
  ["hacer", "Hacer", "Do"],
  ["de", "De", "In"],
  ["otro", "Otro", "Other"],
  ["modo", "Modo", "Case"],
  ["finsegun", "FinSegun", "EndSwitch"],
  ["mientras", "Mientras", "While"],
  ["finmientras", "FinMientras", "EndWhile"],
  ["repetir", "Repetir", "Repeat"],
  ["hasta", "Hasta", "Until"],
  ["que", "Que", "That"],
  ["para", "Para", "For"],
  ["con", "Con", "With"],
  ["paso", "Paso", "Step"],
  ["finpara", "FinPara", "EndFor"],
  ["entero", "Entero", "Integer"],
  ["real", "Real", "Real"],
  ["logico", "Lógico", "Boolean"],
  ["caracter", "Caracter", "Character"],
  ["cadena", "Cadena", "String"],
  ["verdadero", "Verdadero", "True"],
  ["falso", "Falso", "False"],
  ["y", "Y", "And"],
  ["o", "O", "Or"],
  ["no", "NO", "Not"],
  ["div", "DIV", "Div"],
  ["mod", "MOD", "Mod"],
]

const ENGLISH: Record<string, string> = {}
const SPANISH: Record<string, string> = {}
const ALIAS: Record<string, string> = {}

for (const [canonical, spanish, english] of ROWS) {
  SPANISH[canonical] = spanish
  ENGLISH[canonical] = english
  const folded = canonicalize(english)
  if (folded !== canonical) ALIAS[folded] = canonical
}

const DIAGRAM: Record<string, string> = {
  inicio: "Start",
  fin: "End",
}

export function canonicalKeyword(folded: string): string {
  if (folded in ENGLISH) return folded
  return ALIAS[folded] ?? folded
}

export function keywordText(locale: Dialect, canonical: string): string {
  const table = locale === "en" ? ENGLISH : SPANISH
  return table[canonical] ?? canonical
}

export function keywordDisplays(locale: Dialect): string[] {
  const table = locale === "en" ? ENGLISH : SPANISH
  return ROWS.map(([canonical]) => table[canonical])
}

export function allKeywordDisplays(): string[] {
  return ROWS.flatMap(([canonical]) => [SPANISH[canonical], ENGLISH[canonical]])
}

export function editorKeywords(locale: Dialect, fromServer: readonly string[]): string[] {
  const ordered = [...keywordDisplays(locale), ...fromServer, ...allKeywordDisplays()]
  const seen = new Set<string>()
  const result: string[] = []
  for (const word of ordered) {
    const key = canonicalize(word)
    if (seen.has(key)) continue
    seen.add(key)
    result.push(word)
  }
  return result
}

type SpellOptions = { diagram?: boolean; caret?: number | null }

export function spellText(locale: Dialect, text: string, options?: SpellOptions): string {
  if (locale !== "en" || text.length === 0) return text
  const diagram = options?.diagram !== false
  return mapWords(
    text,
    (raw) => {
      const key = canonicalize(raw)
      return ENGLISH[key] ?? (diagram ? DIAGRAM[key] : undefined) ?? raw
    },
    options?.caret,
  )
}

function keywordCanonical(raw: string): string | null {
  const key = canonicalize(raw)
  if (key in ENGLISH) return key
  return ALIAS[key] ?? null
}

function spanishWord(raw: string): string {
  const canonical = keywordCanonical(raw)
  if (!canonical) return raw
  const english = ENGLISH[canonical]
  const spanish = SPANISH[canonical]
  if (english === spanish) return raw
  const folded = canonicalize(raw)
  if (raw === english || (folded === canonicalize(english) && folded !== canonical)) return spanish
  return raw
}

function dialectVote(raw: string): Dialect | null {
  const canonical = keywordCanonical(raw)
  if (!canonical || ENGLISH[canonical] === SPANISH[canonical]) return null
  return spanishWord(raw) === raw ? "es" : "en"
}

export function sourceDialect(text: string, fallback: Dialect = "es"): Dialect {
  let english = 0
  let spanish = 0
  visitWords(text, (raw) => {
    const vote = dialectVote(raw)
    if (vote === "en") english += 1
    else if (vote === "es") spanish += 1
  })
  if (english === 0 && spanish === 0) return fallback
  return english > spanish ? "en" : "es"
}

function toSpanish(text: string, caret?: number | null): string {
  return mapWords(text, spanishWord, caret)
}

export function presentSource(locale: Dialect, text: string, caret?: number | null): string {
  const dialect = sourceDialect(text, locale)
  if (dialect === locale) return text
  return locale === "en" ? spellText("en", text, { diagram: false, caret }) : toSpanish(text, caret)
}

export function commitSource(locale: Dialect, stored: string, shown: string, caret?: number | null): string {
  const dialect = sourceDialect(stored, locale)
  if (dialect === locale) return shown
  const restored = dialect === "es" ? toSpanish(shown, caret) : spellText("en", shown, { diagram: false, caret })
  return alignLexemes(stored, restored, caret)
}

function alignLexemes(original: string, restored: string, caret?: number | null): string {
  const kept = keywordSpans(original)
  const next = keywordSpans(restored)
  if (kept.length !== next.length) return restored
  for (let index = 0; index < kept.length; index += 1) {
    if (kept[index].canonical !== next[index].canonical) return restored
  }
  let out = ""
  let cursor = 0
  for (let index = 0; index < next.length; index += 1) {
    const word = next[index]
    out += restored.slice(cursor, word.start)
    const editing = caret != null && caret >= word.start && caret <= word.end
    out += editing ? restored.slice(word.start, word.end) : original.slice(kept[index].start, kept[index].end)
    cursor = word.end
  }
  return out + restored.slice(cursor)
}

function keywordSpans(text: string): { canonical: string; start: number; end: number }[] {
  const spans: { canonical: string; start: number; end: number }[] = []
  visitWords(text, (raw, start, end) => {
    const canonical = keywordCanonical(raw)
    if (canonical) spans.push({ canonical, start, end })
  })
  return spans
}

export function mapCaret(fromText: string, toText: string, caret: number): number {
  const fromWords: { start: number; end: number }[] = []
  const toWords: { start: number; end: number }[] = []
  visitWords(fromText, (_raw, start, end) => fromWords.push({ start, end }))
  visitWords(toText, (_raw, start, end) => toWords.push({ start, end }))
  if (fromWords.length !== toWords.length) return Math.min(Math.max(caret, 0), toText.length)
  let delta = 0
  for (let index = 0; index < fromWords.length; index += 1) {
    if (fromWords[index].end > caret) break
    delta += toWords[index].end - toWords[index].start - (fromWords[index].end - fromWords[index].start)
  }
  return Math.min(Math.max(caret + delta, 0), toText.length)
}

function mapWords(text: string, mapWord: (raw: string) => string, caret?: number | null): string {
  let out = ""
  let mark = 0
  visitWords(text, (raw, start, end) => {
    out += text.slice(mark, start)
    const editing = caret != null && caret >= start && caret <= end
    out += editing ? raw : mapWord(raw)
    mark = end
  })
  return out + text.slice(mark)
}

function visitWords(text: string, visit: (raw: string, start: number, end: number) => void): void {
  let index = 0
  while (index < text.length) {
    const ch = text[index]
    if (ch === '"' || ch === "'") {
      index = endOfQuote(text, index)
      continue
    }
    if (text.startsWith("//", index)) {
      const end = text.indexOf("\n", index)
      index = end < 0 ? text.length : end
      continue
    }
    if (isIdentStart(ch)) {
      const start = index
      index += 1
      while (index < text.length && isIdentContinue(text[index])) index += 1
      visit(text.slice(start, index), start, index)
      continue
    }
    index += 1
  }
}

function endOfQuote(text: string, start: number): number {
  const quote = text[start]
  let index = start + 1
  while (index < text.length) {
    if (text[index] === "\\") {
      index += 2
      continue
    }
    if (text[index] === quote) return index + 1
    if (text[index] === "\n") return index
    index += 1
  }
  return text.length
}

export function starterSource(locale: Dialect): string {
  if (locale === "en") return 'Algorithm Laboratorio\n\nEndAlgorithm\n'
  return "Algoritmo Laboratorio\n\nFinAlgoritmo\n"
}
