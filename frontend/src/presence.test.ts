import { describe, expect, it } from "vitest"

import { personAway } from "./api"

describe("uso de la sesión", () => {
  const now = 10 * 60_000

  it("cuenta como uso si la persona tocó la página hace poco", () => {
    expect(personAway(now, now - 30_000, false)).toBe(false)
  })

  it("una pestaña sin tocar o escondida solo avisa que sigue abierta", () => {
    expect(personAway(now, now - 6 * 60_000, false)).toBe(true)
    expect(personAway(now, 0, false)).toBe(true)
    expect(personAway(now, now - 1_000, true)).toBe(true)
  })
})
