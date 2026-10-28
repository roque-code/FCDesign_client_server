import { spellText, type Dialect } from "../dialect"
import { isIdentContinue, isIdentStart } from "../words"

export type StepKind =
  | "definir"
  | "dimension"
  | "asignar"
  | "escribir"
  | "leer"
  | "borrar"
  | "esperar"
  | "comentario"
  | "si"
  | "mientras"
  | "repetir"
  | "para"
  | "segun"
  | "libre"

export type CaseBranch = { id: string; label: string; body: Step[] }

export type Step =
  | { id: string; kind: "definir"; names: string; typeName: string }
  | { id: string; kind: "dimension"; name: string; sizes: string; typeName: string }
  | { id: string; kind: "asignar"; destination: string; expression: string }
  | { id: string; kind: "escribir"; text: string }
  | { id: string; kind: "leer"; text: string }
  | { id: string; kind: "borrar" }
  | { id: string; kind: "esperar"; text: string }
  | { id: string; kind: "comentario"; text: string }
  | { id: string; kind: "si"; condition: string; then: Step[]; else: Step[] }
  | { id: string; kind: "mientras"; condition: string; body: Step[] }
  | { id: string; kind: "repetir"; condition: string; body: Step[] }
  | { id: string; kind: "para"; variable: string; from: string; to: string; step: string; body: Step[] }
  | { id: string; kind: "segun"; expression: string; cases: CaseBranch[]; other: Step[] }
  | { id: string; kind: "libre"; text: string; call: boolean }

export type RoutineKind = "funcion" | "procedimiento"

export type Routine = {
  id: string
  kind: RoutineKind
  name: string
  result: string
  params: string
  body: Step[]
}

export type Program = { name: string; body: Step[]; routines: Routine[] }

export type SlotPath =
  | { scope: "root"; index: number }
  | { scope: "then" | "else" | "body" | "other" | "routine"; ownerId: string; index: number }
  | { scope: "case"; ownerId: string; caseId: string; index: number }

const KINDS = new Set<StepKind>([
  "definir",
  "dimension",
  "asignar",
  "escribir",
  "leer",
  "borrar",
  "esperar",
  "comentario",
  "si",
  "mientras",
  "repetir",
  "para",
  "segun",
  "libre",
])

const TYPES = ["Entero", "Real", "Lógico", "Caracter", "Cadena"]

let serial = 0

function nextId(): string {
  serial += 1
  const salt = Math.random().toString(36).slice(2, 7)
  return `n${serial}${salt}`
}

export function newId(): string {
  return nextId()
}

export function isStepKind(value: string): value is StepKind {
  return KINDS.has(value as StepKind)
}

export function figureForKind(kind: StepKind): string {
  if (kind === "escribir") return "output"
  if (kind === "leer") return "input"
  if (kind === "si") return "decision"
  if (kind === "mientras" || kind === "repetir" || kind === "para") return "loop"
  if (kind === "segun") return "switch"
  return "process"
}

function say(locale: Dialect, es: string, en: string): string {
  return locale === "en" ? en : es
}

export function badgeFor(kind: StepKind, locale: Dialect = "es"): string | null {
  if (kind === "si") return say(locale, "Si", "If")
  if (kind === "mientras") return say(locale, "Mientras", "While")
  if (kind === "repetir") return say(locale, "Repetir", "Repeat")
  if (kind === "para") return say(locale, "Para", "For")
  if (kind === "segun") return say(locale, "Según", "Switch")
  return null
}

export function isRoutineKind(value: string): value is RoutineKind {
  return value === "funcion" || value === "procedimiento"
}

export function createRoutine(kind: RoutineKind): Routine {
  const id = nextId()
  if (kind === "funcion") return { id, kind, name: "Doblar", result: "resultado", params: "n", body: [] }
  return { id, kind, name: "Incrementar", result: "", params: "n Por Referencia", body: [] }
}

export function routineTitle(routine: Routine, locale: Dialect = "es"): string {
  const name = clean(routine.name) || (routine.kind === "funcion" ? "funcion" : "procedimiento")
  const params = spellText(locale, clean(routine.params))
  if (routine.kind === "funcion") {
    return `${say(locale, "Funcion", "Function")} ${clean(routine.result) || "resultado"} <- ${name}(${params})`
  }
  return `${say(locale, "SubProceso", "SubProcedure")} ${name}(${params})`
}

