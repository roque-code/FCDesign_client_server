/** Plegado alineado con `language_core.grammar.canonicalize` para el español del curso. */

export function canonicalize(text: string): string {
  return text.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase()
}

export function keywordSet(words: readonly string[]): Set<string> {
  return new Set(words.map(canonicalize))
}

export function isIdentStart(ch: string): boolean {
  return ch === "_" || /\p{L}/u.test(ch)
}

export function isIdentContinue(ch: string): boolean {
  return ch === "_" || /\p{L}/u.test(ch) || /\p{Nd}/u.test(ch)
}
