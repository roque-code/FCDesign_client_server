"""El docente asigna, el alumno responde y la nota queda guardada."""

from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient

from apps.exams.models import ExamAttempt
from apps.tests.helpers import refresh_csrf, register

HOLA = 'Algoritmo Hola\n    Escribir "Hola mundo";\nFinAlgoritmo\n'


def _session(email, **extra):
    client = APIClient(enforce_csrf_checks=True)
    refresh_csrf(client)
    created = register(client, email=email, **extra)
    assert created.status_code == 201
    return client, created.json()


def _group(teacher):
    created = teacher.post(
        "/api/v1/communities/",
        {"name": "Algoritmos 1", "subject": "fundamentos"},
        format="json",
    )
    assert created.status_code == 201
    return created.json()


def _questions():
    return [
        {
            "kind": "choice",
            "prompt": "¿Capital de Francia?",
            "points": 1,
            "feedback": "París",
            "payload": {
                "options": [
                    {"id": "a", "text": "Lyon", "correct": False},
                    {"id": "b", "text": "París", "correct": True},
                ]
            },
        },
        {
            "kind": "multi",
            "prompt": "Pares",
            "points": 2,
            "payload": {
                "options": [
                    {"id": "p", "text": "2", "correct": True},
                    {"id": "q", "text": "3", "correct": False},
                    {"id": "r", "text": "4", "correct": True},
                ]
            },
        },
        {
            "kind": "true_false",
            "prompt": "El 2 es par",
            "points": 1,
            "payload": {"correct": True},
        },
        {
            "kind": "short",
            "prompt": "Río de París",
            "points": 1,
            "payload": {"answers": [{"text": "Sena", "fraction": 100}], "case_sensitive": False},
        },
        {
            "kind": "numerical",
            "prompt": "Mitad de 10",
            "points": 1,
            "payload": {"answers": [{"value": 5, "tolerance": 0.1, "fraction": 100}]},
        },
        {
            "kind": "matching",
            "prompt": "Une",
            "points": 1,
            "payload": {
                "pairs": [
                    {"id": "m1", "left": "perro", "right": "dog"},
                    {"id": "m2", "left": "gato", "right": "cat"},
                ]
            },
        },
        {
            "kind": "order",
            "prompt": "Ordena",
            "points": 1,
            "payload": {"items": [{"id": "o1", "text": "abrir"}, {"id": "o2", "text": "cerrar"}]},
        },
        {
            "kind": "cloze",
            "prompt": "Completa",
            "points": 1,
            "payload": {"text": "El cielo es {{1}}", "blanks": [{"id": "1", "answers": ["azul"]}]},
        },
        {
            "kind": "case",
            "prompt": "Saluda",
            "points": 2,
            "payload": {
                "statement": "Escribe un saludo.",
                "starter": HOLA,
                "cases": [
                    {
                        "name": "visible",
                        "inputs": [],
                        "expected": "Hola mundo",
                        "points": 1,
                        "hidden": False,
                    },
                    {
                        "name": "oculto",
                        "inputs": [],
                        "expected": "Hola mundo",
                        "points": 1,
                        "hidden": True,
                    },
                ],
            },
        },
    ]


def _body(community_id, **extra):
    body = {
        "title": "Parcial 1",
        "instructions": "Lee con calma.",
        "subject": "fundamentos",
        "community_id": community_id,
        "duration_minutes": 40,
        "attempts_allowed": 2,
        "grading_method": "highest",
        "shuffle_questions": False,
        "shuffle_choices": False,
        "navigation": "free",
        "one_per_page": True,
        "grade_to_pass": 60,
        "show_grade": "immediate",
        "audience": "all",
        "questions": _questions(),
    }
    body.update(extra)
    return body


def _answers(questions):
    by_kind = {item["kind"]: item for item in questions}
    return [
        {"question_id": by_kind["choice"]["id"], "answer": {"option": "b"}},
        {"question_id": by_kind["multi"]["id"], "answer": {"options": ["p", "r"]}},
        {"question_id": by_kind["true_false"]["id"], "answer": {"value": True}},
        {"question_id": by_kind["short"]["id"], "answer": {"text": "sena"}},
        {"question_id": by_kind["numerical"]["id"], "answer": {"value": "5"}},
        {"question_id": by_kind["matching"]["id"], "answer": {"pairs": {"m1": "m1", "m2": "m2"}}},
        {"question_id": by_kind["order"]["id"], "answer": {"order": ["o1", "o2"]}},
        {"question_id": by_kind["cloze"]["id"], "answer": {"blanks": {"1": "Azul"}}},
        {"question_id": by_kind["case"]["id"], "answer": {"source": HOLA}},
    ]


