"""Perfil docente o estudiante, y comunidades sobre cuentas ya registradas."""

from rest_framework.test import APIClient

from apps.tests.helpers import refresh_csrf, register


def _session(email, **extra):
    client = APIClient(enforce_csrf_checks=True)
    refresh_csrf(client)
    created = register(client, email=email, **extra)
    assert created.status_code == 201
    return client, created.json()


def test_el_perfil_se_elige_al_crear_la_cuenta_y_se_puede_cambiar(client):
    created = register(client, email="perfil@ejemplo.test")
    assert created.json()["role"] == "student"
    changed = client.patch("/api/v1/auth/me/", {"role": "teacher"}, format="json")
    assert changed.status_code == 200
    assert changed.json()["role"] == "teacher"
    assert client.get("/api/v1/auth/me/").json()["role"] == "teacher"
    refused = client.patch("/api/v1/auth/me/", {"role": "invitado"}, format="json")
    assert refused.status_code == 400


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
