import { newId, normalizeKey, type ErEdge, type ErNode, type NodeKind } from "./model"

const KEY = "traza.erd.projects.v1"
const KINDS = new Set<NodeKind>([
  "entity",
  "weak-entity",
  "relationship",
  "identifying",
  "attribute",
  "multivalued",
  "derived",
  "isa",
])

export type ErProject = {
  id: string
  name: string
  nodes: ErNode[]
  edges: ErEdge[]
}

export type ErStore = {
  activeId: string
  projects: ErProject[]
}

export function createEmpty(name: string): ErProject {
  return { id: newId(), name, nodes: [], edges: [] }
}

function text(value: unknown, max: number): string | null {
  if (typeof value !== "string") return null
  const trimmed = value.trim()
  if (!trimmed) return ""
  return trimmed.slice(0, max)
}

function finite(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null
}

function parseNode(value: unknown): ErNode | null {
  if (!value || typeof value !== "object") return null
  const record = value as Record<string, unknown>
  if (typeof record.id !== "string" || !KINDS.has(record.kind as NodeKind)) return null
  const x = finite(record.x)
  const y = finite(record.y)
  const label = text(record.label, 80)
  if (x == null || y == null || label == null) return null
  return {
    id: record.id,
    kind: record.kind as NodeKind,
    label,
    x,
    y,
    key: normalizeKey(record.key),
    disjoint: record.disjoint === true,
  }
}

function parseEdge(value: unknown, nodeIds: Set<string>): ErEdge | null {
  if (!value || typeof value !== "object") return null
  const record = value as Record<string, unknown>
  if (typeof record.id !== "string" || typeof record.source !== "string" || typeof record.target !== "string") return null
  if (!nodeIds.has(record.source) || !nodeIds.has(record.target) || record.source === record.target) return null
  const min = text(record.min, 4)
  const max = text(record.max, 4)
  const role = text(record.role, 40)
  if (min == null || max == null || role == null) return null
  return { id: record.id, source: record.source, target: record.target, min, max, one: record.one === true, role }
}

function parseProject(value: unknown): ErProject | null {
  if (!value || typeof value !== "object") return null
  const record = value as Record<string, unknown>
  if (typeof record.id !== "string" || !Array.isArray(record.nodes) || !Array.isArray(record.edges)) return null
  const name = text(record.name, 80)
  if (name == null) return null
  const nodes: ErNode[] = []
  const seen = new Set<string>()
  for (const item of record.nodes) {
    const node = parseNode(item)
    if (!node || seen.has(node.id)) continue
    seen.add(node.id)
    nodes.push(node)
    if (nodes.length >= 400) break
  }
  const edges: ErEdge[] = []
  const edgeIds = new Set<string>()
  for (const item of record.edges) {
    const edge = parseEdge(item, seen)
    if (!edge || edgeIds.has(edge.id)) continue
    edgeIds.add(edge.id)
    edges.push(edge)
    if (edges.length >= 800) break
  }
  return { id: record.id, name, nodes, edges }
}

export function parseStore(value: unknown): ErStore | null {
  if (!value || typeof value !== "object") return null
  const record = value as Record<string, unknown>
  if (!Array.isArray(record.projects)) return null
  const projects: ErProject[] = []
  const ids = new Set<string>()
  for (const item of record.projects) {
    const project = parseProject(item)
    if (!project || ids.has(project.id)) continue
    ids.add(project.id)
    projects.push(project)
  }
  if (projects.length === 0) return null
  const activeId = projects.some((project) => project.id === record.activeId) ? String(record.activeId) : projects[0].id
  return { activeId, projects }
}

export function readStore(): ErStore | null {
  try {
    if (typeof localStorage === "undefined") return null
    const raw = localStorage.getItem(KEY)
    if (!raw) return null
    return parseStore(JSON.parse(raw))
  } catch {
    return null
  }
}

export function writeStore(store: ErStore): void {
  try {
    if (typeof localStorage === "undefined") return
    localStorage.setItem(KEY, JSON.stringify({ version: 1, ...store }))
  } catch {
    /* El navegador puede rechazar el almacenamiento. El diagrama sigue en memoria. */
  }
}
