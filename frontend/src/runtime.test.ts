import { expect, test } from "vitest"

import { attemptCheckPath } from "./api"
import { editorEventUrl, labEventUrl, searchFromLaunch } from "./runtime"

const local = { origin: "http://127.0.0.1:9", token: "secreto" }

test("en el navegador el depurador sigue en /api/v1/", () => {
  expect(editorEventUrl("abc", null)).toBe("/api/v1/executions/abc/events/")
  expect(labEventUrl("abc", null)).toBe("/api/v1/learning/runs/abc/events/")
})

test("en la aplicación instalada el depurador va al proceso local", () => {
  const editor = editorEventUrl("abc", local)
  const lab = labEventUrl("abc", local)
  expect(editor.startsWith("http://127.0.0.1:9/local/v1/sessions/abc/events/")).toBe(true)
  expect(lab.startsWith("http://127.0.0.1:9/local/v1/lab/runs/abc/events/")).toBe(true)
  expect(new URL(editor).searchParams.get("token")).toBe("secreto")
})

test("la entrega de un reto no sale del servidor", () => {
  expect(attemptCheckPath("intento")).toBe("/api/v1/learning/attempts/intento/check/")
  expect(attemptCheckPath("intento").includes("/local/")).toBe(false)
})

test("el enlace de la aplicación conserva la misma consulta que la web", () => {
  expect(searchFromLaunch("", "traza://open/?confirmar=abc&token=xyz")).toBe("?confirmar=abc&token=xyz")
  expect(searchFromLaunch("?confirmar=web&token=1", "traza://open/?confirmar=app&token=2")).toBe(
    "?confirmar=web&token=1",
  )
})
