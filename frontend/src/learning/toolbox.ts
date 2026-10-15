import * as Blockly from "blockly/core"

import { type MessageKey } from "../i18n"
import { BLOCK } from "./blocks"

export const TOOL_GROUPS: {
  name: string
  nameKey: MessageKey
  colour: string
  blocks: { id: string; label: string; labelKey: MessageKey }[]
}[] = [
  {
    name: "Variables",
    nameKey: "variables",
    colour: "230",
    blocks: [
      { id: BLOCK.definir, label: "Definir", labelKey: "figDefine" },
      { id: BLOCK.asignar, label: "Asignar", labelKey: "figAssign" },
      { id: BLOCK.variable, label: "Variable", labelKey: "figVariable" },
    ],
  },
  {
    name: "Entrada y salida",
    nameKey: "inputOutput",
    colour: "160",
    blocks: [
      { id: BLOCK.leer, label: "Leer", labelKey: "figRead" },
      { id: BLOCK.escribir, label: "Escribir", labelKey: "figWrite" },
      { id: BLOCK.borrarPantalla, label: "Borrar pantalla", labelKey: "figClear" },
      { id: BLOCK.esperar, label: "Esperar", labelKey: "figWait" },
      { id: BLOCK.unir, label: "Unir texto", labelKey: "figJoin" },
    ],
  },
  {
    name: "Operadores",
    nameKey: "operators",
    colour: "20",
    blocks: [
      { id: BLOCK.entero, label: "Número entero", labelKey: "figInteger" },
      { id: BLOCK.real, label: "Número real", labelKey: "figReal" },
      { id: BLOCK.cadena, label: "Texto", labelKey: "figText" },
      { id: BLOCK.caracter, label: "Caracter", labelKey: "figChar" },
      { id: BLOCK.logico, label: "Verdadero o falso", labelKey: "figBool" },
      { id: BLOCK.aritmetica, label: "Operación", labelKey: "figOp" },
      { id: BLOCK.relacional, label: "Comparación", labelKey: "figCompare" },
      { id: BLOCK.logica, label: "Y / O", labelKey: "figAndOr" },
      { id: BLOCK.no, label: "NO", labelKey: "figNot" },
    ],
  },
  {
    name: "Decisiones",
    nameKey: "decisions",
    colour: "290",
    blocks: [
      { id: BLOCK.si, label: "Si", labelKey: "figIf" },
      { id: BLOCK.siSino, label: "Si / Sino", labelKey: "figIfElse" },
      { id: BLOCK.segun, label: "Segun", labelKey: "figSwitchPlain" },
    ],
  },
  {
    name: "Ciclos",
    nameKey: "loops",
    colour: "290",
    blocks: [
      { id: BLOCK.mientras, label: "Mientras", labelKey: "figWhile" },
      { id: BLOCK.para, label: "Para", labelKey: "figFor" },
      { id: BLOCK.repetir, label: "Repetir", labelKey: "figRepeat" },
    ],
  },
  {
    name: "Arreglos",
    nameKey: "arrays",
    colour: "65",
    blocks: [
      { id: BLOCK.dimension, label: "Dimension", labelKey: "figDimension" },
      { id: BLOCK.indice, label: "Casilla", labelKey: "figCell" },
      { id: BLOCK.asignarIndice, label: "Asignar casilla", labelKey: "figAssignCell" },
      { id: BLOCK.leerIndice, label: "Leer casilla", labelKey: "figReadCell" },
    ],
  },
  {
    name: "Funciones",
    nameKey: "functions",
    colour: "120",
    blocks: [
      { id: BLOCK.funcion, label: "Funcion", labelKey: "figFunctionPlain" },
      { id: BLOCK.procedimiento, label: "SubProceso", labelKey: "figProcedurePlain" },
      { id: BLOCK.llamada, label: "Valor de función", labelKey: "figCallValue" },
      { id: BLOCK.llamar, label: "Llamar procedimiento", labelKey: "figCallProc" },
    ],
  },
]

export function labToolbox(
  allowed?: readonly string[] | null,
  names?: (key: MessageKey) => string,
): Blockly.utils.toolbox.ToolboxInfo {
  const permit = allowed ? new Set(allowed) : null
  return {
    kind: "categoryToolbox",
    contents: TOOL_GROUPS.map((group) => ({
      kind: "category" as const,
      name: names ? names(group.nameKey) : group.name,
      colour: group.colour,
      contents: group.blocks
        .filter((block) => (permit ? permit.has(block.id) : true))
        .map((block) => ({ kind: "block" as const, type: block.id })),
    })).filter((category) => category.contents.length > 0),
  }
}
