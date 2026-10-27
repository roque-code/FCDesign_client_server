import type { Account } from "./api"

/** El docente cierra el pegado en el editor de código y en el del reto. */
export function pasteBlockedFor(account: Pick<Account, "role" | "paste_enabled" | "access">): boolean {
  if (account.access.features.paste !== true) return true
  return account.role !== "teacher" && account.paste_enabled === false
}

export function refusePaste(event: { preventDefault: () => void }): void {
  event.preventDefault()
}

/** Una tecla, un salto o la sangría. Un bloque pegado o escrito en el inspector trae más letras. */
export function handTyped(inserted: string): boolean {
  let letters = 0
  for (const char of inserted) {
    if (!/\s/u.test(char)) letters += 1
    if (letters > 1) return false
  }
  return true
}

export function blockedInsertAllowed(inserted: string, userEvent: string): boolean {
  if (userEvent.startsWith("undo") || userEvent.startsWith("redo") || userEvent.startsWith("delete")) return true
  if (userEvent.startsWith("input.complete")) return true
  if (userEvent.includes(".compose")) return !inserted.includes("\n") && [...inserted].length <= 8
  return handTyped(inserted)
}

/** Conserva el texto anterior cuando el cambio no cabe en una tecla. */
export function keepTypedText(previous: string, next: string): string {
  let start = 0
  const limit = Math.min(previous.length, next.length)
  while (start < limit && previous.charCodeAt(start) === next.charCodeAt(start)) start += 1
  let endPrev = previous.length
  let endNext = next.length
  while (endPrev > start && endNext > start && previous.charCodeAt(endPrev - 1) === next.charCodeAt(endNext - 1)) {
    endPrev -= 1
    endNext -= 1
  }
  return handTyped(next.slice(start, endNext)) ? next : previous
}
