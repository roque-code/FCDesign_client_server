import type { FlowEdge, FlowNode } from "../api"
import type { Dialect } from "../dialect"
import { canonicalize } from "../words"

export function flowLabel(label: string | null, locale: Dialect = "es"): string | null {
  if (label === "Sí") return locale === "en" ? "T" : "V"
  if (label === "No") return "F"
  return label
}

export function labelAnchor(points: Array<{ x: number; y: number }>): { x: number; y: number } | null {
  if (points.length === 0) return null
  const start = points[0]
  const next = points[1] ?? start
  if (Math.abs(start.x - next.x) < 2) return { x: start.x + 12, y: start.y + 16 }
  const direction = next.x < start.x ? -1 : 1
  return { x: start.x + direction * 14, y: start.y - 8 }
}

export function collapseJoins(nodes: FlowNode[], edges: FlowEdge[]): { nodes: FlowNode[]; edges: FlowEdge[] } {
  const joins = new Set(nodes.filter((node) => node.kind === "join").map((node) => node.id))
  const outgoing = new Map<string, FlowEdge[]>()
  for (const edge of edges) {
    const list = outgoing.get(edge.source) ?? []
    list.push(edge)
    outgoing.set(edge.source, list)
  }
  const resolve = (id: string, label: string | null, seen: Set<string>): FlowEdge[] => {
    if (!joins.has(id)) return [{ source: "", target: id, label }]
    if (seen.has(id)) return []
    const nextSeen = new Set(seen)
    nextSeen.add(id)
    return (outgoing.get(id) ?? []).flatMap((edge) => resolve(edge.target, edge.label ?? label, nextSeen))
  }
  const linked: FlowEdge[] = []
  for (const edge of edges) {
    if (joins.has(edge.source)) continue
    for (const end of resolve(edge.target, edge.label, new Set())) {
      linked.push({ source: edge.source, target: end.target, label: end.label })
    }
  }
  return { nodes: nodes.filter((node) => node.kind !== "join"), edges: linked }
}

export function backEdgeIndexes(edges: FlowEdge[]): Set<number> {
  const outgoing = new Map<string, number[]>()
  edges.forEach((edge, index) => {
    const list = outgoing.get(edge.source) ?? []
    list.push(index)
    outgoing.set(edge.source, list)
  })
  const color = new Map<string, number>()
  const backs = new Set<number>()
  const visit = (id: string) => {
    color.set(id, 1)
    for (const index of outgoing.get(id) ?? []) {
      const target = edges[index].target
      const state = color.get(target) ?? 0
      if (state === 1) backs.add(index)
      else if (state === 0) visit(target)
    }
    color.set(id, 2)
  }
  const starts = new Set(edges.map((edge) => edge.source))
  for (const edge of edges) starts.delete(edge.target)
  const roots = starts.size > 0 ? [...starts] : edges.length > 0 ? [edges[0].source] : []
  for (const root of roots) {
    if ((color.get(root) ?? 0) === 0) visit(root)
  }
  for (const edge of edges) {
    if ((color.get(edge.source) ?? 0) === 0) visit(edge.source)
  }
  return backs
}

export function shownFigure(node: FlowNode): string {
  if (node.figure) return node.figure
  if (node.kind === "io") {
    const head = canonicalize(node.text.split(" ")[0] ?? "")
    return head === "leer" || head === "read" ? "input" : "output"
  }
  return node.kind
}
