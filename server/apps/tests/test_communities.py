"""Perfil docente o estudiante, y comunidades sobre cuentas ya registradas."""

from rest_framework.test import APIClient

from apps.tests.helpers import refresh_csrf, register


def _session(email, **extra):
    client = APIClient(enforce_csrf_checks=True)
    refresh_csrf(client)
    created = register(client, email=email, **extra)
    assert created.status_code == 201
    return client, created.json()


def test_el_perfil_se_elige_al_crear_la_cuenta_y_no_se_cambia(client):
    created = register(client, email="perfil@ejemplo.test")
    assert created.json()["role"] == "student"
    teacher = register(
        client, email="perfil-docente@ejemplo.test", display_name="Profe", role="teacher"
    )
    assert teacher.json()["role"] == "teacher"
    refused = client.patch("/api/v1/auth/me/", {"role": "teacher"}, format="json")
    assert refused.status_code == 400
    assert client.get("/api/v1/auth/me/").json()["role"] == "teacher"
    unknown = client.patch("/api/v1/auth/me/", {"role": "invitado"}, format="json")
    assert unknown.status_code == 400


def test_el_docente_lista_alumnos_y_agrega_cuentas_registradas(client):
    created_teacher = register(
        client, email="docente@ejemplo.test", display_name="Profe", role="teacher"
    )
    assert created_teacher.json()["role"] == "teacher"
    student, student_payload = _session(
        "alumno@ejemplo.test", display_name="Alumno", role="student"
    )
    student_id = student_payload["id"]
    _other, other_payload = _session(
        "otra-docente@ejemplo.test", display_name="Otra", role="teacher"
    )
    other_id = other_payload["id"]
    stranger, _stranger_payload = _session(
        "ajeno@ejemplo.test", display_name="Ajeno", role="teacher"
    )

    denied = student.post("/api/v1/communities/", {"name": "Grupo"}, format="json")
    assert denied.status_code == 403

    created = client.post("/api/v1/communities/", {"name": "Algoritmos 1"}, format="json")
    assert created.status_code == 201
    community_id = created.json()["id"]
    assert created.json()["students"] == []

    repeated = client.post("/api/v1/communities/", {"name": "Algoritmos 1"}, format="json")
    assert repeated.status_code == 400

    short = client.get(f"/api/v1/people/?q=a&community={community_id}")
    assert short.status_code == 400

    found = client.get(f"/api/v1/people/?q=alumno@ejemplo&community={community_id}")
    assert found.status_code == 200
    assert found.json()["results"][0]["id"] == student_id
    assert found.json()["results"][0]["member"] is False
    assert found.json()["results"][0]["role"] == "student"

    missing = client.post(
        f"/api/v1/communities/{community_id}/members/",
        {"user_id": 999999},
        format="json",
    )
    assert missing.status_code == 404

    added = client.post(
        f"/api/v1/communities/{community_id}/members/",
        {"user_id": student_id},
        format="json",
    )
    assert added.status_code == 201
    client.post(
        f"/api/v1/communities/{community_id}/members/",
        {"user_id": other_id},
        format="json",
    )
    again = client.post(
        f"/api/v1/communities/{community_id}/members/",
        {"user_id": student_id},
        format="json",
    )
    assert again.status_code == 400

    self_id = client.get("/api/v1/auth/me/").json()["id"]
    own = client.post(
        f"/api/v1/communities/{community_id}/members/",
        {"user_id": self_id},
        format="json",
    )
    assert own.status_code == 400

    detail = client.get(f"/api/v1/communities/{community_id}/")
    assert detail.json()["student_count"] == 1
    assert detail.json()["students"][0]["email"] == "alumno@ejemplo.test"
    assert detail.json()["teachers"][0]["email"] == "otra-docente@ejemplo.test"
    listed = client.get("/api/v1/communities/")
    assert listed.json()["results"][0]["student_count"] == 1

    stolen = stranger.post(
        f"/api/v1/communities/{community_id}/members/",
        {"user_id": student_id},
        format="json",
    )
    assert stolen.status_code == 404

    refresh_csrf(client)
    removed = client.delete(f"/api/v1/communities/{community_id}/members/{student_id}/")
    assert removed.status_code == 204
    assert client.get(f"/api/v1/communities/{community_id}/").json()["students"] == []


def _algorithm(client):
    project_id = client.get("/api/v1/projects/").json()["results"][0]["id"]
    created = client.post(
        "/api/v1/algorithms/",
        {
            "project_id": project_id,
            "name": "Hola",
            "source": 'Algoritmo Hola\n    Escribir "Hola";\nFinAlgoritmo\n',
        },
        format="json",
    )
    assert created.status_code == 201
    return created.json()["id"]


