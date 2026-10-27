import { indentWithTab } from "@codemirror/commands"
import { indentUnit } from "@codemirror/language"
import { EditorState, Prec } from "@codemirror/state"
import { EditorView, keymap } from "@codemirror/view"
import { basicSetup } from "codemirror"
import { useEffect, useRef } from "react"

import { blockBulkPaste } from "../editor/pasteGuard"
import type { ForeignLanguage } from "./keywords"
import { foreignSupport } from "./support"

const tabIndent = Prec.highest(keymap.of([indentWithTab]))

export function ForeignEditor({
  language,
  source,
  onChange,
  pasteBlocked = false,
}: {
  language: ForeignLanguage
  source: string
  onChange: (source: string) => void
  pasteBlocked?: boolean
}) {
  const host = useRef<HTMLDivElement>(null)
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
          ...blockBulkPaste(() => blockedRef.current),
          EditorView.updateListener.of((update) => {
            if (update.docChanged) onChangeRef.current(update.state.doc.toString())
          }),
        ],
      }),
    })
    return () => view.destroy()
  }, [language])

  return <div ref={host} className="foreign-editor" data-language={language} data-paste-blocked={pasteBlocked ? "true" : undefined} />
}
