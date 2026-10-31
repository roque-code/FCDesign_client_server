/** Sugerencias del editor de lenguajes. Después de un punto, los miembros del tipo que se reconoce. */

import { snippetCompletion, type Completion, type CompletionContext, type CompletionResult, type CompletionSource } from "@codemirror/autocomplete"

import { catalogFor, type Catalog, type Entry, type EntryKind } from "./catalog"
import { hashComment, keywordsFor, type ForeignLanguage } from "./keywords"
import { pullToken, type ScanMode, type ScanRules } from "./scan"

const TYPE_OF: Record<EntryKind, string> = {
  function: "function",
  method: "method",
  class: "class",
  property: "property",
  constant: "constant",
  namespace: "namespace",
}

const TYPED = new Set<ForeignLanguage>(["java", "c", "cpp", "csharp"])
const NOT_A_TYPE = new Set(["return", "new", "else", "case", "throw", "goto", "delete", "typeof", "sizeof", "in", "of", "yield", "await", "using", "import", "package"])
const STRING_KEY: Partial<Record<ForeignLanguage, string>> = {
  python: "str",
  javascript: "String",
  typescript: "String",
  java: "String",
  csharp: "String",
}
const IDENTIFIER = /[A-Za-z_$][\w$]*/g
const MAX_DEPTH = 4

function escapeName(name: string): string {
  return name.replace(/\$/g, "\\$")
}

function helpNode(entry: Entry): Node {
  const box = document.createElement("div")
  box.className = "cm-foreign-help"
  const sig = document.createElement("code")
  sig.textContent = entry.sig
  const doc = document.createElement("p")
  doc.textContent = entry.doc
  box.append(sig, doc)
  return box
}

function takesArguments(entry: Entry): boolean {
  const found = new RegExp(`${escapeName(entry.name)}\\(([^)]*)\\)`).exec(entry.sig)
  if (!found) return true
  const inside = found[1].trim()
  return inside !== "" && inside !== "void"
}

export function completionOf(entry: Entry): Completion {
  const base: Completion = {
    label: entry.name,
    detail: entry.sig,
    type: TYPE_OF[entry.kind],
    info: () => helpNode(entry),
  }
  if (entry.kind !== "function" && entry.kind !== "method") return base
  if (!takesArguments(entry)) return { ...base, apply: `${entry.name}()` }
  return snippetCompletion(`${entry.name}(\${1})\${0}`, base)
}

/** true si la columna cae dentro de un texto entre comillas o de un comentario. */
export function insideTextOrComment(line: string, column: number, language: ForeignLanguage): boolean {
  const rules: ScanRules = { reserved: new Set(), hashComment: hashComment(language) }
  let pos = 0
  let mode: ScanMode = "code"
  while (pos < column) {
    const next = pullToken(line, pos, mode, rules)
    if (next.pos <= pos) return false
    if (next.kind === "comment" && pos < column) {
      const piece = line.slice(pos, next.pos)
      const open = next.pos >= line.length && !(piece.startsWith("/*") && piece.endsWith("*/") && piece.length >= 4)
      if (column < next.pos || open) return true
    }
    if (next.kind === "string" && pos < column) {
      const quote = line[pos]
      const closed = next.pos - pos >= 2 && line[next.pos - 1] === quote && line[next.pos - 2] !== "\\"
      if (column < next.pos || !closed) return true
    }
    pos = next.pos
    mode = next.mode
  }
  return false
}

function lastMatch(pattern: RegExp, text: string): RegExpExecArray | null {
  let found: RegExpExecArray | null = null
  pattern.lastIndex = 0
  for (let match = pattern.exec(text); match; match = pattern.exec(text)) {
    found = match
    if (match[0] === "") pattern.lastIndex += 1
  }
  return found
}

function tableFor(catalog: Catalog, typeName: string | undefined | null): string | null {
  if (!typeName) return null
  const clean = typeName.trim().replace(/<.*$/s, "").replace(/\?$/, "")
  const last = clean.split(/::|\./).pop() ?? clean
  if (catalog.aliases[last]) return catalog.aliases[last]
  if (catalog.members[last]) return last
  return null
}

function matchingParen(text: string): number {
  let depth = 0
  for (let index = text.length - 1; index >= 0; index -= 1) {
    const ch = text[index]
    if (ch === ")") depth += 1
    if (ch === "(") {
      depth -= 1
      if (depth === 0) return index
    }
  }
  return -1
}

