/** Tab sangra y Shift+Tab quita la sangría, como en el editor de Lenguajes. */
export function indentText(
  value: string,
  start: number,
  end: number,
  outdent: boolean,
): { value: string; start: number; end: number } {
  if (!outdent && !value.slice(start, end).includes("\n")) {
    return { value: value.slice(0, start) + "\t" + value.slice(end), start: start + 1, end: start + 1 }
  }
  const lineStart = value.lastIndexOf("\n", start - 1) + 1
  const blockEnd = end > start && value[end - 1] === "\n" ? end - 1 : end
  const found = value.indexOf("\n", blockEnd)
  const lineEnd = found === -1 ? value.length : found
  const lines = value.slice(lineStart, lineEnd).split("\n")
  const shifted = lines.map((line) => (outdent ? line.replace(/^(\t| {1,4})/u, "") : `\t${line}`))
  const block = shifted.join("\n")
  const updated = value.slice(0, lineStart) + block + value.slice(lineEnd)
  if (start === end) {
    const caret = Math.max(lineStart, start + shifted[0].length - lines[0].length)
    return { value: updated, start: caret, end: caret }
  }
  return { value: updated, start: lineStart, end: lineStart + block.length }
}
