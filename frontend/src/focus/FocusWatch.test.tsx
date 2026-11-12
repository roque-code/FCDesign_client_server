// @vitest-environment jsdom
import { act } from "react"
import { createRoot, type Root } from "react-dom/client"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import type { FocusEvent } from "../api"
import { useFocusWatch } from "./FocusWatch"

type Sent = [FocusEvent, string | undefined]

function Probe({ send }: { send: (event: FocusEvent, reason?: "hidden" | "blur") => void }) {
  useFocusWatch(true, send)
  return null
}

let root: Root
let host: HTMLElement
let hidden = false
let focused = true
let full: Element | null = null
const sent: Sent[] = []

function settle() {
  act(() => {
    vi.advanceTimersByTime(450)
  })
}

beforeEach(() => {
  ;(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true
  vi.useFakeTimers()
  hidden = false
  focused = true
  full = null
  sent.length = 0
  Object.defineProperty(document, "visibilityState", { configurable: true, get: () => (hidden ? "hidden" : "visible") })
  Object.defineProperty(document, "fullscreenElement", { configurable: true, get: () => full })
  document.hasFocus = () => focused
  host = document.createElement("div")
  document.body.append(host)
  root = createRoot(host)
  act(() => {
    root.render(<Probe send={(event, reason) => sent.push([event, reason])} />)
  })
})

afterEach(() => {
  act(() => root.unmount())
  host.remove()
  vi.useRealTimers()
})

describe("useFocusWatch", () => {
  it("cuenta una salida al cambiar de pestaña y el regreso al volver", () => {
    hidden = true
    focused = false
    document.dispatchEvent(new Event("visibilitychange"))
    window.dispatchEvent(new Event("blur"))
    settle()
    expect(sent).toEqual([["leave", "hidden"]])
    hidden = false
    focused = true
    document.dispatchEvent(new Event("visibilitychange"))
    window.dispatchEvent(new Event("focus"))
    settle()
    expect(sent).toEqual([["leave", "hidden"], ["back", undefined]])
  })

  it("cuenta otra aplicación como salida por foco", () => {
    focused = false
    window.dispatchEvent(new Event("blur"))
    settle()
    expect(sent).toEqual([["leave", "blur"]])
  })

  it("no cuenta un diálogo que devuelve el foco enseguida", () => {
    focused = false
    window.dispatchEvent(new Event("blur"))
    focused = true
    window.dispatchEvent(new Event("focus"))
    settle()
    expect(sent).toEqual([])
  })

  it("registra los intentos de pegar y la salida de pantalla completa", () => {
    act(() => {
      window.dispatchEvent(new Event("paste"))
      full = document.body
      document.dispatchEvent(new Event("fullscreenchange"))
      full = null
      document.dispatchEvent(new Event("fullscreenchange"))
    })
    expect(sent).toEqual([["paste", undefined], ["fullscreen", undefined]])
  })
})
