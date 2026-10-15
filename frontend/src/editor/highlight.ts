import { canonicalize, isIdentContinue, isIdentStart } from "../words"

export type HighlightMode = "code" | "comment" | "string" | "char"
export type TokenKind = "keyword" | "string" | "comment" | "number" | "variableName" | null
export type HighlightSpan = { text: string; kind: TokenKind }

function isSpace(ch: string): boolean {
  return ch !== "" && /[\s\u00a0]/.test(ch)
}

export function consumeToken(
  line: string,
  pos: number,
  mode: HighlightMode,
  reserved: Set<string>,
): { pos: number; mode: HighlightMode; kind: TokenKind } {
  if (pos >= line.length) return { pos, mode, kind: null }
  if (mode === "comment") {
    if (line.startsWith("*/", pos)) return { pos: pos + 2, mode: "code", kind: "comment" }
    return { pos: pos + 1, mode, kind: "comment" }
  }
  if (mode === "string" || mode === "char") {
    const quote = mode === "string" ? '"' : "'"
    if (line[pos] === "\\") return { pos: Math.min(line.length, pos + 2), mode, kind: "string" }
    if (line[pos] === quote) return { pos: pos + 1, mode: "code", kind: "string" }
    return { pos: pos + 1, mode, kind: "string" }
  }
  if (isSpace(line[pos])) {
    let end = pos + 1
    while (end < line.length && isSpace(line[end])) end += 1
    return { pos: end, mode, kind: null }
  }
  if (line.startsWith("//", pos)) return { pos: line.length, mode, kind: "comment" }
  if (line.startsWith("/*", pos)) return { pos: pos + 2, mode: "comment", kind: "comment" }
  if (line[pos] === '"') return { pos: pos + 1, mode: "string", kind: "string" }
  if (line[pos] === "'") return { pos: pos + 1, mode: "char", kind: "string" }
  const number = /^\d+(\.\d+)?/.exec(line.slice(pos))
  if (number) return { pos: pos + number[0].length, mode, kind: "number" }
  if (isIdentStart(line[pos])) {
    let end = pos + 1
    while (end < line.length && isIdentContinue(line[end])) end += 1
    const word = line.slice(pos, end)
    return { pos: end, mode, kind: reserved.has(canonicalize(word)) ? "keyword" : "variableName" }
  }
  return { pos: pos + 1, mode, kind: null }
}

export function highlightSource(source: string, reserved: Set<string>): HighlightSpan[][] {
  let mode: HighlightMode = "code"
  return source.split("\n").map((line) => {
    const spans: HighlightSpan[] = []
    let pos = 0
    while (pos < line.length) {
      const next = consumeToken(line, pos, mode, reserved)
      if (next.pos <= pos) {
        spans.push({ text: line[pos], kind: null })
        pos += 1
        continue
      }
      const text = line.slice(pos, next.pos)
      const last = spans[spans.length - 1]
      if (last && last.kind === next.kind) last.text += text
      else spans.push({ text, kind: next.kind })
      pos = next.pos
      mode = next.mode
    }
    return spans
  })
}
