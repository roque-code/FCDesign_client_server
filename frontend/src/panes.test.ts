import { describe, expect, it } from "vitest"

import { clamp, readLayout, writeLayout } from "./panes"

const DEFAULTS = { programs: 256, output: 144, open: true }

function memory(initial: string | null = null) {
  let value = initial
  return {
    getItem: () => value,
    setItem: (_key: string, next: string) => {
      value = next
    },
  }
}

describe("tamaño y estado de los paneles", () => {
  it("limita el tamaño entre el mínimo y el máximo", () => {
    expect(clamp(50, 168, 500)).toBe(168)
    expect(clamp(900, 168, 500)).toBe(500)
    expect(clamp(300.4, 168, 500)).toBe(300)
    expect(clamp(300, 168, 100)).toBe(168)
  })

  it("recuerda tamaños y paneles plegados", () => {
    const store = memory()
    expect(readLayout(store, "k", DEFAULTS)).toEqual(DEFAULTS)
    writeLayout(store, "k", { ...DEFAULTS, output: 212.6, open: false })
    expect(readLayout(store, "k", DEFAULTS)).toEqual({ programs: 256, output: 213, open: false })
  })

  it("descarta valores dañados o de otro tipo", () => {
    expect(readLayout(memory('{"programs":-3,"output":"x","open":1,"ajeno":5}'), "k", DEFAULTS)).toEqual(DEFAULTS)
    expect(readLayout(memory('{"output":200}'), "k", DEFAULTS)).toEqual({ ...DEFAULTS, output: 200 })
    expect(readLayout(memory("{roto"), "k", DEFAULTS)).toEqual(DEFAULTS)
    expect(readLayout(null, "k", DEFAULTS)).toEqual(DEFAULTS)
  })
})
