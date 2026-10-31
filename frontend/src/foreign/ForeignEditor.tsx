import { acceptCompletion, hasNextSnippetField, hasPrevSnippetField, nextSnippetField, prevSnippetField } from "@codemirror/autocomplete"
import { indentWithTab } from "@codemirror/commands"
import { indentUnit } from "@codemirror/language"
import { EditorState, Prec } from "@codemirror/state"
import { EditorView, keymap } from "@codemirror/view"
import { basicSetup } from "codemirror"
import { useEffect, useRef } from "react"

import { blockBulkPaste, trustedEdit } from "../editor/pasteGuard"
import type { ForeignLanguage } from "./keywords"
import { foreignSupport } from "./support"

const tabIndent = Prec.highest(
  keymap.of([
    {
      key: "Tab",
      run: (view) => {
        if (acceptCompletion(view)) return true
        if (hasNextSnippetField(view.state)) return nextSnippetField(view)
        return Boolean(indentWithTab.run?.(view))
      },
      shift: (view) => {
        if (hasPrevSnippetField(view.state)) return prevSnippetField(view)
        return Boolean(indentWithTab.shift?.(view))
      },
    },
  ]),
)

export function ForeignEditor({
  language,
  source,
  onChange,
  pasteBlocked = false,
  label,
}: {
  language: ForeignLanguage
  source: string
  onChange: (source: string) => void
  pasteBlocked?: boolean
  label?: string
}) {
  const host = useRef<HTMLDivElement>(null)
  const viewRef = useRef<EditorView | null>(null)
  const onChangeRef = useRef(onChange)
  const sourceRef = useRef(source)
  const blockedRef = useRef(pasteBlocked)
  onChangeRef.current = onChange
  sourceRef.current = source
  blockedRef.current = pasteBlocked

  useEffect(() => {
    const parent = host.current
    if (!parent) return
    const view = new EditorView({
      parent,
      state: EditorState.create({
        doc: sourceRef.current,
        extensions: [
          tabIndent,
          basicSetup,
          indentUnit.of("\t"),
          EditorState.tabSize.of(4),
          foreignSupport(language),
          ...(label ? [EditorView.contentAttributes.of({ "aria-label": label })] : []),
          ...blockBulkPaste(() => blockedRef.current),
          EditorView.updateListener.of((update) => {
            if (update.docChanged) onChangeRef.current(update.state.doc.toString())
          }),
        ],
      }),
    })
    viewRef.current = view
    return () => {
      viewRef.current = null
      view.destroy()
    }
  }, [language, label])

  useEffect(() => {
    const view = viewRef.current
    if (!view) return
    const current = view.state.doc.toString()
    if (current === source) return
    view.dispatch({ changes: { from: 0, to: current.length, insert: source }, annotations: trustedEdit.of(true) })
  }, [source])

  return <div ref={host} className="foreign-editor" data-language={language} data-paste-blocked={pasteBlocked ? "true" : undefined} />
}
