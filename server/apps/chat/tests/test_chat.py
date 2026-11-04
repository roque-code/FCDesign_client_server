"""Mensajes personales y de grupo, separados por materia."""

from datetime import timedelta

from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient

from apps.chat.models import Message
from apps.tests.helpers import PASSWORD, refresh_csrf, register


def _person(email, **extra):
    client = APIClient(enforce_csrf_checks=True)
    refresh_csrf(client)
    created = register(client, email=email, **extra)
    assert created.status_code == 201, created.content
    return client, created.json()


def _group(teacher, name, *students, subject="fundamentos"):
    created = teacher.post(
        "/api/v1/communities/", {"name": name, "subject": subject}, format="json"
    )
    assert created.status_code == 201, created.content
    community_id = created.json()["id"]
    for student in students:
        added = teacher.post(
            f"/api/v1/communities/{community_id}/members/",
            {"user_id": student["id"]},
            format="json",
        )
        assert added.status_code == 201, added.content
    return community_id


def _allow(email, **flags):
    from apps.accounts.models import User
    from apps.billing.services import update_plan

    plan = User.objects.get(email=email).subscription.plan
    update_plan(plan, {"features": {**plan.features, **flags}})


def _open(client, community_id, user_id=None, subject="fundamentos"):
    body = {"subject": subject, "community_id": community_id, "user_id": user_id}
    return client.post("/api/v1/chat/conversations/", body, format="json")


