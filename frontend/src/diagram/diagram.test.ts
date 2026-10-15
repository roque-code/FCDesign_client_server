import { describe, expect, it } from "vitest"

import type { FlowGraph, FlowNode } from "../api"
import { focusNodeId } from "./focus"
import { layoutGraph } from "./layout"
import { pdfFromJpeg } from "./pdf"
import { buildSvg, type Drawing } from "./svg"

function node(partial: Partial<FlowNode> & Pick<FlowNode, "id" | "text">): FlowNode {
  return {
    kind: "process",
    line: 1,
    column: 1,
    end_line: 1,
    end_column: 8,
    ...partial,
  }
}

describe("diagrama", () => {
  it("la vertical del ciclo pasa por fuera de las figuras internas", async () => {
    const graph: FlowGraph = {
      entry: "inicio",
      nodes: [
        node({ id: "inicio", kind: "terminal", text: "Inicio" }),
        node({ id: "suma0", kind: "process", text: "suma <- 0" }),
        node({ id: "filaInit", kind: "process", text: "fila <- 1" }),
        node({ id: "fila", kind: "decision", figure: "loop", text: "fila hasta 2" }),
        node({ id: "colInit", kind: "process", text: "columna <- 1" }),
        node({ id: "col", kind: "decision", figure: "loop", text: "columna hasta 3" }),
        node({ id: "asig", kind: "process", text: "tabla[fila, columna] <- fila * 11 + columna" }),
        node({ id: "escribe", kind: "io", figure: "output", text: "Escribir tabla" }),
        node({ id: "suma", kind: "process", text: "suma <- suma + tabla" }),
        node({ id: "colPaso", kind: "process", text: "columna <- columna ± 1" }),
        node({ id: "filaPaso", kind: "process", text: "fila <- fila ± 1" }),
        node({ id: "total", kind: "io", figure: "output", text: "Escribir suma" }),
        node({ id: "fin", kind: "terminal", text: "Fin" }),
      ],
      edges: [
        { source: "inicio", target: "suma0", label: null },
        { source: "suma0", target: "filaInit", label: null },
        { source: "filaInit", target: "fila", label: null },
        { source: "fila", target: "colInit", label: "Sí" },
        { source: "colInit", target: "col", label: null },
        { source: "col", target: "asig", label: "Sí" },
        { source: "asig", target: "escribe", label: null },
        { source: "escribe", target: "suma", label: null },
        { source: "suma", target: "colPaso", label: null },
        { source: "colPaso", target: "col", label: null },
        { source: "col", target: "filaPaso", label: "No" },
        { source: "filaPaso", target: "fila", label: null },
        { source: "fila", target: "total", label: "No" },
        { source: "total", target: "fin", label: null },
      ],
    }
    const drawing = await layoutGraph(graph)
    const at = (id: string) => drawing.nodes.find((item) => item.id === id)
    const col = at("col")
    const asig = at("asig")
    const colPaso = at("colPaso")
    const fila = at("fila")
    const filaPaso = at("filaPaso")
    const total = at("total")
    expect(col && asig && colPaso && fila && filaPaso && total).toBeTruthy()
    if (!col || !asig || !colPaso || !fila || !filaPaso || !total) return
    const falsa = drawing.edges.find((edge) => edge.source === "col" && edge.target === "filaPaso")
    const regreso = drawing.edges.find((edge) => edge.source === "colPaso" && edge.target === "col")
    const regresoFila = drawing.edges.find((edge) => edge.source === "filaPaso" && edge.target === "fila")
    const salida = drawing.edges.find((edge) => edge.source === "fila" && edge.target === "total")
    expect(falsa && regreso && regresoFila && salida).toBeTruthy()
    if (!falsa || !regreso || !regresoFila || !salida) return
    expect(verticalPast(falsa.points, col.x, colPaso.y + colPaso.height)).toBe(true)
    expect(verticalPast(salida.points, fila.x, filaPaso.y + filaPaso.height)).toBe(true)
    expect(channelPast(regreso.points, asig.x + asig.width)).toBe(true)
    expect(channelPast(regresoFila.points, asig.x + asig.width)).toBe(true)
    expect(misses(drawing, "col", "filaPaso", ["asig", "escribe", "suma", "colPaso", "fila"])).toBe(true)
    expect(misses(drawing, "colPaso", "col", ["asig", "escribe", "suma", "filaPaso", "fila"])).toBe(true)
    expect(misses(drawing, "fila", "total", ["col", "asig", "escribe", "suma", "colPaso", "filaPaso", "colInit"])).toBe(true)
    expect(apart(regreso.points, regresoFila.points)).toBe(true)
    expect(apart(falsa.points, salida.points)).toBe(true)
    expect(leavesBottom(drawing, "colPaso", "col")).toBe(true)
    expect(leavesBottom(drawing, "filaPaso", "fila")).toBe(true)
    expect(leavesBottom(drawing, "asig", "escribe")).toBe(true)
    expect(arrivesAtTop(drawing, "colPaso", "col")).toBe(true)
    expect(arrivesAtTop(drawing, "filaPaso", "fila")).toBe(true)
    expect(arrivesAtTop(drawing, "fila", "colInit")).toBe(true)
    expect(arrivesAtTop(drawing, "col", "asig")).toBe(true)
    expect(separated(drawing.nodes)).toBe(true)
  })

  it("dibuja el segun como un triangulo con una casilla por caso", async () => {
    const graph: FlowGraph = {
      entry: "inicio",
      nodes: [
        node({ id: "inicio", kind: "terminal", text: "Inicio" }),
        node({ id: "dia", kind: "decision", figure: "switch", text: "dia" }),
        node({ id: "lunes", kind: "io", figure: "output", text: 'Escribir "Lunes"' }),
        node({ id: "martes", kind: "io", figure: "output", text: 'Escribir "Martes"' }),
        node({ id: "miercoles", kind: "io", figure: "output", text: 'Escribir "Miercoles"' }),
        node({ id: "fin", kind: "terminal", text: "Fin" }),
      ],
      edges: [
        { source: "inicio", target: "dia", label: null },
        { source: "dia", target: "lunes", label: "1" },
        { source: "dia", target: "martes", label: "2" },
        { source: "dia", target: "miercoles", label: "3" },
        { source: "dia", target: "fin", label: null },
        { source: "lunes", target: "fin", label: null },
        { source: "martes", target: "fin", label: null },
        { source: "miercoles", target: "fin", label: null },
      ],
    }
    const drawing = await layoutGraph(graph)
    const at = (id: string) => drawing.nodes.find((item) => item.id === id)
    const inicio = at("inicio")
    const dia = at("dia")
    const lunes = at("lunes")
    const martes = at("martes")
    const miercoles = at("miercoles")
    const fin = at("fin")
    expect(inicio && dia && lunes && martes && miercoles && fin).toBeTruthy()
    if (!inicio || !dia || !lunes || !martes || !miercoles || !fin || !dia.cases) return
    expect(dia.figure).toBe("switch")
    expect(dia.width).toBeGreaterThan(dia.height)
    expect(dia.cases.map((item) => item.label)).toEqual(["1", "2", "3", null])
    expect(Math.abs(inicio.x + inicio.width / 2 - (dia.x + dia.width / 2))).toBeLessThan(2)
    for (const body of [lunes, martes, miercoles]) {
      expect(body.y).toBeGreaterThanOrEqual(dia.y + dia.height)
    }
    expect(lunes.x).toBeLessThan(martes.x)
    expect(martes.x).toBeLessThan(miercoles.x)
    const slotCenter = (index: number) => dia.x + dia.cases![index].offset + dia.cases![index].width / 2
    expect(Math.abs(lunes.x + lunes.width / 2 - slotCenter(0))).toBeLessThan(2)
    expect(Math.abs(martes.x + martes.width / 2 - slotCenter(1))).toBeLessThan(2)
    expect(Math.abs(miercoles.x + miercoles.width / 2 - slotCenter(2))).toBeLessThan(2)
    for (const [target, index] of [["lunes", 0], ["martes", 1], ["miercoles", 2], ["fin", 3]] as const) {
      const edge = drawing.edges.find((item) => item.source === "dia" && item.target === target)
      expect(edge?.label).toBeNull()
      expect(edge && edge.points.length >= 2).toBeTruthy()
      if (!edge) continue
      const start = edge.points[0]
      const next = edge.points[1]
      expect(Math.abs(start.x - slotCenter(index))).toBeLessThan(2)
      expect(Math.abs(start.y - (dia.y + dia.height))).toBeLessThan(2)
      expect(Math.abs(next.x - start.x)).toBeLessThan(2)
      expect(next.y).toBeGreaterThan(start.y)
    }
    expect(misses(drawing, "dia", "fin", ["lunes", "martes", "miercoles"])).toBe(true)
    expect(fin.y).toBeGreaterThan(miercoles.y + miercoles.height)
    expect(separated(drawing.nodes)).toBe(true)
    const svg = buildSvg(drawing)
    expect(svg).toContain("switch")
    expect(svg).toContain("De Otro Modo")
    expect(svg).toContain(">1</text>")
  })

  it("elige el nodo más específico y prefiere el rombo en la línea del Si", () => {
    const nodes = [
      node({ id: "si", kind: "decision", text: "a = 1", line: 4, end_line: 8 }),
      node({ id: "join", kind: "join", text: "", line: 4, end_line: 8 }),
      node({ id: "write", kind: "io", text: "Escribir a", line: 5, end_line: 5 }),
    ]
    expect(focusNodeId(nodes, 4)).toBe("si")
    expect(focusNodeId(nodes, 5)).toBe("write")
    expect(focusNodeId(nodes, null)).toBeNull()
  })

  it("escapa el texto del svg y dibuja el rombo", () => {
    const drawing: Drawing = {
      width: 200,
      height: 120,
      nodes: [
        { id: "n1", kind: "decision", figure: "decision", text: "a < b", line: 2, x: 10, y: 10, width: 80, height: 60 },
      ],
      edges: [{ source: "n1", target: "n2", label: "Sí", points: [{ x: 50, y: 70 }, { x: 50, y: 100 }] }],
    }
    const svg = buildSvg(drawing)
    expect(svg).toContain("a &lt; b")
    expect(svg).toContain("decision")
    expect(svg).toContain("V")
    expect(svg).toContain("#c0392b")
  })

  it("arma un pdf con la imagen jpeg", () => {
    const jpeg = new Uint8Array([0xff, 0xd8, 0xff, 0xd9])
    const pdf = pdfFromJpeg(jpeg, 20, 10)
    expect(new TextDecoder().decode(pdf.slice(0, 8))).toBe("%PDF-1.4")
    expect(pdf.includes(0xd8)).toBe(true)
    expect(new TextDecoder().decode(pdf)).toContain("/DCTDecode")
  })

  it("acomoda un ciclo con coordenadas finitas", async () => {
    const graph: FlowGraph = {
      entry: "n1",
      nodes: [
        { id: "n1", kind: "terminal", text: "Inicio", line: 1, column: 1, end_line: 6, end_column: 1 },
        { id: "n2", kind: "decision", figure: "loop", text: "n < 3", line: 3, column: 1, end_line: 5, end_column: 1 },
        { id: "n3", kind: "process", text: "n <- n + 1", line: 4, column: 1, end_line: 4, end_column: 1 },
        { id: "n4", kind: "terminal", text: "Fin", line: 1, column: 1, end_line: 6, end_column: 1 },
      ],
      edges: [
        { source: "n1", target: "n2", label: null },
        { source: "n2", target: "n3", label: "Sí" },
        { source: "n3", target: "n2", label: null },
        { source: "n2", target: "n4", label: "No" },
      ],
    }
    const drawing = await layoutGraph(graph)
    expect(drawing.nodes).toHaveLength(4)
    expect(drawing.width).toBeGreaterThan(40)
    expect(drawing.nodes.find((item) => item.id === "n2")?.figure).toBe("loop")
    expect(drawing.edges.some((edge) => edge.label === "V")).toBe(true)
    expect(drawing.edges.some((edge) => edge.label === "F")).toBe(true)
    expect(drawing.edges[2].points.length).toBeGreaterThan(1)
    expect(Number.isFinite(drawing.nodes[1].x)).toBe(true)
    expect(separated(drawing.nodes)).toBe(true)
  })

  it("pone el sino a la izquierda y el ciclo a la derecha, sin solapar", async () => {
    const graph: FlowGraph = {
      entry: "inicio",
      nodes: [
        node({ id: "inicio", kind: "terminal", text: "Inicio" }),
        node({ id: "si", kind: "decision", figure: "decision", text: "cantidad > 0" }),
        node({ id: "sino", kind: "io", figure: "output", text: "Escribir sin notas" }),
        node({ id: "inicioPara", kind: "process", text: "i <- 1" }),
        node({ id: "ciclo", kind: "decision", figure: "loop", text: "i hasta cantidad" }),
        node({ id: "leer", kind: "io", figure: "input", text: "Leer nota" }),
        node({ id: "suma", kind: "process", text: "suma <- suma + nota" }),
        node({ id: "paso", kind: "process", text: "i <- i + 1" }),
        node({ id: "promedio", kind: "process", text: "promedio <- suma / cantidad" }),
        node({ id: "escribe", kind: "io", figure: "output", text: "Escribir promedio" }),
        node({ id: "fin", kind: "terminal", text: "Fin" }),
      ],
      edges: [
        { source: "inicio", target: "si", label: null },
        { source: "si", target: "inicioPara", label: "Sí" },
        { source: "si", target: "sino", label: "No" },
        { source: "inicioPara", target: "ciclo", label: null },
        { source: "ciclo", target: "leer", label: "Sí" },
        { source: "leer", target: "suma", label: null },
        { source: "suma", target: "paso", label: null },
        { source: "paso", target: "ciclo", label: null },
        { source: "ciclo", target: "promedio", label: "No" },
        { source: "promedio", target: "escribe", label: null },
        { source: "escribe", target: "fin", label: null },
        { source: "sino", target: "fin", label: null },
      ],
    }
    const drawing = await layoutGraph(graph)
    const at = (id: string) => drawing.nodes.find((item) => item.id === id)
    const si = at("si")
    const sino = at("sino")
    const inicioPara = at("inicioPara")
    const ciclo = at("ciclo")
    const leer = at("leer")
    const promedio = at("promedio")
    const fin = at("fin")
    expect(si && sino && inicioPara && ciclo && leer && promedio && fin).toBeTruthy()
    if (!si || !sino || !inicioPara || !ciclo || !leer || !promedio || !fin) return
    expect(sino.y).toBeGreaterThanOrEqual(si.y + si.height)
    expect(inicioPara.y).toBeGreaterThanOrEqual(si.y + si.height)
    expect(sino.x + sino.width).toBeLessThanOrEqual(inicioPara.x)
    expect(ciclo.y).toBeGreaterThan(inicioPara.y)
    expect(leer.x).toBeGreaterThan(ciclo.x + ciclo.width)
    expect(promedio.y).toBeGreaterThan(ciclo.y + ciclo.height)
    expect(fin.y).toBeGreaterThan(promedio.y)
    expect(fin.y).toBeGreaterThan(sino.y)
    expect(arrivesVertically(drawing, "si", "sino")).toBe(true)
    expect(arrivesVertically(drawing, "si", "inicioPara")).toBe(true)
    expect(leavesSide(drawing, "si", "sino", "left")).toBe(true)
    expect(leavesSide(drawing, "si", "inicioPara", "right")).toBe(true)
    expect(leavesSide(drawing, "ciclo", "leer", "right")).toBe(true)
    expect(arrivesAtTop(drawing, "ciclo", "leer")).toBe(true)
    expect(leer.y).toBeGreaterThanOrEqual(ciclo.y + ciclo.height)
    expect(leavesSide(drawing, "ciclo", "promedio", "left")).toBe(true)
    expect(separated(drawing.nodes)).toBe(true)
  })

  it("conserva la liga falsa cuando el si no tiene sino", async () => {
    const graph: FlowGraph = {
      entry: "inicio",
      nodes: [
        node({ id: "inicio", kind: "terminal", text: "Inicio" }),
        node({ id: "si", kind: "decision", figure: "decision", text: "n1 = n2" }),
        node({ id: "iguales", kind: "io", figure: "output", text: "Escribir iguales" }),
        node({ id: "fin", kind: "terminal", text: "Fin" }),
      ],
      edges: [
        { source: "inicio", target: "si", label: null },
        { source: "si", target: "iguales", label: "Sí" },
        { source: "iguales", target: "fin", label: null },
        { source: "si", target: "fin", label: "No" },
      ],
    }
    const drawing = await layoutGraph(graph)
    const si = drawing.nodes.find((item) => item.id === "si")
    const iguales = drawing.nodes.find((item) => item.id === "iguales")
    const falsa = drawing.edges.find((edge) => edge.source === "si" && edge.label === "F")
    expect(si && iguales && falsa && falsa.points.length).toBeTruthy()
    if (!si || !iguales || !falsa) return
    const laneX = falsa.points[1]?.x ?? si.x
    expect(laneX).toBeLessThan(iguales.x)
    expect(leavesSide(drawing, "si", "fin", "left")).toBe(true)
    expect(leavesSide(drawing, "si", "iguales", "right")).toBe(true)
    expect(iguales.y).toBeGreaterThanOrEqual(si.y + si.height)
    expect(falsa.points.at(-1)?.y).toBeGreaterThan(iguales.y)
    expect(separated(drawing.nodes)).toBe(true)
  })

  it("separa el para de las salidas del si", async () => {
    const graph: FlowGraph = {
      entry: "inicio",
      nodes: [
        node({ id: "inicio", kind: "terminal", text: "Inicio" }),
        node({ id: "leer", kind: "io", figure: "input", text: "Leer n" }),
        node({ id: "uno", kind: "process", text: "resultado <- 1" }),
        node({ id: "si", kind: "decision", figure: "decision", text: "n > 1" }),
        node({ id: "init", kind: "process", text: "i <- 2" }),
        node({ id: "ciclo", kind: "decision", figure: "loop", text: "i hasta n" }),
        node({ id: "cuerpo", kind: "process", text: "resultado <- resultado * i" }),
        node({ id: "paso", kind: "process", text: "i <- i + 1" }),
        node({ id: "escribe", kind: "io", figure: "output", text: "Escribir resultado" }),
        node({ id: "fin", kind: "terminal", text: "Fin" }),
      ],
      edges: [
        { source: "inicio", target: "leer", label: null },
        { source: "leer", target: "uno", label: null },
        { source: "uno", target: "si", label: null },
        { source: "si", target: "init", label: "Sí" },
        { source: "init", target: "ciclo", label: null },
        { source: "ciclo", target: "cuerpo", label: "Sí" },
        { source: "cuerpo", target: "paso", label: null },
        { source: "paso", target: "ciclo", label: null },
        { source: "ciclo", target: "escribe", label: "No" },
        { source: "si", target: "escribe", label: "No" },
        { source: "escribe", target: "fin", label: null },
      ],
    }
    const drawing = await layoutGraph(graph)
    const at = (id: string) => drawing.nodes.find((item) => item.id === id)
    const si = at("si")
    const init = at("init")
    const ciclo = at("ciclo")
    const cuerpo = at("cuerpo")
    const paso = at("paso")
    const escribe = at("escribe")
    expect(si && init && ciclo && cuerpo && paso && escribe).toBeTruthy()
    if (!si || !init || !ciclo || !cuerpo || !paso || !escribe) return
    expect(init.x).toBeGreaterThanOrEqual(si.x + si.width)
    expect(ciclo.x).toBeGreaterThanOrEqual(si.x + si.width)
    expect(cuerpo.x).toBeGreaterThanOrEqual(ciclo.x + ciclo.width)
    expect(init.y).toBeGreaterThanOrEqual(si.y + si.height)
    expect(ciclo.y).toBeGreaterThan(init.y)
    expect(escribe.y).toBeGreaterThan(ciclo.y + ciclo.height)
    expect(escribe.y).toBeGreaterThan(paso.y)
    expect(leavesSide(drawing, "si", "init", "right")).toBe(true)
    expect(leavesSide(drawing, "si", "escribe", "left")).toBe(true)
    expect(leavesSide(drawing, "ciclo", "cuerpo", "right")).toBe(true)
    expect(leavesSide(drawing, "ciclo", "escribe", "left")).toBe(true)
    expect(arrivesVertically(drawing, "si", "init")).toBe(true)
    expect(misses(drawing, "si", "escribe", ["init", "ciclo", "cuerpo", "paso"])).toBe(true)
    expect(misses(drawing, "si", "init", ["ciclo", "cuerpo", "paso"])).toBe(true)
    expect(misses(drawing, "ciclo", "escribe", ["si", "init", "cuerpo", "paso"])).toBe(true)
    expect(separated(drawing.nodes)).toBe(true)
  })

  it("la falsa del repetir sube por fuera de las figuras internas", async () => {
    const graph: FlowGraph = {
      entry: "inicio",
      nodes: [
        node({ id: "inicio", kind: "terminal", text: "Inicio" }),
        node({ id: "menu", kind: "io", figure: "output", text: 'Escribir "Menu"' }),
        node({ id: "opcion", kind: "decision", figure: "switch", text: "op" }),
        node({ id: "literatura", kind: "io", figure: "output", text: 'Escribir "Lecturas recomendables"' }),
        node({ id: "cine", kind: "io", figure: "output", text: 'Escribir "Peliculas recomendables"' }),
        node({ id: "musica", kind: "io", figure: "output", text: 'Escribir "Musica recomendable"' }),
        node({ id: "condicion", kind: "decision", figure: "loop", text: "op = 5" }),
        node({ id: "fin", kind: "terminal", text: "Fin" }),
      ],
      edges: [
        { source: "inicio", target: "menu", label: null },
        { source: "menu", target: "opcion", label: null },
        { source: "opcion", target: "literatura", label: "1" },
        { source: "opcion", target: "cine", label: "2" },
        { source: "opcion", target: "musica", label: "3" },
        { source: "literatura", target: "condicion", label: null },
        { source: "cine", target: "condicion", label: null },
        { source: "musica", target: "condicion", label: null },
        { source: "condicion", target: "menu", label: "No" },
        { source: "condicion", target: "fin", label: "Sí" },
      ],
    }
    const drawing = await layoutGraph(graph)
    const at = (id: string) => drawing.nodes.find((item) => item.id === id)
    const opcion = at("opcion")
    const literatura = at("literatura")
    const condicion = at("condicion")
    expect(opcion && literatura && condicion).toBeTruthy()
    if (!opcion || !literatura || !condicion) return
    const falsa = drawing.edges.find((edge) => edge.source === "condicion" && edge.target === "menu")
    expect(falsa).toBeTruthy()
    if (!falsa) return
    const rail = Math.min(...falsa.points.map((point) => point.x))
    const vertical = falsa.points.find((point, index) => {
      const next = falsa.points[index + 1]
      return next !== undefined && Math.abs(point.x - rail) < 1 && Math.abs(next.x - rail) < 1
    })
    const next = falsa.points[falsa.points.indexOf(vertical!) + 1]
    expect(rail).toBeLessThan(opcion.x)
    expect(rail).toBeLessThan(literatura.x)
    expect(Math.min(vertical!.y, next.y)).toBeLessThan(opcion.y)
    expect(Math.max(vertical!.y, next.y)).toBeGreaterThan(opcion.y + opcion.height)
    expect(leavesSide(drawing, "condicion", "menu", "left")).toBe(true)
    expect(leavesSide(drawing, "condicion", "fin", "right")).toBe(true)
    expect(arrivesAtTop(drawing, "condicion", "menu")).toBe(true)
    expect(misses(drawing, "condicion", "menu", ["opcion", "literatura", "cine", "musica"])).toBe(true)
    expect(separated(drawing.nodes)).toBe(true)
  })
})

