import { describe, expect, it } from "vitest"

import { DEFAULT_PANES, clamp, readPanes, writePanes } from "./panes"

function memory(initial: string | null = null) {
  let value = initial
  return {
    getItem: () => value,
    setItem: (_key: string, next: string) => {
      value = next
    },
  }
}

describe("paneles de Lenguajes", () => {
  it("limita el tamaño entre el mínimo y el máximo", () => {
    expect(clamp(50, 168, 500)).toBe(168)
    expect(clamp(900, 168, 500)).toBe(500)
    expect(clamp(300.4, 168, 500)).toBe(300)
    expect(clamp(300, 168, 100)).toBe(168)
  })

  it("recuerda los tamaños y descarta valores dañados", () => {
    const store = memory()
    expect(readPanes(store)).toEqual(DEFAULT_PANES)
    writePanes(store, { ...DEFAULT_PANES, peek: 412 })
    expect(readPanes(store).peek).toBe(412)
    expect(readPanes(memory('{"programs":-3,"peek":"x","output":200}'))).toEqual({ ...DEFAULT_PANES, output: 200 })
    expect(readPanes(memory("{roto"))).toEqual(DEFAULT_PANES)
    expect(readPanes(null)).toEqual(DEFAULT_PANES)
  })
})
