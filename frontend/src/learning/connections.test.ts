import * as Blockly from "blockly/core"
import { describe, expect, it } from "vitest"

import { BLOCK, defineTrazaBlocks } from "./blocks"
import { labToolbox } from "./toolbox"
import { normalizeCharacter, normalizeVariableName } from "./names"
import { outputChecks } from "./types"

function workspace(): Blockly.Workspace {
  defineTrazaBlocks()
  return new Blockly.Workspace()
}

function reason(parent: Blockly.Block, inputName: string, child: Blockly.Block): number {
  return parent.workspace.connectionChecker.canConnectWithReason(
    parent.getInput(inputName)?.connection ?? null,
    child.outputConnection,
    false,
  )
}

describe("nombres", () => {
  it("acepta un identificador y rechaza una palabra del lenguaje", () => {
    expect(normalizeVariableName("año")).toBe("año")
    expect(normalizeVariableName(" total ")).toBe("total")
    expect(normalizeVariableName("Si")).toBeNull()
    expect(normalizeVariableName("Saltar")).toBeNull()
    expect(normalizeVariableName("Pantalla")).toBeNull()
    expect(normalizeVariableName("Segundos")).toBeNull()
    expect(normalizeVariableName("1a")).toBeNull()
    expect(normalizeCharacter("a")).toBe("a")
    expect(normalizeCharacter("ab")).toBeNull()
  })
})

