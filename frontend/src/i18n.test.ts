import { expect, test } from "vitest"

import { translate } from "./i18n"

test("el inglés y el español cubren la configuración", () => {
  expect(translate("es", "language")).toBe("Idioma")
  expect(translate("en", "language")).toBe("Language")
  expect(translate("en", "settingsNote")).toContain("already wrote")
  expect(translate("es", "deleteConfirm", { name: "Hola" })).toBe("¿Eliminar «Hola»?")
  expect(translate("en", "version", { number: 3 })).toBe("Version 3")
})
