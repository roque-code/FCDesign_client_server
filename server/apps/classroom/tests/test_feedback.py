"""Calificación y comentario del docente sobre pseudocódigo y programas."""

import csv
import io

import pytest
from rest_framework.test import APIClient

from apps.languages.models import LanguageProgram
from apps.tests.helpers import refresh_csrf, register

pytestmark = pytest.mark.django_db


def _browser() -> APIClient:
    client = APIClient(enforce_csrf_checks=True, HTTP_X_AULIVANA_FCDDESIGN_CLIENT="")
    refresh_csrf(client)
    return client


def _person(email: str, name: str, role: str = "student") -> tuple[APIClient, int]:
    client = _browser()
    created = register(client, email=email, display_name=name, role=role)
    assert created.status_code == 201, created.content
    return client, created.json()["id"]


def _algorithm(client: APIClient, name: str) -> dict:
    rows = client.get("/api/v1/algorithms/?page_size=100").json()["results"]
    return next(row for row in rows if row["name"] == name)


def _group(teacher: APIClient, name: str, *student_ids: int) -> None:
    community = teacher.post("/api/v1/communities/", {"name": name}, format="json")
    assert community.status_code == 201, community.content
    for student_id in student_ids:
        added = teacher.post(
            f"/api/v1/communities/{community.json()['id']}/members/",
            {"user_id": student_id},
            format="json",
        )
        assert added.status_code in (200, 201), added.content


def _rows(body: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(body.lstrip("\ufeff"))))


def test_el_docente_califica_y_el_alumno_lo_ve():
    student, student_id = _person("nota.alumno@ejemplo.test", "Ana")
    teacher, _ = _person("nota.profe@ejemplo.test", "Profe Nota", role="teacher")
    algorithm = _algorithm(student, "Hola mundo")
    program = LanguageProgram.objects.create(
        owner_id=student_id, name="Suma", language="python", source="print(1)\n"
    )
    algorithm_url = f"/api/v1/classroom/feedback/algorithm/{algorithm['id']}/"
    program_url = f"/api/v1/classroom/feedback/program/{program.id}/"

    assert teacher.put(algorithm_url, {"grade": 90}, format="json").status_code == 404
    _group(teacher, "Grupo A", student_id)
    assert teacher.get(algorithm_url).json() == {"feedback": None, "focus": None}

    saved = teacher.put(
        algorithm_url, {"grade": "9,5", "comment": "  Bien hecho.  "}, format="json"
    )
    assert saved.status_code == 200, saved.content
    assert saved.json()["feedback"]["grade"] == 9.5
    assert saved.json()["feedback"]["comment"] == "Bien hecho."
    changed = teacher.put(algorithm_url, {"grade": 100, "comment": "Excelente"}, format="json")
    assert changed.json()["feedback"]["grade"] == 100
    assert teacher.get(algorithm_url).json()["feedback"]["comment"] == "Excelente"

    on_program = teacher.put(program_url, {"grade": "", "comment": "Falta probar"}, format="json")
    assert on_program.status_code == 200, on_program.content
    assert on_program.json()["feedback"]["grade"] is None
    assert on_program.json()["feedback"]["context"] == "Python"

    mine = student.get("/api/v1/feedback/")
    assert mine.status_code == 200
    seen = {(row["kind"], row["exercise_name"]): row for row in mine.json()["results"]}
    assert seen[("algorithm", "Hola mundo")]["grade"] == 100
    assert seen[("algorithm", "Hola mundo")]["teacher"]["display_name"] == "Profe Nota"
    assert seen[("program", "Suma")]["comment"] == "Falta probar"

    cleared = teacher.put(program_url, {"grade": None, "comment": ""}, format="json")
    assert cleared.json() == {"feedback": None}
    assert len(student.get("/api/v1/feedback/").json()["results"]) == 1


def test_la_calificacion_se_valida_y_solo_la_pone_el_docente():
    student, student_id = _person("nota.rango@ejemplo.test", "Beto")
    teacher, _ = _person("nota.rango.profe@ejemplo.test", "Profe", role="teacher")
    _group(teacher, "Grupo B", student_id)
    url = f"/api/v1/classroom/feedback/algorithm/{_algorithm(student, 'Hola mundo')['id']}/"

    for bad in (101, -1, "diez", 9.555, True):
        assert teacher.put(url, {"grade": bad}, format="json").status_code == 400, bad
    assert teacher.put(url, {"comment": "x" * 2001}, format="json").status_code == 400
    assert teacher.put(url.replace("algorithm", "otro"), {"grade": 1}).status_code == 400

    assert student.put(url, {"grade": 100}, format="json").status_code == 403

    stranger, _ = _person("nota.ajena@ejemplo.test", "Otra", role="teacher")
    assert stranger.put(url, {"grade": 100}, format="json").status_code == 404
    assert stranger.get(url).status_code == 404