export function createStep(kind: StepKind): Step {
  const id = nextId()
  switch (kind) {
    case "definir":
      return { id, kind, names: "dato", typeName: "Entero" }
    case "dimension":
      return { id, kind, name: "datos", sizes: "5", typeName: "Entero" }
    case "asignar":
      return { id, kind, destination: "dato", expression: "0" }
    case "escribir":
      return { id, kind, text: '"texto"' }
    case "leer":
      return { id, kind, text: "dato" }
    case "borrar":
      return { id, kind }
    case "esperar":
      return { id, kind, text: "1" }
    case "comentario":
      return { id, kind, text: "nota" }
    case "libre":
      return { id, kind, text: "instruccion", call: false }
    case "si":
      return { id, kind, condition: "condicion", then: [], else: [] }
    case "mientras":
      return { id, kind, condition: "condicion", body: [] }
    case "repetir":
      return { id, kind, condition: "condicion", body: [] }
    case "para":
      return { id, kind, variable: "i", from: "1", to: "10", step: "", body: [] }
    case "segun":
      return {
        id,
        kind,
        expression: "opcion",
        cases: [
          { id: nextId(), label: "1", body: [] },
          { id: nextId(), label: "2", body: [] },
        ],
        other: [],
      }
  }
}

export function emptyProgram(): Program {
  return { name: "Diagrama", body: [], routines: [] }
}

export function guessingGame(): Program {
  return {
    name: "Adivina_Numero",
    routines: [],
    body: [
      { id: "def", kind: "definir", names: "intentos, num_secreto, num_ingresado", typeName: "Entero" },
      { id: "as1", kind: "asignar", destination: "intentos", expression: "10" },
      { id: "as2", kind: "asignar", destination: "num_secreto", expression: "Trunc(Aleatorio(0, 100))" },
      { id: "wr1", kind: "escribir", text: '"Adivine el numero (de 1 a 100):"' },
      { id: "rd1", kind: "leer", text: "num_ingresado" },
      {
        id: "wh",
        kind: "mientras",
        condition: "num_secreto <> num_ingresado Y intentos > 1",
        body: [
          {
            id: "si1",
            kind: "si",
            condition: "num_secreto > num_ingresado",
            then: [{ id: "bajo", kind: "escribir", text: '"Muy bajo"' }],
            else: [{ id: "alto", kind: "escribir", text: '"Muy alto"' }],
          },
          { id: "as3", kind: "asignar", destination: "intentos", expression: "intentos - 1" },
          { id: "wr2", kind: "escribir", text: '"Le quedan ", intentos, " intentos."' },
          { id: "rd2", kind: "leer", text: "num_ingresado" },
        ],
      },
      {
        id: "si2",
        kind: "si",
        condition: "num_secreto = num_ingresado",
        then: [{ id: "ok", kind: "escribir", text: '"Exacto! Usted adivino en ", 11 - intentos, " intentos."' }],
        else: [{ id: "no", kind: "escribir", text: '"El numero era ", num_secreto' }],
      },
    ],
  }
}

export function slotKey(path: SlotPath): string {
  if (path.scope === "root") return `root:${path.index}`
  if (path.scope === "case") return `case:${path.ownerId}:${path.caseId}:${path.index}`
  return `${path.scope}:${path.ownerId}:${path.index}`
}

function listsOf(step: Step): Step[][] {
  switch (step.kind) {
    case "si":
      return [step.then, step.else]
    case "mientras":
    case "repetir":
    case "para":
      return [step.body]
    case "segun":
      return [...step.cases.map((item) => item.body), step.other]
    default:
      return []
  }
}

function mapChildren(step: Step, fn: (list: Step[]) => Step[]): Step {
  switch (step.kind) {
    case "si":
      return { ...step, then: fn(step.then), else: fn(step.else) }
    case "mientras":
    case "repetir":
    case "para":
      return { ...step, body: fn(step.body) }
    case "segun":
      return {
        ...step,
        cases: step.cases.map((item) => ({ ...item, body: fn(item.body) })),
        other: fn(step.other),
      }
    default:
      return step
  }
}

