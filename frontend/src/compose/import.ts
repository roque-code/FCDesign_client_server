import { canonicalKeyword } from "../dialect"
import { canonicalize, isIdentContinue, isIdentStart } from "../words"
import { newId, type Program, type Routine, type Step } from "./model"

export type ImportResult = { program: Program; notes: string[] }

type Token = { canon: string; raw: string }

const TYPES: Record<string, string> = {
  entero: "Entero",
  real: "Real",
  logico: "Lógico",
  caracter: "Caracter",
  cadena: "Cadena",
}

const STARTERS = new Set([
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

const CLOSERS = new Set([
  "finsi",
  "finmientras",
  "finpara",
  "finsegun",
  "finalgoritmo",
  "sino",
  "hasta",
  "finfuncion",
  "finsubproceso",
  "de",
])

const BOUNDARIES = new Set([...STARTERS, ...CLOSERS, "entonces", "hacer", "funcion", "subproceso", "//"])

const INFIX = new Set(["+", "-", "*", "/", "%", "^", "<", ">", "==", "<>", "<=", ">=", "!=", "y", "o", "mod", "div"])

export function importSource(source: string): ImportResult {
  return new Parser(tokenize(source)).parseFile()
}

function tokenize(source: string): Token[] {
  const tokens: Token[] = []
  let i = 0
  while (i < source.length) {
    const ch = source[i]
    if (/\s/u.test(ch)) {
      i += 1
      continue
    }
    if (source.startsWith("//", i)) {
      const end = source.indexOf("\n", i)
      const stop = end < 0 ? source.length : end
      tokens.push({ canon: "//", raw: source.slice(i + 2, stop).trim() })
      i = stop
      continue
    }
    if (source.startsWith("/*", i)) {
      const end = source.indexOf("*/", i + 2)
      if (end < 0) throw new Error("Falta cerrar el comentario.")
      i = end + 2
      continue
    }
    if (ch === '"' || ch === "'") {
      const text = readQuoted(source, i)
      tokens.push({ canon: text.raw, raw: text.raw })
      i = text.next
      continue
    }
    const pair = source.slice(i, i + 2)
    if (
      pair === "<-" ||
      pair === "<>" ||
      pair === "<=" ||
      pair === ">=" ||
      pair === "!=" ||
      pair === "=="
    ) {
      tokens.push({ canon: pair, raw: pair })
      i += 2
      continue
    }
    if (isIdentStart(ch)) {
      let j = i + 1
      while (j < source.length && isIdentContinue(source[j])) j += 1
      const raw = source.slice(i, j)
      tokens.push({ canon: canonicalKeyword(canonicalize(raw)), raw })
      i = j
      continue
    }
    if (/\d/u.test(ch)) {
      let j = i + 1
      while (j < source.length && /\d/u.test(source[j])) j += 1
      if (source[j] === "." && /\d/u.test(source[j + 1] ?? "")) {
        j += 2
        while (j < source.length && /\d/u.test(source[j])) j += 1
      }
      const raw = source.slice(i, j)
      tokens.push({ canon: raw, raw })
      i = j
      continue
    }
    tokens.push({ canon: ch, raw: ch })
    i += 1
  }
  return tokens
}

function readQuoted(source: string, start: number): { raw: string; next: number } {
  const quote = source[start]
  let i = start + 1
  while (i < source.length) {
    if (source[i] === "\\") {
      i += 2
      continue
    }
    if (source[i] === quote) return { raw: source.slice(start, i + 1), next: i + 1 }
    i += 1
  }
  throw new Error("Falta cerrar un texto.")
}

function join(parts: string[]): string {
  let text = ""
  for (const part of parts) {
    if (!text) {
      text = part
      continue
    }
    const prev = text.at(-1) ?? ""
    const tightBefore = part === "," || part === ";" || part === ":" || part === ")" || part === "]" || part === "[" || part === "("
    const tightAfter = prev === "(" || prev === "["
    text += text.endsWith("<-") || !(tightBefore || tightAfter) ? ` ${part}` : part
  }
  return text.trim()
}

class Parser {
  private index = 0
  private readonly notes: string[] = []

  constructor(private readonly tokens: Token[]) {}

  parseFile(): ImportResult {
    const routines: Routine[] = []
    let program: Program | null = null
    while (!this.eof()) {
      this.skipSemicolons()
      if (this.eof()) break
      if (this.is("//")) {
        this.index += 1
        continue
      }
      if (this.is("funcion") || this.is("subproceso")) {
        routines.push(this.parseRoutine())
        continue
      }
      if (this.is("algoritmo")) {
        if (program) {
          this.skipAlgorithm()
          this.note("Se usó el primer algoritmo del archivo.")
          continue
        }
        program = this.parseAlgorithm()
        continue
      }
      throw new Error(`No se reconoce «${this.current.raw}» fuera del algoritmo.`)
    }
    if (!program) throw new Error("El texto no tiene un bloque Algoritmo.")
    return { program: { ...program, routines }, notes: this.notes }
  }

  private parseAlgorithm(): Program {
    this.expect("algoritmo", "Algoritmo")
    if (this.eof() || !isIdentStart(this.current.raw[0] ?? "")) {
      throw new Error("Falta el nombre del algoritmo.")
    }
    const name = this.current.raw
    this.index += 1
    this.skipSemicolons()
    const body = this.parseBlock(new Set(["finalgoritmo"]))
    this.expect("finalgoritmo", "FinAlgoritmo")
    this.skipSemicolons()
    return { name, body, routines: [] }
  }

  private parseRoutine(): Routine {
    const kind = this.is("funcion") ? "funcion" : "procedimiento"
    this.index += 1
    let result = ""
    if (kind === "funcion") {
      result = this.readName("el resultado de la función")
      this.expectAssign()
    }
    const name = this.readName(kind === "funcion" ? "el nombre de la función" : "el nombre del procedimiento")
    this.expect("(", "(")
    const params = this.readUntil((token, depth) => depth === 0 && token.raw === ")")
    this.expect(")", ")")
    const stop = kind === "funcion" ? "finfuncion" : "finsubproceso"
    const body = this.parseBlock(new Set([stop]))
    this.expect(stop, kind === "funcion" ? "FinFuncion" : "FinSubProceso")
    this.skipSemicolons()
    return { id: newId(), kind, name, result, params, body }
  }

  private readName(label: string): string {
    if (this.eof() || !isIdentStart(this.current.raw[0] ?? "")) throw new Error(`Falta ${label}.`)
    const name = this.current.raw
    this.index += 1
    return name
  }

  private parseBlock(stops: Set<string>, caseAware = false): Step[] {
    const steps: Step[] = []
    while (!this.eof() && !stops.has(this.current.canon)) {
      this.skipSemicolons()
      if (this.eof() || stops.has(this.current.canon)) break
      if (caseAware && this.looksLikeCaseLabel()) break
      const parsed = this.parseStatement()
      if (Array.isArray(parsed)) steps.push(...parsed)
      else steps.push(parsed)
    }
    return steps
  }

  private parseStatement(): Step | Step[] {
    if (this.is("//")) {
      const text = this.current.raw
      this.index += 1
      return { id: newId(), kind: "comentario", text }
    }
    if (this.is("definir")) return this.parseDefinir()
    if (this.is("dimension")) return this.parseDimension()
    if (this.is("leer")) return this.parseLeer()
    if (this.is("escribir")) return this.parseEscribir()
    if (this.is("borrar")) return this.parseBorrar()
    if (this.is("esperar")) return this.parseEsperar()
    if (this.is("si")) return this.parseSi()
    if (this.is("segun")) return this.parseSegun()
    if (this.is("mientras")) return this.parseMientras()
    if (this.is("repetir")) return this.parseRepetir()
    if (this.is("para")) return this.parsePara()
    if (this.seesAssign()) return this.parseAsignar()
    if (this.seesCall()) return this.parseLibre(true)
    throw new Error(`No se reconoce «${this.eof() ? "el final del texto" : this.current.raw}» como instrucción.`)
  }

  private parseDefinir(): Step {
    this.expect("definir", "Definir")
    const names = this.readUntil((token) => token.canon === "como")
    this.expect("como", "Como")
    if (this.eof()) throw new Error("Falta el tipo después de Como.")
    const typeName = TYPES[this.current.canon] ?? this.current.raw
    this.index += 1
    this.skipSemicolons()
    if (!names) throw new Error("Falta el nombre en Definir.")
    return { id: newId(), kind: "definir", names, typeName }
  }

  private parseDimension(): Step[] {
    this.expect("dimension", "Dimension")
    const steps: Step[] = []
    while (true) {
      const name = this.readName("el nombre del arreglo")
      this.expect("[", "[")
      const sizes = this.readUntil((token, depth) => depth === 0 && token.raw === "]")
      this.expect("]", "]")
      let typeName = ""
      if (this.is("como")) {
        this.index += 1
        if (this.eof()) throw new Error("Falta el tipo después de Como.")
        typeName = TYPES[this.current.canon] ?? this.current.raw
        this.index += 1
      }
      if (!sizes) throw new Error("Falta el tamaño en Dimension.")
      steps.push({ id: newId(), kind: "dimension", name, sizes, typeName })
      if (!this.isRaw(",")) break
      this.index += 1
    }
    this.skipSemicolons()
    return steps
  }

  private parseAsignar(): Step {
    const destination = this.readUntil((token) => token.canon === "<-" || token.raw === "=")
    this.expectAssign()
    const expression = this.readExpr()
    if (!destination || !expression) throw new Error("Falta completar una asignación.")
    return { id: newId(), kind: "asignar", destination, expression }
  }

  private parseEscribir(): Step {
    this.expect("escribir", "Escribir")
    const text = this.readExpr()
    if (this.is("sin")) {
      this.index += 1
      this.expect("saltar", "Saltar")
    }
    this.skipSemicolons()
    return { id: newId(), kind: "escribir", text }
  }

  private parseLeer(): Step {
    this.expect("leer", "Leer")
    return { id: newId(), kind: "leer", text: this.readExpr() }
  }

  private parseLibre(call: boolean): Step {
    const text = this.readUntil(
      (token, depth, consumed) => consumed > 0 && depth === 0 && (token.raw === ";" || BOUNDARIES.has(token.canon) || this.looksLikeCaseLabel()),
    )
    this.skipSemicolons()
    if (!text) throw new Error("Falta el texto de la instrucción.")
    return { id: newId(), kind: "libre", text, call }
  }

  private parseBorrar(): Step {
    this.expect("borrar", "Borrar")
    this.expect("pantalla", "Pantalla")
    this.skipSemicolons()
    return { id: newId(), kind: "borrar" }
  }

  private parseEsperar(): Step {
    this.expect("esperar", "Esperar")
    const text = this.readUntil((token) => token.canon === "segundos" || token.raw === ";")
    if (this.is("segundos")) this.index += 1
    this.skipSemicolons()
    if (!text) throw new Error("Falta el tiempo de Esperar.")
    return { id: newId(), kind: "esperar", text }
  }

  private parseSi(): Step {
    this.expect("si", "Si")
    const condition = this.readUntil((token) => token.canon === "entonces")
    this.expect("entonces", "Entonces")
    const then = this.parseBlock(new Set(["sino", "finsi"]))
    let otherwise: Step[] = []
    if (this.is("sino")) {
      this.index += 1
      otherwise = this.parseBlock(new Set(["finsi"]))
    }
    this.expect("finsi", "FinSi")
    this.skipSemicolons()
    if (!condition) throw new Error("Falta la condición del Si.")
    return { id: newId(), kind: "si", condition, then, else: otherwise }
  }

  private parseMientras(): Step {
    this.expect("mientras", "Mientras")
    const condition = this.readUntil((token) => token.canon === "hacer")
    this.expect("hacer", "Hacer")
    const body = this.parseBlock(new Set(["finmientras"]))
    this.expect("finmientras", "FinMientras")
    this.skipSemicolons()
    if (!condition) throw new Error("Falta la condición del Mientras.")
    return { id: newId(), kind: "mientras", condition, body }
  }

  private parseRepetir(): Step {
    this.expect("repetir", "Repetir")
    const body = this.parseBlock(new Set(["hasta"]))
    this.expect("hasta", "Hasta")
    this.expect("que", "Que")
    const condition = this.readExpr()
    if (!condition) throw new Error("Falta la condición del Repetir.")
    return { id: newId(), kind: "repetir", condition, body }
  }

  private parsePara(): Step {
    this.expect("para", "Para")
    if (this.eof() || !isIdentStart(this.current.raw[0] ?? "")) throw new Error("Falta la variable del Para.")
    const variable = this.current.raw
    this.index += 1
    this.expectAssign()
    const from = this.readUntil((token) => token.canon === "hasta")
    this.expect("hasta", "Hasta")
    const to = this.readUntil((token) => token.canon === "hacer" || token.canon === "con")
    let step = ""
    if (this.is("con")) {
      this.index += 1
      this.expect("paso", "Paso")
      step = this.readUntil((token) => token.canon === "hacer")
    }
    this.expect("hacer", "Hacer")
    const body = this.parseBlock(new Set(["finpara"]))
    this.expect("finpara", "FinPara")
    this.skipSemicolons()
    if (!from || !to) throw new Error("Falta completar un Para.")
    return { id: newId(), kind: "para", variable, from, to, step, body }
  }

  private parseSegun(): Step {
    this.expect("segun", "Segun")
    const expression = this.readUntil((token) => token.canon === "hacer")
    this.expect("hacer", "Hacer")
    const cases: Extract<Step, { kind: "segun" }>["cases"] = []
    let other: Step[] = []
    while (!this.eof() && !this.is("finsegun")) {
      this.skipSemicolons()
      if (this.eof() || this.is("finsegun")) break
      if (this.is("de")) {
        this.index += 1
        this.expect("otro", "Otro")
        this.expect("modo", "Modo")
        if (this.isRaw(":")) this.index += 1
        other = this.parseBlock(new Set(["finsegun"]))
        break
      }
      const label = this.readUntil((token) => token.raw === ":")
      this.expect(":", ":")
      const body = this.parseBlock(new Set(["finsegun", "de"]), true)
      if (!label) throw new Error("Falta la etiqueta de un caso del Según.")
      cases.push({ id: newId(), label, body })
    }
    this.expect("finsegun", "FinSegun")
    this.skipSemicolons()
    if (!expression) throw new Error("Falta la expresión del Según.")
    return { id: newId(), kind: "segun", expression, cases, other }
  }

  private readExpr(): string {
    const parts: string[] = []
    let depth = 0
    while (!this.eof()) {
      const token = this.current
      if (depth === 0 && !this.expressionContinues(parts.length)) break
      if (token.raw === "(" || token.raw === "[") depth += 1
      else if (token.raw === ")" || token.raw === "]") depth = Math.max(0, depth - 1)
      parts.push(token.raw)
      this.index += 1
    }
    this.skipSemicolons()
    if (!parts.length) throw new Error("Falta el texto de la instrucción.")
    return join(parts)
  }

  private expressionContinues(consumed: number): boolean {
    if (this.eof()) return false
    const token = this.current
    if (token.raw === ";" || token.raw === ":" || token.canon === "<-" || BOUNDARIES.has(token.canon)) return false
    if (consumed === 0) return true
    const previous = this.tokens[this.index - 1]
    if (this.expectsOperand(previous)) return true
    if ((token.raw === "-" || token.raw === "+") && this.looksLikeCaseLabel()) return false
    return INFIX.has(token.canon) || token.raw === "," || token.raw === "(" || token.raw === "["
  }

  private expectsOperand(token: Token): boolean {
    return INFIX.has(token.canon) || token.raw === "," || token.raw === "(" || token.raw === "["
  }

  private readUntil(stop: (token: Token, depth: number, consumed: number) => boolean): string {
    const parts: string[] = []
    let depth = 0
    while (!this.eof()) {
      const token = this.current
      if (stop(token, depth, parts.length)) break
      if (token.raw === "(" || token.raw === "[") depth += 1
      else if (token.raw === ")" || token.raw === "]") depth = Math.max(0, depth - 1)
      parts.push(token.raw)
      this.index += 1
    }
    return join(parts)
  }

  private looksLikeCaseLabel(): boolean {
    let depth = 0
    let consumed = 0
    for (let i = this.index; i < this.tokens.length; i += 1) {
      const token = this.tokens[i]
      if (depth === 0) {
        if (consumed > 0 && token.raw === ":") return true
        if (!this.tokenContinues(token, consumed, i)) return false
      }
      if (token.raw === "(" || token.raw === "[") depth += 1
      else if (token.raw === ")" || token.raw === "]") depth = Math.max(0, depth - 1)
      consumed += 1
    }
    return false
  }

  private tokenContinues(token: Token, consumed: number, index: number): boolean {
    if (token.raw === ";" || token.raw === ":" || token.canon === "<-" || BOUNDARIES.has(token.canon)) return false
    if (consumed === 0) return true
    const previous = this.tokens[index - 1]
    if (this.expectsOperand(previous)) return true
    return INFIX.has(token.canon) || token.raw === "," || token.raw === "(" || token.raw === "["
  }

  private seesAssign(): boolean {
    let depth = 0
    for (let i = this.index; i < this.tokens.length; i += 1) {
      const token = this.tokens[i]
      if (depth === 0) {
        if (token.canon === "<-" || token.raw === "=") return true
        if (token.raw === ";" || BOUNDARIES.has(token.canon)) return false
      }
      if (token.raw === "(" || token.raw === "[") depth += 1
      else if (token.raw === ")" || token.raw === "]") depth = Math.max(0, depth - 1)
    }
    return false
  }

  private seesCall(): boolean {
    return !this.eof() && isIdentStart(this.current.raw[0] ?? "") && this.tokens[this.index + 1]?.raw === "("
  }

  private skipAlgorithm() {
    this.index += 1
    while (!this.eof() && !this.is("finalgoritmo")) this.index += 1
    if (this.eof()) throw new Error("Falta FinAlgoritmo.")
    this.index += 1
    this.skipSemicolons()
  }

  private skipSemicolons() {
    while (this.isRaw(";")) this.index += 1
  }

  private expectAssign() {
    if (!this.eof() && (this.current.canon === "<-" || this.current.raw === "=")) {
      this.index += 1
      return
    }
    const found = this.eof() ? "el final del texto" : `«${this.current.raw}»`
    throw new Error(`Se esperaba <- o = y se encontró ${found}.`)
  }

  private expect(canon: string, label: string) {
    if (!this.is(canon) && !this.isRaw(canon)) {
      const found = this.eof() ? "el final del texto" : `«${this.current.raw}»`
      throw new Error(`Se esperaba ${label} y se encontró ${found}.`)
    }
    this.index += 1
  }

  private note(text: string) {
    if (!this.notes.includes(text)) this.notes.push(text)
  }

  private get current(): Token {
    return this.tokens[this.index]
  }

  private eof(): boolean {
    return this.index >= this.tokens.length
  }

  private is(canon: string): boolean {
    return !this.eof() && this.current.canon === canon
  }

  private isRaw(raw: string): boolean {
    return !this.eof() && this.current.raw === raw
  }
}
