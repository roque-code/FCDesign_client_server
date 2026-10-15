import { spellText, type Dialect } from "../dialect"
import { flowLabel, labelAnchor } from "./figures"

export type Point = { x: number; y: number }

export type DrawnNode = {
  id: string
  kind: string
  figure: string
  text: string
  line: number | null
  x: number
  y: number
  width: number
  height: number
  cases?: Array<{ label: string | null; offset: number; width: number }>
}

export type DrawnEdge = {
  source: string
  target: string
  label: string | null
  points: Point[]
}

export type Drawing = {
  nodes: DrawnNode[]
  edges: DrawnEdge[]
  width: number
  height: number
}

function escapeXml(text: string): string {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
}

function shape(node: DrawnNode): string {
  const { x, y, width, height, figure } = node
  const box = `class="${figure}"`
  if (figure === "join") return ""
  if (figure === "terminal") {
    return `<ellipse ${box} cx="${x + width / 2}" cy="${y + height / 2}" rx="${width / 2}" ry="${height / 2}"/>`
  }
  if (figure === "switch") return ""
  if (figure === "decision") {
    const points = [
      [x + width / 2, y + 1],
      [x + width - 1, y + height / 2],
      [x + width / 2, y + height - 1],
      [x + 1, y + height / 2],
    ]
    return `<polygon ${box} points="${points.map((pair) => pair.join(",")).join(" ")}"/>`
  }
  if (figure === "loop") {
    const inset = width * 0.18
    const points = [
      [x + inset, y + 1],
      [x + width - inset, y + 1],
      [x + width - 1, y + height / 2],
      [x + width - inset, y + height - 1],
      [x + inset, y + height - 1],
      [x + 1, y + height / 2],
    ]
    return `<polygon ${box} points="${points.map((pair) => pair.join(",")).join(" ")}"/>`
  }
  if (figure === "output" || figure === "input") {
    const skew = Math.min(16, width * 0.14)
    const points =
      figure === "output"
        ? [
            [x + skew, y],
            [x + width, y],
            [x + width - skew, y + height],
            [x, y + height],
          ]
        : [
            [x, y],
            [x + width - skew, y],
            [x + width, y + height],
            [x + skew, y + height],
          ]
    return `<polygon ${box} points="${points.map((pair) => pair.join(",")).join(" ")}"/>`
  }
  const rect = `<rect ${box} x="${x}" y="${y}" width="${width}" height="${height}"/>`
  if (figure !== "subprocess") return rect
  return `${rect}<rect class="subprocess" x="${x + 5}" y="${y + 5}" width="${width - 10}" height="${height - 10}" fill="none"/>`
}

function switchShape(node: DrawnNode, locale: Dialect): string {
  const { x, y, width, height } = node
  const bar = 30
  const tri = y + height - bar
  const body = [
    `M${x + width / 2},${y + 1}`,
    `L${x + width - 1},${tri}`,
    `L${x + width - 1},${y + height - 1}`,
    `L${x + 1},${y + height - 1}`,
    `L${x + 1},${tri} Z`,
    `M${x + 1},${tri} L${x + width - 1},${tri}`,
  ]
  const cases = node.cases ?? []
  cases.slice(0, -1).forEach((item) => {
    const at = x + item.offset + item.width
    body.push(`M${at},${tri} L${at},${y + height - 1}`)
  })
  const title = `<text x="${x + width / 2}" y="${y + (height - bar) * 0.62}" text-anchor="middle" dominant-baseline="middle">${escapeXml(node.text)}</text>`
  const labels = cases
    .map((item) => {
      const caption = spellText(locale, item.label ?? "De Otro Modo")
      return `<text class="switch-label" x="${x + item.offset + item.width / 2}" y="${tri + bar / 2 + 1}" text-anchor="middle" dominant-baseline="middle">${escapeXml(caption)}</text>`
    })
    .join("")
  return `<path class="switch" d="${body.join(" ")}"/>${title}${labels}`
}

function edgePath(points: Point[]): string {
  return points.map((point, index) => `${index === 0 ? "M" : "L"}${point.x},${point.y}`).join(" ")
}

export function buildSvg(drawing: Drawing, locale: Dialect = "es"): string {
  const shapes = drawing.nodes
    .map((node) => {
      const body = node.figure === "switch" ? switchShape(node, locale) : shape(node)
      if (!body) return ""
      if (node.figure === "switch") return `<g>${body}</g>`
      const label = `<text x="${node.x + node.width / 2}" y="${node.y + node.height / 2}" text-anchor="middle" dominant-baseline="middle">${escapeXml(node.text)}</text>`
      return `<g>${body}${label}</g>`
    })
    .join("")
  const edges = drawing.edges
    .map((edge) => {
      const path = `<path d="${edgePath(edge.points)}" fill="none" stroke="#c0392b" stroke-width="1.7" marker-end="url(#arrow)"/>`
      const label = flowLabel(edge.label, locale)
      const anchor = labelAnchor(edge.points)
      if (!label || !anchor) return path
      return `${path}<text class="flow-label" x="${anchor.x}" y="${anchor.y}">${escapeXml(label)}</text>`
    })
    .join("")
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${drawing.width}" height="${drawing.height}" viewBox="0 0 ${drawing.width} ${drawing.height}">
<style>
text{font-family:"Avenir Next","Segoe UI",sans-serif;font-size:13px;fill:#2c261c}
.flow-label{font-size:12px;font-weight:700;fill:#6a3d86}
.terminal{fill:#fff4c8;stroke:#e0a82a;stroke-width:1.4}
.process{fill:#fff8dc;stroke:#d4b03a;stroke-width:1.4}
.subprocess{fill:#fff8dc;stroke:#d4b03a;stroke-width:1.4}
.output{fill:#e7f6d4;stroke:#67a83d;stroke-width:1.4}
.input{fill:#f8d4ea;stroke:#d45398;stroke-width:1.4}
.decision{fill:#f3e4fb;stroke:#a45cc0;stroke-width:1.4}
.switch{fill:#d4e4fb;stroke:#3d6eae;stroke-width:1.5}
.switch-label{font-size:12px;font-weight:700;fill:#1d3f73}
.loop{fill:#efe6ff;stroke:#7d5cb8;stroke-width:1.6}
</style>
<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="#c0392b"/></marker></defs>
${shapes}${edges}
</svg>`
}
