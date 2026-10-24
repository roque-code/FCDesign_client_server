/** Recorre una línea con la lista de un solo lenguaje. */

export type ScanMode = "code" | "block"

export type ScanRules = {
  reserved: ReadonlySet<string>
  hashComment: boolean
}

export function pullToken(
  line: string,
  pos: number,
  mode: ScanMode,
  rules: ScanRules,
): { pos: number; mode: ScanMode; kind: string | null } {
  if (mode === "block") {
    const end = line.indexOf("*/", pos)
    if (end < 0) return { pos: Math.max(line.length, pos + 1), mode: "block", kind: "comment" }
    return { pos: end + 2, mode: "code", kind: "comment" }
  }
  if (pos >= line.length) return { pos: pos + 1, mode, kind: null }
  const ch = line[pos]
  if (ch === " " || ch === "\t" || ch === "\r") {
    let index = pos + 1
    while (index < line.length && (line[index] === " " || line[index] === "\t" || line[index] === "\r")) {
      index += 1
    }
    return { pos: index, mode, kind: null }
  }
  if (line.startsWith("//", pos)) return { pos: line.length, mode, kind: "comment" }
  if (line.startsWith("/*", pos)) {
    const end = line.indexOf("*/", pos + 2)
    if (end < 0) return { pos: line.length, mode: "block", kind: "comment" }
    return { pos: end + 2, mode, kind: "comment" }
  }
  if (rules.hashComment && ch === "#") return { pos: line.length, mode, kind: "comment" }
  if (ch === '"' || ch === "'" || ch === "`") {
    let index = pos + 1
    while (index < line.length) {
      if (line[index] === "\\") {
        index += 2
        continue
      }
      if (line[index] === ch) return { pos: index + 1, mode, kind: "string" }
      index += 1
    }
    return { pos: line.length, mode, kind: "string" }
  }
  if (ch >= "0" && ch <= "9") {
    let index = pos + 1
    while (index < line.length && /[0-9A-Fa-fxX_.]/.test(line[index])) index += 1
    return { pos: index, mode, kind: "number" }
  }
  if (/[A-Za-z_]/.test(ch)) {
    let index = pos + 1
    while (index < line.length && /[A-Za-z0-9_]/.test(line[index])) index += 1
    const word = line.slice(pos, index)
    return { pos: index, mode, kind: rules.reserved.has(word) ? "keyword" : null }
  }
  return { pos: pos + 1, mode, kind: null }
}

export function kindsOf(line: string, keywords: readonly string[], hashComment: boolean): string[] {
  const rules: ScanRules = { reserved: new Set(keywords), hashComment }
  const found: string[] = []
  let pos = 0
  let mode: ScanMode = "code"
  while (pos < line.length) {
    const next = pullToken(line, pos, mode, rules)
    if (next.pos <= pos) break
    if (next.kind) found.push(next.kind)
    pos = next.pos
    mode = next.mode
  }
  return found
}
