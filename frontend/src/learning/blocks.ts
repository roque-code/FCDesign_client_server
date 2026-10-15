/**
 * Bloques del primer corte visual.
 * No hay generador de código: la serialización es el JSON de Blockly.
 */

import * as Blockly from "blockly/core"

import { spellText, type Dialect } from "../dialect"
import { normalizeCharacter, normalizeVariableName } from "./names"
import { CHECK, isTrazaType, outputChecks, TYPE_LABELS } from "./types"

let wordsLocale: Dialect = "es"
let extensionsReady = false
let builtLocale: Dialect | null = null

function say(es: string, en: string): string {
  return wordsLocale === "en" ? en : es
}

function typeOptions(): [string, string][] {
  return TYPE_LABELS.map(([label, value]) => [spellText(wordsLocale, label), value])
}

function modeOptions(): [string, string][] {
  return [
    [say("por valor", "By Value"), "valor"],
    [say("por referencia", "By Reference"), "referencia"],
  ]
}

export const BLOCK = {
  definir: "traza_definir",
  asignar: "traza_asignar",
  variable: "traza_variable",
  leer: "traza_leer",
  escribir: "traza_escribir",
  borrarPantalla: "traza_borrar_pantalla",
  esperar: "traza_esperar",
  unir: "traza_unir",
  entero: "traza_entero",
  real: "traza_real",
  cadena: "traza_cadena",
  caracter: "traza_caracter",
  logico: "traza_logico",
  aritmetica: "traza_aritmetica",
  relacional: "traza_relacional",
  logica: "traza_logica",
  no: "traza_no",
  si: "traza_si",
  siSino: "traza_si_sino",
  mientras: "traza_mientras",
  segun: "traza_segun",
  para: "traza_para",
  repetir: "traza_repetir",
  dimension: "traza_dimension",
  indice: "traza_indice",
  asignarIndice: "traza_asignar_indice",
  leerIndice: "traza_leer_indice",
  funcion: "traza_funcion",
  procedimiento: "traza_procedimiento",
  llamada: "traza_llamada",
  llamar: "traza_llamar",
} as const

const VARIABLE = 230
const IO = 160
const OPERATOR = 20
const CONTROL = 290
const ARRAY = 65
const ROUTINE = 120
const SEGUN_MIN = 1
const SEGUN_MAX = 12
const SEGUN_DEFAULT = 2

const segunCases = new WeakMap<Blockly.Block, number>()

function segunIcon(path: string): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"><rect width="16" height="16" rx="3" fill="#ffffff"/>${path}</svg>`
  return `data:image/svg+xml,${encodeURIComponent(svg)}`
}

const SEGUN_PLUS = segunIcon('<path d="M7 3h2v10H7zM3 7h10v2H3z" fill="#3d2a5c"/>')
const SEGUN_MINUS = segunIcon('<path d="M3 7h10v2H3z" fill="#3d2a5c"/>')

function segunCount(block: Blockly.Block): number {
  return segunCases.get(block) ?? SEGUN_DEFAULT
}

function clampSegun(count: number): number {
  return Math.min(SEGUN_MAX, Math.max(SEGUN_MIN, Math.floor(count)))
}

function paintSegunButtons(block: Blockly.Block) {
  if (block.getInput("CASOS")) block.removeInput("CASOS")
  const row = block.appendDummyInput("CASOS")
  const count = segunCount(block)
  if (count < SEGUN_MAX) {
    row.appendField(new Blockly.FieldImage(SEGUN_PLUS, 16, 16, "Agregar caso", () => addSegunCase(block, 1)))
  }
  if (count > SEGUN_MIN) {
    row.appendField(new Blockly.FieldImage(SEGUN_MINUS, 16, 16, "Quitar caso", () => addSegunCase(block, -1)))
  }
  if (block.getInput("OTRO_ETIQUETA")) block.moveInputBefore("CASOS", "OTRO_ETIQUETA")
}

function ensureSegunTail(block: Blockly.Block) {
  if (block.getInput("OTRO")) return
  block.appendDummyInput("CASOS")
  block.appendDummyInput("OTRO_ETIQUETA").appendField(say("De Otro Modo:", "In Other Case:"))
  block.appendStatementInput("OTRO")
  block.appendDummyInput("CIERRE").appendField(say("FinSegun", "EndSwitch"))
  paintSegunButtons(block)
}

