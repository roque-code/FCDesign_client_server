// @vitest-environment jsdom
import { act } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, describe, expect, it } from "vitest"

import { EDITOR_FONT_SIZE, shareEditorFont, useEditorFont } from "./fontSize"

function Probe() {
  return <p>{useEditorFont()}</p>
}

afterEach(() => {
  act(() => shareEditorFont(EDITOR_FONT_SIZE))
})

describe("tamaño de letra de los editores", () => {
  it("un cambio llega a todos los editores montados y a los campos de código", () => {
    ;(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true
    const host = document.createElement("div")
    const root = createRoot(host)
    act(() => root.render(<><Probe /><Probe /></>))
    expect(host.textContent).toBe("1616")
    act(() => shareEditorFont(22))
    expect(host.textContent).toBe("2222")
    expect(document.documentElement.style.getPropertyValue("--editor-font-size")).toBe("22px")
    act(() => root.unmount())
  })

  it("ignora valores que no son tamaños", () => {
    shareEditorFont(Number.NaN)
    shareEditorFont(0)
    let seen = 0
    function Read() {
      seen = useEditorFont()
      return null
    }
    const root = createRoot(document.createElement("div"))
    act(() => root.render(<Read />))
    expect(seen).toBe(EDITOR_FONT_SIZE)
    act(() => root.unmount())
  })
})