def test_el_mensaje_puede_ser_personal_o_para_todo_el_grupo(client):
    register(client, email="profe-chat@ejemplo.test", display_name="Profe Chat", role="teacher")
    student, student_payload = _person(
        "alumno-chat@ejemplo.test", display_name="Ana Chat", role="student"
    )
    classmate, classmate_payload = _person(
        "companero-chat@ejemplo.test", display_name="Leo Chat", role="student"
    )
    other_teacher, _other_teacher = _person(
        "otra-profe-chat@ejemplo.test", display_name="Otra Profe", role="teacher"
    )
    group_a = _group(client, "Grupo A", student_payload, classmate_payload)
    group_b = _group(client, "Grupo B", student_payload)
    foreign = _group(other_teacher, "Grupo ajeno", classmate_payload)

    board = client.get("/api/v1/chat/board/?subject=fundamentos")
    assert board.status_code == 200, board.content
    assert board.json()["hours"] == 24
    assert board.json()["subject"] == "fundamentos"
    by_name = {item["name"]: item for item in board.json()["groups"]}
    assert sorted(by_name) == ["Grupo A", "Grupo B"]
    assert [item["display_name"] for item in by_name["Grupo A"]["people"]] == [
        "Ana Chat",
        "Leo Chat",
    ]
    assert [item["display_name"] for item in by_name["Grupo B"]["people"]] == ["Ana Chat"]

    student_board = student.get("/api/v1/chat/board/?subject=fundamentos")
    assert student_board.status_code == 200
    student_groups = {item["name"]: item for item in student_board.json()["groups"]}
    assert [item["display_name"] for item in student_groups["Grupo A"]["people"]] == ["Profe Chat"]
    assert [item["display_name"] for item in student_groups["Grupo B"]["people"]] == ["Profe Chat"]

    invalid = client.get("/api/v1/chat/board/?subject=dibujo")
    assert invalid.status_code == 400
    assert "materia" in invalid.json()["error"]["message"]

    missing_group = client.post(
        "/api/v1/chat/conversations/",
        {"subject": "fundamentos"},
        format="json",
    )
    assert missing_group.status_code == 400
    assert "grupo" in missing_group.json()["error"]["message"]

    outsider = other_teacher.post(
        "/api/v1/chat/conversations/",
        {"subject": "fundamentos", "community_id": group_a, "user_id": None},
        format="json",
    )
    assert outsider.status_code == 400
    assert "grupo" in outsider.json()["error"]["message"]

    not_mine = client.post(
        "/api/v1/chat/conversations/",
        {"subject": "fundamentos", "community_id": foreign, "user_id": classmate_payload["id"]},
        format="json",
    )
    assert not_mine.status_code == 400

    bad_person = client.post(
        "/api/v1/chat/conversations/",
        {"subject": "fundamentos", "community_id": group_a, "user_id": "no"},
        format="json",
    )
    assert bad_person.status_code == 400

    between_students = student.post(
        "/api/v1/chat/conversations/",
        {"subject": "fundamentos", "community_id": group_a, "user_id": classmate_payload["id"]},
        format="json",
    )
    assert between_students.status_code == 400

    personal = _open(client, group_a, student_payload["id"])
    assert personal.status_code == 200, personal.content
    personal_id = personal.json()["id"]
    assert personal.json()["kind"] == "personal"
    assert personal.json()["subject"] == "fundamentos"
    assert personal.json()["community_id"] == group_a
    assert personal.json()["peer_id"] == student_payload["id"]
    assert personal.json()["messages"] == []

    other_group = _open(client, group_b, student_payload["id"])
    assert other_group.status_code == 200
    assert other_group.json()["id"] != personal_id
    assert other_group.json()["messages"] == []

    other_subject = _open(client, group_a, student_payload["id"], subject="bases")
    assert other_subject.status_code == 400
    assert "materia" in other_subject.json()["error"]["message"]

    blank = client.post(
        f"/api/v1/chat/conversations/{personal_id}/messages/",
        {"body": "   "},
        format="json",
    )
    assert blank.status_code == 400
    missing_body = client.post(
        f"/api/v1/chat/conversations/{personal_id}/messages/", {}, format="json"
    )
    assert missing_body.status_code == 400
    long = client.post(
        f"/api/v1/chat/conversations/{personal_id}/messages/",
        {"body": "a" * 2001},
        format="json",
    )
    assert long.status_code == 400

    sent = client.post(
        f"/api/v1/chat/conversations/{personal_id}/messages/",
        {"body": "  Hola, Ana  "},
        format="json",
    )
    assert sent.status_code == 201, sent.content
    assert sent.json()["body"] == "Hola, Ana"

    again = _open(student, group_a, student_groups["Grupo A"]["people"][0]["id"])
    assert again.status_code == 200
    assert again.json()["id"] == personal_id
    reply = student.post(
        f"/api/v1/chat/conversations/{personal_id}/messages/",
        {"body": "Hola, profe"},
        format="json",
    )
    assert reply.status_code == 201
    listed = client.get(f"/api/v1/chat/conversations/{personal_id}/messages/")
    assert [item["body"] for item in listed.json()["results"]] == ["Hola, Ana", "Hola, profe"]

    hidden = other_teacher.get(f"/api/v1/chat/conversations/{personal_id}/messages/")
    assert hidden.status_code == 404
    classmate_personal = classmate.get(f"/api/v1/chat/conversations/{personal_id}/messages/")
    assert classmate_personal.status_code == 404

    group_thread = _open(client, group_a)
    assert group_thread.status_code == 200, group_thread.content
    group_id = group_thread.json()["id"]
    assert group_thread.json()["kind"] == "group"
    assert group_thread.json()["peer_id"] is None
    notice = client.post(
        f"/api/v1/chat/conversations/{group_id}/messages/",
        {"body": "Aviso para todos"},
        format="json",
    )
    assert notice.status_code == 201
    seen = _open(student, group_a)
    assert seen.json()["id"] == group_id
    assert [item["body"] for item in seen.json()["messages"]] == ["Aviso para todos"]
    answered = classmate.post(
        f"/api/v1/chat/conversations/{group_id}/messages/",
        {"body": "Enterado"},
        format="json",
    )
    assert answered.status_code == 201
    refreshed = client.get(f"/api/v1/chat/conversations/{group_id}/messages/")
    assert [item["body"] for item in refreshed.json()["results"]] == [
        "Aviso para todos",
        "Enterado",
    ]

    _allow("profe-chat@ejemplo.test", subject_software=True)
    other_group_chat = _open(client, group_a, subject="software")
    assert other_group_chat.status_code == 400

    stranger = other_teacher.get(f"/api/v1/chat/conversations/{group_id}/messages/")
    assert stranger.status_code == 403

    updated = client.get("/api/v1/chat/board/?subject=fundamentos")
    current = {item["name"]: item for item in updated.json()["groups"]}
    assert current["Grupo A"]["last_message"]["body"] == "Enterado"
    ana = next(item for item in current["Grupo A"]["people"] if item["display_name"] == "Ana Chat")
    assert ana["last_message"]["body"] == "Hola, profe"


