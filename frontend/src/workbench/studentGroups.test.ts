import { describe, expect, it } from "vitest"

import type { ClassroomStudent } from "../api"
import { groupNames, studentLabel, studentsIn } from "./studentGroups"

const people: ClassroomStudent[] = [
  { id: 1, display_name: "Zoe", email: "zoe@ejemplo.test", communities: ["alumnosFPD"] },
  { id: 2, display_name: "Álvaro", email: "alvaro@ejemplo.test", communities: ["alumnosFPC", "externos"] },
  { id: 3, display_name: "Demian Téllez", email: "demian1@ejemplo.test", communities: ["alumnosFPD"] },
  { id: 4, display_name: "Demian Téllez", email: "demian2@ejemplo.test", communities: ["alumnosFPD"] },
  { id: 5, display_name: "Bruno", email: "bruno@ejemplo.test", communities: ["alumnosFPC"] },
]

describe("alumnos por grupo", () => {
  it("lista cada grupo una vez y en orden", () => {
    expect(groupNames(people)).toEqual(["alumnosFPC", "alumnosFPD", "externos"])
  })

  it("muestra solo los alumnos del grupo, en orden alfabético", () => {
    expect(studentsIn(people, "alumnosFPC").map((item) => item.display_name)).toEqual(["Álvaro", "Bruno"])
    expect(studentsIn(people, "externos").map((item) => item.id)).toEqual([2])
  })

  it("distingue por correo a dos alumnos con el mismo nombre", () => {
    const group = studentsIn(people, "alumnosFPD")
    expect(group.map((item) => studentLabel(item, group))).toEqual([
      "Demian Téllez · demian1@ejemplo.test",
      "Demian Téllez · demian2@ejemplo.test",
      "Zoe",
    ])
  })
})