def test_el_alumno_filtra_y_pagina_sus_calificaciones():
    student, student_id = _person("nota.lista@ejemplo.test", "Caro")
    teacher, _ = _person("nota.lista.profe@ejemplo.test", "Profe Lista", role="teacher")
    _group(teacher, "Grupo L", student_id)
    rows = student.get("/api/v1/algorithms/?page_size=100").json()["results"][:3]
    for index, row in enumerate(rows):
        teacher.put(
            f"/api/v1/classroom/feedback/algorithm/{row['id']}/",
            {"grade": 70 + index},
            format="json",
        )
    for language, grade in (("python", 90), ("python", 80), ("java", 100)):
        program = LanguageProgram.objects.create(
            owner_id=student_id, name=f"P {language} {grade}", language=language, source=""
        )
        teacher.put(
            f"/api/v1/classroom/feedback/program/{program.id}/", {"grade": grade}, format="json"
        )

    first = student.get("/api/v1/feedback/?page_size=4").json()
    assert (first["count"], first["page"], first["pages"], len(first["results"])) == (6, 1, 2, 4)
    assert first["totals"] == {"all": 6, "algorithm": 3, "program": 3}
    assert first["languages"] == [
        {"code": "java", "label": "Java", "count": 1},
        {"code": "python", "label": "Python", "count": 2},
    ]
    second = student.get("/api/v1/feedback/?page_size=4&page=2").json()
    assert len(second["results"]) == 2
    seen = {row["id"] for row in first["results"]} | {row["id"] for row in second["results"]}
    assert len(seen) == 6
    assert student.get("/api/v1/feedback/?page_size=4&page=9").json()["page"] == 2

    pseudo = student.get("/api/v1/feedback/?kind=algorithm").json()
    assert {row["kind"] for row in pseudo["results"]} == {"algorithm"}
    assert pseudo["average"] == 71
    python = student.get("/api/v1/feedback/?kind=program&language=python").json()
    assert python["count"] == 2 and python["average"] == 85
    assert {row["context"] for row in python["results"]} == {"Python"}
    one = student.get(f"/api/v1/feedback/?kind=algorithm&exercise={rows[0]['id']}").json()
    assert [row["exercise_id"] for row in one["results"]] == [rows[0]["id"]]

    for bad in ("kind=otro", "language=cobol", "page=0", "page=x", "page_size=51"):
        assert student.get(f"/api/v1/feedback/?{bad}").status_code == 400, bad
    assert student.get("/api/v1/feedback/?exercise=nada").status_code == 404


def test_el_csv_lista_alumnos_ejercicios_y_calificaciones():
    ana, ana_id = _person("csv.ana@ejemplo.test", "Ana")
    beto, beto_id = _person("csv.beto@ejemplo.test", "=Beto")
    teacher, _ = _person("csv.profe@ejemplo.test", "Profe CSV", role="teacher")
    _group(teacher, "Grupo Uno", ana_id)
    _group(teacher, "Grupo Dos", beto_id)
    LanguageProgram.objects.create(owner_id=ana_id, name="Suma", language="cpp", source="")
    program = LanguageProgram.objects.get(owner_id=ana_id, name="Suma")
    algorithm = _algorithm(ana, "Hola mundo")
    teacher.put(
        f"/api/v1/classroom/feedback/algorithm/{algorithm['id']}/",
        {"grade": 8.5, "comment": "Revisa la salida"},
        format="json",
    )
    teacher.put(f"/api/v1/classroom/feedback/program/{program.id}/", {"grade": 10}, format="json")

    everyone = teacher.get("/api/v1/classroom/grades/")
    assert everyone.status_code == 200
    assert everyone["Content-Type"].startswith("text/csv")
    assert 'filename="calificaciones-alumnos.csv"' in everyone["Content-Disposition"]
    rows = _rows(everyone.content.decode("utf-8"))
    assert rows[0] == [
        "Nombre",
        "Correo",
        "Comunidades",
        "Tipo",
        "Proyecto o lenguaje",
        "Ejercicio",
        "Calificación",
        "Comentario",
        "Fecha de la calificación",
        "Salidas",
        "Tiempo fuera",
    ]
    hello = next(row for row in rows if row[0] == "Ana" and row[5] == "Hola mundo")
    assert hello[3] == "Pseudocódigo"
    assert hello[6:8] == ["8.5", "Revisa la salida"]
    assert hello[8] != ""
    suma = next(row for row in rows if row[0] == "Ana" and row[5] == "Suma")
    assert suma[3:7] == ["Lenguaje", "C++", "Suma", "10"]
    assert any(row[0] == "'=Beto" for row in rows)
    ungraded = [row for row in rows[1:] if row[0] == "Ana" and row[5] not in ("Hola mundo", "Suma")]
    assert ungraded and all(row[6] == "" for row in ungraded)

    one = teacher.get("/api/v1/classroom/grades/?community=Grupo%20Uno&lang=en")
    assert 'filename="calificaciones-grupo-uno.csv"' in one["Content-Disposition"]
    english = _rows(one.content.decode("utf-8"))
    assert english[0][0] == "Name"
    assert {row[0] for row in english[1:]} == {"Ana"}
    assert teacher.get("/api/v1/classroom/grades/?community=Nada").status_code == 404
    assert beto.get("/api/v1/classroom/grades/").status_code == 403
