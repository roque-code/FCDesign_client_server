import { centerOf, nodeBox, snap, type NodeKind } from "./geometry"

export type { NodeKind }

export type AttributeKey = "none" | "primary" | "partial"

export type ErNode = {
  id: string
  kind: NodeKind
  label: string
  x: number
  y: number
  key: AttributeKey
  disjoint: boolean
}

/** `source` is the relationship and `target` is the entity when the edge carries cardinality. */
export type ErEdge = {
  id: string
  source: string
  target: string
  min: string
  max: string
  /** Arrowhead at `target`: that entity is the “one” side. */
  one: boolean
  role: string
}

export type LinkTool = "partial" | "total" | "many-many" | "many-one" | "one-one"

export type Selection = { type: "node" | "edge"; id: string }

export type ConnectReason = "same" | "exists" | "kind" | "between-entities"

export type ConnectResult =
  | { ok: true; nodes: ErNode[]; edges: ErEdge[]; select: Selection }
  | { ok: false; reason: ConnectReason }

const KEYS = new Set<AttributeKey>(["none", "primary", "partial"])

export function newId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") return crypto.randomUUID()
  return `erd-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
}

export function isEntity(kind: NodeKind): boolean {
  return kind === "entity" || kind === "weak-entity"
}

export function isRelationship(kind: NodeKind): boolean {
  return kind === "relationship" || kind === "identifying"
}

export function isAttribute(kind: NodeKind): boolean {
  return kind === "attribute" || kind === "multivalued" || kind === "derived"
}

export function isTotal(edge: { min: string }): boolean {
  return edge.min === "1"
}

export function showsCardinality(edge: { min: string; max: string }): boolean {
  return edge.min !== "" && edge.max !== ""
}

export function applyCardinality(edge: ErEdge, min: string, max: string): ErEdge {
  return { ...edge, min, max, one: max === "1" }
}

export type EdgeFamily = "attribute" | "isa" | "participation" | "other"

export function edgeFamily(edge: ErEdge, nodes: ErNode[]): EdgeFamily {
  const source = nodes.find((node) => node.id === edge.source)
  const target = nodes.find((node) => node.id === edge.target)
  if (!source || !target) return "other"
  if (isAttribute(source.kind) || isAttribute(target.kind)) return "attribute"
  if (source.kind === "isa" || target.kind === "isa") return "isa"
  if (
    (isEntity(source.kind) && isRelationship(target.kind)) ||
    (isRelationship(source.kind) && isEntity(target.kind))
  ) {
    return "participation"
  }
  return "other"
}

export function createNode(kind: NodeKind, x: number, y: number, label: string): ErNode {
  const draft: ErNode = { id: newId(), kind, label, x: 0, y: 0, key: "none", disjoint: false }
  const box = nodeBox(draft)
  return { ...draft, x: snap(x - box.w / 2), y: snap(y - box.h / 2) }
}

export function removeNode(nodes: ErNode[], edges: ErEdge[], id: string): { nodes: ErNode[]; edges: ErEdge[] } {
  return {
    nodes: nodes.filter((node) => node.id !== id),
    edges: edges.filter((edge) => edge.source !== id && edge.target !== id),
  }
}

export function normalizeKey(value: unknown): AttributeKey {
  return typeof value === "string" && KEYS.has(value as AttributeKey) ? (value as AttributeKey) : "none"
}

function plainEdge(source: string, target: string, min = "", max = ""): ErEdge {
  return { id: newId(), source, target, min, max, one: false, role: "" }
}

function linked(edges: ErEdge[], left: string, right: string): boolean {
  return edges.some(
    (edge) => (edge.source === left && edge.target === right) || (edge.source === right && edge.target === left),
  )
}

function canJoinAttribute(kind: NodeKind): boolean {
  return isAttribute(kind) || isEntity(kind) || isRelationship(kind)
}

function participation(
  role: "one" | "open" | "total",
  entity: ErNode,
  relationshipKind: NodeKind,
): { min: string; max: string; one: boolean } {
  const min = role === "one" || role === "total" ? "1" : "0"
  const max = role === "one" ? "1" : "n"
  const forced = entity.kind === "weak-entity" && relationshipKind === "identifying" && min === "0" ? "1" : min
  return { min: forced, max, one: role === "one" }
}

function entityEdge(relationship: ErNode, entity: ErNode, role: "one" | "open" | "total"): ErEdge {
  const card = participation(role, entity, relationship.kind)
  return {
    id: newId(),
    source: relationship.id,
    target: entity.id,
    min: card.min,
    max: card.max,
    one: card.one,
    role: "",
  }
}

export function connectPair(
  nodes: ErNode[],
  edges: ErEdge[],
  firstId: string,
  secondId: string,
  tool: LinkTool,
  labels: { relationship: string; identifying: string },
): ConnectResult {
  if (firstId === secondId) return { ok: false, reason: "same" }
  const first = nodes.find((node) => node.id === firstId)
  const second = nodes.find((node) => node.id === secondId)
  if (!first || !second) return { ok: false, reason: "kind" }
  if (linked(edges, firstId, secondId)) return { ok: false, reason: "exists" }

  if (isAttribute(first.kind) || isAttribute(second.kind)) {
    if (!canJoinAttribute(first.kind) || !canJoinAttribute(second.kind)) return { ok: false, reason: "kind" }
    const edge = plainEdge(first.id, second.id)
    return { ok: true, nodes, edges: [...edges, edge], select: { type: "edge", id: edge.id } }
  }

  if (first.kind === "isa" || second.kind === "isa") {
    const other = first.kind === "isa" ? second : first
    if (!isEntity(other.kind)) return { ok: false, reason: "kind" }
    const edge = plainEdge(first.id, second.id, tool === "total" ? "1" : "", "")
    return { ok: true, nodes, edges: [...edges, edge], select: { type: "edge", id: edge.id } }
  }

  if (isEntity(first.kind) && isEntity(second.kind)) {
    if (tool !== "many-many" && tool !== "many-one" && tool !== "one-one") {
      return { ok: false, reason: "between-entities" }
    }
    const weak = first.kind === "weak-entity" || second.kind === "weak-entity"
    const kind: NodeKind = weak ? "identifying" : "relationship"
    const left = centerOf(first)
    const right = centerOf(second)
    const created = createNode(kind, (left.x + right.x) / 2, (left.y + right.y) / 2, weak ? labels.identifying : labels.relationship)
    const firstRole = tool === "one-one" ? "one" : "open"
    const secondRole = tool === "many-many" ? "open" : "one"
    const nextEdges = [
      ...edges,
      entityEdge(created, first, firstRole),
      entityEdge(created, second, secondRole),
    ]
    return {
      ok: true,
      nodes: [...nodes, created],
      edges: nextEdges,
      select: { type: "node", id: created.id },
    }
  }

  const entity = isEntity(first.kind) ? first : isEntity(second.kind) ? second : null
  const relationship = isRelationship(first.kind) ? first : isRelationship(second.kind) ? second : null
  if (!entity || !relationship) return { ok: false, reason: "kind" }
  const role = tool === "many-one" || tool === "one-one" ? "one" : tool === "total" ? "total" : "open"
  const edge = entityEdge(relationship, entity, role)
  return { ok: true, nodes, edges: [...edges, edge], select: { type: "edge", id: edge.id } }
}
