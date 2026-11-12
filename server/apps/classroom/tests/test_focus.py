"""El docente vigila las salidas de la plataforma por grupo o por alumno."""

from rest_framework.test import APIClient

from apps.classroom.models import ExerciseFocus
from apps.exams.models import ExamAttempt
from apps.languages.models import LanguageProgram
from apps.learning.models import ChallengeAttempt
from apps.tests.helpers import refresh_csrf, register


def _session(email, **extra):
    client = APIClient(enforce_csrf_checks=True)
    refresh_csrf(client)
    created = register(client, email=email, **extra)
    assert created.status_code == 201
    return client, created.json()


def _classroom(client):
    register(client, email="docente-foco@ejemplo.test", display_name="Profe", role="teacher")
    ana, ana_me = _session("ana-foco@ejemplo.test", display_name="Ana", role="student")
    luis, luis_me = _session("luis-foco@ejemplo.test", display_name="Luis", role="student")
    group = client.post(
        "/api/v1/communities/", {"name": "Grupo foco", "subject": "fundamentos"}, format="json"
    ).json()
    for person in (ana_me, luis_me):
        added = client.post(
            f"/api/v1/communities/{group['id']}/members/", {"user_id": person["id"]}, format="json"
        )
        assert added.status_code == 201
    return group, (ana, ana_me), (luis, luis_me)


def _exam(client, group_id):
    created = client.post(
        "/api/v1/exams/",
        {
            "title": "Parcial foco",
            "subject": "fundamentos",
            "community_id": group_id,
            "duration_minutes": 30,
            "attempts_allowed": 1,
            "audience": "all",
            "show_grade": "immediate",
            "questions": [
                {
                    "kind": "true_false",
                    "prompt": "El 2 es par",
                    "points": 1,
                    "payload": {"correct": True},
                }
            ],
        },
        format="json",
    )
    assert created.status_code == 201, created.content
    exam = created.json()
    assert client.post(f"/api/v1/exams/{exam['id']}/publish/", {}, format="json").status_code == 200
    return exam


def _event(client, attempt_id, event, **extra):
    response = client.post(
        f"/api/v1/exams/attempts/{attempt_id}/focus/", {"event": event, **extra}, format="json"
    )
    assert response.status_code == 200, response.content
    return response.json()


def test_el_docente_activa_la_vigilancia_por_grupo_y_por_alumno(client):
    group, (_ana, ana_me), (_luis, luis_me) = _classroom(client)
    url = f"/api/v1/communities/{group['id']}/"
    assert client.get(url).json()["focus_watch"] is False
    saved = client.patch(url, {"focus_watch": True, "focus_limit": 3}, format="json").json()
    assert saved["focus_watch"] is True
    assert saved["focus_limit"] == 3
    assert all(person["focus_watch"] is True for person in saved["students"])
    single = client.patch(
        f"{url}members/{luis_me['id']}/", {"focus_watch": False}, format="json"
    ).json()
    watched = {person["id"]: person["focus_watch"] for person in single["students"]}
    assert watched == {ana_me["id"]: True, luis_me["id"]: False}
    assert client.patch(url, {"focus_limit": 11}, format="json").status_code == 400
    assert client.patch(url, {"focus_limit": None}, format="json").json()["focus_limit"] is None
    reset = client.patch(url, {"focus_watch": False}, format="json").json()
    assert all(person["focus_watch"] is False for person in reset["students"])


def test_el_examen_registra_salidas_y_se_entrega_solo_a_la_tercera(client):
    group, (ana, _ana_me), (luis, _luis_me) = _classroom(client)
    client.patch(
        f"/api/v1/communities/{group['id']}/",
        {"focus_watch": True, "focus_limit": 3},
        format="json",
    )
    luis_id = _luis_me["id"]
    client.patch(
        f"/api/v1/communities/{group['id']}/members/{luis_id}/",
        {"focus_watch": False},
        format="json",
    )
    exam = _exam(client, group["id"])
    play = ana.post(f"/api/v1/exams/{exam['id']}/attempts/", {}, format="json").json()
    assert play["focus"]["limit"] == 3
    assert play["focus"]["exits"] == 0
    question = play["questions"][0]["id"]

    assert _event(ana, play["id"], "leave", reason="hidden")["focus"]["exits"] == 1
    assert _event(ana, play["id"], "leave", reason="blur")["focus"]["exits"] == 1
    stored = ExamAttempt.objects.get(pk=play["id"])
    stored.focus["left_at"] -= 100
    stored.save(update_fields=["focus"])
    back = _event(ana, play["id"], "back")
    assert back["focus"]["away_seconds"] >= 100
    _event(ana, play["id"], "fullscreen")
    _event(ana, play["id"], "paste")
    _event(ana, play["id"], "leave", reason="hidden")
    _event(ana, play["id"], "back")
    done = _event(
        ana,
        play["id"],
        "leave",
        reason="hidden",
        answers=[{"question_id": question, "answer": {"value": True}}],
    )
    assert done["state"] == "graded"
    assert done["percent"] == 100
    assert done["focus"]["exits"] == 3
    assert done["focus"]["auto_submitted"] is True
    assert _event(ana, play["id"], "back")["focus"]["exits"] == 3

    board = client.get(f"/api/v1/exams/{exam['id']}/results/").json()
    report = next(
        row["attempts"][0]["focus"]
        for row in board["rows"]
        if row["student"]["id"] == _ana_me["id"]
    )
    assert report["exits"] == 3
    assert report["fullscreen_exits"] == 1
    assert report["pastes"] == 1
    assert report["away_seconds"] >= 100
    grades = client.get(f"/api/v1/exams/{exam['id']}/grades/").json()["content"]
    assert "Salidas" in grades
    assert "Tiempo fuera" in grades

    other = luis.post(f"/api/v1/exams/{exam['id']}/attempts/", {}, format="json").json()
    assert other["focus"] is None
    assert _event(luis, other["id"], "leave", reason="hidden")["focus"] is None
    assert ExamAttempt.objects.get(pk=other["id"]).focus == {}
    bad = ana.post(f"/api/v1/exams/attempts/{play['id']}/focus/", {"event": "nada"}, format="json")
    assert bad.status_code == 400


