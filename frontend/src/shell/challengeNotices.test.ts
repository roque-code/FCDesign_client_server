import { describe, expect, it } from "vitest"

import type { LabPath } from "../api"
import { acknowledge, noticeDiff } from "./challengeNotices"

function path(challenges: LabPath["challenges"]): LabPath {
  return { id: "ruta", name: "Juegos", description: "", challenges }
}

function challenge(id: string, state: LabPath["challenges"][number]["state"], withdrawn = false) {
  return {
    id,
    title: id,
    activity_type: "build",
    difficulty: 1,
    points: 10,
    concept: "Ciclo mientras",
    position: 1,
    state,
    withdrawn,
    time_limit_seconds: null,
    attempt_count: 0,
  }
}

describe("avisos de retos", () => {
  it("la primera visita no avisa de los retos que ya estaban", () => {
    const listed = path([challenge("uno", "available"), challenge("dos", "locked")])
    const first = noticeDiff(null, [listed])
    expect(first.notices).toEqual([])
    expect(first.seen.uno).toEqual({ state: "available", withdrawn: false })
  })

  it("avisa de un reto nuevo y de uno que el docente vuelve a habilitar", () => {
    const known = noticeDiff(null, [path([challenge("uno", "available"), challenge("dos", "scheduled")])])
    const added = noticeDiff(known.seen, [
      path([challenge("uno", "available"), challenge("dos", "available"), challenge("tres", "locked")]),
    ])
    expect(added.notices.map((item) => [item.id, item.kind])).toEqual([
      ["dos", "enabled"],
      ["tres", "new"],
    ])
    const again = noticeDiff(added.seen, [
      path([challenge("uno", "available"), challenge("dos", "available"), challenge("tres", "locked")]),
    ])
    expect(again.notices.map((item) => item.id)).toEqual(["dos", "tres"])
  })

  it("un reto que desaparece y regresa cuenta como habilitado", () => {
    const known = noticeDiff(null, [path([challenge("uno", "available")])])
    const gone = noticeDiff(known.seen, [path([])])
    expect(gone.notices).toEqual([])
    expect(gone.seen.uno.withdrawn).toBe(true)
    const back = noticeDiff(gone.seen, [path([challenge("uno", "available")])])
    expect(back.notices.map((item) => item.kind)).toEqual(["enabled"])
  })

  it("marcar como vistos apaga el aviso", () => {
    const known = noticeDiff(null, [path([challenge("uno", "available")])])
    const added = noticeDiff(known.seen, [path([challenge("uno", "available"), challenge("dos", "available")])])
    const cleared = acknowledge([path([challenge("uno", "available"), challenge("dos", "available")])], added.seen)
    expect(noticeDiff(cleared, [path([challenge("uno", "available"), challenge("dos", "available")])]).notices).toEqual([])
  })
})