function verticalPast(points: Array<{ x: number; y: number }>, limitX: number, pastY: number): boolean {
  for (let index = 0; index < points.length - 1; index += 1) {
    const from = points[index]
    const to = points[index + 1]
    if (Math.abs(from.x - to.x) > 1) continue
    if (from.x >= limitX) continue
    const low = Math.max(from.y, to.y)
    if (low >= pastY - 1) return true
  }
  return false
}

function apart(left: Array<{ x: number; y: number }>, right: Array<{ x: number; y: number }>): boolean {
  for (let i = 0; i < left.length - 1; i += 1) {
    for (let j = 0; j < right.length - 1; j += 1) {
      const a = left[i]
      const b = left[i + 1]
      const c = right[j]
      const d = right[j + 1]
      if (Math.hypot(b.x - a.x, b.y - a.y) < 24 || Math.hypot(d.x - c.x, d.y - c.y) < 24) continue
      const vertical = Math.abs(a.x - b.x) < 1 && Math.abs(c.x - d.x) < 1
      const horizontal = Math.abs(a.y - b.y) < 1 && Math.abs(c.y - d.y) < 1
      if (vertical && Math.abs(a.x - c.x) < 12 && overlap(a.y, b.y, c.y, d.y)) return false
      if (horizontal && Math.abs(a.y - c.y) < 12 && overlap(a.x, b.x, c.x, d.x)) return false
    }
  }
  return true
}