def test_el_reto_se_cierra_solo_y_el_docente_ve_las_salidas(client):
    group, (ana, ana_me), _luis = _classroom(client)
    client.patch(
        f"/api/v1/communities/{group['id']}/",
        {"focus_watch": True, "focus_limit": 2},
        format="json",
    )
    rows = ana.get("/api/v1/learning/path/").json()["challenges"]
    challenge = rows[0]["id"]
    opened = ana.post(f"/api/v1/learning/challenges/{challenge}/attempts/", {}, format="json")
    assert opened.status_code == 200, opened.content
    attempt = opened.json()["attempt"]
    assert attempt["focus"]["limit"] == 2

    url = f"/api/v1/learning/attempts/{attempt['id']}/focus/"
    first = ana.post(url, {"event": "leave", "reason": "hidden"}, format="json").json()
    assert first["attempt"]["focus"]["away_now"] is True
    ana.post(url, {"event": "back"}, format="json")
    closed = ana.post(url, {"event": "leave", "reason": "blur"}, format="json").json()
    assert closed["attempt"]["status"] == "abandoned"
    assert closed["attempt"]["focus"]["auto_submitted"] is True
    assert "Se entregó automáticamente" in closed["attempt"]["summary"]
    stage = ana.post(
        f"/api/v1/learning/attempts/{attempt['id']}/stage/",
        {"stage": "comprender", "answer": {"ack": True}},
        format="json",
    )
    assert stage.status_code == 409
    stored = ChallengeAttempt.objects.get(pk=attempt["id"])
    assert stored.focus["exits"] == 2

    work = client.get(f"/api/v1/learning/roster/{ana_me['id']}/challenges/{challenge}/")
    assert work.status_code == 200, work.content
    assert work.json()["attempt"]["focus"]["exits"] == 2
    assert work.json()["attempt"]["focus"]["auto_submitted"] is True


def test_los_editores_registran_salidas_por_ejercicio(client):
    group, (ana, ana_me), (luis, luis_me) = _classroom(client)
    rows = ana.get("/api/v1/algorithms/?page_size=100").json()["results"]
    algorithm = rows[0]["id"]
    program = LanguageProgram.objects.create(
        owner_id=ana_me["id"], name="Suma", language="python", source="print(1)\n"
    )
    algorithm_url = f"/api/v1/focus/algorithm/{algorithm}/"
    program_url = f"/api/v1/focus/program/{program.id}/"

    quiet = ana.post(algorithm_url, {"event": "open"}, format="json")
    assert quiet.status_code == 200, quiet.content
    assert quiet.json() == {"focus": None}
    assert not ExerciseFocus.objects.exists()

    client.patch(
        f"/api/v1/communities/{group['id']}/",
        {"focus_watch": True, "focus_limit": 1},
        format="json",
    )
    opened = ana.post(algorithm_url, {"event": "open"}, format="json").json()["focus"]
    assert opened["exits"] == 0
    assert opened["limit"] is None
    ana.post(algorithm_url, {"event": "leave", "reason": "hidden"}, format="json")
    log = ExerciseFocus.objects.get(algorithm_id=algorithm)
    log.focus["left_at"] -= 70
    log.save(update_fields=["focus"])
    back = ana.post(algorithm_url, {"event": "back"}, format="json").json()["focus"]
    assert back["exits"] == 1
    assert back["away_seconds"] >= 70
    assert back["auto_submitted"] is False
    ana.post(algorithm_url, {"event": "paste"}, format="json")
    ana.post(algorithm_url, {"event": "leave", "reason": "blur"}, format="json")
    reopened = ana.post(algorithm_url, {"event": "open"}, format="json").json()["focus"]
    assert reopened["exits"] == 2
    assert reopened["away_now"] is False
    assert reopened["away_seconds"] < 80

    ana.post(program_url, {"event": "open"}, format="json")
    ana.post(program_url, {"event": "fullscreen"}, format="json")
    assert ana.post(program_url, {"event": "nada"}, format="json").status_code == 400
    assert luis.post(program_url, {"event": "open"}, format="json").status_code == 404

    seen = client.get(f"/api/v1/classroom/feedback/algorithm/{algorithm}/").json()["focus"]
    assert seen["exits"] == 2
    assert seen["pastes"] == 1
    assert (
        client.get(f"/api/v1/classroom/feedback/program/{program.id}/").json()["focus"][
            "fullscreen_exits"
        ]
        == 1
    )
    grades = client.get("/api/v1/classroom/grades/").content.decode("utf-8")
    assert "Salidas" in grades
    assert ",2,1 min" in grades
