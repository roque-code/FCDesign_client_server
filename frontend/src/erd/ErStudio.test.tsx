import { renderToStaticMarkup } from "react-dom/server"
import { afterEach, describe, expect, it, vi } from "vitest"

import type { Account } from "../api"
import { LocaleProvider } from "../i18n"
import { LeaveSubjectProvider } from "../subjects/leave"
import { ErCanvas } from "./ErCanvas"
import { ErStudio } from "./ErStudio"
import { accidentExample } from "./example"

function account(): Account {
  return {
    id: 7,
    email: "ana@example.com",
    display_name: "Ana Ruiz",
    institution: "",
    role: "student",
    points: 12,
    rank: 4,
    translation_enabled: true,
    paste_enabled: true,
    avatar: null,
    plan: {
      code: "gratis",
      name: "Gratis",
      audience: "student",
      price_cents: 0,
      currency: "MXN",
      period_days: 30,
      status: "active",
      paid_until: null,
      days_remaining: 9,
    },
    access: {
      browser_app: true,
      features: {},
      limits: { max_projects: null, max_algorithms: null, max_executions_per_day: 3 },
    },
    usage: { projects: 1, algorithms: 2, executions_today: 0 },
  }
}

describe("materia de bases de datos", () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("deja el lienzo al centro y las figuras de Chen a la derecha, sin el editor de código", () => {
    vi.stubGlobal("localStorage", { getItem: () => null, setItem: () => undefined, removeItem: () => undefined })
    const html = renderToStaticMarkup(
      <LocaleProvider locale="es">
        <LeaveSubjectProvider leave={() => undefined}>
          <ErStudio account={account()} onAccount={() => undefined} />
        </LeaveSubjectProvider>
      </LocaleProvider>,
    )
    expect(html).toContain("erd-canvas")
    expect(html).toContain("Editor entidad-relación")
    expect(html).toContain("Entidad débil")
    expect(html).toContain("Relación identificadora")
    expect(html).toContain("Atributo multivaluado")
    expect(html).toContain("Atributo derivado")
    expect(html).toContain(">ISA<")
    expect(html).toContain("Muchos a muchos")
    expect(html).toContain("Muchos a uno")
    expect(html).toContain("Uno a uno")
    expect(html).toContain("Participación total")
    expect(html).toContain("mín..máx")
    expect(html).toContain("Nuevo proyecto")
    expect(html).toContain("Suelta aquí las figuras")
    expect(html).toContain(">Materias<")
    expect(html).not.toContain("Pseudocódigo")
    expect(html).not.toContain("Ejecutar")
    expect(html).not.toContain("Nassi")
  })

  it("dibuja el ejemplo con cardinalidad y flecha, sin las etiquetas N:M", () => {
    const diagram = accidentExample()
    const html = renderToStaticMarkup(
      <ErCanvas
        nodes={diagram.nodes}
        edges={diagram.edges}
        view={{ x: -40, y: -40, w: 1400, h: 800 }}
        selectedId={null}
        pendingId={null}
        cursor={null}
        emptyLabel=""
        canvasLabel="Editor entidad-relación"
        disjointLabel="disjunta"
        deleteLineLabel="Borrar línea"
        onBackgroundPointerDown={() => undefined}
        onNodePointerDown={() => undefined}
        onNodeDoubleClick={() => undefined}
        onEdgePointerDown={() => undefined}
        onDeleteEdge={() => undefined}
      />,
    )
    expect(html).toContain("PERSONA")
    expect(html).toContain("VEHICULO")
    expect(html).toContain("ACCIDENTE")
    expect(html).toContain("MULTA")
    expect(html).toContain("1..n")
    expect(html).toContain("1..1")
    expect(html).toContain("0..n")
    expect(html).toContain("erd-arrow")
    expect(html).not.toContain("N:M")
    expect(html).not.toContain("1:M")
    const selected = renderToStaticMarkup(
      <ErCanvas
        nodes={diagram.nodes}
        edges={diagram.edges}
        view={{ x: -40, y: -40, w: 1400, h: 800 }}
        selectedId={diagram.edges[0].id}
        pendingId={null}
        cursor={null}
        emptyLabel=""
        canvasLabel="Editor entidad-relación"
        disjointLabel="disjunta"
        deleteLineLabel="Borrar línea"
        onBackgroundPointerDown={() => undefined}
        onNodePointerDown={() => undefined}
        onNodeDoubleClick={() => undefined}
        onEdgePointerDown={() => undefined}
        onDeleteEdge={() => undefined}
      />,
    )
    expect(selected).toContain("erd-line-delete")
    expect(selected).toContain("Borrar línea")
  })
})
