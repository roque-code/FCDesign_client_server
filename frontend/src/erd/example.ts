import type { ErEdge, ErNode } from "./model"

function node(
  id: string,
  kind: ErNode["kind"],
  label: string,
  x: number,
  y: number,
  key: ErNode["key"] = "none",
): ErNode {
  return { id, kind, label, x, y, key, disjoint: false }
}

function link(id: string, source: string, target: string, min: string, max: string, one = false): ErEdge {
  return { id, source, target, min, max, one, role: "" }
}

function attr(id: string, attribute: string, owner: string): ErEdge {
  return link(id, attribute, owner, "", "", false)
}

/**
 * The accidents diagram, drawn in Chen notation.
 * Cardinality is min..max. A minimum of 1 is a double line.
 * The arrow points at the one side. The N:M and 1:M tags are not drawn.
 */
export function accidentExample(): { nodes: ErNode[]; edges: ErEdge[] } {
  const nodes: ErNode[] = [
    node("persona", "entity", "PERSONA", 250, 90),
    node("vehiculo", "entity", "VEHICULO", 250, 450),
    node("accidente", "entity", "ACCIDENTE", 900, 90),
    node("multa", "entity", "MULTA", 900, 450),
    node("tiene", "relationship", "tiene", 262, 254),
    node("inv-pa", "relationship", "involucra", 587, 74),
    node("inv-va", "relationship", "involucra", 450, 156),
    node("apl-vm", "relationship", "aplicada", 587, 434),
    node("apl-am", "relationship", "aplicada", 912, 254),
    node("dni", "attribute", "dni", 40, 50, "primary"),
    node("nombre", "attribute", "nombre", 40, 160),
    node("matricula", "attribute", "matrícula", 30, 440, "primary"),
    node("marca", "attribute", "marca", 80, 580),
    node("modelo", "attribute", "modelo", 260, 580),
    node("hora-a", "attribute", "hora", 760, 0),
    node("cod-a", "attribute", "código", 1040, 0, "primary"),
    node("fecha-a", "attribute", "fecha", 1120, 80),
    node("lugar-a", "attribute", "lugar", 1120, 170),
    node("importe", "attribute", "importe", 1120, 390),
    node("lugar-m", "attribute", "lugar", 1120, 480),
    node("hora-m", "attribute", "hora", 1040, 580),
    node("fecha-m", "attribute", "fecha", 740, 580),
    node("cod-m", "attribute", "código", 600, 580, "primary"),
  ]
  const edges: ErEdge[] = [
    link("t-p", "tiene", "persona", "0", "n"),
    link("t-v", "tiene", "vehiculo", "0", "n"),
    link("i-p", "inv-pa", "persona", "1", "n"),
    link("i-a", "inv-pa", "accidente", "0", "n"),
    link("iv-v", "inv-va", "vehiculo", "1", "n"),
    link("iv-a", "inv-va", "accidente", "0", "n"),
    link("av-v", "apl-vm", "vehiculo", "1", "1", true),
    link("av-m", "apl-vm", "multa", "0", "n"),
    link("aa-a", "apl-am", "accidente", "1", "1", true),
    link("aa-m", "apl-am", "multa", "0", "n"),
    attr("ad", "dni", "persona"),
    attr("an", "nombre", "persona"),
    attr("am", "matricula", "vehiculo"),
    attr("ab", "marca", "vehiculo"),
    attr("ao", "modelo", "vehiculo"),
    attr("ah", "hora-a", "accidente"),
    attr("ac", "cod-a", "accidente"),
    attr("af", "fecha-a", "accidente"),
    attr("al", "lugar-a", "accidente"),
    attr("mi", "importe", "multa"),
    attr("ml", "lugar-m", "multa"),
    attr("mh", "hora-m", "multa"),
    attr("mf", "fecha-m", "multa"),
    attr("mc", "cod-m", "multa"),
  ]
  return { nodes, edges }
}
