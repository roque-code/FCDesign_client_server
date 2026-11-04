import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { type Account } from "../api"
import { LocaleProvider } from "../i18n"
import { ExamDesk } from "./ExamDesk"

function account(role: Account["role"]): Account {
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
      features: { communities: true },
      limits: { max_projects: null, max_algorithms: null, max_executions_per_day: 3 },
    },
    usage: { projects: 1, algorithms: 2, executions_today: 0 },
  }
}

describe("escritorio de exámenes", () => {
  it("abre la lista para el docente y para el alumno", () => {
    const teacher = renderToStaticMarkup(
      <LocaleProvider locale="es">
        <ExamDesk account={account("teacher")} onAccount={() => undefined} onBack={() => undefined} />
      </LocaleProvider>,
    )
    const student = renderToStaticMarkup(
      <LocaleProvider locale="es">
        <ExamDesk account={account("student")} onAccount={() => undefined} onBack={() => undefined} />
      </LocaleProvider>,
    )
    expect(teacher).toContain("Exámenes")
    expect(teacher).toContain("Cargando exámenes")
    expect(student).toContain("Volver a las materias")
  })
})