function mapTree(steps: Step[], id: string, patch: (step: Step) => Step): Step[] {
  return steps.map((step) => {
    const next = step.id === id ? patch(step) : step
    return mapChildren(next, (list) => mapTree(list, id, patch))
  })
}

function strip(steps: Step[], id: string): Step[] {
  return steps.filter((step) => step.id !== id).map((step) => mapChildren(step, (list) => strip(list, id)))
}

export function containsId(step: Step, id: string): boolean {
  if (step.id === id) return true
  return listsOf(step).some((list) => list.some((child) => containsId(child, id)))
}

export function findStep(program: Program, id: string): Step | null {
  const walk = (steps: Step[]): Step | null => {
    for (const step of steps) {
      if (step.id === id) return step
      const nested = walk(listsOf(step).flat())
      if (nested) return nested
    }
    return null
  }
  return walk(program.body) ?? walk(program.routines.flatMap((routine) => routine.body))
}

export function findRoutine(program: Program, id: string): Routine | null {
  return program.routines.find((routine) => routine.id === id) ?? null
}

function locateIn(steps: Step[], path: SlotPath, id: string): SlotPath | null {
  for (let index = 0; index < steps.length; index += 1) {
    if (steps[index].id === id) return { ...path, index }
    const nested = locateInside(steps[index], id)
    if (nested) return nested
  }
  return null
}

function locateInside(step: Step, id: string): SlotPath | null {
  switch (step.kind) {
    case "si":
      return (
        locateIn(step.then, { scope: "then", ownerId: step.id, index: 0 }, id) ??
        locateIn(step.else, { scope: "else", ownerId: step.id, index: 0 }, id)
      )
    case "mientras":
    case "repetir":
    case "para":
      return locateIn(step.body, { scope: "body", ownerId: step.id, index: 0 }, id)
    case "segun": {
      for (const item of step.cases) {
        const found = locateIn(item.body, { scope: "case", ownerId: step.id, caseId: item.id, index: 0 }, id)
        if (found) return found
      }
      return locateIn(step.other, { scope: "other", ownerId: step.id, index: 0 }, id)
    }
    default:
      return null
  }
}

export function locateStep(program: Program, id: string): SlotPath | null {
  const inBody = locateIn(program.body, { scope: "root", index: 0 }, id)
  if (inBody) return inBody
  for (const routine of program.routines) {
    const found = locateIn(routine.body, { scope: "routine", ownerId: routine.id, index: 0 }, id)
    if (found) return found
  }
  return null
}

function sameList(left: SlotPath, right: SlotPath): boolean {
  if (left.scope !== right.scope) return false
  if (left.scope === "root" || right.scope === "root") return left.scope === "root"
  if (left.ownerId !== right.ownerId) return false
  if (left.scope === "case" && right.scope === "case") return left.caseId === right.caseId
  return true
}

function transform(steps: Step[], path: SlotPath, change: (list: Step[]) => Step[]): Step[] {
  if (path.scope === "root") return change(steps)
  return steps.map((step) => rewrite(step, path, change))
}

function rewrite(step: Step, path: SlotPath, change: (list: Step[]) => Step[]): Step {
  if (path.scope !== "root" && step.id === path.ownerId) return applyOwner(step, path, change)
  return mapChildren(step, (list) => list.map((child) => rewrite(child, path, change)))
}

function applyOwner(step: Step, path: SlotPath, change: (list: Step[]) => Step[]): Step {
  if (step.kind === "si" && path.scope === "then") return { ...step, then: change(step.then) }
  if (step.kind === "si" && path.scope === "else") return { ...step, else: change(step.else) }
  if ((step.kind === "mientras" || step.kind === "repetir" || step.kind === "para") && path.scope === "body") {
    return { ...step, body: change(step.body) }
  }
  if (step.kind === "segun" && path.scope === "other") return { ...step, other: change(step.other) }
  if (step.kind === "segun" && path.scope === "case") {
    return {
      ...step,
      cases: step.cases.map((item) => (item.id === path.caseId ? { ...item, body: change(item.body) } : item)),
    }
  }
  return step
}

