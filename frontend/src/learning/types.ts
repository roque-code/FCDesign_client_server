/** Tipos de conexión del laboratorio. El menú limita el encaje; el tipo real lo fija Definir. */

export const TRAZA_TYPES = ["entero", "real", "logico", "caracter", "cadena"] as const

export type TrazaType = (typeof TRAZA_TYPES)[number]

export const TYPE_LABELS: readonly (readonly [string, TrazaType])[] = [
  ["Entero", "entero"],
  ["Real", "real"],
  ["Lógico", "logico"],
  ["Caracter", "caracter"],
  ["Cadena", "cadena"],
]

const EXPRESION = "Expresion"
const NUMERO = "Numero"

export function isTrazaType(value: string): value is TrazaType {
  return (TRAZA_TYPES as readonly string[]).includes(value)
}

/** Un valor cabe en una entrada si comparten al menos una marca. */
export function outputChecks(type: TrazaType): string[] {
  switch (type) {
    case "entero":
      return [EXPRESION, NUMERO, "Entero"]
    case "real":
      return [EXPRESION, NUMERO, "Real"]
    case "cadena":
      return [EXPRESION, "Cadena"]
    case "caracter":
      return [EXPRESION, "Caracter"]
    case "logico":
      return [EXPRESION, "Logico"]
  }
}

export const CHECK = {
  expresion: EXPRESION,
  numero: NUMERO,
  cadena: "Cadena",
  logico: "Logico",
} as const
