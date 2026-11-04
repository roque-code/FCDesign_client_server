import { describe, expect, it } from "vitest"

import { isReloadKey } from "./ReloadGuard"

const key = (value: string, mods: Partial<{ ctrlKey: boolean; metaKey: boolean; altKey: boolean }> = {}) => ({
  key: value,
  ctrlKey: false,
  metaKey: false,
  altKey: false,
  ...mods,
})

describe("aviso al recargar", () => {
  it("reconoce F5, Ctrl+R y Cmd+R", () => {
    expect(isReloadKey(key("F5"))).toBe(true)
    expect(isReloadKey(key("F5", { ctrlKey: true }))).toBe(true)
    expect(isReloadKey(key("r", { ctrlKey: true }))).toBe(true)
    expect(isReloadKey(key("R", { metaKey: true }))).toBe(true)
  })

  it("deja escribir la letra r y otros atajos", () => {
    expect(isReloadKey(key("r"))).toBe(false)
    expect(isReloadKey(key("R"))).toBe(false)
    expect(isReloadKey(key("r", { ctrlKey: true, altKey: true }))).toBe(false)
    expect(isReloadKey(key("s", { metaKey: true }))).toBe(false)
  })
})