function splice(list: Step[], index: number, step: Step): Step[] {
  const next = list.slice()
  const at = Math.max(0, Math.min(index, next.length))
  next.splice(at, 0, step)
  return next
}

export function insertStep(program: Program, path: SlotPath, step: Step): Program {
  if (path.scope === "routine") {
    return {
      ...program,
      routines: program.routines.map((routine) =>
        routine.id === path.ownerId ? { ...routine, body: splice(routine.body, path.index, step) } : routine,
      ),
    }
  }
  const change = (list: Step[]) => splice(list, path.index, step)
  if (path.scope === "root") return { ...program, body: transform(program.body, path, change) }
  return {
    ...program,
    body: transform(program.body, path, change),
    routines: program.routines.map((routine) => ({ ...routine, body: transform(routine.body, path, change) })),
  }
}

export function removeStep(program: Program, id: string): Program {
  return {
    ...program,
    body: strip(program.body, id),
    routines: program.routines.map((routine) => ({ ...routine, body: strip(routine.body, id) })),
  }
}

export function addRoutine(program: Program, routine: Routine): Program {
  return { ...program, routines: [...program.routines, routine] }
}

export function removeRoutine(program: Program, id: string): Program {
  return { ...program, routines: program.routines.filter((routine) => routine.id !== id) }
}

export function updateRoutine(program: Program, id: string, patch: (routine: Routine) => Routine): Program {
  return { ...program, routines: program.routines.map((routine) => (routine.id === id ? patch(routine) : routine)) }
}

export function moveStep(program: Program, id: string, path: SlotPath): Program {
  const step = findStep(program, id)
  if (!step) return program
  if (path.scope !== "root" && containsId(step, path.ownerId)) return program
  const current = locateStep(program, id)
  let index = path.index
  if (current && sameList(current, path) && current.index < path.index) index -= 1
  const adjusted = { ...path, index }
  const cleared = removeStep(program, id)
  return insertStep(cleared, adjusted, step)
}

export function updateStep(program: Program, id: string, patch: (step: Step) => Step): Program {
  return {
    ...program,
    body: mapTree(program.body, id, patch),
    routines: program.routines.map((routine) => ({ ...routine, body: mapTree(routine.body, id, patch) })),
  }
}

export function addCase(program: Program, ownerId: string): Program {
  return updateStep(program, ownerId, (step) => {
    if (step.kind !== "segun" || step.cases.length >= 6) return step
    return {
      ...step,
      cases: [...step.cases, { id: nextId(), label: String(step.cases.length + 1), body: [] }],
    }
  })
}

export function removeCase(program: Program, ownerId: string): Program {
  return updateStep(program, ownerId, (step) => {
    if (step.kind !== "segun" || step.cases.length <= 1) return step
    return { ...step, cases: step.cases.slice(0, -1) }
  })
}

function dimensionText(step: Extract<Step, { kind: "dimension" }>, locale: Dialect): string {
  const typed = step.typeName ? ` ${say(locale, "Como", "As")} ${spellText(locale, step.typeName)}` : ""
  return `${say(locale, "Dimension", "Dimension")} ${clean(step.name) || "…"}[${clean(step.sizes) || "…"}]${typed}`
}

function clean(text: string): string {
  return text.trim().replace(/\s+/g, " ")
}

export function algorithmName(name: string): string {
  const trimmed = clean(name).replace(/ /g, "_")
  const chars = [...trimmed]
  if (chars.length === 0 || !isIdentStart(chars[0])) return "Diagrama"
  if (!chars.every((ch, index) => (index === 0 ? isIdentStart(ch) : isIdentContinue(ch)))) return "Diagrama"
  return trimmed
}

