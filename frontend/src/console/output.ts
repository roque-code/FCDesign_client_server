export type ConsolePayload = {
  output?: string
  text?: string
  output_reset?: boolean
}

export function applyConsoleOutput(current: string, eventName: string, data: ConsolePayload): string {
  if (data.output_reset) return data.text ?? ""
  if (eventName === "output" && typeof data.text === "string") return current + data.text
  if (typeof data.output === "string") return data.output
  return current
}