function reshapeSegun(block: Blockly.Block) {
  const count = segunCount(block)
  for (let index = SEGUN_MAX; index > count; index -= 1) {
    if (block.getInput(`HACER${index}`)) block.removeInput(`HACER${index}`)
    if (block.getInput(`CASO${index}`)) block.removeInput(`CASO${index}`)
  }
  ensureSegunTail(block)
  for (let index = 1; index <= count; index += 1) {
    if (block.getInput(`CASO${index}`)) continue
    block.appendValueInput(`CASO${index}`).setCheck(CHECK.expresion).appendField(say("caso", "case"))
    block.appendStatementInput(`HACER${index}`)
    block.moveInputBefore(`CASO${index}`, "CASOS")
    block.moveInputBefore(`HACER${index}`, "CASOS")
  }
  paintSegunButtons(block)
}

function addSegunCase(block: Blockly.Block, delta: number) {
  const next = clampSegun(segunCount(block) + delta)
  if (next === segunCount(block)) return
  segunCases.set(block, next)
  reshapeSegun(block)
}

const COUNT_MIN = 0
const COUNT_MAX = 4
const WRITE_MIN = 1
const WRITE_MAX = 8
const DIM_MIN = 1
const DIM_MAX = 4

const dimCounts = new WeakMap<Blockly.Block, number>()
const indexCounts = new WeakMap<Blockly.Block, number>()
const paramCounts = new WeakMap<Blockly.Block, number>()
const argCounts = new WeakMap<Blockly.Block, number>()
const writeCounts = new WeakMap<Blockly.Block, number>()


function clampCount(count: number, low: number, high: number): number {
  return Math.min(high, Math.max(low, Math.floor(count)))
}

function nameField(fieldName: string, text: string) {
  const field = new Blockly.FieldTextInput(text)
  field.setValidator((value: string) => normalizeVariableName(String(value)))
  return { field, fieldName }
}

function paintCount(
  block: Blockly.Block,
  rowName: string,
  before: string | null,
  count: number,
  low: number,
  high: number,
  plus: string,
  minus: string,
  change: (delta: number) => void,
) {
  if (block.getInput(rowName)) block.removeInput(rowName)
  const row = block.appendDummyInput(rowName)
  if (count < high) {
    row.appendField(new Blockly.FieldImage(SEGUN_PLUS, 16, 16, plus, () => change(1)))
  }
  if (count > low) {
    row.appendField(new Blockly.FieldImage(SEGUN_MINUS, 16, 16, minus, () => change(-1)))
  }
  if (before && block.getInput(before)) block.moveInputBefore(rowName, before)
}

function reshapeSizes(block: Blockly.Block) {
  const count = dimCounts.get(block) ?? DIM_MIN
  for (let index = DIM_MAX; index > count; index -= 1) {
    if (block.getInput(`TAMANO${index}`)) block.removeInput(`TAMANO${index}`)
  }
  if (!block.getInput("TAMANOS")) block.appendDummyInput("TAMANOS")
  for (let index = 1; index <= count; index += 1) {
    if (block.getInput(`TAMANO${index}`)) continue
    block.appendValueInput(`TAMANO${index}`).setCheck(CHECK.numero).appendField(say("tamaño", "size"))
    block.moveInputBefore(`TAMANO${index}`, "TAMANOS")
  }
  paintCount(block, "TAMANOS", null, count, DIM_MIN, DIM_MAX, say("Agregar dimensión", "Add dimension"), say("Quitar dimensión", "Remove dimension"), (delta) => {
    const next = clampCount(count + delta, DIM_MIN, DIM_MAX)
    if (next === count) return
    dimCounts.set(block, next)
    reshapeSizes(block)
  })
}

