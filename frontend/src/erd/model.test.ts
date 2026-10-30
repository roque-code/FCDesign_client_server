import { describe, expect, it } from "vitest"

import { accidentExample } from "./example"
import { boundaryPoint, distanceToSegment, nodeBox, zoomAt } from "./geometry"
import {
  applyCardinality,
  connectPair,
  isTotal,
  type ErNode,
  type LinkTool,
} from "./model"
import { parseStore } from "./store"

const labels = { relationship: "Relación", identifying: "Relación identificadora" }

function figure(id: string, kind: ErNode["kind"], x = 0, y = 0): ErNode {
  return { id, kind, label: id, x, y, key: "none", disjoint: false }
}

function join(first: ErNode, second: ErNode, tool: LinkTool) {
  return connectPair([first, second], [], first.id, second.id, tool, labels)
}

describe("notación de Chen", () => {
  it("une dos entidades con un rombo y cardinalidad mín..máx", () => {
    const persona = figure("persona", "entity", 0, 0)
    const vehiculo = figure("vehiculo", "entity", 240, 0)
    const many = join(persona, vehiculo, "many-many")
    expect(many.ok).toBe(true)
    if (!many.ok) return
    expect(many.nodes.map((node) => node.kind)).toContain("relationship")
    const sides = many.edges.map((edge) => `${edge.min}..${edge.max}:${edge.one}`)
    expect(sides).toEqual(["0..n:false", "0..n:false"])

    const directed = join(persona, vehiculo, "many-one")
    expect(directed.ok).toBe(true)
    if (!directed.ok) return
    const one = directed.edges.find((edge) => edge.target === "vehiculo")
    const manySide = directed.edges.find((edge) => edge.target === "persona")
    expect(one).toMatchObject({ min: "1", max: "1", one: true })
    expect(manySide).toMatchObject({ min: "0", max: "n", one: false })
    expect(isTotal(one!)).toBe(true)

    const pair = join(persona, vehiculo, "one-one")
    expect(pair.ok).toBe(true)
    if (!pair.ok) return
    expect(pair.edges.every((edge) => edge.min === "1" && edge.max === "1" && edge.one)).toBe(true)
  })

  it("exige un rombo para unir entidades y no duplica una línea", () => {
    const left = figure("a", "entity")
    const right = figure("b", "entity")
    expect(join(left, right, "partial")).toMatchObject({ ok: false, reason: "between-entities" })
    const linked = join(left, right, "many-many")
    expect(linked.ok).toBe(true)
    if (!linked.ok) return
    const again = connectPair(linked.nodes, linked.edges, linked.edges[0].source, linked.edges[0].target, "partial", labels)
    expect(again).toMatchObject({ ok: false, reason: "exists" })
  })

  it("marca participación total en la relación identificadora de la entidad débil", () => {
    const owner = figure("dueno", "entity", 0, 0)
    const weak = figure("dependiente", "weak-entity", 200, 0)
    const result = join(owner, weak, "many-many")
    expect(result.ok).toBe(true)
    if (!result.ok) return
    expect(result.nodes.some((node) => node.kind === "identifying")).toBe(true)
    expect(result.edges.find((edge) => edge.target === "dependiente")).toMatchObject({ min: "1", max: "n", one: false })
    expect(result.edges.find((edge) => edge.target === "dueno")).toMatchObject({ min: "0", max: "n", one: false })
  })

  it("une un atributo sin cardinalidad y una generalización total con línea doble", () => {
    const attribute = figure("dni", "attribute")
    const person = figure("persona", "entity")
    const attached = join(attribute, person, "many-one")
    expect(attached.ok).toBe(true)
    if (!attached.ok) return
    expect(attached.edges[0]).toMatchObject({ min: "", max: "", one: false })
    expect(attached.nodes).toHaveLength(2)

    const isa = figure("isa", "isa")
    const child = figure("hijo", "entity")
    const total = join(isa, child, "total")
    expect(total.ok).toBe(true)
    if (!total.ok) return
    expect(total.edges[0]).toMatchObject({ min: "1", max: "" })
    expect(isTotal(total.edges[0])).toBe(true)
    expect(join(isa, attribute, "partial")).toMatchObject({ ok: false, reason: "kind" })
    expect(join(person, person, "many-many")).toMatchObject({ ok: false, reason: "same" })
  })

  it("los atajos 0..1 y 1..1 encienden la flecha del lado uno", () => {
    const edge = { id: "e", source: "r", target: "a", min: "0", max: "n", one: false, role: "" }
    expect(applyCardinality(edge, "1", "1")).toMatchObject({ min: "1", max: "1", one: true })
    expect(applyCardinality(edge, "0", "1")).toMatchObject({ min: "0", max: "1", one: true })
    expect(applyCardinality(edge, "1", "n")).toMatchObject({ min: "1", max: "n", one: false })
    expect(applyCardinality(edge, "0", "n").one).toBe(false)
  })

  it("el ejemplo de accidentes usa mín..máx, línea doble y flecha, sin N:M", () => {
    const diagram = accidentExample()
    expect(diagram.nodes.filter((node) => node.key === "primary").map((node) => node.label).sort()).toEqual([
      "código",
      "código",
      "dni",
      "matrícula",
    ])
    expect(diagram.nodes.some((node) => node.label === "N:M" || node.label === "1:M")).toBe(false)
    expect(diagram.edges.every((edge) => edge.role === "")).toBe(true)
    const persona = diagram.edges.filter((edge) => edge.target === "persona" && edge.max !== "")
    expect(persona.map((edge) => `${edge.min}..${edge.max}:${edge.one}`).sort()).toEqual(["0..n:false", "1..n:false"])
    expect(diagram.edges.find((edge) => edge.target === "vehiculo" && edge.one)).toMatchObject({ min: "1", max: "1" })
    expect(diagram.edges.find((edge) => edge.target === "accidente" && edge.one)).toMatchObject({ min: "1", max: "1" })
    const fines = diagram.edges.filter((edge) => edge.target === "multa" && edge.max !== "")
    expect(fines).toHaveLength(2)
    expect(fines.every((edge) => edge.min === "0" && edge.max === "n" && !edge.one)).toBe(true)
  })
})

