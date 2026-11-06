import { describe, expect, it } from "vitest"

import type { LabPathChallenge, LabSession } from "../api"
import { handoffBlock, handoffResult, handoffTargets } from "./handoffRules"

function session(tools: string[] | undefined, stage: string, extra: Partial<LabSession> = {}): LabSession {
  return {
    challenge: { activity_type: "build", task: { tools } },
    attempt: { next_stage: stage },
    history: [],
    ...extra,
  } as unknown as LabSession
}

function challenge(activity_type: string, state: LabPathChallenge["state"]): LabPathChallenge {
  return { id: `${activity_type}-${state}`, activity_type, state } as LabPathChallenge
}

describe("pasar el pseudocódigo a un reto", () => {
  it("solo ofrece retos de construir abiertos", () => {
    const listed = handoffTargets([
      challenge("build", "available"),
      challenge("build", "locked"),
      challenge("build", "completed"),
      challenge("predict", "available"),
    ])
    expect(listed.map((item) => item.id)).toEqual(["build-available"])
  })

  it("pide el análisis y que el reto acepte código", () => {
    expect(handoffBlock(session(["codigo", "bloques"], "razonar"))).toBe("analysis")
    expect(handoffBlock(session(["codigo"], "comprender"))).toBe("analysis")
    expect(handoffBlock(session(["bloques"], "construir"))).toBe("noCode")
    expect(handoffBlock(session(undefined, "construir"))).toBe("noCode")
    expect(handoffBlock(session(["codigo"], "explicar"))).toBe("built")
    expect(handoffBlock(session(["codigo"], "construir"))).toBeNull()
    expect(handoffBlock(session(["codigo", "diagrama"], "comprobar"))).toBeNull()
  })

  it("resume la comprobación", () => {
    const row = (passed: boolean) => ({ name: "c", kind: "visible", passed, output: "" })
    expect(handoffResult(session(["codigo"], "lenguaje", { passed: true, cases: [row(true), row(true)] }))).toEqual({ kind: "passed" })
    expect(handoffResult(session(["codigo"], "comprobar", { passed: false, cases: [row(true), row(false)] }))).toEqual({
      kind: "cases",
      done: 1,
      total: 2,
    })
    expect(
      handoffResult(
        session(["codigo"], "comprobar", {
          passed: false,
          cases: [row(true)],
          diagnostics: [{ severity: "error", code: "L0102", message: "Falta un bloque que el reto pide.", line: 1, column: 1 }],
        } as Partial<LabSession>),
      ),
    ).toEqual({ kind: "error", message: "Falta un bloque que el reto pide." })
    expect(handoffResult(session(["codigo"], "comprobar", { passed: true, cases: [] }))).toEqual({ kind: "passed" })
    expect(handoffResult(session(["codigo"], "comprobar", { passed: false, cases: [] }))).toEqual({ kind: "mismatch" })
  })
})
