import { acceptCompletion, autocompletion, closeCompletion, completeFromList } from "@codemirror/autocomplete"
import { indentWithTab, insertNewlineAndIndent } from "@codemirror/commands"
import { HighlightStyle, indentUnit, StreamLanguage, syntaxHighlighting, type StringStream } from "@codemirror/language"
import { tags } from "@lezer/highlight"
import { EditorState, Prec, StateEffect, StateField, type Extension } from "@codemirror/state"
import { Decoration, EditorView, gutter, GutterMarker, keymap, type DecorationSet } from "@codemirror/view"
import { basicSetup } from "codemirror"
import { useEffect, useRef } from "react"

import { commitSource, mapCaret, presentSource } from "../dialect"
import { useLocale } from "../i18n"
import { keywordSet } from "../words"
import { consumeToken, type HighlightMode } from "./highlight"

type TokenState = { mode: HighlightMode }

const trazaHighlight = HighlightStyle.define([
  { tag: tags.keyword, color: "var(--code-keyword)", fontWeight: "650" },
  { tag: tags.string, color: "var(--code-string)" },
  { tag: tags.comment, color: "var(--code-comment)", fontStyle: "italic" },
  { tag: tags.number, color: "var(--code-number)" },
])

function trazaLanguage(reserved: Set<string>): Extension {
  return StreamLanguage.define<TokenState>({
    startState: () => ({ mode: "code" }),
    token(stream: StringStream, state: TokenState) {
      const next = consumeToken(stream.string, stream.pos, state.mode, reserved)
      stream.pos = next.pos
      state.mode = next.mode
      return next.kind
    },
  })
}

const setBreakpoints = StateEffect.define<number[]>()
const breakpointField = StateField.define<Set<number>>({
  create: () => new Set(),
  update(value, transaction) {
    for (const effect of transaction.effects) {
      if (effect.is(setBreakpoints)) return new Set(effect.value)
    }
    return value
  },
})

class DotMarker extends GutterMarker {
  constructor(private hidden: boolean) {
    super()
  }

  toDOM() {
    const dot = document.createElement("span")
    dot.className = this.hidden ? "cm-breakpoint-spacer" : "cm-breakpoint"
    dot.textContent = "●"
    return dot
  }
}

const breakpointDot = new DotMarker(false)
const breakpointSpacer = new DotMarker(true)
const toggleBreakpoint: { current: (line: number) => void } = { current: () => undefined }

const breakpointGutter = gutter({
  class: "cm-breakpoint-gutter",
  renderEmptyElements: true,
  lineMarker(view, line) {
    const marks = view.state.field(breakpointField)
    const number = view.state.doc.lineAt(line.from).number
    return marks.has(number) ? breakpointDot : null
  },
  lineMarkerChange(update) {
    return update.transactions.some((transaction) =>
      transaction.effects.some((effect) => effect.is(setBreakpoints)),
    )
  },
  initialSpacer: () => breakpointSpacer,
  domEventHandlers: {
    mousedown(view, line, event) {
      event.preventDefault()
      toggleBreakpoint.current(view.state.doc.lineAt(line.from).number)
      return true
    },
  },
})

const setDebugLine = StateEffect.define<number | null>()
const debugLineMark = Decoration.line({ class: "cm-debug-line" })
const debugLineField = StateField.define<DecorationSet>({
  create: () => Decoration.none,
  update(value, transaction) {
    for (const effect of transaction.effects) {
      if (effect.is(setDebugLine)) {
        if (effect.value == null) return Decoration.none
        const lineNo = Math.min(Math.max(effect.value, 1), transaction.state.doc.lines)
        return Decoration.set([debugLineMark.range(transaction.state.doc.line(lineNo).from)])
      }
    }
    return value.map(transaction.changes)
  },
  provide: (field) => EditorView.decorations.from(field),
})

const debugExtensions: Extension[] = [breakpointField, breakpointGutter, debugLineField]

const tabIndent = Prec.highest(
  keymap.of([
    {
      key: "Tab",
      run: (view) => acceptCompletion(view) || Boolean(indentWithTab.run?.(view)),
      shift: (view) => Boolean(indentWithTab.shift?.(view)),
    },
    {
      key: "Enter",
      run: (view) => {
        closeCompletion(view)
        return insertNewlineAndIndent(view)
      },
    },
  ]),
)

type Props = {
  source: string
  keywords: string[]
  stdlib: string[]
  fontSize: number
  indentSize: number
  theme: "light" | "dark"
  jump: { line: number; token: number } | null
  breakpoints: number[]
  currentLine: number | null
  onToggleBreakpoint: (line: number) => void
  onChange: (source: string) => void
  onCursor: (line: number) => void
}