function reshapeIndexes(block: Blockly.Block) {
  const count = indexCounts.get(block) ?? DIM_MIN
  for (let index = DIM_MAX; index > count; index -= 1) {
    if (block.getInput(`INDICE${index}`)) block.removeInput(`INDICE${index}`)
  }
  if (block.type === BLOCK.asignarIndice && !block.getInput("VALOR")) {
    block.appendValueInput("VALOR").setCheck(CHECK.expresion).appendField("<-")
  }
  if (!block.getInput("INDICES")) block.appendDummyInput("INDICES")
  if (block.getInput("VALOR")) block.moveInputBefore("INDICES", "VALOR")
  for (let index = 1; index <= count; index += 1) {
    if (block.getInput(`INDICE${index}`)) continue
    block.appendValueInput(`INDICE${index}`).setCheck(CHECK.numero).appendField(say("índice", "index"))
    block.moveInputBefore(`INDICE${index}`, "INDICES")
  }
  paintCount(block, "INDICES", block.getInput("VALOR") ? "VALOR" : null, count, DIM_MIN, DIM_MAX, say("Agregar índice", "Add index"), say("Quitar índice", "Remove index"), (delta) => {
    const next = clampCount(count + delta, DIM_MIN, DIM_MAX)
    if (next === count) return
    indexCounts.set(block, next)
    reshapeIndexes(block)
  })
}

function reshapeRoutine(block: Blockly.Block) {
  const count = paramCounts.get(block) ?? 1
  const closing = block.type === BLOCK.procedimiento ? say("FinSubProceso", "EndSubProcedure") : say("FinFuncion", "EndFunction")
  for (let index = COUNT_MAX; index > count; index -= 1) {
    if (block.getInput(`PARAM${index}`)) block.removeInput(`PARAM${index}`)
  }
  if (!block.getInput("CUERPO")) {
    block.appendStatementInput("CUERPO")
    block.appendDummyInput("CIERRE").appendField(closing)
  }
  if (!block.getInput("PARAMS")) block.appendDummyInput("PARAMS")
  block.moveInputBefore("PARAMS", "CUERPO")
  for (let index = 1; index <= count; index += 1) {
    if (block.getInput(`PARAM${index}`)) continue
    const named = nameField(`PARAM${index}`, "n")
    block
      .appendDummyInput(`PARAM${index}`)
      .appendField(named.field, named.fieldName)
      .appendField(new Blockly.FieldDropdown(modeOptions()), `MODO${index}`)
    block.moveInputBefore(`PARAM${index}`, "PARAMS")
  }
  paintCount(block, "PARAMS", "CUERPO", count, COUNT_MIN, COUNT_MAX, "Agregar parámetro", "Quitar parámetro", (delta) => {
    const next = clampCount(count + delta, COUNT_MIN, COUNT_MAX)
    if (next === count) return
    paramCounts.set(block, next)
    reshapeRoutine(block)
  })
}

function reshapeWrites(block: Blockly.Block) {
  const count = writeCounts.get(block) ?? WRITE_MIN
  for (let index = WRITE_MAX; index > count; index -= 1) {
    if (block.getInput(`VALOR${index}`)) block.removeInput(`VALOR${index}`)
  }
  if (!block.getInput("VALORES")) block.appendDummyInput("VALORES")
  for (let index = 2; index <= count; index += 1) {
    if (block.getInput(`VALOR${index}`)) continue
    block.appendValueInput(`VALOR${index}`).setCheck(CHECK.expresion).appendField(",")
    block.moveInputBefore(`VALOR${index}`, "VALORES")
  }
  paintCount(
    block,
    "VALORES",
    null,
    count,
    WRITE_MIN,
    WRITE_MAX,
    "Agregar valor",
    "Quitar valor",
    (delta) => {
      const next = clampCount(count + delta, WRITE_MIN, WRITE_MAX)
      if (next === count) return
      writeCounts.set(block, next)
      reshapeWrites(block)
    },
  )
}

function reshapeArgs(block: Blockly.Block) {
  const count = argCounts.get(block) ?? 1
  for (let index = COUNT_MAX; index > count; index -= 1) {
    if (block.getInput(`ARG${index}`)) block.removeInput(`ARG${index}`)
  }
  if (!block.getInput("ABRIR")) block.appendDummyInput("ABRIR").appendField("(")
  if (!block.getInput("CERRAR")) block.appendDummyInput("CERRAR").appendField(")")
  if (!block.getInput("ARGS")) block.appendDummyInput("ARGS")
  for (let index = 1; index <= count; index += 1) {
    if (block.getInput(`ARG${index}`)) continue
    block.appendValueInput(`ARG${index}`).setCheck(CHECK.expresion)
    block.moveInputBefore(`ARG${index}`, "CERRAR")
  }
  if (block.getInput("ARGS")) block.moveInputBefore("ARGS", "CERRAR")
  if (block.getInput("ABRIR")) {
    const first = count > 0 ? `ARG1` : "ARGS"
    if (block.getInput(first)) block.moveInputBefore("ABRIR", first)
  }
  paintCount(block, "ARGS", "CERRAR", count, COUNT_MIN, COUNT_MAX, "Agregar argumento", "Quitar argumento", (delta) => {
    const next = clampCount(count + delta, COUNT_MIN, COUNT_MAX)
    if (next === count) return
    argCounts.set(block, next)
    reshapeArgs(block)
  })
}


