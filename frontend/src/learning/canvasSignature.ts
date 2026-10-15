const LAYOUT = new Set(["x", "y", "width", "height"])

function strip(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(strip)
  if (value === null || typeof value !== "object") return value
  const copy: Record<string, unknown> = {}
  for (const [key, item] of Object.entries(value)) {
    if (LAYOUT.has(key)) continue
    copy[key] = strip(item)
  }
  return copy
}

export function canvasSignature(workspace: object): string {
  return JSON.stringify(strip(workspace))
}
