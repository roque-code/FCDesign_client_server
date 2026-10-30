import { useId, type PointerEvent as ReactPointerEvent } from "react"

import { boundaryPoint, edgeEnds, labelNear, nodeBox, textWidth, type Point, type View } from "./geometry"
import { isEntity, isTotal, showsCardinality, type ErEdge, type ErNode } from "./model"
import { Shape } from "./shapes"

function shorten(from: Point, to: Point, amount: number): Point {
  const dx = to.x - from.x
  const dy = to.y - from.y
  const len = Math.hypot(dx, dy) || 1
  return { x: to.x - (dx / len) * amount, y: to.y - (dy / len) * amount }
}

function shift(start: Point, end: Point, amount: number): { start: Point; end: Point } {
  const dx = end.x - start.x
  const dy = end.y - start.y
  const len = Math.hypot(dx, dy) || 1
  const ox = (-dy / len) * amount
  const oy = (dx / len) * amount
  return {
    start: { x: start.x + ox, y: start.y + oy },
    end: { x: end.x + ox, y: end.y + oy },
  }
}

function arrowPoints(tip: Point, from: Point): string {
  const dx = tip.x - from.x
  const dy = tip.y - from.y
  const len = Math.hypot(dx, dy) || 1
  const ux = dx / len
  const uy = dy / len
  const base = { x: tip.x - ux * 12, y: tip.y - uy * 12 }
  const left = { x: base.x - uy * 5.5, y: base.y + ux * 5.5 }
  const right = { x: base.x + uy * 5.5, y: base.y - ux * 5.5 }
  return `${tip.x},${tip.y} ${left.x},${left.y} ${right.x},${right.y}`
}

function Tag({ at, text }: { at: Point; text: string }) {
  const width = textWidth(text, 12) + 10
  return (
    <g className="erd-tag" pointerEvents="none">
      <rect x={at.x - width / 2} y={at.y - 9} width={width} height={16} rx={3} />
      <text x={at.x} y={at.y} textAnchor="middle" dominantBaseline="middle" fontSize={12} fontWeight={650}>
        {text}
      </text>
    </g>
  )
}

function NodeLabel({ node }: { node: ErNode }) {
  if (node.kind === "isa") return null
  const box = nodeBox(node)
  const size = node.kind === "attribute" || node.kind === "multivalued" || node.kind === "derived" ? 12 : 13
  const weight = node.kind === "entity" || node.kind === "weak-entity" ? 700 : 600
  const width = textWidth(node.label, size)
  const marked = node.kind === "attribute" && node.key !== "none"
  return (
    <g className="erd-label" pointerEvents="none">
      <text
        x={box.w / 2}
        y={box.h / 2}
        textAnchor="middle"
        dominantBaseline="middle"
        fontSize={size}
        fontWeight={weight}
      >
        {node.label}
      </text>
      {marked ? (
        <line
          x1={box.w / 2 - width / 2}
          x2={box.w / 2 + width / 2}
          y1={box.h / 2 + size * 0.62}
          y2={box.h / 2 + size * 0.62}
          strokeDasharray={node.key === "partial" ? "3 2" : undefined}
        />
      ) : null}
    </g>
  )
}

function EdgeView({
  edge,
  source,
  target,
  selected,
  onPointerDown,
}: {
  edge: ErEdge
  source: ErNode
  target: ErNode
  selected: boolean
  onPointerDown: (event: ReactPointerEvent, id: string) => void
}) {
  const ends = edgeEnds(source, target)
  const tip = ends.b
  const end = edge.one ? shorten(ends.a, ends.b, 12) : ends.b
  const total = isTotal(edge)
  const lines = total ? [shift(ends.a, end, 2.2), shift(ends.a, end, -2.2)] : [{ start: ends.a, end }]
  const entityPoint = isEntity(target.kind) && !isEntity(source.kind) ? tip : isEntity(source.kind) && !isEntity(target.kind) ? ends.a : null
  const otherPoint = entityPoint === tip ? ends.a : tip
  const card = showsCardinality(edge) && entityPoint ? labelNear(entityPoint, otherPoint, 48, 1) : null
  const mid = { x: (ends.a.x + ends.b.x) / 2, y: (ends.a.y + ends.b.y) / 2 }
  const roleAt = edge.role ? labelNear(mid, ends.b, 0, -1) : null
  return (
    <g className={selected ? "erd-link is-selected" : "erd-link"}>
      {lines.map((line, index) => (
        <line key={index} x1={line.start.x} y1={line.start.y} x2={line.end.x} y2={line.end.y} />
      ))}
      {edge.one ? <polygon className="erd-arrow" points={arrowPoints(tip, ends.a)} /> : null}
      <line
        className="erd-hit"
        x1={ends.a.x}
        y1={ends.a.y}
        x2={ends.b.x}
        y2={ends.b.y}
        onPointerDown={(event) => onPointerDown(event, edge.id)}
      />
      {card ? <Tag at={card} text={`${edge.min}..${edge.max}`} /> : null}
      {roleAt && edge.role ? (
        <text className="erd-role" x={roleAt.x} y={roleAt.y} textAnchor="middle" dominantBaseline="middle" fontSize={12}>
          {edge.role}
        </text>
      ) : null}
    </g>
  )
}