def test_asignar_resolver_y_descargar(client):
    register(client, email="docente@ejemplo.test", display_name="Profe", role="teacher")
    student, _student = _session("alumno@ejemplo.test", display_name="Ana Ruiz", role="student")
    other, other_payload = _session("otro@ejemplo.test", display_name="Luis", role="student")
    community = _group(client)
    client.post(
        f"/api/v1/communities/{community['id']}/members/",
        {"user_id": student.get("/api/v1/auth/me/").json()["id"]},
        format="json",
    )
    denied = student.post("/api/v1/exams/", _body(community["id"]), format="json")
    assert denied.status_code == 403
    created = client.post("/api/v1/exams/", _body(community["id"]), format="json")
    assert created.status_code == 201
    exam_id = created.json()["id"]
    assert created.json()["published"] is False
    assert student.get("/api/v1/exams/mine/").json()["results"] == []
    empty = client.post(f"/api/v1/exams/{exam_id}/publish/", {}, format="json")
    assert empty.status_code == 200
    assert student.get("/api/v1/exams/notices/").json()["unread"] == 1
    assert other.get("/api/v1/exams/mine/").json()["results"] == []
    assert other.post(f"/api/v1/exams/{exam_id}/attempts/", {}, format="json").status_code == 403
    started = student.post(f"/api/v1/exams/{exam_id}/attempts/", {}, format="json")
    assert started.status_code == 201
    play = started.json()
    choice = next(item for item in play["questions"] if item["kind"] == "choice")
    assert "correct" not in choice["payload"]["options"][0]
    case = next(item for item in play["questions"] if item["kind"] == "case")
    assert case["payload"]["hidden_count"] == 1
    assert "expected" not in case["payload"]["cases"][0]
    detail = client.get(f"/api/v1/exams/{exam_id}/").json()
    saved = student.patch(
        f"/api/v1/exams/attempts/{play['id']}/",
        {"answers": _answers(detail["questions"])[:1]},
        format="json",
    )
    assert saved.status_code == 200
    submitted = student.post(
        f"/api/v1/exams/attempts/{play['id']}/submit/",
        {"answers": _answers(detail["questions"])},
        format="json",
    )
    assert submitted.status_code == 200
    body = submitted.json()
    assert body["graded_visible"] is True
    assert body["percent"] == 100
    assert body["passed"] is True
    assert body["state"] == "graded"
    notices = student.get("/api/v1/exams/notices/").json()
    assert notices["unread"] == 2
    assert any(item["kind"] == "graded" and item["percent"] == 100 for item in notices["results"])
    read = student.post("/api/v1/exams/notices/", {}, format="json")
    assert read.json()["unread"] == 0
    board = client.get(f"/api/v1/exams/{exam_id}/results/").json()
    assert board["rows"][0]["student"]["email"] == "alumno@ejemplo.test"
    assert board["rows"][0]["official"]["percent"] == 100
    grades = client.get(f"/api/v1/exams/{exam_id}/grades/").json()
    assert "alumno@ejemplo.test" in grades["content"]
    assert "Ana Ruiz" in grades["content"]
    assert student.get(f"/api/v1/exams/{exam_id}/results/").status_code == 403
    exported = client.get(f"/api/v1/exams/{exam_id}/export/?as=json").json()
    assert "Parcial 1" in exported["content"]
    assert "case" in exported["content"]
    assert client.get(f"/api/v1/exams/{exam_id}/export/?format=json").status_code == 200
    moodle = client.get(f"/api/v1/exams/{exam_id}/export/?as=moodle")
    assert moodle.status_code == 200
    assert moodle.json()["filename"].endswith(".xml")
    assert "<quiz>" in moodle.json()["content"]
    gift = client.get(f"/api/v1/exams/{exam_id}/export/?as=gift")
    assert gift.status_code == 200
    assert gift.json()["filename"].endswith(".txt")
    assert client.get(f"/api/v1/exams/{exam_id}/export/?as=pdf").status_code == 400
    locked = client.patch(f"/api/v1/exams/{exam_id}/", {"title": "Otro"}, format="json")
    assert locked.status_code == 400
    assert client.delete(f"/api/v1/exams/{exam_id}/").status_code == 400
    assert other_payload["role"] == "student"