function findEntry(entries: Entry[] | undefined, name: string): Entry | undefined {
  return entries?.find((item) => item.name === name)
}

function closedStringLiteral(text: string): boolean {
  const quote = text[text.length - 1]
  if (quote !== '"' && quote !== "'" && quote !== "`") return false
  const open = text.lastIndexOf(quote, text.length - 2)
  return open >= 0
}

function rhsType(rhs: string, language: ForeignLanguage, catalog: Catalog, source: string, depth: number): string | null {
  const value = rhs.trim().replace(/;$/, "").trim()
  if (!value) return null
  if (/^(?:[fFrRbBuU]{1,2})?["'`]/.test(value)) return STRING_KEY[language] ?? null
  if (language === "python") {
    if (value.startsWith("[")) return "list"
    if (/^\{\s*\}/.test(value) || /^\{[^}]*:/.test(value)) return "dict"
    if (value.startsWith("{")) return "set"
  }
  if ((language === "javascript" || language === "typescript") && value.startsWith("[")) return "Array"
  const created = /^new\s+([\w.:]+)\s*(?:<[^;]*?>)?\s*(\[)?/.exec(value)
  if (created) return created[2] ? (catalog.members.array ? "array" : null) : tableFor(catalog, created[1])
  return receiverTable(value, language, catalog, source, depth + 1)
}

/** Tabla de miembros de una variable por su declaración más reciente. */
export function declaredTable(name: string, language: ForeignLanguage, source: string, depth = 0): string | null {
  if (depth > MAX_DEPTH) return null
  const catalog = catalogFor(language)
  const id = escapeName(name)
  if (language === "python") {
    const found = lastMatch(new RegExp(`^[ \\t]*${id}[ \\t]*(?::[ \\t]*([\\w\\[\\], ]+?))?[ \\t]*=(?!=)[ \\t]*(.+)$`, "gm"), source)
    if (!found) return null
    if (found[1]) {
      const hinted = found[1].trim().replace(/\[.*$/, "")
      if (catalog.members[hinted]) return hinted
    }
    return rhsType(found[2], language, catalog, source, depth)
  }
  if (language === "javascript" || language === "typescript") {
    const found = lastMatch(new RegExp(`\\b(?:let|const|var)\\s+${id}\\s*(?::\\s*([^=;\\n]+?))?\\s*(?:=\\s*([^;\\n]+))?(?:;|$)`, "gm"), source)
    if (!found) return null
    const hint = found[1]?.trim()
    if (hint) {
      if (hint === "string") return "String"
      if (/\[\]$/.test(hint) || /^Array</.test(hint)) return "Array"
      const hinted = tableFor(catalog, hint)
      if (hinted) return hinted
    }
    return found[2] ? rhsType(found[2], language, catalog, source, depth) : null
  }
  if (!TYPED.has(language)) return null
  const inferred = lastMatch(new RegExp(`\\b(?:var|auto)\\s+${id}\\s*=\\s*([^;\\n]+)`, "g"), source)
  const assigned = lastMatch(new RegExp(`\\b${id}\\s*=\\s*(new\\s+[^;\\n]+)`, "g"), source)
  const declared = lastMatch(
    new RegExp(`([A-Za-z_][\\w.:]*)\\s*(<[^;=(){}]*>)?\\s*((?:\\[\\s*\\])*)[\\s&*]+${id}\\s*(?=[=;,):\\[])`, "g"),
    source,
  )
  const candidates = [
    inferred ? { at: inferred.index, kind: "inferred" as const, match: inferred } : null,
    assigned ? { at: assigned.index, kind: "assigned" as const, match: assigned } : null,
    declared && !NOT_A_TYPE.has(declared[1]) ? { at: declared.index, kind: "declared" as const, match: declared } : null,
  ].filter((item) => item !== null)
  candidates.sort((a, b) => b.at - a.at)
  const best = candidates[0]
  if (!best) return null
  if (best.kind === "assigned" || best.kind === "inferred") return rhsType(best.match[1], language, catalog, source, depth)
  const [, typeName, , brackets] = best.match
  if (brackets && catalog.members.array) return "array"
  if (typeName === "var" || typeName === "auto") return null
  return tableFor(catalog, typeName)
}

/** Tabla de miembros de lo que está escrito antes del punto. */
export function receiverTable(text: string, language: ForeignLanguage, catalog: Catalog, source: string, depth = 0): string | null {
  if (depth > MAX_DEPTH) return null
  const value = text.trimEnd()
  if (!value) return null
  if (closedStringLiteral(value)) return STRING_KEY[language] ?? null
  if (value.endsWith(")")) {
    const open = matchingParen(value)
    if (open < 0) return null
    const head = value.slice(0, open).trimEnd()
    const called = /([A-Za-z_$][\w$]*)$/.exec(head)
    if (!called) return null
    const name = called[1]
    const prefix = head.slice(0, head.length - name.length)
    if (/\bnew\s+$/.test(prefix)) return tableFor(catalog, name)
    const sep = prefix.endsWith("::") ? "::" : prefix.endsWith(".") ? "." : ""
    if (sep) {
      const owner = receiverTable(prefix.slice(0, -sep.length), language, catalog, source, depth + 1)
      return findEntry(owner ? catalog.members[owner] : undefined, name)?.returns ?? null
    }
    return findEntry(catalog.globals, name)?.returns ?? null
  }
  const chain = /([A-Za-z_$][\w$]*(?:(?:\.|::)[A-Za-z_$][\w$]*)*)$/.exec(value)
  if (!chain) return null
  const full = chain[1]
  if (catalog.receivers[full]) return catalog.receivers[full]
  const split = Math.max(full.lastIndexOf("."), full.lastIndexOf("::"))
  if (split > 0) {
    const sepLength = full.startsWith("::", split) ? 2 : 1
    const owner = receiverTable(full.slice(0, split), language, catalog, source, depth + 1)
    const field = full.slice(split + sepLength)
    return findEntry(owner ? catalog.members[owner] : undefined, field)?.returns ?? null
  }
  return declaredTable(full, language, source, depth + 1)
}

function documentWords(source: string, skip: Set<string>, typed: string): Completion[] {
  const counts = new Map<string, number>()
  for (const match of source.matchAll(IDENTIFIER)) {
    const word = match[0]
    if (word.length < 2 || skip.has(word)) continue
    counts.set(word, (counts.get(word) ?? 0) + 1)
  }
  const found: Completion[] = []
  for (const [word, count] of counts) {
    if (word === typed && count === 1) continue
    found.push({ label: word, type: "variable", boost: -1 })
  }
  return found
}

export function foreignCompletion(language: ForeignLanguage): CompletionSource {
  const catalog = catalogFor(language)
  const keywords = keywordsFor(language)
  const keywordOptions: Completion[] = keywords.map((word) => ({ label: word, type: "keyword" }))
  const globalOptions = catalog.globals.map(completionOf)
  const stdOptions = (catalog.members.std ?? []).map(completionOf)
  const memberOptions = new Map<string, Completion[]>()
  const membersOf = (table: string): Completion[] => {
    let options = memberOptions.get(table)
    if (!options) {
      options = (catalog.members[table] ?? []).map(completionOf)
      memberOptions.set(table, options)
    }
    return options
  }

  return (context: CompletionContext): CompletionResult | null => {
    const word = context.matchBefore(/[\w$]*/)
    if (!word) return null
    if (/^\d/.test(word.text)) return null
    const line = context.state.doc.lineAt(context.pos)
    if (insideTextOrComment(line.text, word.from - line.from, language)) return null
    const before = context.state.sliceDoc(line.from, word.from)
    const sep = language === "cpp" && before.endsWith("::") ? "::" : before.endsWith(".") ? "." : ""
    const source = context.state.sliceDoc(0, word.from)
    if (sep) {
      const owner = receiverTable(before.slice(0, -sep.length), language, catalog, source)
      if (!owner) return null
      const options = membersOf(owner)
      if (options.length === 0) return null
      return { from: word.from, options, validFor: /^[\w$]*$/ }
    }
    if (word.from === word.to && !context.explicit) return null
    const usesStd = language === "cpp" && /\busing\s+namespace\s+std\b/.test(source)
    const named = new Set<string>([...keywords, ...catalog.globals.map((item) => item.name)])
    if (usesStd) for (const item of catalog.members.std ?? []) named.add(item.name)
    const whole = context.state.doc.toString()
    const options = [
      ...keywordOptions,
      ...globalOptions,
      ...(usesStd ? stdOptions : []),
      ...documentWords(whole, named, word.text),
    ]
    return { from: word.from, options, validFor: /^[\w$]*$/ }
  }
}
