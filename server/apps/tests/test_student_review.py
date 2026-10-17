"""Un docente ve y ejecuta el código de un alumno sin modificarlo."""

from rest_framework.test import APIClient

from apps.projects.models import Algorithm
from apps.tests.helpers import refresh_csrf, register

SOURCE = 'Algoritmo Demo\n    Escribir "hola";\nFinAlgoritmo\n'


def _session(email, **extra):
    client = APIClient(enforce_csrf_checks=True)
    refresh_csrf(client)
    created = register(client, email=email, **extra)
    assert created.status_code == 201
    return client, created.json()


def test_el_docente_ve_y_ejecuta_sin_cambiar_el_codigo(client):
    register(client, email="profe-rev@ejemplo.test", display_name="Profe", role="teacher")
    student, student_payload = _session(
        "alumno-rev@ejemplo.test", display_name="Ana", role="student"
    )
    outsider, _outsider_payload = _session(
        "ajeno-rev@ejemplo.test", display_name="Ajeno", role="teacher"
    )
    colleague, colleague_payload = _session(
        "colega-rev@ejemplo.test", display_name="Colega", role="teacher"
    )
    student_id = student_payload["id"]

    assert student.get("/api/v1/classroom/students/").status_code == 403

    community_id = client.post("/api/v1/communities/", {"name": "Grupo"}, format="json").json()[
        "id"
    ]
    added = client.post(
        f"/api/v1/communities/{community_id}/members/",
        {"user_id": student_id},
        format="json",
    )
    assert added.status_code == 201
    client.post(
        f"/api/v1/communities/{community_id}/members/",
        {"user_id": colleague_payload["id"]},
        format="json",
    )

    project = student.post("/api/v1/projects/", {"name": "Tareas"}, format="json").json()
    created = student.post(
        "/api/v1/algorithms/",
        {"project_id": project["id"], "name": "Demo", "source": SOURCE},
        format="json",
    )
    assert created.status_code == 201
    algorithm_id = created.json()["id"]
    stored = Algorithm.objects.get(id=algorithm_id)
    before = (
        stored.source,
        stored.updated_at,
        stored.current_version,
        stored.flowchart,
        stored.versions.count(),
    )

    roster = client.get("/api/v1/classroom/students/")
    assert roster.status_code == 200
    listed = roster.json()["results"]
    assert [item["id"] for item in listed] == [student_id]
    assert listed[0]["display_name"] == "Ana"
    assert listed[0]["communities"] == ["Grupo"]

    assert outsider.get(f"/api/v1/classroom/students/{student_id}/projects/").status_code == 404
    assert (
        client.get(f"/api/v1/classroom/students/{colleague_payload['id']}/projects/").status_code
        == 404
    )

    work = client.get(f"/api/v1/classroom/students/{student_id}/projects/")
    assert work.status_code == 200
    tasks = next(item for item in work.json()["projects"] if item["name"] == "Tareas")
    assert tasks["algorithms"][0]["source"] == created.json()["source"]

    edited = client.patch(
        f"/api/v1/algorithms/{algorithm_id}/",
        {"source": 'Algoritmo Demo\n    Escribir "no";\nFinAlgoritmo\n'},
        format="json",
    )
    assert edited.status_code == 404

    checked = client.post(f"/api/v1/algorithms/{algorithm_id}/validate/")
    assert checked.status_code == 200
    ran = client.post(f"/api/v1/algorithms/{algorithm_id}/execute/")
    assert ran.status_code == 201
    diagram = client.get(f"/api/v1/algorithms/{algorithm_id}/flowchart/")
    assert diagram.status_code == 200
    assert diagram.json()["graph"] is not None

    stored.refresh_from_db()
    assert (
        stored.source,
        stored.updated_at,
        stored.current_version,
        stored.flowchart,
        stored.versions.count(),
    ) == before
