export type GlyphCase = { label: string | null; width: number }

export function ShapeGlyph({ figure, active = false }: { figure: string; active?: boolean }) {
  const stroke = active ? "#c4554a" : undefined
  const strokeWidth = active ? 2.6 : 1.5
  if (figure === "join") return null
  if (figure === "terminal") {
    return (
      <svg viewBox="0 0 100 40" preserveAspectRatio="none" aria-hidden="true">
        <ellipse className="terminal" cx="50" cy="20" rx="48" ry="18" stroke={stroke} strokeWidth={strokeWidth} />
      </svg>
    )
  }
  if (figure === "decision") {
    return (
      <svg viewBox="0 0 100 70" preserveAspectRatio="none" aria-hidden="true">
        <polygon className="decision" points="50,2 98,35 50,68 2,35" stroke={stroke} strokeWidth={strokeWidth} />
      </svg>
    )
  }
  if (figure === "loop") {
    return (
      <svg viewBox="0 0 100 56" preserveAspectRatio="none" aria-hidden="true">
        <polygon className="loop" points="18,2 82,2 98,28 82,54 18,54 2,28" stroke={stroke} strokeWidth={strokeWidth} />
      </svg>
    )
  }
  if (figure === "output" || figure === "input") {
    const points = figure === "output" ? "14,2 98,2 86,38 2,38" : "2,2 86,2 98,38 14,38"
    return (
      <svg viewBox="0 0 100 40" preserveAspectRatio="none" aria-hidden="true">
        <polygon className={figure} points={points} stroke={stroke} strokeWidth={strokeWidth} />
      </svg>
    )
  }
  return (
    <svg viewBox="0 0 100 40" preserveAspectRatio="none" aria-hidden="true">
      <rect className="process" x="2" y="2" width="96" height="36" stroke={stroke} strokeWidth={strokeWidth} />
      {figure === "subprocess" && (
        <rect x="7" y="7" width="86" height="26" fill="none" stroke={stroke ?? "#d4b03a"} strokeWidth={strokeWidth} />
      )}
    </svg>
  )
}

export function SwitchGlyph({
  width,
  height,
  cases,
  active = false,
}: {
  width: number
  height: number
  cases: GlyphCase[]
  active?: boolean
}) {
  const bar = 30
  const tri = Math.max(bar, height - bar)
  const stroke = active ? "#c4554a" : "#3d6eae"
  const outline = `M${width / 2},1 L${width - 1},${tri} L${width - 1},${height - 1} L1,${height - 1} L1,${tri} Z`
  let cursor = 0
  const dividers = cases.slice(0, -1).map((item) => {
    cursor += item.width
    return `M${cursor},${tri} L${cursor},${height - 1}`
  })
  return (
    <svg viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
      <path
        className="switch"
        d={`${outline} M1,${tri} L${width - 1},${tri} ${dividers.join(" ")}`}
        stroke={stroke}
        strokeWidth={active ? 2.4 : 1.5}
      />
    </svg>
  )
}