def test_el_docente_habilita_la_traduccion_por_grupo_y_por_alumno(client):
    del client
    teacher, _account = _session("profe-tr@ejemplo.test", display_name="Profe", role="teacher")
    student, student_body = _session("alumno-tr@ejemplo.test", display_name="Alumno")
    assert student_body["translation_enabled"] is True
    student_id = student_body["id"]
    algorithm_id = _algorithm(student)
    assert student.post(f"/api/v1/algorithms/{algorithm_id}/translate/").status_code == 200
    other, other_body = _session("otro-tr@ejemplo.test", display_name="Otro")
    other_id = other_body["id"]
    other_algorithm = _algorithm(other)
    colleague, colleague_body = _session(
        "colega-tr@ejemplo.test", display_name="Colega", role="teacher"
    )
    colleague_id = colleague_body["id"]
    colleague_algorithm = _algorithm(colleague)

    created = teacher.post("/api/v1/communities/", {"name": "Algoritmos"}, format="json")
    assert created.status_code == 201
    assert created.json()["translation_enabled"] is True
    community_id = created.json()["id"]
    for user_id in (student_id, other_id, colleague_id):
        added = teacher.post(
            f"/api/v1/communities/{community_id}/members/",
            {"user_id": user_id},
            format="json",
        )
        assert added.status_code == 201

    closed = teacher.patch(
        f"/api/v1/communities/{community_id}/",
        {"translation_enabled": False},
        format="json",
    )
    assert closed.status_code == 200
    assert closed.json()["translation_enabled"] is False
    assert all(row["translation_enabled"] is False for row in closed.json()["students"])
    assert "translation_enabled" not in closed.json()["teachers"][0]

    assert student.get("/api/v1/auth/me/").json()["translation_enabled"] is False
    blocked = student.post(f"/api/v1/algorithms/{algorithm_id}/translate/")
    assert blocked.status_code == 403
    assert other.get("/api/v1/auth/me/").json()["translation_enabled"] is False

    opened = teacher.patch(
        f"/api/v1/communities/{community_id}/members/{student_id}/",
        {"translation_enabled": True},
        format="json",
    )
    assert opened.status_code == 200
    assert opened.json()["translation_enabled"] is False
    by_email = {row["email"]: row["translation_enabled"] for row in opened.json()["students"]}
    assert by_email["alumno-tr@ejemplo.test"] is True
    assert by_email["otro-tr@ejemplo.test"] is False

    assert student.get("/api/v1/auth/me/").json()["translation_enabled"] is True
    assert student.post(f"/api/v1/algorithms/{algorithm_id}/translate/").status_code == 200
    assert other.post(f"/api/v1/algorithms/{other_algorithm}/translate/").status_code == 403
    assert colleague.get("/api/v1/auth/me/").json()["translation_enabled"] is True
    assert colleague.post(f"/api/v1/algorithms/{colleague_algorithm}/translate/").status_code == 200

    group = teacher.patch(
        f"/api/v1/communities/{community_id}/",
        {"translation_enabled": True},
        format="json",
    )
    assert group.status_code == 200
    assert all(row["translation_enabled"] is True for row in group.json()["students"])
    assert student.get("/api/v1/auth/me/").json()["translation_enabled"] is True
    assert other.get("/api/v1/auth/me/").json()["translation_enabled"] is True

    one = teacher.patch(
        f"/api/v1/communities/{community_id}/members/{other_id}/",
        {"translation_enabled": False},
        format="json",
    )
    assert one.status_code == 200
    by_email = {row["email"]: row["translation_enabled"] for row in one.json()["students"]}
    assert by_email["alumno-tr@ejemplo.test"] is True
    assert by_email["otro-tr@ejemplo.test"] is False
    teacher_member = teacher.patch(
        f"/api/v1/communities/{community_id}/members/{colleague_id}/",
        {"translation_enabled": False},
        format="json",
    )
    assert teacher_member.status_code == 400
    invalid = teacher.patch(
        f"/api/v1/communities/{community_id}/",
        {"translation_enabled": "no"},
        format="json",
    )
    assert invalid.status_code == 400

    refused = student.patch(
        f"/api/v1/communities/{community_id}/",
        {"translation_enabled": True},
        format="json",
    )
    assert refused.status_code == 403
    assert other.get("/api/v1/auth/me/").json()["translation_enabled"] is False
    assert other.post(f"/api/v1/algorithms/{other_algorithm}/translate/").status_code == 403