export function caption(step: Step, locale: Dialect = "es"): string {
  switch (step.kind) {
    case "definir":
      return `${say(locale, "Definir", "Declare")} ${clean(step.names) || "…"} ${say(locale, "Como", "As")} ${spellText(locale, step.typeName)}`
    case "dimension":
      return dimensionText(step, locale)
    case "asignar":
      return `${clean(step.destination) || "…"} <- ${spellText(locale, clean(step.expression) || "…")}`
    case "escribir":
      return `${say(locale, "Escribir", "Write")} ${spellText(locale, clean(step.text) || "…")}`
    case "leer":
      return `${say(locale, "Leer", "Read")} ${clean(step.text) || "…"}`
    case "borrar":
      return say(locale, "Borrar Pantalla", "Clear Screen")
    case "esperar":
      return `${say(locale, "Esperar", "Wait")} ${clean(step.text) || "…"} ${say(locale, "Segundos", "Seconds")}`
    case "comentario":
      return `// ${clean(step.text) || "…"}`
    case "libre":
      return spellText(locale, clean(step.text) || "…")
    case "si":
    case "mientras":
    case "repetir":
      return spellText(locale, clean(step.condition) || "condición")
    case "para": {
      const pace = clean(step.step)
      const range = `${clean(step.variable) || "i"} <- ${clean(step.from) || "…"} ${say(locale, "hasta", "until")} ${clean(step.to) || "…"}`
      return pace ? `${range} ${say(locale, "paso", "step")} ${pace}` : range
    }
    case "segun":
      return spellText(locale, clean(step.expression) || "expresión")
  }
}

function pad(level: number): string {
  return "    ".repeat(level)
}

function writeBody(steps: Step[], level: number, lines: string[], semicolons: boolean, locale: Dialect) {
  for (const step of steps) writeStep(step, level, lines, semicolons, locale)
}

function writeStep(step: Step, level: number, lines: string[], semicolons: boolean, locale: Dialect) {
  const indent = pad(level)
  const stop = semicolons ? ";" : ""
  switch (step.kind) {
    case "definir":
      lines.push(
        `${indent}${say(locale, "Definir", "Declare")} ${clean(step.names) || "…"} ${say(locale, "Como", "As")} ${spellText(locale, step.typeName)}${stop}`,
      )
      return
    case "dimension":
      lines.push(`${indent}${dimensionText(step, locale)}${stop}`)
      return
    case "asignar":
      lines.push(`${indent}${clean(step.destination) || "…"} <- ${spellText(locale, clean(step.expression) || "…")}${stop}`)
      return
    case "escribir":
      lines.push(`${indent}${say(locale, "Escribir", "Write")} ${spellText(locale, clean(step.text) || "…")}${stop}`)
      return
    case "leer":
      lines.push(`${indent}${say(locale, "Leer", "Read")} ${clean(step.text) || "…"}${stop}`)
      return
    case "borrar":
      lines.push(`${indent}${say(locale, "Borrar Pantalla", "Clear Screen")}${stop}`)
      return
    case "esperar":
      lines.push(`${indent}${say(locale, "Esperar", "Wait")} ${clean(step.text) || "…"} ${say(locale, "Segundos", "Seconds")}${stop}`)
      return
    case "comentario":
      lines.push(`${indent}// ${clean(step.text) || "…"}`)
      return
    case "libre":
      lines.push(`${indent}${spellText(locale, clean(step.text) || "…")}${stop}`)
      return
    case "si":
      lines.push(`${indent}${say(locale, "Si", "If")} ${spellText(locale, clean(step.condition) || "…")} ${say(locale, "Entonces", "Then")}`)
      writeBody(step.then, level + 1, lines, semicolons, locale)
      lines.push(`${indent}${say(locale, "Sino", "Else")}`)
      writeBody(step.else, level + 1, lines, semicolons, locale)
      lines.push(`${indent}${say(locale, "FinSi", "EndIf")}`)
      return
    case "mientras":
      lines.push(`${indent}${say(locale, "Mientras", "While")} ${spellText(locale, clean(step.condition) || "…")} ${say(locale, "Hacer", "Do")}`)
      writeBody(step.body, level + 1, lines, semicolons, locale)
      lines.push(`${indent}${say(locale, "FinMientras", "EndWhile")}`)
      return
    case "repetir":
      lines.push(`${indent}${say(locale, "Repetir", "Repeat")}`)
      writeBody(step.body, level + 1, lines, semicolons, locale)
      lines.push(`${indent}${say(locale, "Hasta Que", "Until That")} ${spellText(locale, clean(step.condition) || "…")}`)
      return
    case "para": {
      const pace = clean(step.step)
      const extra = pace ? ` ${say(locale, "Con Paso", "With Step")} ${pace}` : ""
      lines.push(
        `${indent}${say(locale, "Para", "For")} ${clean(step.variable) || "…"} <- ${clean(step.from) || "…"} ${say(locale, "Hasta", "Until")} ${clean(step.to) || "…"}${extra} ${say(locale, "Hacer", "Do")}`,
      )
      writeBody(step.body, level + 1, lines, semicolons, locale)
      lines.push(`${indent}${say(locale, "FinPara", "EndFor")}`)
      return
    }
    case "segun": {
      lines.push(`${indent}${say(locale, "Segun", "Switch")} ${spellText(locale, clean(step.expression) || "…")} ${say(locale, "Hacer", "Do")}`)
      const inner = pad(level + 1)
      for (const item of step.cases) {
        lines.push(`${inner}${clean(item.label) || "…"}:`)
        writeBody(item.body, level + 2, lines, semicolons, locale)
      }
      lines.push(`${inner}${say(locale, "De Otro Modo:", "In Other Case:")}`)
      writeBody(step.other, level + 2, lines, semicolons, locale)
      lines.push(`${indent}${say(locale, "FinSegun", "EndSwitch")}`)
      return
    }
  }
}

