import { api } from "../api"
import { installedLocal, localForeignRun } from "../runtime"

/** Corre cada caso en esta máquina y devuelve la salida que hay que comparar. */
export async function runLanguageCases(
  language: string,
  source: string,
  cases: { inputs: string[] }[],
): Promise<string[]> {
  if (installedLocal()) await api.consumeExecution()
  const outputs: string[] = []
  for (const item of cases) {
    const stdin = item.inputs.length > 0 ? `${item.inputs.join("\n")}\n` : ""
    const ran = await localForeignRun(language, source, stdin)
    const stdout = ran.stdout ?? ""
    const stderr = ran.stderr ?? ""
    const message = ran.message ?? ""
    outputs.push(ran.status === "ok" ? stdout : stderr || stdout || message)
  }
  return outputs
}