def test_cada_materia_tiene_sus_grupos_y_los_mensajes_nuevos_quedan_sin_leer(client):
    register(
        client, email="profe-materia@ejemplo.test", display_name="Profe Materia", role="teacher"
    )
    student, student_payload = _person(
        "alumno-materia@ejemplo.test", display_name="Ana Materia", role="student"
    )
    other, other_payload = _person(
        "otra-materia@ejemplo.test", display_name="Leo Materia", role="student"
    )
    fundamentos = _group(client, "FC1", student_payload, other_payload, subject="fundamentos")
    bases = _group(client, "BD1", student_payload, subject="bases")

    board = client.get("/api/v1/chat/board/?subject=fundamentos")
    assert [item["name"] for item in board.json()["groups"]] == ["FC1"]
    assert [item["display_name"] for item in board.json()["groups"][0]["people"]] == [
        "Ana Materia",
        "Leo Materia",
    ]
    bases_board = client.get("/api/v1/chat/board/?subject=bases")
    assert [item["name"] for item in bases_board.json()["groups"]] == ["BD1"]
    assert [item["display_name"] for item in bases_board.json()["groups"][0]["people"]] == [
        "Ana Materia"
    ]
    _allow("profe-materia@ejemplo.test", subject_objetos=True)
    assert client.get("/api/v1/chat/board/?subject=objetos").json()["groups"] == []

    personal = _open(client, fundamentos, student_payload["id"])
    assert (
        client.post(
            f"/api/v1/chat/conversations/{personal.json()['id']}/messages/",
            {"body": "Solo para Ana"},
            format="json",
        ).status_code
        == 201
    )
    group_thread = _open(client, bases, subject="bases")
    assert (
        client.post(
            f"/api/v1/chat/conversations/{group_thread.json()['id']}/messages/",
            {"body": "Aviso de bases"},
            format="json",
        ).status_code
        == 201
    )

    student_fundamentos = student.get("/api/v1/chat/board/?subject=fundamentos").json()["groups"][0]
    ana = student_fundamentos["people"][0]
    assert ana["display_name"] == "Profe Materia"
    assert ana["unread"] == 1
    assert student_fundamentos["unread"] == 0
    assert [
        item["display_name"]
        for item in student.get("/api/v1/chat/board/?subject=bases").json()["groups"][0]["people"]
    ] == ["Profe Materia"]
    student_bases = student.get("/api/v1/chat/board/?subject=bases").json()["groups"][0]
    assert student_bases["unread"] == 1
    assert student_bases["people"][0]["unread"] == 0

    opened = _open(student, fundamentos, ana["id"])
    assert opened.status_code == 200
    after = student.get("/api/v1/chat/board/?subject=fundamentos").json()["groups"][0]
    assert after["people"][0]["unread"] == 0
    seen = student.get(f"/api/v1/chat/conversations/{group_thread.json()['id']}/messages/")
    assert seen.status_code == 200
    assert student.get("/api/v1/chat/board/?subject=bases").json()["groups"][0]["unread"] == 0

    teacher_board = client.get("/api/v1/chat/board/?subject=fundamentos").json()["groups"][0]
    assert teacher_board["people"][0]["unread"] == 0
    assert (
        next(item for item in teacher_board["people"] if item["id"] == other_payload["id"])[
            "unread"
        ]
        == 0
    )


