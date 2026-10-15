import type { FlowNode } from "../api"

export function focusNodeId(nodes: FlowNode[], line: number | null): string | null {
  if (line == null) return null
  const hits = nodes.filter((node) => {
    if (node.kind === "join" || node.line == null || node.end_line == null) return false
    return node.line <= line && line <= node.end_line
  })
  if (hits.length === 0) return null
  const rank = (node: FlowNode) => {
    const span = (node.end_line ?? node.line ?? line) - (node.line ?? line)
    const preference = node.kind === "decision" ? 0 : node.kind === "io" ? 1 : node.kind === "subprocess" ? 2 : 3
    const starts = node.line === line ? 0 : 1
    return [span, starts, preference] as const
  }
  hits.sort((left, right) => {
    const a = rank(left)
    const b = rank(right)
    return a[0] - b[0] || a[1] - b[1] || a[2] - b[2]
  })
  return hits[0].id
}