function bindName(block: Blockly.Block, fieldName = "NOMBRE") {
  block.getField(fieldName)?.setValidator((value: string) => normalizeVariableName(String(value)))
}

function bindCharacter(block: Blockly.Block) {
  block.getField("VALOR")?.setValidator((value: string) => normalizeCharacter(String(value)))
}

function bindVariableType(block: Blockly.Block) {
  const field = block.getField("TIPO")
  field?.setValidator((value: string) => {
    if (!isTrazaType(value)) return null
    block.setOutput(true, outputChecks(value))
    return value
  })
}

function writeBlock() {
  return {
  type: BLOCK.escribir,
  message0: say("Escribir %1 sin saltar %2", "Write %1 Without Newline %2"),
  args0: [
    { type: "input_value", name: "VALOR", check: CHECK.expresion },
    { type: "field_checkbox", name: "SIN_SALTAR", checked: false },
  ],
  inputsInline: true,
  previousStatement: null,
  nextStatement: null,
  colour: IO,
  tooltip: "Muestra uno o más valores. Con sin saltar no baja de línea.",
  mutator: "traza_escribir_estado",
  }
}

function screenBlocks() {
  return [
  {
    type: BLOCK.borrarPantalla,
    message0: say("Borrar pantalla", "Clear Screen"),
    previousStatement: null,
    nextStatement: null,
    colour: IO,
    tooltip: "Limpia la salida.",
  },
  {
    type: BLOCK.esperar,
    message0: say("Esperar %1 segundos", "Wait %1 Seconds"),
    args0: [{ type: "input_value", name: "SEGUNDOS", check: CHECK.numero }],
    inputsInline: true,
    previousStatement: null,
    nextStatement: null,
    colour: IO,
    tooltip: "Detiene el algoritmo esa cantidad de segundos.",
  },
  ]
}

let writeBlockReady = false
let screenBlockReady = false

function installWriteBlock() {
  if (writeBlockReady) return
  if (!Blockly.Extensions.isRegistered("traza_escribir_estado")) {
    Blockly.Extensions.registerMutator(
      "traza_escribir_estado",
      {
        saveExtraState(this: Blockly.Block) {
          return { valores: writeCounts.get(this) ?? WRITE_MIN }
        },
        loadExtraState(this: Blockly.Block, state: { valores?: unknown }) {
          const raw = typeof state?.valores === "number" ? state.valores : WRITE_MIN
          writeCounts.set(this, clampCount(raw, WRITE_MIN, WRITE_MAX))
          reshapeWrites(this)
        },
      },
      function (this: Blockly.Block) {
        writeCounts.set(this, WRITE_MIN)
        reshapeWrites(this)
      },
    )
  }
  Blockly.common.defineBlocksWithJsonArray([writeBlock()])
  writeBlockReady = true
}

function installScreenBlocks() {
  if (screenBlockReady) return
  Blockly.common.defineBlocksWithJsonArray(screenBlocks())
  screenBlockReady = true
}

