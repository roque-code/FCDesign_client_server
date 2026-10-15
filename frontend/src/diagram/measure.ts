export function measure(kind: string, text: string): { width: number; height: number } {
  if (kind === "join") return { width: 16, height: 16 }
  const wide = kind === "decision" || kind === "loop"
  const width = Math.max(
    wide ? 168 : 132,
    Math.min(340, Math.ceil(text.length * 7.2 + (wide ? 72 : 36))),
  )
  const inner = Math.max(48, width - (wide ? 72 : 28))
  const lines = Math.max(1, Math.ceil((text.length * 7.2) / inner))
  const height = wide
    ? Math.max(kind === "loop" ? 72 : 96, lines * 22 + (kind === "loop" ? 36 : 56))
    : Math.max(kind === "terminal" ? 48 : 44, lines * 20 + 16)
  return { width, height }
}
