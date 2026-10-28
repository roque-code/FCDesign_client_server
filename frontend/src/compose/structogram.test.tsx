import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { createStep, emptyProgram, guessingGame, insertStep, type Program } from "./model"
import { Structogram } from "./Structogram"

const quiet = {
  selected: null,
  armed: null,
  preview: true,
  dragging: false,
  hot: null,
  hint: () => "",
  onSelect: () => undefined,
  onHot: () => undefined,
  onPlace: () => undefined,
  onDragPiece: () => undefined,
  onDragDone: () => undefined,
}

function markup(program: Program, locale: "es" | "en" = "es"): string {
  return renderToStaticMarkup(<Structogram program={program} locale={locale} {...quiet} />)
}

describe("diagrama Nassi-Shneiderman", () => {
  it("dibuja lectura, escritura, si y mientras del ejemplo", () => {
    const html = markup(guessingGame())
    expect(html).toContain("ns-kind-escribir")
    expect(html).toContain("ns-kind-leer")
    expect(html).toContain("ns-kind-mientras")
    expect(html).toContain("ns-kind-si")
    expect(html).toContain("Mientras")
    expect(html).toContain(">Si<")
    expect(html).toContain(">No<")
  })

  it("dibuja comentario, hasta que, para y según", () => {
    let program = emptyProgram()
    for (const kind of ["comentario", "repetir", "para", "segun"] as const) {
      program = insertStep(program, { scope: "root", index: program.body.length }, createStep(kind))
    }
    const html = markup(program)
    expect(html).toContain("// nota")
    expect(html).toContain("Hasta que")
    expect(html).toContain("Para")
    expect(html).toContain("Según")
    expect(html).toContain(">1<")
    expect(html).toContain(">Otro<")
    expect(markup(program, "en")).toContain("Until")
    expect(markup(program, "en")).toContain("Switch")
  })
})