export function ErCanvas({
  nodes,
  edges,
  view,
  selectedId,
  pendingId,
  cursor,
  emptyLabel,
  canvasLabel,
  disjointLabel,
  deleteLineLabel,
  onBackgroundPointerDown,
  onNodePointerDown,
  onNodeDoubleClick,
  onEdgePointerDown,
  onDeleteEdge,
}: {
  nodes: ErNode[]
  edges: ErEdge[]
  view: View
  selectedId: string | null
  pendingId: string | null
  cursor: Point | null
  emptyLabel: string
  canvasLabel: string
  disjointLabel: string
  deleteLineLabel: string
  onBackgroundPointerDown: (event: ReactPointerEvent) => void
  onNodePointerDown: (event: ReactPointerEvent, id: string) => void
  onNodeDoubleClick: (id: string) => void
  onEdgePointerDown: (event: ReactPointerEvent, id: string) => void
  onDeleteEdge: (id: string) => void
}) {
  const gridId = `erd-grid-${useId().replace(/:/g, "")}`
  const pending = nodes.find((node) => node.id === pendingId) ?? null
  const draft = pending && cursor ? { from: boundaryPoint(pending, cursor), to: cursor } : null
  const ordered = [...nodes].sort((left, right) => Number(left.id === selectedId) - Number(right.id === selectedId))
  return (
    <svg
      className="erd-canvas"
      role="application"
      aria-label={canvasLabel}
      viewBox={`${view.x} ${view.y} ${view.w} ${view.h}`}
      preserveAspectRatio="none"
    >
      <defs>
        <pattern id={gridId} width={24} height={24} patternUnits="userSpaceOnUse">
          <path d="M 24 0 L 0 0 0 24" fill="none" stroke="var(--line)" strokeWidth={1} />
        </pattern>
      </defs>
      <rect
        className="erd-board"
        x={view.x}
        y={view.y}
        width={view.w}
        height={view.h}
        fill={`url(#${gridId})`}
        onPointerDown={onBackgroundPointerDown}
      />
      {edges.map((edge) => {
        const source = nodes.find((node) => node.id === edge.source)
        const target = nodes.find((node) => node.id === edge.target)
        if (!source || !target) return null
        return (
          <EdgeView
            key={edge.id}
            edge={edge}
            source={source}
            target={target}
            selected={edge.id === selectedId}
            onPointerDown={onEdgePointerDown}
          />
        )
      })}
      {ordered.map((node) => {
        const box = nodeBox(node)
        const pendingNode = node.id === pendingId
        const selected = node.id === selectedId || pendingNode
        return (
          <g
            key={node.id}
            className={pendingNode ? "erd-node is-pending" : "erd-node"}
            transform={`translate(${box.x} ${box.y})`}
            onPointerDown={(event) => onNodePointerDown(event, node.id)}
            onDoubleClick={(event) => {
              event.preventDefault()
              event.stopPropagation()
              onNodeDoubleClick(node.id)
            }}
          >
            <title>{node.label}</title>
            {selected ? (
              <rect className="erd-select" x={-6} y={-6} width={box.w + 12} height={box.h + 12} rx={8} />
            ) : null}
            <Shape kind={node.kind} w={box.w} h={box.h} label={node.label} />
            <NodeLabel node={node} />
            {node.kind === "isa" && node.disjoint ? (
              <text className="erd-role" x={box.w + 6} y={box.h / 2} dominantBaseline="middle" fontSize={12}>
                {disjointLabel}
              </text>
            ) : null}
            <rect className="erd-node-hit" width={box.w} height={box.h} fill="transparent" />
          </g>
        )
      })}
      {edges.flatMap((edge) => {
        if (edge.id !== selectedId) return []
        const source = nodes.find((node) => node.id === edge.source)
        const target = nodes.find((node) => node.id === edge.target)
        if (!source || !target) return []
        const ends = edgeEnds(source, target)
        const mid = { x: (ends.a.x + ends.b.x) / 2, y: (ends.a.y + ends.b.y) / 2 }
        return [
          <g
            key={`${edge.id}-delete`}
            className="erd-line-delete"
            transform={`translate(${mid.x} ${mid.y})`}
            onPointerDown={(event) => {
              event.stopPropagation()
              event.preventDefault()
              onDeleteEdge(edge.id)
            }}
          >
            <title>{deleteLineLabel}</title>
            <circle r={12} />
            <text y={1} textAnchor="middle" dominantBaseline="middle" fontSize={16}>×</text>
          </g>,
        ]
      })}
      {draft ? (
        <line className="erd-draft" pointerEvents="none" x1={draft.from.x} y1={draft.from.y} x2={draft.to.x} y2={draft.to.y} />
      ) : null}
      {nodes.length === 0 ? (
        <text
          className="erd-empty"
          x={view.x + view.w / 2}
          y={view.y + view.h / 2}
          textAnchor="middle"
          fontSize={Math.min(22, view.w / 42)}
        >
          {emptyLabel}
        </text>
      ) : null}
    </svg>
  )
}