function overlap(a1: number, a2: number, b1: number, b2: number): boolean {
  return Math.min(Math.max(a1, a2), Math.max(b1, b2)) - Math.max(Math.min(a1, a2), Math.min(b1, b2)) > 10
}

function leavesBottom(
  drawing: { nodes: Array<{ id: string; x: number; y: number; width: number; height: number }>; edges: Array<{ source: string; target: string; points: Array<{ x: number; y: number }> }> },
  source: string,
  target: string,
): boolean {
  const node = drawing.nodes.find((item) => item.id === source)
  const edge = drawing.edges.find((item) => item.source === source && item.target === target)
  if (!node || !edge || edge.points.length < 2) return false
  const start = edge.points[0]
  const next = edge.points[1]
  return Math.abs(start.x - (node.x + node.width / 2)) < 2 && Math.abs(start.y - (node.y + node.height)) < 2 && Math.abs(next.x - start.x) < 2 && next.y > start.y
}

function channelPast(points: Array<{ x: number; y: number }>, limitX: number): boolean {
  return points.some((point, index) => {
    const next = points[index + 1]
    return next !== undefined && Math.abs(point.x - next.x) < 1 && point.x >= limitX - 1 && Math.abs(point.y - next.y) > 20
  })
}

function leavesSide(
  drawing: { nodes: Array<{ id: string; x: number; width: number }>; edges: Array<{ source: string; target: string; points: Array<{ x: number; y: number }> }> },
  source: string,
  target: string,
  side: "left" | "right",
): boolean {
  const node = drawing.nodes.find((item) => item.id === source)
  const edge = drawing.edges.find((item) => item.source === source && item.target === target)
  if (!node || !edge || edge.points.length < 2) return false
  const start = edge.points[0]
  const next = edge.points[1]
  const exitX = side === "left" ? node.x : node.x + node.width
  return Math.abs(start.x - exitX) < 1 && Math.abs(start.y - next.y) < 1 && (side === "left" ? next.x < start.x : next.x > start.x)
}

