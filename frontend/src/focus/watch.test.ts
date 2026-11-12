import { describe, expect, it } from "vitest"

import { awayClock, exitsLeft } from "./watch"

const report = {
  limit: 3,
  exits: 1,
  away_seconds: 160,
  fullscreen_exits: 0,
  pastes: 0,
  away_now: false,
  auto_submitted: false,
}

describe("vigilancia de salidas", () => {
  it("escribe el tiempo fuera en minutos y segundos", () => {
    expect(awayClock(160)).toBe("2 min 40 s")
    expect(awayClock(45)).toBe("45 s")
    expect(awayClock(-3)).toBe("0 s")
  })

  it("cuenta las salidas que quedan antes de entregar", () => {
    expect(exitsLeft(report)).toBe(2)
    expect(exitsLeft({ ...report, exits: 5 })).toBe(0)
    expect(exitsLeft({ ...report, limit: null })).toBeNull()
  })
})
