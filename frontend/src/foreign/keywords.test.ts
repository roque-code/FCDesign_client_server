import { expect, test } from "vitest"

import {
  C_KEYWORDS,
  CPP_KEYWORDS,
  CSHARP_KEYWORDS,
  FOREIGN_LANGUAGES,
  JAVA_KEYWORDS,
  JAVASCRIPT_KEYWORDS,
  PYTHON_KEYWORDS,
  TYPESCRIPT_KEYWORDS,
  keywordsFor,
} from "./keywords"
import { kindsOf } from "./scan"

const PSEUDOCODE = ["Algoritmo", "FinAlgoritmo", "Escribir", "Mientras", "Definir", "Procedimiento"]

test("cada lenguaje usa solo su lista", () => {
  expect(keywordsFor("python")).toBe(PYTHON_KEYWORDS)
  expect(keywordsFor("javascript")).toBe(JAVASCRIPT_KEYWORDS)
  expect(keywordsFor("typescript")).toBe(TYPESCRIPT_KEYWORDS)
  expect(keywordsFor("java")).toBe(JAVA_KEYWORDS)
  expect(keywordsFor("c")).toBe(C_KEYWORDS)
  expect(keywordsFor("cpp")).toBe(CPP_KEYWORDS)
  expect(keywordsFor("csharp")).toBe(CSHARP_KEYWORDS)
  expect(FOREIGN_LANGUAGES).toHaveLength(7)
})

test("las palabras no se mezclan entre lenguajes ni con el pseudocódigo", () => {
  const lists = [
    PYTHON_KEYWORDS,
    JAVASCRIPT_KEYWORDS,
    TYPESCRIPT_KEYWORDS,
    JAVA_KEYWORDS,
    C_KEYWORDS,
    CPP_KEYWORDS,
    CSHARP_KEYWORDS,
  ]
  for (const list of lists) {
    for (const word of PSEUDOCODE) expect(list).not.toContain(word)
  }
  expect(PYTHON_KEYWORDS).toContain("elif")
  expect(JAVA_KEYWORDS).not.toContain("elif")
  expect(JAVASCRIPT_KEYWORDS).not.toContain("elif")
  expect(C_KEYWORDS).not.toContain("elif")
  expect(JAVA_KEYWORDS).toContain("strictfp")
  expect(PYTHON_KEYWORDS).not.toContain("strictfp")
  expect(JAVASCRIPT_KEYWORDS).not.toContain("strictfp")
  expect(CSHARP_KEYWORDS).not.toContain("strictfp")
  expect(JAVASCRIPT_KEYWORDS).toContain("typeof")
  expect(PYTHON_KEYWORDS).not.toContain("typeof")
  expect(TYPESCRIPT_KEYWORDS).toContain("keyof")
  expect(JAVASCRIPT_KEYWORDS).not.toContain("keyof")
  expect(C_KEYWORDS).toContain("restrict")
  expect(CPP_KEYWORDS).not.toContain("restrict")
  expect(CPP_KEYWORDS).toContain("constexpr")
  expect(C_KEYWORDS).not.toContain("constexpr")
  expect(CSHARP_KEYWORDS).toContain("stackalloc")
  expect(JAVA_KEYWORDS).not.toContain("stackalloc")
})

test("el resaltado de una línea no toma palabras de otro lenguaje", () => {
  expect(kindsOf("def n", PYTHON_KEYWORDS, true)).toContain("keyword")
  expect(kindsOf("def n", JAVA_KEYWORDS, false)).not.toContain("keyword")
  expect(kindsOf("strictfp final", JAVA_KEYWORDS, false)).toContain("keyword")
  expect(kindsOf("strictfp final", PYTHON_KEYWORDS, true)).not.toContain("keyword")
  expect(kindsOf("# nota", PYTHON_KEYWORDS, true)).toEqual(["comment"])
  expect(kindsOf("#campo", JAVASCRIPT_KEYWORDS, false)).not.toContain("comment")
})