function misses(
  drawing: { nodes: Array<{ id: string; x: number; y: number; width: number; height: number }>; edges: Array<{ source: string; target: string; points: Array<{ x: number; y: number }> }> },
  source: string,
  target: string,
  blocked: string[],
): boolean {
  const edge = drawing.edges.find((item) => item.source === source && item.target === target)
  if (!edge) return false
  for (const id of blocked) {
    const node = drawing.nodes.find((item) => item.id === id)
    if (!node) return false
    for (let index = 0; index < edge.points.length - 1; index += 1) {
      if (hits(edge.points[index], edge.points[index + 1], node)) return false
    }
  }
  return true
}

function hits(from: { x: number; y: number }, to: { x: number; y: number }, node: { x: number; y: number; width: number; height: number }): boolean {
  const left = node.x + 4
  const right = node.x + node.width - 4
  const top = node.y + 4
  const bottom = node.y + node.height - 4
  if (Math.abs(from.y - to.y) < 1) {
    const minX = Math.min(from.x, to.x)
    const maxX = Math.max(from.x, to.x)
    return from.y > top && from.y < bottom && maxX > left && minX < right
  }
  if (Math.abs(from.x - to.x) < 1) {
    const minY = Math.min(from.y, to.y)
    const maxY = Math.max(from.y, to.y)
    return from.x > left && from.x < right && maxY > top && minY < bottom
  }
  return false
}

