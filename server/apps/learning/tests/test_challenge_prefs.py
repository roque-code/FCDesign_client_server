"""El editor del reto usa el índice y el punto y coma de la configuración."""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.editor.models import EditorPreference
from apps.learning.tests.test_progress import SALUDO, _start, _stage
from apps.tests.helpers import register

pytestmark = pytest.mark.django_db


def test_importar_respeta_el_indice_cero_del_usuario(client: APIClient):
    created = register(client, email="reto.indice@ejemplo.test")
    assert created.status_code == 201, created.content
    user = User.objects.get(pk=created.json()["id"])
    pref, _ = EditorPreference.objects.get_or_create(user=user)
    pref.index_base = 0
    pref.require_semicolons = False
    pref.save(update_fields=["index_base", "require_semicolons"])

    source = (
        "Algoritmo Base\n"
        "    Definir datos Como Entero\n"
        "    Dimension datos[2] Como Entero\n"
        "    datos[0] <- 5\n"
        "    Escribir datos[0]\n"
        "FinAlgoritmo\n"
    )
    imported = client.post("/api/v1/learning/import/", {"source": source}, format="json")
    assert imported.status_code == 200, imported.content
    assert imported.json()["workspace"] is not None


def test_el_borrador_del_reto_se_guarda_y_vuelve(client: APIClient):
    created = register(client, email="reto.borrador@ejemplo.test")
    assert created.status_code == 201, created.content
    EditorPreference.objects.get_or_create(user_id=created.json()["id"])

    started = _start(client, "Presentar un saludo")
    attempt_id = started["attempt"]["id"]
    _stage(client, attempt_id, "comprender", {"ack": True})
    _stage(client, attempt_id, "razonar", {"text": "<-"})

    source = 'Algoritmo Laboratorio\nEscribir "hola";\nFinAlgoritmo\n'
    saved = client.post(
        f"/api/v1/learning/attempts/{attempt_id}/build/",
        {"tool": "codigo", "source": source, "workspace": SALUDO},
        format="json",
    )
    assert saved.status_code == 200, saved.content
    draft = saved.json()["attempt"]["draft"]
    assert draft["tool"] == "codigo"
    assert "hola" in draft["source"]

    again = _start(client, "Presentar un saludo")
    assert again["attempt"]["id"] == attempt_id
    assert again["attempt"]["draft"]["source"] == draft["source"]