def test_al_salir_del_grupo_ya_no_pueden_leer_la_conversacion(client):
    register(client, email="profe-sale@ejemplo.test", display_name="Profe Sale", role="teacher")
    student, student_payload = _person(
        "alumno-sale@ejemplo.test", display_name="Leo Sale", role="student"
    )
    community_id = _group(client, "Grupo sale", student_payload)
    personal = _open(client, community_id, student_payload["id"])
    group_thread = _open(client, community_id)
    assert (
        client.post(
            f"/api/v1/chat/conversations/{personal.json()['id']}/messages/",
            {"body": "Quedó la nota"},
            format="json",
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/v1/chat/conversations/{group_thread.json()['id']}/messages/",
            {"body": "Aviso del grupo"},
            format="json",
        ).status_code
        == 201
    )

    removed = client.delete(f"/api/v1/communities/{community_id}/members/{student_payload['id']}/")
    assert removed.status_code == 204

    assert (
        student.get(f"/api/v1/chat/conversations/{personal.json()['id']}/messages/").status_code
        == 403
    )
    assert (
        student.get(f"/api/v1/chat/conversations/{group_thread.json()['id']}/messages/").status_code
        == 403
    )
    assert student.get("/api/v1/chat/board/?subject=fundamentos").json()["groups"] == []
    teacher_board = client.get("/api/v1/chat/board/?subject=fundamentos").json()["groups"]
    assert teacher_board[0]["people"] == []
    assert _open(client, community_id).status_code == 200


def test_el_administrador_define_la_duracion_y_los_mensajes_viejos_se_borran(client):
    anonymous = client.get("/api/v1/auth/message-lifetime/")
    assert anonymous.status_code == 403

    register(client, email="profe-tiempo@ejemplo.test", display_name="Profe Tiempo", role="teacher")
    student, student_payload = _person(
        "alumno-tiempo@ejemplo.test", display_name="Nia Tiempo", role="student"
    )
    community_id = _group(client, "Grupo tiempo", student_payload)
    refused = client.patch("/api/v1/auth/message-lifetime/", {"hours": 1}, format="json")
    assert refused.status_code == 403

    opened = _open(client, community_id)
    conversation_id = opened.json()["id"]
    old = client.post(
        f"/api/v1/chat/conversations/{conversation_id}/messages/",
        {"body": "Esto caduca"},
        format="json",
    )
    fresh = client.post(
        f"/api/v1/chat/conversations/{conversation_id}/messages/",
        {"body": "Esto sigue"},
        format="json",
    )
    assert old.status_code == 201
    assert fresh.status_code == 201
    Message.objects.filter(pk=old.json()["id"]).update(
        created_at=timezone.now() - timedelta(hours=2)
    )

    call_command("create_admin", email="admin-chat@ejemplo.test", password=PASSWORD, name="Ada")
    admin = APIClient(enforce_csrf_checks=True)
    refresh_csrf(admin)
    entered = admin.post(
        "/api/v1/auth/login/",
        {"email": "admin-chat@ejemplo.test", "password": PASSWORD},
        format="json",
    )
    assert entered.status_code == 200, entered.content
    refresh_csrf(admin)

    current = admin.get("/api/v1/auth/message-lifetime/")
    assert current.status_code == 200
    assert current.json() == {"hours": 24}

    invalid = admin.patch("/api/v1/auth/message-lifetime/", {"hours": 0}, format="json")
    assert invalid.status_code == 400
    flag = admin.patch("/api/v1/auth/message-lifetime/", {"hours": True}, format="json")
    assert flag.status_code == 400
    text = admin.patch("/api/v1/auth/message-lifetime/", {"hours": "1"}, format="json")
    assert text.status_code == 400
    missing = admin.patch("/api/v1/auth/message-lifetime/", {}, format="json")
    assert missing.status_code == 400

    saved = admin.patch("/api/v1/auth/message-lifetime/", {"hours": 1}, format="json")
    assert saved.status_code == 200, saved.content
    assert saved.json() == {"hours": 1}
    assert Message.objects.filter(pk=old.json()["id"]).exists() is False
    assert Message.objects.filter(pk=fresh.json()["id"]).exists() is True

    listed = client.get(f"/api/v1/chat/conversations/{conversation_id}/messages/")
    assert [item["body"] for item in listed.json()["results"]] == ["Esto sigue"]

    Message.objects.filter(pk=fresh.json()["id"]).update(
        created_at=timezone.now() - timedelta(hours=3)
    )
    call_command("purge_chat_messages")
    assert Message.objects.filter(conversation_id=conversation_id).count() == 0
    board = client.get("/api/v1/chat/board/?subject=fundamentos")
    assert board.json()["hours"] == 1
    assert board.json()["groups"][0]["last_message"] is None

    blocked = admin.get("/api/v1/chat/board/?subject=fundamentos")
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "admin_account"
