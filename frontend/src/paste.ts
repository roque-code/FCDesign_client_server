import type { Account } from "./api"

/** El docente cierra el pegado en el editor de código y en el del reto. */
export function pasteBlockedFor(account: Pick<Account, "role" | "paste_enabled" | "access">): boolean {
  if (account.access.features.paste !== true) return true
  return account.role !== "teacher" && account.paste_enabled === false
}

export function refusePaste(event: { preventDefault: () => void }): void {
  event.preventDefault()
}
