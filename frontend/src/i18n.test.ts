import { expect, test } from "vitest"

import { knownText, translate } from "./i18n"

test("el inglés y el español cubren la configuración", () => {
  expect(translate("es", "language")).toBe("Idioma")
  expect(translate("en", "language")).toBe("Language")
  expect(translate("en", "settingsNote")).toContain("already wrote")
  expect(translate("es", "deleteConfirm", { name: "Hola" })).toBe("¿Eliminar «Hola»?")
  expect(translate("en", "version", { number: 3 })).toBe("Version 3")
  expect(knownText("en", "Tu docente desactivó la traducción de código.")).toBe(
    "Your teacher turned off code translation.",
  )
  expect(knownText("en", "El archivo admite hasta 200 retos.")).toBe("The file allows up to 200 challenges.")
  expect(knownText("es", "Falta titulo.")).toBe("Falta titulo.")
})