def test_la_traduccion_exige_permiso_en_cada_grupo(client):
    del client
    teacher_a, _first = _session("profe-a-tr@ejemplo.test", display_name="Profe A", role="teacher")
    teacher_b, _second = _session("profe-b-tr@ejemplo.test", display_name="Profe B", role="teacher")
    student, student_body = _session("compartido-tr@ejemplo.test", display_name="Compartido")
    student_id = student_body["id"]
    algorithm_id = _algorithm(student)

    group_a = teacher_a.post("/api/v1/communities/", {"name": "Uno"}, format="json").json()["id"]
    assert (
        teacher_a.post(
            f"/api/v1/communities/{group_a}/members/",
            {"user_id": student_id},
            format="json",
        ).status_code
        == 201
    )
    assert (
        teacher_a.patch(
            f"/api/v1/communities/{group_a}/",
            {"translation_enabled": False},
            format="json",
        ).status_code
        == 200
    )

    group_b = teacher_b.post("/api/v1/communities/", {"name": "Dos"}, format="json").json()["id"]
    assert (
        teacher_b.post(
            f"/api/v1/communities/{group_b}/members/",
            {"user_id": student_id},
            format="json",
        ).status_code
        == 201
    )

    assert student.get("/api/v1/auth/me/").json()["translation_enabled"] is False
    assert student.post(f"/api/v1/algorithms/{algorithm_id}/translate/").status_code == 403

    assert (
        teacher_a.patch(
            f"/api/v1/communities/{group_a}/members/{student_id}/",
            {"translation_enabled": True},
            format="json",
        ).status_code
        == 200
    )
    assert student.get("/api/v1/auth/me/").json()["translation_enabled"] is True

    assert (
        teacher_b.patch(
            f"/api/v1/communities/{group_b}/members/{student_id}/",
            {"translation_enabled": False},
            format="json",
        ).status_code
        == 200
    )
    assert student.get("/api/v1/auth/me/").json()["translation_enabled"] is False


def test_un_docente_ajeno_no_cambia_la_traduccion(client):
    del client
    teacher, _account = _session("dueno-tr@ejemplo.test", display_name="Dueno", role="teacher")
    _student, student_body = _session("sola-tr@ejemplo.test", display_name="Sola")
    student_id = student_body["id"]
    community_id = teacher.post("/api/v1/communities/", {"name": "Grupo"}, format="json").json()[
        "id"
    ]
    assert (
        teacher.post(
            f"/api/v1/communities/{community_id}/members/",
            {"user_id": student_id},
            format="json",
        ).status_code
        == 201
    )
    stranger, _account = _session("ajeno-tr@ejemplo.test", display_name="Ajeno", role="teacher")
    stolen = stranger.patch(
        f"/api/v1/communities/{community_id}/",
        {"translation_enabled": False},
        format="json",
    )
    assert stolen.status_code == 404
    missing = teacher.patch(
        f"/api/v1/communities/{community_id}/members/999999/",
        {"translation_enabled": False},
        format="json",
    )
    assert missing.status_code == 404


def test_el_docente_bloquea_pegar_en_el_grupo_o_en_un_alumno(client):
    register(client, email="pega-profe@ejemplo.test", display_name="Profe Pega", role="teacher")
    student, student_body = _session("pega-ana@ejemplo.test", display_name="Ana Pega")
    other, other_body = _session("pega-beto@ejemplo.test", display_name="Beto Pega")
    created = client.post("/api/v1/communities/", {"name": "Sin pegar"}, format="json")
    assert created.status_code == 201
    assert created.json()["paste_enabled"] is True
    community_id = created.json()["id"]
    for user_id in (student_body["id"], other_body["id"]):
        assert (
            client.post(
                f"/api/v1/communities/{community_id}/members/",
                {"user_id": user_id},
                format="json",
            ).status_code
            == 201
        )
    assert student.get("/api/v1/auth/me/").json()["paste_enabled"] is True

    blocked = client.patch(
        f"/api/v1/communities/{community_id}/",
        {"paste_enabled": False},
        format="json",
    )
    assert blocked.status_code == 200, blocked.content
    assert blocked.json()["paste_enabled"] is False
    assert all(row["paste_enabled"] is False for row in blocked.json()["students"])
    assert all("paste_enabled" not in row for row in blocked.json()["teachers"])
    assert student.get("/api/v1/auth/me/").json()["paste_enabled"] is False
    assert other.get("/api/v1/auth/me/").json()["paste_enabled"] is False
    assert client.get("/api/v1/auth/me/").json()["paste_enabled"] is True

    exception = client.patch(
        f"/api/v1/communities/{community_id}/members/{student_body['id']}/",
        {"paste_enabled": True},
        format="json",
    )
    assert exception.status_code == 200, exception.content
    by_email = {row["email"]: row["paste_enabled"] for row in exception.json()["students"]}
    assert by_email["pega-ana@ejemplo.test"] is True
    assert by_email["pega-beto@ejemplo.test"] is False
    assert student.get("/api/v1/auth/me/").json()["paste_enabled"] is True
    assert other.get("/api/v1/auth/me/").json()["paste_enabled"] is False

    reset = client.patch(
        f"/api/v1/communities/{community_id}/",
        {"paste_enabled": True},
        format="json",
    )
    assert reset.status_code == 200
    assert all(row["paste_enabled"] is True for row in reset.json()["students"])
    alone = client.patch(
        f"/api/v1/communities/{community_id}/members/{other_body['id']}/",
        {"paste_enabled": False},
        format="json",
    )
    assert alone.status_code == 200
    assert other.get("/api/v1/auth/me/").json()["paste_enabled"] is False
    assert student.get("/api/v1/auth/me/").json()["paste_enabled"] is True
    invalid = client.patch(
        f"/api/v1/communities/{community_id}/",
        {"paste_enabled": "no"},
        format="json",
    )
    assert invalid.status_code == 400
