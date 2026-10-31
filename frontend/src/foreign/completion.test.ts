import { CompletionContext, type CompletionResult } from "@codemirror/autocomplete"
import { EditorState } from "@codemirror/state"
import { expect, test } from "vitest"

import { completionOf, declaredTable, foreignCompletion, insideTextOrComment } from "./completion"
import { catalogFor } from "./catalog"
import { FOREIGN_LANGUAGES, type ForeignLanguage } from "./keywords"

function offered(language: ForeignLanguage, text: string, explicit = false): string[] {
  const cursor = text.indexOf("|")
  const doc = text.replace("|", "")
  const state = EditorState.create({ doc })
  const result = foreignCompletion(language)(new CompletionContext(state, cursor, explicit)) as CompletionResult | null
  return result ? result.options.map((item) => item.label) : []
}

test("Python: después del punto salen los métodos del texto que leyó input", () => {
  const labels = offered("python", "nombre = input()\nnombre.|")
  expect(labels).toContain("upper")
  expect(labels).toContain("split")
  expect(labels).not.toContain("append")
})

test("Python: una lista ofrece append y el módulo math sus funciones", () => {
  expect(offered("python", "datos = []\ndatos.|")).toContain("append")
  expect(offered("python", "import math\nmath.|")).toContain("sqrt")
  expect(offered("python", "partes = input().split()\npartes.|")).toContain("sort")
})

test("Java: System.out y el Scanner muestran sus métodos", () => {
  expect(offered("java", "System.out.|")).toEqual(expect.arrayContaining(["println", "print", "printf"]))
  const source = "Scanner sc = new Scanner(System.in);\nString linea = sc.nextLine();\nsc.|"
  expect(offered("java", source)).toContain("nextInt")
  expect(offered("java", "String linea = sc.nextLine();\nlinea.|")).toContain("charAt")
  expect(offered("java", "int[] datos = new int[5];\ndatos.|")).toEqual(["length"])
})

test("C#: Console y la línea leída", () => {
  expect(offered("csharp", "Console.|")).toContain("WriteLine")
  expect(offered("csharp", "var linea = Console.ReadLine();\nlinea.|")).toContain("Trim")
  expect(offered("csharp", "List<int> numeros = new List<int>();\nnumeros.|")).toContain("Add")
  expect(offered("csharp", "var datos = new int[5];\ndatos.|")).toEqual(["Length"])
})

test("C++: std:: y los métodos de vector y string", () => {
  expect(offered("cpp", "std::|")).toEqual(expect.arrayContaining(["cout", "vector", "getline"]))
  expect(offered("cpp", "std::vector<int> v;\nv.|")).toContain("push_back")
  expect(offered("cpp", "std::string s;\ns.|")).toContain("substr")
  expect(offered("cpp", "using namespace std;\nint main() { co|", true)).toContain("cout")
})

test("JavaScript: console, Math y un arreglo", () => {
  expect(offered("javascript", "console.|")).toContain("log")
  expect(offered("javascript", "Math.|")).toContain("sqrt")
  expect(offered("javascript", "const nombres = [];\nnombres.|")).toContain("push")
  expect(offered("typescript", "let texto: string = \"\";\ntexto.|")).toContain("toUpperCase")
})

test("C sugiere funciones de la biblioteca con su encabezado", () => {
  const labels = offered("c", "int main() { pri|")
  expect(labels).toContain("printf")
  const printf = catalogFor("c").globals.find((item) => item.name === "printf")
  expect(printf?.sig).toContain("<stdio.h>")
})

test("al escribir una palabra salen las del lenguaje, sus funciones y los nombres del programa", () => {
  const labels = offered("python", "contador = 0\npr|")
  expect(labels).toContain("print")
  expect(labels).toContain("while")
  expect(labels).toContain("contador")
})

test("un punto sin tipo conocido no inventa métodos", () => {
  expect(offered("python", "algo.|")).toEqual([])
  expect(offered("java", "objeto.|")).toEqual([])
  expect(offered("python", "x = 3.|")).toEqual([])
})

test("no sugiere dentro de un texto ni de un comentario", () => {
  expect(offered("python", 'print("pri|")')).toEqual([])
  expect(offered("java", "// System.out.|")).toEqual([])
  expect(insideTextOrComment('x = "abc"', 9, "python")).toBe(false)
  expect(insideTextOrComment('x = "ab', 7, "python")).toBe(true)
  expect(insideTextOrComment("x = 1 # nota", 12, "python")).toBe(true)
})

test("los lenguajes no se mezclan", () => {
  expect(offered("python", "Sys|", true)).not.toContain("System")
  expect(offered("java", "pri|", true)).not.toContain("print")
  expect(declaredTable("s", "java", "String s = \"\";")).toBe("String")
  expect(declaredTable("s", "csharp", "string s = \"\";")).toBe("String")
})

test("una función con datos deja el cursor entre paréntesis; sin datos los cierra", () => {
  const sqrt = catalogFor("python").members.math.find((item) => item.name === "sqrt")!
  const nextLine = catalogFor("java").members.Scanner.find((item) => item.name === "nextLine")!
  expect(typeof completionOf(sqrt).apply).toBe("function")
  expect(completionOf(nextLine).apply).toBe("nextLine()")
})

test("cada entrada del catálogo tiene firma y explicación", () => {
  for (const language of FOREIGN_LANGUAGES) {
    const catalog = catalogFor(language)
    const entries = [...catalog.globals, ...Object.values(catalog.members).flat()]
    for (const entry of entries) {
      expect(entry.sig.length, `${language} ${entry.name}`).toBeGreaterThan(0)
      expect(entry.doc.length, `${language} ${entry.name}`).toBeGreaterThan(0)
      if (entry.returns) expect(catalog.members[entry.returns], `${language} ${entry.name}`).toBeDefined()
    }
    for (const table of Object.values(catalog.receivers)) expect(catalog.members[table], `${language} ${table}`).toBeDefined()
  }
})
