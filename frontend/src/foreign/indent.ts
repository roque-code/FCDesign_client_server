import { hashComment, type ForeignLanguage } from "./keywords"
import { pullToken, type ScanMode } from "./scan"

const OPENERS = new Set(["{", "(", "["])

function lastCodeChar(line: string, language: ForeignLanguage): string {
  const rules = { reserved: new Set<string>(), hashComment: hashComment(language) }
  let pos = 0
  let mode: ScanMode = "code"
  let last = ""
  while (pos < line.length) {
    const next = pullToken(line, pos, mode, rules)
    if (next.pos <= pos) break
    const piece = line.slice(pos, Math.min(next.pos, line.length))
    if (next.kind !== "comment" && piece.trim() !== "") last = piece.trimEnd().slice(-1)
    pos = next.pos
    mode = next.mode
  }
  return last
}

/** La línea de arriba abre un bloque si termina en { ( [ o, en Python, en dos puntos. */
export function opensBlock(line: string, language: ForeignLanguage): boolean {
  const last = lastCodeChar(line, language)
  return OPENERS.has(last) || (language === "python" && last === ":")
}

export function closesBlock(textAfter: string): boolean {
  return /^\s*[}\])]/u.test(textAfter)
}

export function leadingColumns(line: string, tabSize: number): number {
  let column = 0
  for (const ch of line) {
    if (ch === " ") column += 1
    else if (ch === "\t") column += tabSize - (column % tabSize)
    else break
  }
  return column
}

export function nextIndent(
  previous: string | null,
  textAfter: string,
  language: ForeignLanguage,
  tabSize: number,
  unit: number,
): number {
  if (previous === null) return 0
  let column = leadingColumns(previous, tabSize)
  if (opensBlock(previous, language)) column += unit
  if (closesBlock(textAfter)) column -= unit
  return Math.max(0, column)
}