export function defineTrazaBlocks(locale: Dialect = "es"): void {
  wordsLocale = locale
  if (!extensionsReady) {
  Blockly.Extensions.register("traza_nombre", function (this: Blockly.Block) {
    bindName(this)
  })
  Blockly.Extensions.register("traza_caracter", function (this: Blockly.Block) {
    bindCharacter(this)
  })
  Blockly.Extensions.register("traza_tipo_variable", function (this: Blockly.Block) {
    bindVariableType(this)
  })
  Blockly.Extensions.registerMutator(
    "traza_segun_estado",
    {
      saveExtraState(this: Blockly.Block) {
        return { casos: segunCount(this) }
      },
      loadExtraState(this: Blockly.Block, state: { casos?: unknown }) {
        const raw = typeof state?.casos === "number" ? state.casos : SEGUN_DEFAULT
        segunCases.set(this, clampSegun(raw))
        reshapeSegun(this)
      },
    },
    function (this: Blockly.Block) {
      segunCases.set(this, SEGUN_DEFAULT)
      reshapeSegun(this)
    },
  )
  Blockly.Extensions.registerMutator(
    "traza_dimension_estado",
    {
      saveExtraState(this: Blockly.Block) {
        return { dimensiones: dimCounts.get(this) ?? DIM_MIN }
      },
      loadExtraState(this: Blockly.Block, state: { dimensiones?: unknown }) {
        const raw = typeof state?.dimensiones === "number" ? state.dimensiones : DIM_MIN
        dimCounts.set(this, clampCount(raw, DIM_MIN, DIM_MAX))
        reshapeSizes(this)
      },
    },
    function (this: Blockly.Block) {
      dimCounts.set(this, DIM_MIN)
      reshapeSizes(this)
    },
  )
  Blockly.Extensions.registerMutator(
    "traza_indice_estado",
    {
      saveExtraState(this: Blockly.Block) {
        return { dimensiones: indexCounts.get(this) ?? DIM_MIN }
      },
      loadExtraState(this: Blockly.Block, state: { dimensiones?: unknown }) {
        const raw = typeof state?.dimensiones === "number" ? state.dimensiones : DIM_MIN
        indexCounts.set(this, clampCount(raw, DIM_MIN, DIM_MAX))
        reshapeIndexes(this)
      },
    },
    function (this: Blockly.Block) {
      indexCounts.set(this, DIM_MIN)
      reshapeIndexes(this)
    },
  )
  Blockly.Extensions.registerMutator(
    "traza_rutina_estado",
    {
      saveExtraState(this: Blockly.Block) {
        return { parametros: paramCounts.get(this) ?? 1 }
      },
      loadExtraState(this: Blockly.Block, state: { parametros?: unknown }) {
        const raw = typeof state?.parametros === "number" ? state.parametros : 1
        paramCounts.set(this, clampCount(raw, COUNT_MIN, COUNT_MAX))
        reshapeRoutine(this)
      },
    },
    function (this: Blockly.Block) {
      paramCounts.set(this, 1)
      reshapeRoutine(this)
    },
  )
  Blockly.Extensions.registerMutator(
    "traza_argumentos_estado",
    {
      saveExtraState(this: Blockly.Block) {
        return { argumentos: argCounts.get(this) ?? 1 }
      },
      loadExtraState(this: Blockly.Block, state: { argumentos?: unknown }) {
        const raw = typeof state?.argumentos === "number" ? state.argumentos : 1
        argCounts.set(this, clampCount(raw, COUNT_MIN, COUNT_MAX))
        reshapeArgs(this)
      },
    },
    function (this: Blockly.Block) {
      argCounts.set(this, 1)
      reshapeArgs(this)
    },
  )
  Blockly.Extensions.register("traza_funcion_nombres", function (this: Blockly.Block) {
    bindName(this, "RESULTADO")
    bindName(this, "NOMBRE")
  })
  extensionsReady = true
  }
  if (builtLocale === locale && Blockly.Blocks[BLOCK.definir]) return
  for (const type of Object.values(BLOCK)) delete Blockly.Blocks[type]
  writeBlockReady = false
  screenBlockReady = false
  builtLocale = locale
  installWriteBlock()
  installScreenBlocks()

  Blockly.common.defineBlocksWithJsonArray([
    {
      type: BLOCK.definir,
      message0: say("Definir %1 Como %2", "Declare %1 As %2"),
      args0: [
        { type: "field_input", name: "NOMBRE", text: "x" },
        { type: "field_dropdown", name: "TIPO", options: typeOptions() },
      ],
      previousStatement: null,
      nextStatement: null,
      colour: VARIABLE,
      tooltip: "Declara una variable y su tipo.",
      extensions: ["traza_nombre"],
    },
    {
      type: BLOCK.asignar,
      message0: "%1 <- %2",
      args0: [
        { type: "field_input", name: "NOMBRE", text: "x" },
        { type: "input_value", name: "VALOR", check: CHECK.expresion },
      ],
      inputsInline: true,
      previousStatement: null,
      nextStatement: null,
      colour: VARIABLE,
      tooltip: "Asigna una expresión a una variable.",
      extensions: ["traza_nombre"],
    },
    {
      type: BLOCK.variable,
      message0: say("%1 de tipo %2", "%1 of type %2"),
      args0: [
        { type: "field_input", name: "NOMBRE", text: "x" },
        { type: "field_dropdown", name: "TIPO", options: typeOptions() },
      ],
      inputsInline: true,
      output: outputChecks("entero"),
      colour: VARIABLE,
      tooltip: "Usa el valor de una variable. El tipo limita dónde puede entrar.",
      extensions: ["traza_nombre", "traza_tipo_variable"],
    },
    {
      type: BLOCK.leer,
      message0: say("Leer %1", "Read %1"),
      args0: [{ type: "field_input", name: "NOMBRE", text: "x" }],
      previousStatement: null,
      nextStatement: null,
      colour: IO,
      tooltip: "Lee un dato y lo guarda en la variable.",
      extensions: ["traza_nombre"],
    },
    {
      type: BLOCK.unir,
      message0: say("unir %1 con %2", "join %1 with %2"),
      args0: [
        { type: "input_value", name: "IZQUIERDA", check: CHECK.cadena },
        { type: "input_value", name: "DERECHA", check: CHECK.cadena },
      ],
      inputsInline: true,
      output: outputChecks("cadena"),
      colour: IO,
      tooltip: "Une dos textos.",
    },
    {
      type: BLOCK.entero,
      message0: "%1",
      args0: [{ type: "field_number", name: "VALOR", value: 0, precision: 1 }],
      output: outputChecks("entero"),
      colour: OPERATOR,
      tooltip: "Un número entero.",
    },
    {
      type: BLOCK.real,
      message0: "%1",
      args0: [{ type: "field_number", name: "VALOR", value: 0, precision: 0.01 }],
      output: outputChecks("real"),
      colour: OPERATOR,
      tooltip: "Un número real.",
    },
    {
      type: BLOCK.cadena,
      message0: "\" %1 \"",
      args0: [{ type: "field_input", name: "VALOR", text: "" }],
      output: outputChecks("cadena"),
      colour: OPERATOR,
      tooltip: "Un texto.",
    },
    {
      type: BLOCK.caracter,
      message0: "' %1 '",
      args0: [{ type: "field_input", name: "VALOR", text: "a" }],
      output: outputChecks("caracter"),
      colour: OPERATOR,
      tooltip: "Un carácter.",
      extensions: ["traza_caracter"],
    },
    {
      type: BLOCK.logico,
      message0: "%1",
      args0: [
        {
          type: "field_dropdown",
          name: "VALOR",
          options: [
            [say("Verdadero", "True"), "verdadero"],
            [say("Falso", "False"), "falso"],
          ],
        },
      ],
      output: outputChecks("logico"),
      colour: OPERATOR,
      tooltip: "Un valor lógico.",
    },
    {
      type: BLOCK.aritmetica,
      message0: "%1 %2 %3",
      args0: [
        { type: "input_value", name: "IZQUIERDA", check: CHECK.numero },
        {
          type: "field_dropdown",
          name: "OPERADOR",
          options: [
            ["+", "add"],
            ["-", "sub"],
            ["*", "mul"],
            ["/", "div"],
            [say("DIV", "Div"), "idiv"],
            [say("MOD", "Mod"), "mod"],
          ],
        },
        { type: "input_value", name: "DERECHA", check: CHECK.numero },
      ],
      inputsInline: true,
      output: [CHECK.expresion, CHECK.numero],
      colour: OPERATOR,
      tooltip: "Operación entre números.",
    },
    {
      type: BLOCK.relacional,
      message0: "%1 %2 %3",
      args0: [
        { type: "input_value", name: "IZQUIERDA", check: CHECK.expresion },
        {
          type: "field_dropdown",
          name: "OPERADOR",
          options: [
            ["=", "eq"],
            ["<>", "neq"],
            ["<", "lt"],
            ["<=", "lte"],
            [">", "gt"],
            [">=", "gte"],
          ],
        },
        { type: "input_value", name: "DERECHA", check: CHECK.expresion },
      ],
      inputsInline: true,
      output: outputChecks("logico"),
      colour: OPERATOR,
      tooltip: "Compara dos expresiones y da un lógico.",
    },
    {
      type: BLOCK.logica,
      message0: "%1 %2 %3",
      args0: [
        { type: "input_value", name: "IZQUIERDA", check: CHECK.logico },
        {
          type: "field_dropdown",
          name: "OPERADOR",
          options: [
            [say("Y", "And"), "and"],
            [say("O", "Or"), "or"],
          ],
        },
        { type: "input_value", name: "DERECHA", check: CHECK.logico },
      ],
      inputsInline: true,
      output: outputChecks("logico"),
      colour: OPERATOR,
      tooltip: "Combina dos condiciones.",
    },
    {
      type: BLOCK.no,
      message0: say("NO %1", "Not %1"),
      args0: [{ type: "input_value", name: "VALOR", check: CHECK.logico }],
      inputsInline: true,
      output: outputChecks("logico"),
      colour: OPERATOR,
      tooltip: "Niega una condición.",
    },
    {
      type: BLOCK.si,
      message0: say("Si %1 Entonces", "If %1 Then"),
      args0: [{ type: "input_value", name: "CONDICION", check: CHECK.logico }],
      message1: "%1",
      args1: [{ type: "input_statement", name: "ENTONCES" }],
      message2: say("FinSi", "EndIf"),
      previousStatement: null,
      nextStatement: null,
      colour: CONTROL,
      tooltip: "Ejecuta las instrucciones solo si la condición se cumple.",
    },
    {
      type: BLOCK.siSino,
      message0: say("Si %1 Entonces", "If %1 Then"),
      args0: [{ type: "input_value", name: "CONDICION", check: CHECK.logico }],
      message1: "%1",
      args1: [{ type: "input_statement", name: "ENTONCES" }],
      message2: say("Sino", "Else"),
      message3: "%1",
      args3: [{ type: "input_statement", name: "SINO" }],
      message4: say("FinSi", "EndIf"),
      previousStatement: null,
      nextStatement: null,
      colour: CONTROL,
      tooltip: "Ejecuta una rama si la condición se cumple y otra si no.",
    },
    {
      type: BLOCK.mientras,
      message0: say("Mientras %1 Hacer", "While %1 Do"),
      args0: [{ type: "input_value", name: "CONDICION", check: CHECK.logico }],
      message1: "%1",
      args1: [{ type: "input_statement", name: "CUERPO" }],
      message2: say("FinMientras", "EndWhile"),
      previousStatement: null,
      nextStatement: null,
      colour: CONTROL,
      tooltip: "Repite las instrucciones mientras la condición se cumpla.",
    },
    {
      type: BLOCK.segun,
      message0: say("Segun %1 Hacer", "Switch %1 Do"),
      args0: [{ type: "input_value", name: "VALOR", check: CHECK.expresion }],
      previousStatement: null,
      nextStatement: null,
      colour: CONTROL,
      tooltip:
        "Ejecuta el caso cuyo literal coincide. El botón + agrega otro caso, hasta 12. Si ninguno coincide, usa De Otro Modo.",
      mutator: "traza_segun_estado",
    },
    {
      type: BLOCK.para,
      message0: say("Para %1 <- %2 Hasta %3 Con Paso %4 Hacer", "For %1 <- %2 Until %3 With Step %4 Do"),
      args0: [
        { type: "field_input", name: "NOMBRE", text: "i" },
        { type: "input_value", name: "DESDE", check: CHECK.numero },
        { type: "input_value", name: "HASTA", check: CHECK.numero },
        { type: "input_value", name: "PASO", check: CHECK.numero },
      ],
      message1: "%1",
      args1: [{ type: "input_statement", name: "CUERPO" }],
      message2: say("FinPara", "EndFor"),
      previousStatement: null,
      nextStatement: null,
      colour: CONTROL,
      tooltip: "Recorre un entero desde un inicio hasta un límite, sumando el paso.",
      extensions: ["traza_nombre"],
    },
    {
      type: BLOCK.repetir,
      message0: say("Repetir", "Repeat"),
      message1: "%1",
      args1: [{ type: "input_statement", name: "CUERPO" }],
      message2: say("Hasta Que %1", "Until That %1"),
      args2: [{ type: "input_value", name: "CONDICION", check: CHECK.logico }],
      previousStatement: null,
      nextStatement: null,
      colour: CONTROL,
      tooltip: "Ejecuta el cuerpo y después mira la condición. Corre al menos una vez.",
    },
    {
      type: BLOCK.dimension,
      message0: say("Dimension %1 Como %2", "Dimension %1 As %2"),
      args0: [
        { type: "field_input", name: "NOMBRE", text: "datos" },
        { type: "field_dropdown", name: "TIPO", options: typeOptions() },
      ],
      previousStatement: null,
      nextStatement: null,
      colour: ARRAY,
      tooltip: "Reserva las casillas de un arreglo. El botón + agrega otra dimensión, hasta 4.",
      extensions: ["traza_nombre"],
      mutator: "traza_dimension_estado",
    },
    {
      type: BLOCK.indice,
      message0: say("%1 de tipo %2", "%1 of type %2"),
      args0: [
        { type: "field_input", name: "NOMBRE", text: "datos" },
        { type: "field_dropdown", name: "TIPO", options: typeOptions() },
      ],
      output: outputChecks("entero"),
      colour: ARRAY,
      tooltip: "Lee una casilla. El índice empieza en 1.",
      extensions: ["traza_nombre", "traza_tipo_variable"],
      mutator: "traza_indice_estado",
    },
    {
      type: BLOCK.asignarIndice,
      message0: "%1",
      args0: [{ type: "field_input", name: "NOMBRE", text: "datos" }],
      previousStatement: null,
      nextStatement: null,
      colour: ARRAY,
      tooltip: "Guarda un valor en una casilla. El índice empieza en 1.",
      extensions: ["traza_nombre"],
      mutator: "traza_indice_estado",
    },
    {
      type: BLOCK.leerIndice,
      message0: say("Leer %1", "Read %1"),
      args0: [{ type: "field_input", name: "NOMBRE", text: "datos" }],
      previousStatement: null,
      nextStatement: null,
      colour: ARRAY,
      tooltip: "Lee un dato y lo guarda en una casilla.",
      extensions: ["traza_nombre"],
      mutator: "traza_indice_estado",
    },
    {
      type: BLOCK.funcion,
      message0: say("Funcion %1 <- %2", "Function %1 <- %2"),
      args0: [
        { type: "field_input", name: "RESULTADO", text: "resultado" },
        { type: "field_input", name: "NOMBRE", text: "Doblar" },
      ],
      colour: ROUTINE,
      hat: "cap",
      tooltip: "Define una función. El resultado se asigna dentro del cuerpo. Va suelta en el lienzo.",
      extensions: ["traza_funcion_nombres"],
      mutator: "traza_rutina_estado",
    },
    {
      type: BLOCK.procedimiento,
      message0: say("SubProceso %1", "SubProcedure %1"),
      args0: [{ type: "field_input", name: "NOMBRE", text: "Incrementar" }],
      colour: ROUTINE,
      hat: "cap",
      tooltip: "Define un procedimiento. Por referencia permite modificar la variable. Va suelto en el lienzo.",
      extensions: ["traza_nombre"],
      mutator: "traza_rutina_estado",
    },
    {
      type: BLOCK.llamada,
      message0: say("%1 como %2", "%1 As %2"),
      args0: [
        { type: "field_input", name: "NOMBRE", text: "Doblar" },
        { type: "field_dropdown", name: "TIPO", options: typeOptions() },
      ],
      output: outputChecks("entero"),
      colour: ROUTINE,
      tooltip: "Llama una función y usa el valor que devuelve.",
      extensions: ["traza_nombre", "traza_tipo_variable"],
      mutator: "traza_argumentos_estado",
    },
    {
      type: BLOCK.llamar,
      message0: "%1",
      args0: [{ type: "field_input", name: "NOMBRE", text: "Incrementar" }],
      previousStatement: null,
      nextStatement: null,
      colour: ROUTINE,
      tooltip: "Llama un procedimiento en su propia línea.",
      extensions: ["traza_nombre"],
      mutator: "traza_argumentos_estado",
    },
  ])
}
