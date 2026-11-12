// @vitest-environment jsdom
import { act } from "react"
import { createRoot, type Root } from "react-dom/client"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import type { FocusReport } from "../api"
import { useExerciseFocus } from "./FocusWatch"

const exerciseFocus = vi.hoisted(() => vi.fn())
vi.mock("../api", () => ({ api: { exerciseFocus } }))

function report(exits: number): FocusReport {
  return { limit: null, exits, away_seconds: 0, fullscreen_exits: 0, pastes: 0, away_now: false, auto_submitted: false }
}

function Probe({ id, enabled }: { id: string; enabled: boolean }) {
  const { report: shown } = useExerciseFocus("program", id, enabled)
  return <p>{shown ? `salidas ${shown.exits}` : "sin vigilancia"}</p>
}

let root: Root
let host: HTMLElement
let focused = true

async function show(id: string, enabled = true) {
  await act(async () => {
    root.render(<Probe id={id} enabled={enabled} />)
  })
}

async function leave() {
  focused = false
  window.dispatchEvent(new Event("blur"))
  await act(async () => {
    vi.advanceTimersByTime(450)
  })
}

beforeEach(() => {
  ;(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true
  vi.useFakeTimers()
  focused = true
  exerciseFocus.mockReset()
  Object.defineProperty(document, "visibilityState", { configurable: true, get: () => "visible" })
  document.hasFocus = () => focused
  host = document.createElement("div")
  document.body.append(host)
  root = createRoot(host)
})

afterEach(() => {
  act(() => root.unmount())
  host.remove()
  vi.useRealTimers()
})

describe("useExerciseFocus", () => {
  it("no escucha nada cuando el servidor dice que el alumno no está vigilado", async () => {
    exerciseFocus.mockResolvedValue({ focus: null })
    await show("p1")
    await leave()
    expect(exerciseFocus.mock.calls).toEqual([["program", "p1", "open"]])
    expect(host.textContent).toBe("sin vigilancia")
  })

  it("abre el ejercicio y registra las salidas en ese ejercicio", async () => {
    exerciseFocus.mockResolvedValueOnce({ focus: report(2) }).mockResolvedValueOnce({ focus: report(3) })
    await show("p1")
    expect(host.textContent).toBe("salidas 2")
    await leave()
    expect(exerciseFocus.mock.calls).toEqual([
      ["program", "p1", "open"],
      ["program", "p1", "leave", "blur"],
    ])
    expect(host.textContent).toBe("salidas 3")
  })

  it("no envía nada mientras el docente revisa", async () => {
    await show("p1", false)
    await leave()
    expect(exerciseFocus).not.toHaveBeenCalled()
  })
})
