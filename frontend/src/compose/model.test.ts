import { describe, expect, it } from "vitest"

import { layoutProgram } from "./layout"
import {
  addCase,
  addRoutine,
  createRoutine,
  createStep,
  emptyProgram,
  guessingGame,
  insertStep,
  moveStep,
  removeStep,
  toSource,
  updateStep,
} from "./model"

function overlaps(program = guessingGame()): string[] {
  const scene = layoutProgram(program)
  const boxes = [
    ...scene.nodes.map((node) => ({ id: node.id, x: node.x, y: node.y, width: node.width, height: node.height })),
    ...scene.slots.map((slot) => ({ id: slot.key, x: slot.x, y: slot.y, width: slot.width, height: slot.height })),
  ]
  const found: string[] = []
  for (let left = 0; left < boxes.length; left += 1) {
    for (let right = left + 1; right < boxes.length; right += 1) {
      const a = boxes[left]
      const b = boxes[right]
      const hit =
        a.x + 2 < b.x + b.width &&
        b.x + 2 < a.x + a.width &&
        a.y + 2 < b.y + b.height &&
        b.y + 2 < a.y + a.height
      if (hit) found.push(`${a.id} ~ ${b.id}`)
    }
  }
  return found
}

describe("pseudocódigo del diagrama", () => {
  it("empieza vacío entre Inicio y Fin", () => {
    expect(toSource(emptyProgram())).toBe("Algoritmo Diagrama\nFinAlgoritmo\n")
    const scene = layoutProgram(emptyProgram())
    expect(scene.slots).toHaveLength(1)
    const start = scene.nodes.find((node) => node.id === "start")
    const end = scene.nodes.find((node) => node.id === "end")
    expect(start && end && start.y < end.y).toBe(true)
  })

  it("escribe el juego de adivinar con Si, Sino y Mientras", () => {
    expect(toSource(guessingGame())).toBe(`Algoritmo Adivina_Numero
    Definir intentos, num_secreto, num_ingresado Como Entero;
    intentos <- 10;
    num_secreto <- Trunc(Aleatorio(0, 100));
    Escribir "Adivine el numero (de 1 a 100):";
    Leer num_ingresado;
    Mientras num_secreto <> num_ingresado Y intentos > 1 Hacer
        Si num_secreto > num_ingresado Entonces
            Escribir "Muy bajo";
        Sino
            Escribir "Muy alto";
        FinSi
        intentos <- intentos - 1;
        Escribir "Le quedan ", intentos, " intentos.";
        Leer num_ingresado;
    FinMientras
    Si num_secreto == num_ingresado Entonces
        Escribir "Exacto! Usted adivino en ", 11 - intentos, " intentos.";
    Sino
        Escribir "El numero era ", num_secreto;
    FinSi
FinAlgoritmo
`)
  })

  it("arma Para, Repetir y Según", () => {
    const para = createStep("para")
    const repetir = createStep("repetir")
    const segun = createStep("segun")
    if (para.kind !== "para" || repetir.kind !== "repetir" || segun.kind !== "segun") return
    para.body = [createStep("escribir")]
    repetir.body = [createStep("leer")]
    segun.other = [createStep("escribir")]
    let program = emptyProgram()
    program = insertStep(program, { scope: "root", index: 0 }, para)
    program = insertStep(program, { scope: "root", index: 1 }, repetir)
    program = insertStep(program, { scope: "root", index: 2 }, segun)
    const source = toSource(program)
    expect(source).toContain("Para i <- 1 Hasta 10 Hacer")
    expect(source).toContain("FinPara")
    expect(source).toContain("Repetir")
    expect(source).toContain("Hasta Que condicion")
    expect(source).toContain("Segun opcion Hacer")
    expect(source).toContain("De Otro Modo:")
    expect(source).toContain("FinSegun")
  })

  it("mueve una figura y no la mete dentro de sí misma", () => {
    const si = createStep("si")
    const write = createStep("escribir")
    let program = insertStep(emptyProgram(), { scope: "root", index: 0 }, si)
    program = insertStep(program, { scope: "then", ownerId: si.id, index: 0 }, write)
    const stuck = moveStep(program, si.id, { scope: "then", ownerId: si.id, index: 0 })
    expect(stuck.body.map((step) => step.id)).toEqual([si.id])
    const moved = moveStep(program, write.id, { scope: "else", ownerId: si.id, index: 0 })
    const host = moved.body[0]
    expect(host.kind === "si" && host.then).toEqual([])
    expect(host.kind === "si" && host.else.map((step) => step.id)).toEqual([write.id])
  })

  it("quita una figura y agrega un caso", () => {
    const segun = createStep("segun")
    let program = insertStep(emptyProgram(), { scope: "root", index: 0 }, segun)
    program = addCase(program, segun.id)
    const grown = program.body[0]
    expect(grown.kind === "segun" && grown.cases).toHaveLength(3)
    program = removeStep(program, segun.id)
    expect(program.body).toEqual([])
  })

  it("junta las figuras y las separa solo al insertar", () => {
    const program = insertStep(emptyProgram(), { scope: "root", index: 0 }, createStep("leer"))
    const closed = layoutProgram(program)
    const open = layoutProgram(program, "es", true)
    expect(open.height).toBeGreaterThan(closed.height)
    const read = closed.nodes.find((node) => node.figure === "input")
    const end = closed.nodes.find((node) => node.id === "end")
    expect(read && end && end.y - (read.y + read.height) < 40).toBe(true)
  })

  it("acomoda el ejemplo sin encimar figuras ni huecos", () => {
    expect(overlaps()).toEqual([])
    const scene = layoutProgram(guessingGame())
    const labels = scene.wires.map((wire) => wire.label).filter((label) => label)
    expect(labels).toContain("V")
    expect(labels).toContain("F")
    const start = scene.nodes.find((node) => node.label === "Inicio")
    const end = scene.nodes.find((node) => node.label === "Fin")
    const read = scene.nodes.find((node) => node.id === "rd1")
    expect(start && read && end && start.y < read.y && read.y < end.y).toBe(true)
  })

  it("omite el punto y coma cuando la configuración lo deja opcional", () => {
    const source = toSource(guessingGame(), false)
    expect(source).not.toContain(";")
    expect(source).toContain('Escribir "Adivine el numero (de 1 a 100):"')
    expect(source).toContain("Leer num_ingresado")
    expect(source).toContain("intentos <- 10")
    expect(source).toContain("FinMientras")
  })

  it("actualiza el texto de una figura en el fuente", () => {
    const write = createStep("escribir")
    let program = insertStep(emptyProgram(), { scope: "root", index: 0 }, write)
    program = updateStep(program, write.id, (step) => (step.kind === "escribir" ? { ...step, text: '"Hola"' } : step))
    expect(toSource(program)).toContain('Escribir "Hola";')
  })

  it("escribe la función y el procedimiento antes del algoritmo", () => {
    const fn = createRoutine("funcion")
    const proc = createRoutine("procedimiento")
    let program = addRoutine(addRoutine(emptyProgram(), fn), proc)
    program = insertStep(program, { scope: "routine", ownerId: fn.id, index: 0 }, createStep("asignar"))
    const source = toSource(program)
    expect(source.startsWith("Funcion resultado <- Doblar(n)\n")).toBe(true)
    expect(source).toContain("    dato <- 0;\nFinFuncion\nSubProceso Incrementar(n Por Referencia)\nFinSubProceso\nAlgoritmo Diagrama\n")
    expect(toSource(program, false)).toContain("    dato <- 0\nFinFuncion")
    expect(toSource(program, false)).not.toContain(";")
    const scene = layoutProgram(program)
    expect(scene.nodes.some((node) => node.label.includes("Doblar"))).toBe(true)
    expect(scene.nodes.some((node) => node.label === "FinFuncion")).toBe(true)
    expect(scene.slots.some((slot) => slot.path.scope === "routine" && slot.path.ownerId === fn.id)).toBe(true)
    expect(overlaps(program)).toEqual([])
  })
})
