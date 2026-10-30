export type NodeKind =
  | "entity"
  | "weak-entity"
  | "relationship"
  | "identifying"
  | "attribute"
  | "multivalued"
  | "derived"
  | "isa"

export type Point = { x: number; y: number }
export type Box = { x: number; y: number; w: number; h: number }
export type View = { x: number; y: number; w: number; h: number }
export type Camera = { cx: number; cy: number; scale: number }
export type Placed = { kind: NodeKind; label: string; x: number; y: number }

const BASE: Record<NodeKind, { w: number; h: number }> = {
  entity: { w: 148, h: 48 },
  "weak-entity": { w: 156, h: 56 },
  relationship: { w: 124, h: 80 },
  identifying: { w: 132, h: 88 },
  attribute: { w: 112, h: 48 },
  multivalued: { w: 120, h: 56 },
  derived: { w: 112, h: 48 },
  isa: { w: 84, h: 68 },
}

export function baseSize(kind: NodeKind): { w: number; h: number } {
  return BASE[kind]
}

export function textWidth(text: string, size: number): number {
  let width = 0
  for (const char of text) {
    if (char === " ") width += size * 0.33
    else if ("ilIj".includes(char)) width += size * 0.28
    else if ("mwMW".includes(char)) width += size * 0.85
    else width += size * 0.62
  }
  return width
}

export function nodeBox(node: Placed): Box {
  const base = BASE[node.kind]
  const grow = node.kind === "isa" ? 0 : Math.max(0, textWidth(node.label, 13) + 28 - base.w)
  return { x: node.x, y: node.y, w: base.w + grow, h: base.h }
}

export function centerOf(node: Placed): Point {
  const box = nodeBox(node)
  return { x: box.x + box.w / 2, y: box.y + box.h / 2 }
}

export function snap(value: number, step = 8): number {
  return Math.round(value / step) * step
}

export function clampScale(scale: number): number {
  return Math.min(2.6, Math.max(0.3, scale))
}

export function viewFrom(camera: Camera, width: number, height: number): View {
  const w = width / camera.scale
  const h = height / camera.scale
  return { x: camera.cx - w / 2, y: camera.cy - h / 2, w, h }
}

export function clientToWorld(
  rect: { left: number; top: number; width: number; height: number },
  view: View,
  clientX: number,
  clientY: number,
): Point {
  return {
    x: view.x + ((clientX - rect.left) / rect.width) * view.w,
    y: view.y + ((clientY - rect.top) / rect.height) * view.h,
  }
}

export function zoomAt(
  camera: Camera,
  rect: { left: number; top: number; width: number; height: number },
  clientX: number,
  clientY: number,
  factor: number,
): Camera {
  const scale = clampScale(camera.scale * factor)
  const current = viewFrom(camera, rect.width, rect.height)
  const vx = (clientX - rect.left) / rect.width
  const vy = (clientY - rect.top) / rect.height
  const worldX = current.x + vx * current.w
  const worldY = current.y + vy * current.h
  const next = viewFrom({ cx: camera.cx, cy: camera.cy, scale }, rect.width, rect.height)
  return {
    scale,
    cx: worldX - (vx - 0.5) * next.w,
    cy: worldY - (vy - 0.5) * next.h,
  }
}

export function frameOf(nodes: Placed[]): View {
  if (nodes.length === 0) return { x: -80, y: -80, w: 1120, h: 760 }
  let minX = Infinity
  let minY = Infinity
  let maxX = -Infinity
  let maxY = -Infinity
  for (const node of nodes) {
    const box = nodeBox(node)
    minX = Math.min(minX, box.x)
    minY = Math.min(minY, box.y)
    maxX = Math.max(maxX, box.x + box.w)
    maxY = Math.max(maxY, box.y + box.h)
  }
  const pad = 72
  return { x: minX - pad, y: minY - pad, w: maxX - minX + pad * 2, h: maxY - minY + pad * 2 }
}

export function cameraToFit(nodes: Placed[], width: number, height: number): Camera {
  const frame = frameOf(nodes)
  return {
    cx: frame.x + frame.w / 2,
    cy: frame.y + frame.h / 2,
    scale: clampScale(Math.min(width / frame.w, height / frame.h)),
  }
}