describe("geometría del lienzo", () => {
  it("sale por el borde del rectángulo y conserva el punto bajo el cursor al acercar", () => {
    const entity = figure("E", "entity")
    expect(nodeBox(entity)).toMatchObject({ w: 148, h: 48 })
    const point = boundaryPoint(entity, { x: 400, y: 24 })
    expect(point.x).toBeCloseTo(147, 0)
    expect(point.y).toBeCloseTo(24, 0)
    expect(distanceToSegment({ x: 10, y: 0 }, { x: 0, y: 0 }, { x: 20, y: 0 })).toBe(0)
    const camera = zoomAt({ cx: 100, cy: 50, scale: 1 }, { left: 0, top: 0, width: 200, height: 100 }, 100, 50, 2)
    expect(camera.cx).toBeCloseTo(100)
    expect(camera.cy).toBeCloseTo(50)
    expect(camera.scale).toBe(2)
  })
})

describe("proyectos del diagrama", () => {
  it("ignora un archivo dañado y conserva la clave primaria", () => {
    expect(parseStore(null)).toBeNull()
    expect(parseStore({ projects: [] })).toBeNull()
    const stored = parseStore({
      activeId: "p",
      projects: [
        {
          id: "p",
          name: "Clase",
          nodes: [
            { id: "e", kind: "entity", label: "PERSONA", x: 8, y: 16, key: "none", disjoint: false },
            { id: "mal", kind: "tabla", label: "no", x: 0, y: 0 },
          ],
          edges: [
            { id: "ok", source: "e", target: "ausente", min: "0", max: "n", one: false, role: "" },
          ],
        },
      ],
    })
    expect(stored?.projects[0].nodes).toHaveLength(1)
    expect(stored?.projects[0].edges).toHaveLength(0)
    const keyed = parseStore({
      activeId: "p",
      projects: [
        {
          id: "p",
          name: "Clase",
          nodes: [{ id: "dni", kind: "attribute", label: "dni", x: 0, y: 0, key: "primary", disjoint: false }],
          edges: [],
        },
      ],
    })
    expect(keyed?.projects[0].nodes[0].key).toBe("primary")
  })
})