export function CodeEditor({
  source,
  keywords,
  stdlib,
  fontSize,
  indentSize,
  theme,
  jump,
  breakpoints,
  currentLine,
  onToggleBreakpoint,
  onChange,
  onCursor,
}: Props) {
  const locale = useLocale()
  const host = useRef<HTMLDivElement>(null)
  const viewRef = useRef<EditorView | null>(null)
  const applying = useRef(false)
  const onChangeRef = useRef(onChange)
  const onCursorRef = useRef(onCursor)
  const localeRef = useRef(locale)
  const storedRef = useRef(source)
  const fromUser = useRef(false)
  onChangeRef.current = onChange
  onCursorRef.current = onCursor
  localeRef.current = locale
  storedRef.current = source
  toggleBreakpoint.current = onToggleBreakpoint

  function publish(text: string, head: number) {
    const next = commitSource(localeRef.current, storedRef.current, text, head)
    if (next === storedRef.current) return
    fromUser.current = true
    onChangeRef.current(next)
  }

  function reportCursor(update: { state: EditorState; selectionSet: boolean; docChanged: boolean }) {
    if (!update.selectionSet && !update.docChanged) return
    onCursorRef.current(update.state.doc.lineAt(update.state.selection.main.head).number)
  }

  useEffect(() => {
    if (!host.current) return
    const view = new EditorView({
      parent: host.current,
      state: EditorState.create({
        doc: presentSource(localeRef.current, storedRef.current),
        extensions: [
          tabIndent,
          basicSetup,
          debugExtensions,
          EditorView.updateListener.of((update) => {
            if (update.docChanged && !applying.current) {
              publish(update.state.doc.toString(), update.state.selection.main.head)
            }
            reportCursor(update)
          }),
        ],
      }),
    })
    viewRef.current = view
    return () => {
      view.destroy()
      viewRef.current = null
    }
  }, [])

  useEffect(() => {
    const view = viewRef.current
    if (!view) return
    const reserved = keywordSet([...keywords, ...stdlib])
    const themeExtension = EditorView.theme(
      {
        "&": {
          fontSize: `${fontSize}px`,
          background: theme === "dark" ? "#171a21" : "#ffffff",
          color: theme === "dark" ? "#f2f4f8" : "#16181d",
        },
        ".cm-gutters": {
          background: theme === "dark" ? "#141820" : "#f7f8fb",
          color: theme === "dark" ? "#a1a8b5" : "#667085",
          border: "none",
        },
        ".cm-activeLine": {
          backgroundColor: theme === "dark" ? "rgba(129, 140, 248, 0.1)" : "rgba(79, 70, 229, 0.08)",
        },
      },
      { dark: theme === "dark" },
    )
    view.dispatch({
      effects: StateEffect.reconfigure.of([
        tabIndent,
        basicSetup,
        syntaxHighlighting(trazaHighlight),
        trazaLanguage(reserved),
        autocompletion({
          activateOnTyping: true,
          selectOnOpen: false,
          override: [completeFromList([...keywords, ...stdlib].map((label) => ({ label, type: "keyword" })))],
        }),
        indentUnit.of(" ".repeat(indentSize)),
        themeExtension,
        debugExtensions,
        EditorView.updateListener.of((update) => {
          if (update.docChanged && !applying.current) {
            publish(update.state.doc.toString(), update.state.selection.main.head)
          }
          reportCursor(update)
        }),
      ]),
    })
  }, [keywords, stdlib, fontSize, indentSize, theme])

  useEffect(() => {
    const view = viewRef.current
    if (!view) return
    if (fromUser.current) {
      fromUser.current = false
      return
    }
    const shown = presentSource(locale, source)
    const current = view.state.doc.toString()
    if (current === shown) return
    const head = view.state.selection.main.head
    applying.current = true
    view.dispatch({
      changes: { from: 0, to: current.length, insert: shown },
      selection: { anchor: mapCaret(current, shown, head) },
    })
    applying.current = false
  }, [source, locale])

  useEffect(() => {
    const view = viewRef.current
    if (!view || !jump) return
    const lineNumber = Math.min(Math.max(jump.line, 1), view.state.doc.lines)
    const line = view.state.doc.line(lineNumber)
    view.dispatch({
      selection: { anchor: line.from },
      scrollIntoView: true,
    })
    view.focus()
  }, [jump])

  useEffect(() => {
    const view = viewRef.current
    if (!view) return
    view.dispatch({ effects: setBreakpoints.of(breakpoints) })
  }, [breakpoints])

  useEffect(() => {
    const view = viewRef.current
    if (!view) return
    const effects: StateEffect<unknown>[] = [setDebugLine.of(currentLine)]
    if (currentLine != null) {
      const lineNo = Math.min(Math.max(currentLine, 1), view.state.doc.lines)
      effects.push(EditorView.scrollIntoView(view.state.doc.line(lineNo).from))
    }
    view.dispatch({ effects })
  }, [currentLine])

  return <div className="editor-host" ref={host} />
}