def test_pregunta_abierta_grupo_parcial_e_importacion(client):
    register(client, email="docente2@ejemplo.test", display_name="Profe", role="teacher")
    student, student_payload = _session("ana2@ejemplo.test", display_name="Ana", role="student")
    outsider, _outsider = _session("luis2@ejemplo.test", display_name="Luis", role="student")
    community = _group(client)
    client.post(
        f"/api/v1/communities/{community['id']}/members/",
        {"user_id": student_payload["id"]},
        format="json",
    )
    client.post(
        f"/api/v1/communities/{community['id']}/members/",
        {"user_id": outsider.get("/api/v1/auth/me/").json()["id"]},
        format="json",
    )
    created = client.post(
        "/api/v1/exams/",
        _body(
            community["id"],
            title="Ensayo",
            audience="selected",
            student_ids=[student_payload["id"]],
            questions=[
                {
                    "kind": "essay",
                    "prompt": "Explica el ciclo",
                    "points": 5,
                    "payload": {"rubric": "Claridad"},
                }
            ],
            show_grade="after_close",
            opens_at=(timezone.now() - timedelta(minutes=5)).isoformat(),
            closes_at=(timezone.now() + timedelta(hours=2)).isoformat(),
        ),
        format="json",
    )
    assert created.status_code == 201
    exam_id = created.json()["id"]
    client.post(f"/api/v1/exams/{exam_id}/publish/", {}, format="json")
    assert outsider.get("/api/v1/exams/mine/").json()["results"] == []
    started = student.post(f"/api/v1/exams/{exam_id}/attempts/", {}, format="json")
    submitted = student.post(
        f"/api/v1/exams/attempts/{started.json()['id']}/submit/",
        {
            "answers": [
                {
                    "question_id": created.json()["questions"][0]["id"],
                    "answer": {"text": "Se repite."},
                }
            ]
        },
        format="json",
    )
    assert submitted.status_code == 200
    assert submitted.json()["pending"] is True
    assert submitted.json()["graded_visible"] is False
    graded = client.post(
        f"/api/v1/exams/attempts/{started.json()['id']}/grade/",
        {
            "scores": [
                {"question_id": created.json()["questions"][0]["id"], "score": 4, "comment": "Bien"}
            ]
        },
        format="json",
    )
    assert graded.status_code == 200
    assert graded.json()["percent"] == 80
    hidden = student.get(f"/api/v1/exams/attempts/{started.json()['id']}/").json()
    assert hidden["graded_visible"] is False
    assert "percent" not in hidden
    client.post(f"/api/v1/exams/{exam_id}/close/", {}, format="json")
    visible = student.get(f"/api/v1/exams/attempts/{started.json()['id']}/").json()
    assert visible["percent"] == 80
    assert visible["questions"][0]["comment"] == "Bien"
    moodle = """<quiz><question type="multichoice"><questiontext format="html"><text>Color</text></questiontext>
      <single>true</single><defaultgrade>1</defaultgrade>
      <answer fraction="100"><text>Azul</text></answer>
      <answer fraction="0"><text>Verde</text></answer></question></quiz>"""
    imported = client.post(
        "/api/v1/exams/import/",
        {
            "format": "moodle",
            "text": moodle,
            "subject": "fundamentos",
            "community_id": community["id"],
            "title": "Importado",
        },
        format="json",
    )
    assert imported.status_code == 201
    assert imported.json()["questions"][0]["kind"] == "choice"
    assert imported.json()["published"] is False
    draft = client.post(
        "/api/v1/exams/", _body(community["id"], title="Borrador", questions=[]), format="json"
    )
    assert draft.status_code == 201
    assert (
        client.post(f"/api/v1/exams/{draft.json()['id']}/publish/", {}, format="json").status_code
        == 400
    )
    assert client.delete(f"/api/v1/exams/{draft.json()['id']}/").status_code == 204


def test_el_tiempo_y_la_ventana_cierran_el_intento(client):
    register(client, email="docente3@ejemplo.test", display_name="Profe", role="teacher")
    student, student_payload = _session("ana3@ejemplo.test", display_name="Ana", role="student")
    community = _group(client)
    client.post(
        f"/api/v1/communities/{community['id']}/members/",
        {"user_id": student_payload["id"]},
        format="json",
    )
    later = client.post(
        "/api/v1/exams/",
        _body(
            community["id"],
            title="Después",
            opens_at=(timezone.now() + timedelta(days=1)).isoformat(),
            questions=[
                {"kind": "true_false", "prompt": "¿Sí?", "points": 1, "payload": {"correct": True}}
            ],
        ),
        format="json",
    )
    exam_id = later.json()["id"]
    client.post(f"/api/v1/exams/{exam_id}/publish/", {}, format="json")
    refused = student.post(f"/api/v1/exams/{exam_id}/attempts/", {}, format="json")
    assert refused.status_code == 400
    opened = client.post(
        "/api/v1/exams/",
        _body(
            community["id"],
            title="Relámpago",
            duration_minutes=1,
            questions=[
                {"kind": "true_false", "prompt": "¿Sí?", "points": 1, "payload": {"correct": False}}
            ],
        ),
        format="json",
    )
    opened_id = opened.json()["id"]
    client.post(f"/api/v1/exams/{opened_id}/publish/", {}, format="json")
    started = student.post(f"/api/v1/exams/{opened_id}/attempts/", {}, format="json")
    attempt = ExamAttempt.objects.get(pk=started.json()["id"])
    attempt.deadline = timezone.now() - timedelta(seconds=5)
    attempt.save(update_fields=["deadline"])
    review = student.get(f"/api/v1/exams/attempts/{attempt.id}/")
    assert review.status_code == 200
    assert review.json()["state"] == "graded"
    assert review.json()["score"] == 0
    mismatch = client.post(
        "/api/v1/exams/",
        _body(community["id"], subject="bases"),
        format="json",
    )
    assert mismatch.status_code == 400
    assert (
        client.post(
            "/api/v1/exams/import/",
            {"text": "   ", "subject": "fundamentos", "community_id": community["id"]},
            format="json",
        ).status_code
        == 400
    )
