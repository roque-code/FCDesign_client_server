import { Annotation, EditorState, Transaction, type Extension } from "@codemirror/state"
import { EditorView } from "@codemirror/view"

import { blockedInsertAllowed, handTyped } from "../paste"

/** El programa carga el fuente guardado. El inspector y la consola no llevan esta marca. */
export const trustedEdit = Annotation.define<true>()

export function blockBulkPaste(blocked: boolean | (() => boolean)): Extension[] {
  const closed = () => (typeof blocked === "function" ? blocked() : blocked)
  return [
    EditorState.transactionFilter.of((transaction) => {
      if (!closed() || !transaction.docChanged || transaction.annotation(trustedEdit)) return transaction
      let inserted = ""
      transaction.changes.iterChanges((_fromA, _toA, _fromB, _toB, text) => {
        inserted += text.toString()
      })
      const userEvent = transaction.annotation(Transaction.userEvent) ?? ""
      return blockedInsertAllowed(inserted, userEvent) ? transaction : []
    }),
    EditorView.inputHandler.of((_view, _from, _to, text) => closed() && !handTyped(text)),
    EditorView.domEventHandlers({
      paste(event) {
        if (!closed()) return false
        event.preventDefault()
        return true
      },
      drop(event) {
        if (!closed()) return false
        event.preventDefault()
        return true
      },
    }),
  ]
}