describe("conexiones", () => {
  it("deja entrar un número a una cuenta y deja fuera a un lógico", () => {
    const ws = workspace()
    const math = ws.newBlock(BLOCK.aritmetica)
    const whole = ws.newBlock(BLOCK.entero)
    const flag = ws.newBlock(BLOCK.logico)
    const negation = ws.newBlock(BLOCK.no)
    expect(reason(math, "IZQUIERDA", whole)).toBe(Blockly.Connection.CAN_CONNECT)
    expect(reason(math, "IZQUIERDA", flag)).toBe(Blockly.Connection.REASON_CHECKS_FAILED)
    expect(reason(negation, "VALOR", flag)).toBe(Blockly.Connection.CAN_CONNECT)
    expect(reason(negation, "VALOR", whole)).toBe(Blockly.Connection.REASON_CHECKS_FAILED)
    expect(outputChecks("entero")).toContain("Numero")
    expect(outputChecks("logico")).not.toContain("Numero")
    ws.dispose()
  })

  it("solo une textos y deja escribir cualquier expresión", () => {
    const ws = workspace()
    const join = ws.newBlock(BLOCK.unir)
    const text = ws.newBlock(BLOCK.cadena)
    const whole = ws.newBlock(BLOCK.entero)
    const write = ws.newBlock(BLOCK.escribir)
    const read = ws.newBlock(BLOCK.leer)
    expect(reason(join, "IZQUIERDA", text)).toBe(Blockly.Connection.CAN_CONNECT)
    expect(reason(join, "IZQUIERDA", whole)).toBe(Blockly.Connection.REASON_CHECKS_FAILED)
    expect(reason(write, "VALOR", text)).toBe(Blockly.Connection.CAN_CONNECT)
    expect(reason(write, "VALOR", whole)).toBe(Blockly.Connection.CAN_CONNECT)
    expect(reason(write, "VALOR", read)).toBe(Blockly.Connection.REASON_TARGET_NULL)
    ws.dispose()
  })

  it("cambia el tipo de la variable y apila sentencias", () => {
    const ws = workspace()
    const math = ws.newBlock(BLOCK.aritmetica)
    const variable = ws.newBlock(BLOCK.variable)
    expect(reason(math, "DERECHA", variable)).toBe(Blockly.Connection.CAN_CONNECT)
    variable.setFieldValue("logico", "TIPO")
    expect(reason(math, "DERECHA", variable)).toBe(Blockly.Connection.REASON_CHECKS_FAILED)
    const logic = ws.newBlock(BLOCK.logica)
    expect(reason(logic, "IZQUIERDA", variable)).toBe(Blockly.Connection.CAN_CONNECT)

    const define = ws.newBlock(BLOCK.definir)
    const assign = ws.newBlock(BLOCK.asignar)
    expect(
      define.workspace.connectionChecker.canConnectWithReason(
        define.nextConnection,
        assign.previousConnection,
        false,
      ),
    ).toBe(Blockly.Connection.CAN_CONNECT)
    define.setFieldValue("Mientras", "NOMBRE")
    expect(define.getFieldValue("NOMBRE")).toBe("x")
    define.setFieldValue("total", "NOMBRE")
    expect(define.getFieldValue("NOMBRE")).toBe("total")
    ws.dispose()
  })

  it("acepta un lógico en Si y una sentencia dentro de Mientras", () => {
    const ws = workspace()
    const branch = ws.newBlock(BLOCK.si)
    const loop = ws.newBlock(BLOCK.mientras)
    const flag = ws.newBlock(BLOCK.logico)
    const whole = ws.newBlock(BLOCK.entero)
    const write = ws.newBlock(BLOCK.escribir)
    expect(reason(branch, "CONDICION", flag)).toBe(Blockly.Connection.CAN_CONNECT)
    expect(reason(branch, "CONDICION", whole)).toBe(Blockly.Connection.REASON_CHECKS_FAILED)
    expect(reason(loop, "CONDICION", flag)).toBe(Blockly.Connection.CAN_CONNECT)
    expect(
      loop.workspace.connectionChecker.canConnectWithReason(
        loop.getInput("CUERPO")?.connection ?? null,
        write.previousConnection,
        false,
      ),
    ).toBe(Blockly.Connection.CAN_CONNECT)
    expect(
      loop.workspace.connectionChecker.canConnectWithReason(
        loop.getInput("CUERPO")?.connection ?? null,
        whole.outputConnection,
        false,
      ),
    ).toBe(Blockly.Connection.REASON_WRONG_TYPE)
    const names = JSON.stringify(labToolbox())
    expect(names).toContain(BLOCK.si)
    expect(names).toContain(BLOCK.siSino)
    expect(names).toContain(BLOCK.mientras)
    expect(names).toContain(BLOCK.segun)
    expect(names).toContain(BLOCK.para)
    expect(names).toContain(BLOCK.repetir)
    expect(names).toContain(BLOCK.dimension)
    expect(names).toContain(BLOCK.funcion)
    expect(names).toContain(BLOCK.borrarPantalla)
    expect(names).toContain(BLOCK.esperar)
    const wait = ws.newBlock(BLOCK.esperar)
    expect(reason(wait, "SEGUNDOS", whole)).toBe(Blockly.Connection.CAN_CONNECT)
    expect(reason(wait, "SEGUNDOS", flag)).toBe(Blockly.Connection.REASON_CHECKS_FAILED)
    expect(ws.newBlock(BLOCK.borrarPantalla).previousConnection).toBeTruthy()
    const counted = ws.newBlock(BLOCK.para)
    const again = ws.newBlock(BLOCK.repetir)
    expect(reason(counted, "DESDE", whole)).toBe(Blockly.Connection.CAN_CONNECT)
    expect(reason(counted, "PASO", flag)).toBe(Blockly.Connection.REASON_CHECKS_FAILED)
    expect(reason(again, "CONDICION", flag)).toBe(Blockly.Connection.CAN_CONNECT)
    expect(reason(again, "CONDICION", whole)).toBe(Blockly.Connection.REASON_CHECKS_FAILED)
    const segun = ws.newBlock(BLOCK.segun)
    expect(segun.getInput("CASO2")).toBeTruthy()
    expect(segun.getInput("CASO3")).toBeNull()
    expect(reason(segun, "CASO1", whole)).toBe(Blockly.Connection.CAN_CONNECT)
    segun.loadExtraState?.({ casos: 3 })
    expect(segun.getInput("CASO3")).toBeTruthy()
    expect(segun.getInput("HACER3")).toBeTruthy()
    const plug = whole.outputConnection
    if (plug) segun.getInput("CASO1")?.connection?.connect(plug)
    const saved = Blockly.serialization.workspaces.save(ws)
    const restored = new Blockly.Workspace()
    Blockly.serialization.workspaces.load(saved, restored)
    const copy = restored.getBlocksByType(BLOCK.segun, false)[0]
    expect(copy?.getInput("CASO3")).toBeTruthy()
    expect(copy?.getInput("CASO1")?.connection?.targetBlock()?.type).toBe(BLOCK.entero)
    expect(copy?.saveExtraState?.()).toEqual({ casos: 3 })
    copy?.loadExtraState?.({ casos: 1 })
    expect(copy?.getInput("CASO2")).toBeNull()
    expect(copy?.getInput("OTRO")).toBeTruthy()
    restored.dispose()
    const several = ws.newBlock(BLOCK.escribir)
    expect(several.getFieldValue("SIN_SALTAR")).toBe("FALSE")
    expect(several.getInput("VALOR")).toBeTruthy()
    expect(several.getInput("VALOR2")).toBeNull()
    several.loadExtraState?.({ valores: 3 })
    expect(several.getInput("VALOR2")).toBeTruthy()
    expect(several.getInput("VALOR3")).toBeTruthy()
    defineTrazaBlocks()
    const loaded = new Blockly.Workspace()
    Blockly.serialization.workspaces.load(
      {
        blocks: {
          languageVersion: 0,
          blocks: [
            {
              type: BLOCK.escribir,
              id: "e",
              extraState: { valores: 3 },
              inputs: {
                VALOR: { block: { type: BLOCK.cadena, id: "c1", fields: { VALOR: "a" } } },
                VALOR2: { block: { type: BLOCK.entero, id: "n", fields: { VALOR: 1 } } },
                VALOR3: { block: { type: BLOCK.cadena, id: "c2", fields: { VALOR: "b" } } },
              },
            },
          ],
        },
      },
      loaded,
    )
    expect(loaded.getAllBlocks(false)).toHaveLength(4)
    loaded.dispose()
    const datos = ws.newBlock(BLOCK.dimension)
    expect(datos.getInput("TAMANO1")).toBeTruthy()
    expect(datos.getInput("TAMANO2")).toBeNull()
    datos.loadExtraState?.({ dimensiones: 2 })
    expect(datos.getInput("TAMANO2")).toBeTruthy()
    const doblar = ws.newBlock(BLOCK.funcion)
    expect(doblar.getInput("PARAM1")).toBeTruthy()
    expect(doblar.getInput("CUERPO")).toBeTruthy()
    doblar.loadExtraState?.({ parametros: 0 })
    expect(doblar.getInput("PARAM1")).toBeNull()
    expect(doblar.getInput("CUERPO")).toBeTruthy()
    const onlyWrite = labToolbox([BLOCK.escribir, BLOCK.si])
    const types = JSON.stringify(onlyWrite)
    expect(types).toContain(BLOCK.si)
    expect(types).not.toContain(BLOCK.mientras)
    ws.dispose()
  })

  it("guarda el JSON del workspace y lo vuelve a cargar", () => {
    const ws = workspace()
    const define = ws.newBlock(BLOCK.definir)
    const assign = ws.newBlock(BLOCK.asignar)
    const whole = ws.newBlock(BLOCK.entero)
    define.nextConnection!.connect(assign.previousConnection!)
    assign.getInput("VALOR")!.connection!.connect(whole.outputConnection!)
    define.setFieldValue("precio", "NOMBRE")
    const saved = Blockly.serialization.workspaces.save(ws)
    expect(JSON.stringify(saved)).not.toContain("javascript")
    const restored = new Blockly.Workspace()
    Blockly.serialization.workspaces.load(saved, restored)
    const names = restored.getAllBlocks(false).map((block) => block.type).sort()
    expect(names).toEqual([BLOCK.asignar, BLOCK.definir, BLOCK.entero].sort())
    const defined = restored.getBlocksByType(BLOCK.definir, false)[0]
    expect(defined?.getFieldValue("NOMBRE")).toBe("precio")
    expect(defined?.getNextBlock()?.type).toBe(BLOCK.asignar)
    ws.dispose()
    restored.dispose()
  })
})
