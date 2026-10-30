import { isaPolygon, type NodeKind } from "./geometry"
import type { LinkTool } from "./model"

export function Shape({ kind, w, h, label }: { kind: NodeKind; w: number; h: number; label?: string }) {
  const tone =
    kind === "entity" || kind === "weak-entity"
      ? "entity"
      : kind === "relationship" || kind === "identifying"
        ? "relationship"
        : kind === "isa"
          ? "isa"
          : "attribute"
  const derived = kind === "derived" ? " derived" : ""
  if (kind === "weak-entity") {
    return (
      <g className={`erd-shape ${tone}`}>
        <rect x={0.5} y={0.5} width={w - 1} height={h - 1} rx={3} />
        <rect x={5} y={5} width={w - 10} height={h - 10} rx={2} />
      </g>
    )
  }
  if (kind === "entity") {
    return (
      <g className={`erd-shape ${tone}`}>
        <rect x={0.5} y={0.5} width={w - 1} height={h - 1} rx={3} />
      </g>
    )
  }
  if (kind === "relationship" || kind === "identifying") {
    const outer = `${w / 2},1 ${w - 1},${h / 2} ${w / 2},${h - 1} 1,${h / 2}`
    const inner = `${w / 2},8 ${w - 8},${h / 2} ${w / 2},${h - 8} 8,${h / 2}`
    return (
      <g className={`erd-shape ${tone}`}>
        <polygon points={outer} />
        {kind === "identifying" ? <polygon points={inner} /> : null}
      </g>
    )
  }
  if (kind === "isa") {
    const top = 10
    const bottom = h - 6
    const cy = (top + top + bottom) / 3
    return (
      <g className={`erd-shape ${tone}`}>
        <polygon points={isaPolygon(w, h)} />
        <text x={w / 2} y={cy} textAnchor="middle" dominantBaseline="middle" fontSize={h < 48 ? 9 : 12}>
          {label ?? "ISA"}
        </text>
      </g>
    )
  }
  const inset = kind === "multivalued" ? 5 : 1
  return (
    <g className={`erd-shape ${tone}${derived}`}>
      <ellipse cx={w / 2} cy={h / 2} rx={w / 2 - 1} ry={h / 2 - 1} />
      {kind === "multivalued" ? <ellipse cx={w / 2} cy={h / 2} rx={w / 2 - inset - 4} ry={h / 2 - inset - 3} /> : null}
    </g>
  )
}

export function Glyph({ kind }: { kind: NodeKind }) {
  return (
    <svg className="erd-glyph" width="52" height="36" viewBox="0 0 52 36" aria-hidden="true">
      <Shape kind={kind} w={52} h={36} />
    </svg>
  )
}

export function LineIcon({ tool }: { tool: "move" | LinkTool }) {
  if (tool === "move") {
    return (
      <svg className="erd-icon" width="46" height="28" viewBox="0 0 46 28" aria-hidden="true">
        <path d="M23 4v20M13 14h20M23 4l-3 3M23 4l3 3M23 24l-3-3M23 24l3-3M13 14l3-3M13 14l3 3M33 14l-3-3M33 14l-3 3" />
      </svg>
    )
  }
  if (tool === "partial") {
    return (
      <svg className="erd-icon" width="46" height="28" viewBox="0 0 46 28" aria-hidden="true">
        <line x1="4" y1="14" x2="42" y2="14" />
      </svg>
    )
  }
  if (tool === "total") {
    return (
      <svg className="erd-icon" width="46" height="28" viewBox="0 0 46 28" aria-hidden="true">
        <line x1="4" y1="11" x2="42" y2="11" />
        <line x1="4" y1="17" x2="42" y2="17" />
      </svg>
    )
  }
  const arrows = tool === "one-one" ? "both" : tool === "many-one" ? "end" : "none"
  return (
    <svg className="erd-icon" width="52" height="28" viewBox="0 0 52 28" aria-hidden="true">
      <rect x="1.5" y="8" width="10" height="12" rx="1" />
      <polygon points="26,4 34,14 26,24 18,14" />
      <rect x="40.5" y="8" width="10" height="12" rx="1" />
      <line x1="11.5" y1="14" x2="18" y2="14" />
      <line x1="34" y1="14" x2="40.5" y2="14" />
      {arrows === "end" || arrows === "both" ? <polygon className="erd-icon-fill" points="40.5,14 34.5,10.5 34.5,17.5" /> : null}
      {arrows === "both" ? <polygon className="erd-icon-fill" points="11.5,14 17.5,10.5 17.5,17.5" /> : null}
    </svg>
  )
}