function writeRoutine(routine: Routine, lines: string[], semicolons: boolean, locale: Dialect) {
  const name = algorithmName(routine.name)
  const params = spellText(locale, clean(routine.params))
  if (routine.kind === "funcion") {
    lines.push(`${say(locale, "Funcion", "Function")} ${clean(routine.result) || "resultado"} <- ${name}(${params})`)
  } else {
    lines.push(`${say(locale, "SubProceso", "SubProcedure")} ${name}(${params})`)
  }
  writeBody(routine.body, 1, lines, semicolons, locale)
  lines.push(routine.kind === "funcion" ? say(locale, "FinFuncion", "EndFunction") : say(locale, "FinSubProceso", "EndSubProcedure"))
}

export function toSource(program: Program, semicolons = true, locale: Dialect = "es"): string {
  const lines: string[] = []
  for (const routine of program.routines) writeRoutine(routine, lines, semicolons, locale)
  lines.push(`${say(locale, "Algoritmo", "Algorithm")} ${algorithmName(program.name)}`)
  writeBody(program.body, 1, lines, semicolons, locale)
  lines.push(say(locale, "FinAlgoritmo", "EndAlgorithm"))
  return `${lines.join("\n")}\n`
}

export function issues(program: Program): string[] {
  const notes: string[] = []
  if (algorithmName(program.name) === "Diagrama" && clean(program.name) !== "Diagrama") {
    notes.push("El nombre del algoritmo tiene que ser un identificador.")
  }
  const walk = (steps: Step[]) => {
    for (const step of steps) {
      if ((step.kind === "si" || step.kind === "mientras" || step.kind === "repetir") && !clean(step.condition)) {
        notes.push("Falta una condición.")
      }
      if (step.kind === "definir" && !clean(step.names)) notes.push("Falta el nombre en Definir.")
      if (step.kind === "dimension" && (!clean(step.name) || !clean(step.sizes))) {
        notes.push("Falta el nombre o el tamaño en Dimension.")
      }
      if (step.kind === "asignar" && (!clean(step.destination) || !clean(step.expression))) {
        notes.push("Falta completar una asignación.")
      }
      if (
        (step.kind === "escribir" ||
          step.kind === "leer" ||
          step.kind === "esperar" ||
          step.kind === "libre" ||
          step.kind === "comentario") &&
        !clean(step.text)
      ) {
        notes.push("Hay una figura sin texto.")
      }
      if (step.kind === "para" && (!clean(step.variable) || !clean(step.from) || !clean(step.to))) {
        notes.push("Falta completar un Para.")
      }
      if (step.kind === "segun") {
        if (!clean(step.expression)) notes.push("Falta la expresión del Según.")
        if (step.cases.some((item) => !clean(item.label))) notes.push("Hay un caso del Según sin etiqueta.")
      }
      for (const list of listsOf(step)) walk(list)
    }
  }
  walk(program.body)
  for (const routine of program.routines) {
    if (algorithmName(routine.name) === "Diagrama" && clean(routine.name) !== "Diagrama") {
      notes.push(routine.kind === "funcion" ? "El nombre de la función no es válido." : "El nombre del procedimiento no es válido.")
    }
    if (routine.kind === "funcion" && !clean(routine.result)) notes.push("Falta el resultado de la función.")
    walk(routine.body)
  }
  return notes
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null
}

