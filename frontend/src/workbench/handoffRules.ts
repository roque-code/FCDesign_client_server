import type { LabPathChallenge, LabSession } from "../api"

export type HandoffBlock = "analysis" | "noCode" | "built" | null

export function handoffTargets(challenges: LabPathChallenge[]): LabPathChallenge[] {
  return challenges.filter((item) => item.activity_type === "build" && item.state === "available")
}

export function handoffBlock(session: LabSession): HandoffBlock {
  const { challenge, attempt } = session
  const tools = challenge.task.tools?.length ? challenge.task.tools : ["bloques"]
  if (!tools.includes("codigo")) return "noCode"
  if (attempt.next_stage === "comprender" || attempt.next_stage === "razonar") return "analysis"
  if (attempt.next_stage !== "construir" && attempt.next_stage !== "comprobar") return "built"
  return null
}

export type HandoffResult =
  | { kind: "passed" }
  | { kind: "cases"; done: number; total: number }
  | { kind: "error"; message: string }
  | { kind: "mismatch" }

export function handoffResult(result: LabSession): HandoffResult {
  const rows = result.cases ?? []
  const done = rows.filter((item) => item.passed).length
  if (rows.length > 0 && done === rows.length && result.passed !== false) return { kind: "passed" }
  if (rows.length === 0 && result.passed === true) return { kind: "passed" }
  const error = (result.diagnostics ?? []).find((item) => item.severity === "error")
  if (error) return { kind: "error", message: error.message }
  if (rows.length > 0) return { kind: "cases", done, total: rows.length }
  return { kind: "mismatch" }
}
