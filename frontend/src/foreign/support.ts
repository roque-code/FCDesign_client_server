import { HighlightStyle, StreamLanguage, getIndentUnit, indentService, syntaxHighlighting } from "@codemirror/language"
import { EditorView } from "@codemirror/view"
import { tags } from "@lezer/highlight"
import type { Extension } from "@codemirror/state"

import { nextIndent } from "./indent"
import { hashComment, keywordsFor, type ForeignLanguage } from "./keywords"
import { pullToken, type ScanMode } from "./scan"

const highlight = HighlightStyle.define([
  { tag: tags.keyword, color: "var(--code-keyword)", fontWeight: "650" },
  { tag: tags.string, color: "var(--code-string)" },
  { tag: tags.comment, color: "var(--code-comment)", fontStyle: "italic" },
  { tag: tags.number, color: "var(--code-number)" },
])

export function foreignSupport(language: ForeignLanguage): Extension {
  const reserved = new Set(keywordsFor(language))
  const rules = { reserved, hashComment: hashComment(language) }
  const mode = StreamLanguage.define<{ mode: ScanMode }>({
    startState: () => ({ mode: "code" }),
    token(stream, state) {
      if (stream.eol()) return null
      const next = pullToken(stream.string, stream.pos, state.mode, rules)
      if (next.pos <= stream.pos) {
        stream.next()
        return null
      }
      stream.pos = Math.min(next.pos, stream.string.length)
      state.mode = next.mode
      return next.kind
    },
    languageData: {
      indentOnInput: /^\s*[}\])]$/u,
      commentTokens: language === "python" ? { line: "#" } : { line: "//", block: { open: "/*", close: "*/" } },
    },
  })
  const indent = indentService.of((context, pos) => {
    const current = context.lineAt(pos, 1)
    let above = context.lineAt(pos, -1)
    if (above.from === current.from) {
      if (pos === 0) return 0
      above = context.lineAt(pos - 1, -1)
    }
    while (above.text.trim() === "" && above.from > 0) above = context.lineAt(above.from - 1, -1)
    const previous = above.text.trim() === "" ? null : above.text
    return nextIndent(previous, current.text, language, context.state.tabSize, getIndentUnit(context.state))
  })
  return [
    mode,
    indent,
    syntaxHighlighting(highlight),
    EditorView.theme({
      "&": { background: "var(--sheet)", color: "var(--ink)", height: "100%" },
      ".cm-gutters": { background: "var(--panel)", color: "var(--muted)", border: "none" },
      ".cm-scroller": { overflow: "auto" },
    }),
  ]
}