function isStep(value: unknown): value is Step {
  if (!isRecord(value) || typeof value.id !== "string" || typeof value.kind !== "string" || !isStepKind(value.kind)) {
    return false
  }
  const kind = value.kind
  if (kind === "definir") return typeof value.names === "string" && typeof value.typeName === "string"
  if (kind === "dimension") {
    return typeof value.name === "string" && typeof value.sizes === "string" && typeof value.typeName === "string"
  }
  if (kind === "asignar") return typeof value.destination === "string" && typeof value.expression === "string"
  if (kind === "escribir" || kind === "leer" || kind === "esperar" || kind === "comentario") return typeof value.text === "string"
  if (kind === "libre") return typeof value.text === "string" && typeof value.call === "boolean"
  if (kind === "borrar") return true
  if (kind === "si") {
    return typeof value.condition === "string" && Array.isArray(value.then) && value.then.every(isStep) && Array.isArray(value.else) && value.else.every(isStep)
  }
  if (kind === "mientras" || kind === "repetir") {
    return typeof value.condition === "string" && Array.isArray(value.body) && value.body.every(isStep)
  }
  if (kind === "para") {
    return (
      typeof value.variable === "string" &&
      typeof value.from === "string" &&
      typeof value.to === "string" &&
      typeof value.step === "string" &&
      Array.isArray(value.body) &&
      value.body.every(isStep)
    )
  }
  if (!Array.isArray(value.cases) || !Array.isArray(value.other) || typeof value.expression !== "string") return false
  return (
    value.other.every(isStep) &&
    value.cases.every(
      (item) => isRecord(item) && typeof item.id === "string" && typeof item.label === "string" && Array.isArray(item.body) && item.body.every(isStep),
    )
  )
}

export function parseProgram(value: unknown): Program | null {
  if (!isRecord(value) || typeof value.name !== "string" || !Array.isArray(value.body) || !value.body.every(isStep)) {
    return null
  }
  const body = value.body.map(normalizeStep)
  const routines = Array.isArray(value.routines) ? value.routines.filter(isRoutine).map(normalizeRoutine) : []
  return { name: value.name, body, routines }
}

function isRoutine(value: unknown): value is Routine {
  if (!isRecord(value) || typeof value.id !== "string" || (value.kind !== "funcion" && value.kind !== "procedimiento")) return false
  return typeof value.name === "string" && typeof value.result === "string" && typeof value.params === "string" && Array.isArray(value.body) && value.body.every(isStep)
}

function normalizeRoutine(routine: Routine): Routine {
  return { ...routine, body: routine.body.map(normalizeStep) }
}

function normalizeStep(step: Step): Step {
  if (step.kind === "definir" && !TYPES.includes(step.typeName)) return { ...step, typeName: "Entero" }
  if (step.kind === "dimension" && step.typeName && !TYPES.includes(step.typeName)) return { ...step, typeName: "Entero" }
  if (step.kind === "si") return { ...step, then: step.then.map(normalizeStep), else: step.else.map(normalizeStep) }
  if (step.kind === "mientras" || step.kind === "repetir" || step.kind === "para") {
    return { ...step, body: step.body.map(normalizeStep) }
  }
  if (step.kind === "segun") {
    return {
      ...step,
      cases: step.cases.map((item) => ({ ...item, body: item.body.map(normalizeStep) })),
      other: step.other.map(normalizeStep),
    }
  }
  return step
}

export const TYPE_OPTIONS = TYPES