export function labelNear(from: Point, to: Point, distance: number, side = 1): Point {
  const dx = to.x - from.x
  const dy = to.y - from.y
  const len = Math.hypot(dx, dy) || 1
  const travel = Math.min(distance, len * 0.42)
  return {
    x: from.x + (dx / len) * travel - (dy / len) * side * 16,
    y: from.y + (dy / len) * travel + (dx / len) * side * 16,
  }
}

export function distanceToSegment(point: Point, start: Point, end: Point): number {
  const dx = end.x - start.x
  const dy = end.y - start.y
  const len2 = dx * dx + dy * dy
  if (len2 === 0) return Math.hypot(point.x - start.x, point.y - start.y)
  const t = Math.max(0, Math.min(1, ((point.x - start.x) * dx + (point.y - start.y) * dy) / len2))
  return Math.hypot(point.x - (start.x + dx * t), point.y - (start.y + dy * t))
}

function isaVertices(box: Box): Point[] {
  return [
    { x: box.x + 8, y: box.y + 10 },
    { x: box.x + box.w - 8, y: box.y + 10 },
    { x: box.x + box.w / 2, y: box.y + box.h - 6 },
  ]
}

function centroid(points: Point[]): Point {
  const sum = points.reduce((acc, point) => ({ x: acc.x + point.x, y: acc.y + point.y }), { x: 0, y: 0 })
  return { x: sum.x / points.length, y: sum.y / points.length }
}

function rayHit(origin: Point, dir: Point, start: Point, end: Point): number | null {
  const vx = end.x - start.x
  const vy = end.y - start.y
  const det = dir.x * vy - dir.y * vx
  if (Math.abs(det) < 1e-8) return null
  const t = ((start.x - origin.x) * vy - (start.y - origin.y) * vx) / det
  const u = ((start.x - origin.x) * dir.y - (start.y - origin.y) * dir.x) / det
  if (t > 1e-4 && u >= -1e-4 && u <= 1 + 1e-4) return t
  return null
}

export function boundaryPoint(node: Placed, toward: Point): Point {
  const box = nodeBox(node)
  const cx = box.x + box.w / 2
  const cy = box.y + box.h / 2
  const dx = toward.x - cx
  const dy = toward.y - cy
  if (Math.hypot(dx, dy) < 1e-6) return { x: cx, y: cy }
  if (node.kind === "attribute" || node.kind === "multivalued" || node.kind === "derived") {
    const rx = box.w / 2 - 1
    const ry = box.h / 2 - 1
    const denom = Math.sqrt((dx * dx) / (rx * rx) + (dy * dy) / (ry * ry))
    return { x: cx + dx / denom, y: cy + dy / denom }
  }
  if (node.kind === "relationship" || node.kind === "identifying") {
    const rx = box.w / 2 - 1
    const ry = box.h / 2 - 1
    const t = 1 / (Math.abs(dx) / rx + Math.abs(dy) / ry)
    return { x: cx + dx * t, y: cy + dy * t }
  }
  if (node.kind === "isa") {
    const vertices = isaVertices(box)
    const origin = centroid(vertices)
    const dir = { x: toward.x - origin.x, y: toward.y - origin.y }
    if (Math.hypot(dir.x, dir.y) < 1e-6) return origin
    let best = Infinity
    let hit = origin
    for (let index = 0; index < vertices.length; index += 1) {
      const t = rayHit(origin, dir, vertices[index], vertices[(index + 1) % vertices.length])
      if (t != null && t < best) {
        best = t
        hit = { x: origin.x + dir.x * t, y: origin.y + dir.y * t }
      }
    }
    return hit
  }
  const hx = box.w / 2 - 1
  const hy = box.h / 2 - 1
  const sx = dx === 0 ? Infinity : hx / Math.abs(dx)
  const sy = dy === 0 ? Infinity : hy / Math.abs(dy)
  const t = Math.min(sx, sy)
  return { x: cx + dx * t, y: cy + dy * t }
}

export function edgeEnds(source: Placed, target: Placed): { a: Point; b: Point } {
  return {
    a: boundaryPoint(source, centerOf(target)),
    b: boundaryPoint(target, centerOf(source)),
  }
}

export function isaPolygon(w: number, h: number): string {
  return `${8},${10} ${w - 8},${10} ${w / 2},${h - 6}`
}
