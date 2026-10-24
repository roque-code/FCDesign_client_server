import { basicSetup } from "codemirror"
import { EditorState } from "@codemirror/state"
import { EditorView } from "@codemirror/view"
import { useEffect, useRef } from "react"

import type { ForeignLanguage } from "./keywords"
import { foreignSupport } from "./support"

export function ForeignEditor({
  language,
  source,
  onChange,
}: {
  language: ForeignLanguage
  source: string
  onChange: (source: string) => void
}) {
  const host = useRef<HTMLDivElement>(null)
  const onChangeRef = useRef(onChange)
  const sourceRef = useRef(source)
  onChangeRef.current = onChange
  sourceRef.current = source

  useEffect(() => {
    const parent = host.current
    if (!parent) return
    const view = new EditorView({
      parent,
      state: EditorState.create({
        doc: sourceRef.current,
        extensions: [
          basicSetup,
          foreignSupport(language),
          EditorView.updateListener.of((update) => {
            if (update.docChanged) onChangeRef.current(update.state.doc.toString())
          }),
        ],
      }),
    })
    return () => view.destroy()
  }, [language])

  return <div ref={host} className="foreign-editor" data-language={language} />
}
