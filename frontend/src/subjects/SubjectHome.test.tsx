import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { type Account } from "../api"
import { LocaleProvider } from "../i18n"
import { SUBJECTS, openSubject } from "./catalog"
import { SubjectHome } from "./SubjectHome"

function account(role: Account["role"], communities: boolean): Account {
  return {
    id: 7,
    email: "ana@example.com",
    display_name: "Ana Ruiz",
    institution: "",
    role,
    points: 12,
    rank: 4,
    translation_enabled: true,
    paste_enabled: true,
    avatar: null,
    plan: {
      code: "gratis",
      name: "Gratis",
      audience: role === "admin" ? "student" : role,
      price_cents: 0,
      currency: "MXN",
      period_days: 30,
      status: "active",
      paid_until: null,
      days_remaining: 9,
    },
    access: {
      browser_app: true,
      features: { communities },
      limits: { max_projects: null, max_algorithms: null, max_executions_per_day: 3 },
    },
    usage: { projects: 1, algorithms: 2, executions_today: 0 },
  }
}

function home(role: Account["role"], communities = false): string {
  return renderToStaticMarkup(
    <LocaleProvider locale="es">
      <SubjectHome
        account={account(role, communities)}
        onAccount={() => undefined}
        onOpenCommunities={() => undefined}
        onEnter={() => undefined}
      />
    </LocaleProvider>,
  )
}

describe("pantalla de materias", () => {
  it("abre Fundamentos y Bases de datos", () => {
    expect(SUBJECTS.map((item) => item.id)).toEqual(["fundamentos", "bases", "objetos", "software"])
    expect(SUBJECTS.filter((item) => item.open).map((item) => item.id)).toEqual(["fundamentos", "bases"])
    expect(openSubject("fundamentos")?.id).toBe("fundamentos")
    expect(openSubject("bases")?.id).toBe("bases")
    expect(openSubject("objetos")).toBeNull()
  })

  it("muestra la cuenta, la campana, los días de pago y el logo", () => {
    const html = home("student")
    expect(html).toContain("Aulivana")
    expect(html).toContain("Ana Ruiz")
    expect(html).toContain("Avisos de retos")
    expect(html).toContain(">9<")
    expect(html).toContain("días")
    expect(html).toContain("Elige una materia")
    expect(html).toContain("Fundamentos")
    expect(html).toContain("Bases de datos")
    expect(html).toContain("notación de Chen")
    expect(html).toContain("Programación orientada a objetos")
    expect(html).toContain("Ingeniería de software")
    expect(html).toContain("Todavía no se abre.")
    expect(html.match(/<button[^>]*class="subject-card"/g)?.length).toBe(2)
    expect(html).toContain("Unirme")
    expect(html).not.toContain(">Comunidades<")
    expect(html).not.toContain("Salir")
    expect(html).not.toContain("puntos")
    expect(html).not.toContain("puesto")
    expect(html).not.toContain("ejec.")
  })

  it("ofrece comunidades al docente que puede gestionarlas", () => {
    expect(home("teacher", true)).toContain(">Comunidades<")
    expect(home("teacher", false)).not.toContain(">Comunidades<")
  })
})
