import { expect, test } from "vitest"

import { canonicalKeyword, commitSource, editorKeywords, presentSource, spellText } from "./dialect"

test("english spellings keep strings and names", () => {
  const source = 'Definir base Como Real;\n    Escribir "Si";\n    Si base > 0 Y Verdadero Entonces\n        Escribir base Sin Saltar;\n    FinSi'
  expect(spellText("en", source)).toBe(
    'Declare base As Real;\n    Write "Si";\n    If base > 0 And True Then\n        Write base Without Newline;\n    EndIf',
  )
  expect(spellText("es", source)).toBe(source)
})

test("diagram words and the default arm follow the dialect", () => {
  expect(spellText("en", "Inicio Doblar")).toBe("Start Doblar")
  expect(spellText("en", "Fin Saludar")).toBe("End Saludar")
  expect(spellText("en", "De Otro Modo")).toBe("In Other Case")
  expect(spellText("en", "Borrar Pantalla")).toBe("Clear Screen")
})

test("english words resolve to the spanish canonical", () => {
  expect(canonicalKeyword("algorithm")).toBe("algoritmo")
  expect(canonicalKeyword("if")).toBe("si")
  expect(canonicalKeyword("integer")).toBe("entero")
  expect(canonicalKeyword("real")).toBe("real")
  expect(canonicalKeyword("base")).toBe("base")
})

test("the editor shows the selected dialect and keeps the stored words", () => {
  const stored = 'Algoritmo Demo\n    Definir n Como Entero;\n    Si n > 0 Y Verdadero Entonces\n        Escribir "Si" Sin Saltar;\n    Sino\n        Escribir n DIV 2;\n    FinSi\n    Segun n Hacer\n    FinSegun\nFinAlgoritmo'
  const shown = presentSource("en", stored)
  expect(shown).toContain("Algorithm Demo")
  expect(shown).toContain("Declare n As Integer")
  expect(shown).toContain('Write "Si" Without Newline')
  expect(shown).toContain("Write n Div 2")
  expect(shown).toContain("Switch n Do")
  expect(shown).not.toContain("Algoritmo")
  expect(commitSource("en", stored, shown)).toBe(stored)
  const edited = shown.replace("Demo", "Area")
  expect(commitSource("en", stored, edited)).toBe(stored.replace("Demo", "Area"))
  expect(presentSource("en", commitSource("en", stored, edited))).toBe(edited)

  const english = 'Algorithm Demo\n    Declare n As Integer;\n    Write "Si";\nEndAlgorithm'
  expect(presentSource("es", english)).toBe('Algoritmo Demo\n    Definir n Como Entero;\n    Escribir "Si";\nFinAlgoritmo')
  expect(commitSource("es", english, presentSource("es", english))).toBe(english)
  expect(presentSource("es", stored)).toBe(stored)
})

test("a word still being typed keeps its letters", () => {
  let stored = "Algoritmo Demo\n"
  let shown = presentSource("en", stored)
  for (const word of ["Declare", "decision", "nombre", "Integer"]) {
    let typed = ""
    for (const ch of word) {
      typed += ch
      const draft = `${shown}${ch}`
      const caret = draft.length
      stored = commitSource("en", stored, draft, caret)
      shown = presentSource("en", stored, caret)
      expect(shown.endsWith(typed)).toBe(true)
    }
    const finished = `${shown} `
    stored = commitSource("en", stored, finished, finished.length)
    shown = presentSource("en", stored, finished.length)
  }
  expect(shown).toContain("Declare decision nombre Integer")
  expect(shown).not.toContain("Not")
  expect(shown).not.toContain(" In ")
  expect(stored).toContain("decision nombre")
  expect(stored).not.toContain("Not")
})

test("autocomplete prefers the active dialect and still lists the other", () => {
  const words = editorKeywords("en", ["Algoritmo", "DIV", "Raíz"])
  expect(words[0]).toBe("Algorithm")
  expect(words).toContain("Algoritmo")
  expect(words).toContain("Div")
  expect(words).toContain("Raíz")
  expect(words.filter((word) => word === "DIV" || word === "Div")).toEqual(["Div"])
})
