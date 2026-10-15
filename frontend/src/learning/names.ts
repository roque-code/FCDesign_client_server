/** Nombres de variable, con las mismas letras que el lexer y sin palabras del lenguaje. */

import { canonicalize, isIdentContinue, isIdentStart } from "../words"

const RESERVED = new Set([
  "algoritmo",
  "finalgoritmo",
  "funcion",
  "finfuncion",
  "subproceso",
  "finsubproceso",
  "definir",
  "como",
  "dimension",
  "por",
  "valor",
  "referencia",
  "leer",
  "escribir",
  "sin",
  "saltar",
  "borrar",
  "pantalla",
  "esperar",
  "segundos",
  "si",
  "entonces",
  "sino",
  "finsi",
  "segun",
  "hacer",
  "de",
  "otro",
  "modo",
  "finsegun",
  "mientras",
  "finmientras",
  "repetir",
  "hasta",
  "que",
  "para",
  "con",
  "paso",
  "finpara",
  "entero",
  "real",
  "logico",
  "caracter",
  "cadena",
  "verdadero",
  "falso",
  "y",
  "o",
  "no",
  "div",
  "mod",
])

export function normalizeVariableName(value: string): string | null {
  const name = value.trim()
  const chars = [...name]
  if (chars.length === 0 || !isIdentStart(chars[0])) return null
  if (!chars.every((ch, index) => (index === 0 ? isIdentStart(ch) : isIdentContinue(ch)))) return null
  if (RESERVED.has(canonicalize(name))) return null
  return name
}

export function normalizeCharacter(value: string): string | null {
  const text = value.trim()
  if ([...text].length !== 1) return null
  return text
}