function arrivesAtTop(
  drawing: { nodes: Array<{ id: string; x: number; y: number; width: number }>; edges: Array<{ source: string; target: string; points: Array<{ x: number; y: number }> }> },
  source: string,
  target: string,
): boolean {
  const node = drawing.nodes.find((item) => item.id === target)
  const edge = drawing.edges.find((item) => item.source === source && item.target === target)
  if (!node || !edge || edge.points.length < 2) return false
  const last = edge.points[edge.points.length - 1]
  const previous = edge.points[edge.points.length - 2]
  return Math.abs(last.x - (node.x + node.width / 2)) < 2 && Math.abs(last.y - node.y) < 2 && Math.abs(last.x - previous.x) < 2 && last.y > previous.y
}

function arrivesVertically(drawing: { edges: Array<{ source: string; target: string; points: Array<{ x: number; y: number }> }> }, source: string, target: string): boolean {
  const edge = drawing.edges.find((item) => item.source === source && item.target === target)
  if (!edge || edge.points.length < 2) return false
  const last = edge.points[edge.points.length - 1]
  const previous = edge.points[edge.points.length - 2]
  return Math.abs(last.x - previous.x) < 2 && last.y > previous.y
}

function separated(nodes: Array<{ id: string; x: number; y: number; width: number; height: number }>): boolean {
  for (const left of nodes) {
    for (const right of nodes) {
      if (left.id >= right.id) continue
      const apart =
        left.x + left.width <= right.x + 0.5 ||
        right.x + right.width <= left.x + 0.5 ||
        left.y + left.height <= right.y + 0.5 ||
        right.y + right.height <= left.y + 0.5
      if (!apart) return false
    }
  }
  return true
}
