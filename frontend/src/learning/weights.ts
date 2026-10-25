export const WEIGHT_KEYS = ["comprension", "diseno", "correccion", "lenguaje", "explicacion", "autonomia"] as const

export type WeightKey = (typeof WEIGHT_KEYS)[number]

export type LabWeights = Record<WeightKey, number>

export function defaultWeights(activity: string): LabWeights {
  if (activity === "build") {
    return { comprension: 15, diseno: 20, correccion: 20, lenguaje: 20, explicacion: 15, autonomia: 10 }
  }
  return { comprension: 20, diseno: 25, correccion: 30, lenguaje: 0, explicacion: 15, autonomia: 10 }
}

export function parseWeights(raw: unknown, activity: string): LabWeights {
  const fallback = defaultWeights(activity)
  if (!raw || typeof raw !== "object") return fallback
  const source = raw as Record<string, unknown>
  const next = { ...fallback }
  for (const key of WEIGHT_KEYS) {
    const value = source[key]
    if (typeof value === "number" && Number.isInteger(value) && value >= 0 && value <= 100) {
      next[key] = value
    }
  }
  if (activity !== "build") next.lenguaje = 0
  return next
}

export function weightTotal(weights: LabWeights): number {
  return WEIGHT_KEYS.reduce((sum, key) => sum + weights[key], 0)
}
