"""Un alumno recorre clasificar, ordenar, construir y predecir."""

import json

from apps.executions.models import Execution
from apps.learning.models import ChallengeAttempt, WorkspaceSnapshot
from apps.learning.path_data import PATH
from apps.tests.helpers import register

SALUDO = {
    "blocks": {
        "languageVersion": 0,
        "blocks": [
            {
                "type": "traza_definir",
                "id": "d1",
                "fields": {"NOMBRE": "saludo", "TIPO": "cadena"},
                "next": {
                    "block": {
                        "type": "traza_asignar",
                        "id": "a1",
                        "fields": {"NOMBRE": "saludo"},
                        "inputs": {
                            "VALOR": {
                                "block": {
                                    "type": "traza_cadena",
                                    "id": "c1",
                                    "fields": {"VALOR": "hola"},
                                }
                            }
                        },
                        "next": {
                            "block": {
                                "type": "traza_escribir",
                                "id": "e1",
                                "inputs": {
                                    "VALOR": {
                                        "block": {
                                            "type": "traza_variable",
                                            "id": "v1",
                                            "fields": {"NOMBRE": "saludo", "TIPO": "cadena"},
                                        }
                                    }
                                },
                            }
                        },
                    }
                },
            }
        ],
    }
}


def _spec(title: str) -> dict:
    for unit in PATH["units"]:
        assert isinstance(unit, dict)
        for challenge in unit["challenges"]:
            assert isinstance(challenge, dict)
            if challenge["title"] == title:
                return challenge
    raise AssertionError(title)


def _rows(client) -> dict[str, dict]:
    response = client.get("/api/v1/learning/path/")
    assert response.status_code == 200, response.content
    return {item["title"]: item for item in response.json()["challenges"]}


def _start(client, title: str) -> dict:
    opened = client.post(
        f"/api/v1/learning/challenges/{_rows(client)[title]['id']}/attempts/",
        {},
        format="json",
    )
    assert opened.status_code == 200, opened.content
    return opened.json()


def _stage(client, attempt_id: str, stage: str, answer: dict) -> dict:
    response = client.post(
        f"/api/v1/learning/attempts/{attempt_id}/stage/",
        {"stage": stage, "answer": answer},
        format="json",
    )
    assert response.status_code == 200, response.content
    return response.json()


def _close(client, attempt_id: str) -> dict:
    response = client.post(
        f"/api/v1/learning/attempts/{attempt_id}/close/",
        {"reflection": "Ya entiendo cómo funciona este reto."},
        format="json",
    )
    assert response.status_code == 200, response.content
    return response.json()


def test_la_ruta_publica_los_retos_sin_la_solucion(client) -> None:
    register(client, email="lab-fase5-ruta@ejemplo.test")
    rows = list(_rows(client).values())
    assert [item["position"] for item in rows] == list(range(1, 35))
    assert rows[10]["title"] == "Partes de una decisión"
    assert rows[10]["state"] == "locked"
    assert rows[17]["title"] == "Contar positivos"
    assert rows[17]["time_limit_seconds"] == 600
    assert rows[18]["title"] == "Partes de un Segun"
    assert rows[26]["title"] == "Subir hasta el tope"
    assert rows[27]["title"] == "Casilla, tamaño y valor"
    assert rows[33]["title"] == "Sumar uno por referencia"
    assert {item["activity_type"] for item in rows} == {"classify", "order", "build", "predict"}
    assert rows[0]["state"] == "available"
    assert rows[0]["time_limit_seconds"] == 180
    assert rows[2]["time_limit_seconds"] == 480
    assert rows[1]["state"] == "locked"
    detail = client.get(f"/api/v1/learning/challenges/{rows[0]['id']}/")
    raw = json.dumps(detail.json())
    assert "accepted" not in raw
    assert "solution" not in raw
    assert "starter" not in raw
    assert "expected_output" not in raw
    assert "Esta es la solución explicada" not in raw
    locked = client.post(
        f"/api/v1/learning/challenges/{rows[1]['id']}/attempts/",
        {},
        format="json",
    )
    assert locked.status_code == 403


def test_un_alumno_termina_los_cuatro_tipos(client) -> None:
    register(client, email="lab-fase5-alumno@ejemplo.test")
    before = Execution.objects.count()

    classify = _spec("Qué entra y qué sale")
    restrictions = classify["restrictions"]
    assert isinstance(restrictions, dict)
    started = _start(client, "Qué entra y qué sale")
    attempt_id = started["attempt"]["id"]
    assert started["attempt"]["next_stage"] == "comprender"
    _stage(client, attempt_id, "comprender", {"ack": True})
    choices = {item["id"]: item["category"] for item in restrictions["items"]}
    graded = _stage(client, attempt_id, "razonar", {"choices": choices})
    assert graded["correct"] is True
    assert graded["attempt"]["next_stage"] == "explicar"
    closed = _close(client, attempt_id)
    assert closed["attempt"]["status"] == "completed"
    assert closed["attempt"]["score"] == 100
    assert closed["points"] == 10
    assert closed["rank"] == 1
    me = client.get("/api/v1/auth/me/").json()
    assert me["points"] == 10
    assert me["rank"] == 1
    assert closed["attempt"]["elapsed_seconds"] >= 0
    assert closed["history"][-1]["status"] == "completed"
    assert closed["history"][-1]["elapsed_seconds"] == closed["attempt"]["elapsed_seconds"]

    order = _spec("Orden para mostrar un precio")
    order_rules = order["restrictions"]
    assert isinstance(order_rules, dict)
    started = _start(client, "Orden para mostrar un precio")
    attempt_id = started["attempt"]["id"]
    _stage(client, attempt_id, "comprender", {"ack": True})
    graded = _stage(client, attempt_id, "razonar", {"order": order_rules["solution"]})
    assert graded["correct"] is True
    _close(client, attempt_id)

    build = _spec("Presentar un saludo")
    build_rules = build["restrictions"]
    assert isinstance(build_rules, dict)
    started = _start(client, "Presentar un saludo")
    attempt_id = started["attempt"]["id"]
    detail = json.dumps(started)
    assert "hola\\n" not in detail
    early = client.post(
        f"/api/v1/learning/attempts/{attempt_id}/check/",
        {"workspace": SALUDO},
        format="json",
    )
    assert early.status_code == 409
    _stage(client, attempt_id, "comprender", {"ack": True})
    _stage(client, attempt_id, "razonar", {"text": "<-"})
    checked = client.post(
        f"/api/v1/learning/attempts/{attempt_id}/check/",
        {"workspace": SALUDO},
        format="json",
    )
    assert checked.status_code == 200, checked.content
    assert checked.json()["passed"] is True
    _close(client, attempt_id)
    snapshot = WorkspaceSnapshot.objects.filter(attempt_id=attempt_id, schema_version=1).latest(
        "created_at"
    )
    assert "saludo <- " in snapshot.pseudocode
    assert snapshot.ast_dump
    assert snapshot.blockly_json["blocks"]["blocks"][0]["type"] == "traza_definir"

    predict = _spec("Después de asignar")
    predict_rules = predict["restrictions"]
    assert isinstance(predict_rules, dict)
    started = _start(client, "Después de asignar")
    attempt_id = started["attempt"]["id"]
    assert "n <- 4" in started["challenge"]["task"]["source"]
    assert "5" not in started["challenge"]["task"]["source"]
    _stage(client, attempt_id, "comprender", {"ack": True})
    blocked = client.post(f"/api/v1/learning/attempts/{attempt_id}/run/", {}, format="json")
    assert blocked.status_code == 409
    guessed = _stage(client, attempt_id, "razonar", {"text": "4"})
    assert guessed["correct"] is False
    guessed_run = client.post(f"/api/v1/learning/attempts/{attempt_id}/run/", {}, format="json")
    assert guessed_run.status_code == 409
    answer = _stage(client, attempt_id, "razonar", {"text": "5"})
    assert answer["correct"] is True
    assert answer["attempt"]["prediction"]["is_correct"] is True
    ran = client.post(f"/api/v1/learning/attempts/{attempt_id}/run/", {}, format="json")
    assert ran.status_code == 200, ran.content
    assert ran.json()["output"] == predict_rules["output"]
    finished = _close(client, attempt_id)
    assert finished["attempt"]["status"] == "completed"
    assert Execution.objects.count() == before
    assert ChallengeAttempt.objects.filter(status="completed").count() == 4
    again = list(_rows(client).values())
    assert again[3]["state"] == "completed"
    assert again[4]["state"] == "available"


def test_la_pista_siguiente_no_es_la_solucion_y_el_error_nombra_el_concepto(client) -> None:
    register(client, email="lab-fase5-pista@ejemplo.test")
    _finish_until(client, "Presentar un saludo")
    started = _start(client, "Presentar un saludo")
    attempt_id = started["attempt"]["id"]
    first = client.post(f"/api/v1/learning/attempts/{attempt_id}/hint/", {}, format="json")
    assert first.status_code == 200
    assert first.json()["attempt"]["hints"][0]["solution"] is False
    assert "solución explicada" not in first.json()["attempt"]["hints"][0]["body"]
    client.post(f"/api/v1/learning/attempts/{attempt_id}/hint/", {}, format="json")
    third = client.post(f"/api/v1/learning/attempts/{attempt_id}/hint/", {}, format="json")
    assert third.json()["attempt"]["hints"][-1]["solution"] is True
    _stage(client, attempt_id, "comprender", {"ack": True})
    _stage(client, attempt_id, "razonar", {"text": "<-"})
    broken = client.post(
        f"/api/v1/learning/attempts/{attempt_id}/check/",
        {
            "workspace": {
                "blocks": {
                    "blocks": [
                        {
                            "type": "traza_asignar",
                            "id": "a1",
                            "fields": {"NOMBRE": "saludo"},
                            "inputs": {
                                "VALOR": {
                                    "block": {
                                        "type": "traza_cadena",
                                        "id": "c1",
                                        "fields": {"VALOR": "hola"},
                                    }
                                }
                            },
                        }
                    ]
                }
            }
        },
        format="json",
    )
    assert broken.json()["passed"] is False
    assert any(item["message"].startswith("Asignación:") for item in broken.json()["diagnostics"])
    stranger_id = attempt_id
    from rest_framework.test import APIClient

    stranger = APIClient()
    register(stranger, email="lab-fase5-ajeno@ejemplo.test")
    hidden = stranger.get(f"/api/v1/learning/challenges/{started['challenge']['id']}/")
    assert hidden.status_code == 403
    missing = stranger.post(
        f"/api/v1/learning/attempts/{stranger_id}/hint/",
        {},
        format="json",
    )
    assert missing.status_code == 404


def test_el_tiempo_configurado_cierra_el_intento_y_permite_otro(client) -> None:
    from datetime import timedelta

    from django.utils import timezone

    from apps.learning.models import Challenge

    register(client, email="lab-fase5-tiempo@ejemplo.test")
    started = _start(client, "Qué entra y qué sale")
    attempt_id = started["attempt"]["id"]
    assert started["attempt"]["seconds_left"] <= 180
    challenge = Challenge.objects.get(pk=started["challenge"]["id"])
    challenge.time_limit_seconds = 30
    challenge.save(update_fields=["time_limit_seconds"])
    attempt = ChallengeAttempt.objects.get(pk=attempt_id)
    attempt.started_at = timezone.now() - timedelta(seconds=31)
    attempt.save(update_fields=["started_at"])
    late = client.post(
        f"/api/v1/learning/attempts/{attempt_id}/stage/",
        {"stage": "comprender", "answer": {"ack": True}},
        format="json",
    )
    assert late.status_code == 409
    attempt.refresh_from_db()
    assert attempt.status == "abandoned"
    assert attempt.summary == "Se agotó el tiempo."
    assert attempt.elapsed_seconds >= 30
    again = _start(client, "Qué entra y qué sale")
    assert again["attempt"]["id"] != attempt_id
    assert again["attempt"]["status"] == "open"
    assert again["history"][0]["status"] == "abandoned"
    assert again["history"][0]["elapsed_seconds"] >= 30
    listed = _rows(client)["Qué entra y qué sale"]
    assert listed["attempt_count"] == 1
    assert again["challenge"]["time_limit_seconds"] == 30
    assert again["attempt"]["seconds_left"] > 0


def test_un_reto_cerrado_no_se_reabre_con_un_intento_vacio(client) -> None:
    from django.contrib.auth import get_user_model

    from apps.learning.models import Challenge

    register(client, email="lab-fase5-reabrir@ejemplo.test")
    first = _start(client, "Qué entra y qué sale")
    second = _start(client, "Qué entra y qué sale")
    assert second["attempt"]["id"] == first["attempt"]["id"]
    attempt_id = first["attempt"]["id"]
    _stage(client, attempt_id, "comprender", {"ack": True})
    restrictions = _spec("Qué entra y qué sale")["restrictions"]
    assert isinstance(restrictions, dict)
    choices = {item["id"]: item["category"] for item in restrictions["items"]}
    _stage(client, attempt_id, "razonar", {"choices": choices})
    _close(client, attempt_id)
    user = get_user_model().objects.get(email="lab-fase5-reabrir@ejemplo.test")
    challenge = Challenge.objects.get(pk=first["challenge"]["id"])
    ChallengeAttempt.objects.create(user=user, challenge=challenge)
    again = _start(client, "Qué entra y qué sale")
    assert again["attempt"]["id"] == attempt_id
    assert again["attempt"]["status"] == "completed"


def _block(
    type_name: str,
    ident: str,
    fields: dict[str, object] | None = None,
    inputs: dict[str, object] | None = None,
) -> dict[str, object]:
    data: dict[str, object] = {"type": type_name, "id": ident}
    if fields is not None:
        data["fields"] = fields
    if inputs is not None:
        data["inputs"] = inputs
    return data


def _link(blocks: list[dict[str, object]]) -> dict[str, object]:
    for earlier, later in zip(blocks, blocks[1:], strict=False):
        earlier["next"] = {"block": later}
    return {"blocks": {"languageVersion": 0, "blocks": [blocks[0]]}}


def _mark_done_before(email: str, title: str) -> None:
    from django.contrib.auth import get_user_model
    from django.utils import timezone

    from apps.learning.models import Challenge

    user = get_user_model().objects.get(email=email)
    pending = Challenge.objects.filter(unit__path__name="Fundamentos", is_published=True).order_by(
        "unit__position", "position"
    )
    for challenge in pending:
        if challenge.title == title:
            return
        if ChallengeAttempt.objects.filter(
            user=user, challenge=challenge, status="completed"
        ).exists():
            continue
        ChallengeAttempt.objects.create(
            user=user,
            challenge=challenge,
            status="completed",
            score=100,
            finished_at=timezone.now(),
            elapsed_seconds=1,
        )


MAYOR = _link(
    [
        _block("traza_definir", "d", {"NOMBRE": "edad", "TIPO": "entero"}),
        _block("traza_leer", "lee", {"NOMBRE": "edad"}),
        _block(
            "traza_si_sino",
            "si",
            inputs={
                "CONDICION": {
                    "block": _block(
                        "traza_relacional",
                        "c",
                        {"OPERADOR": "gte"},
                        {
                            "IZQUIERDA": {
                                "block": _block(
                                    "traza_variable", "v", {"NOMBRE": "edad", "TIPO": "entero"}
                                )
                            },
                            "DERECHA": {"block": _block("traza_entero", "n", {"VALOR": 18})},
                        },
                    )
                },
                "ENTONCES": {
                    "block": _block(
                        "traza_escribir",
                        "es",
                        inputs={"VALOR": {"block": _block("traza_cadena", "ts", {"VALOR": "si"})}},
                    )
                },
                "SINO": {
                    "block": _block(
                        "traza_escribir",
                        "en",
                        inputs={"VALOR": {"block": _block("traza_cadena", "tn", {"VALOR": "no"})}},
                    )
                },
            },
        ),
    ]
)


def _contar() -> dict[str, object]:
    increment = _block(
        "traza_asignar",
        "suma",
        {"NOMBRE": "cantidad"},
        {
            "VALOR": {
                "block": _block(
                    "traza_aritmetica",
                    "op",
                    {"OPERADOR": "add"},
                    {
                        "IZQUIERDA": {
                            "block": _block(
                                "traza_variable", "vc", {"NOMBRE": "cantidad", "TIPO": "entero"}
                            )
                        },
                        "DERECHA": {"block": _block("traza_entero", "uno", {"VALOR": 1})},
                    },
                )
            }
        },
    )
    branch = _block(
        "traza_si",
        "si",
        inputs={
            "CONDICION": {
                "block": _block(
                    "traza_relacional",
                    "pos",
                    {"OPERADOR": "gt"},
                    {
                        "IZQUIERDA": {
                            "block": _block(
                                "traza_variable", "vp", {"NOMBRE": "n", "TIPO": "entero"}
                            )
                        },
                        "DERECHA": {"block": _block("traza_entero", "cero", {"VALOR": 0})},
                    },
                )
            },
            "ENTONCES": {"block": increment},
        },
    )
    branch["next"] = {"block": _block("traza_leer", "lee2", {"NOMBRE": "n"})}
    loop = _block(
        "traza_mientras",
        "ciclo",
        inputs={
            "CONDICION": {
                "block": _block(
                    "traza_relacional",
                    "dist",
                    {"OPERADOR": "neq"},
                    {
                        "IZQUIERDA": {
                            "block": _block(
                                "traza_variable", "vn", {"NOMBRE": "n", "TIPO": "entero"}
                            )
                        },
                        "DERECHA": {"block": _block("traza_entero", "fin", {"VALOR": 0})},
                    },
                )
            },
            "CUERPO": {"block": branch},
        },
    )
    return _link(
        [
            _block("traza_definir", "dn", {"NOMBRE": "n", "TIPO": "entero"}),
            _block("traza_definir", "dc", {"NOMBRE": "cantidad", "TIPO": "entero"}),
            _block(
                "traza_asignar",
                "inicio",
                {"NOMBRE": "cantidad"},
                {"VALOR": {"block": _block("traza_entero", "base", {"VALOR": 0})}},
            ),
            _block("traza_leer", "lee", {"NOMBRE": "n"}),
            loop,
            _block(
                "traza_escribir",
                "out",
                inputs={
                    "VALOR": {
                        "block": _block(
                            "traza_variable", "vo", {"NOMBRE": "cantidad", "TIPO": "entero"}
                        )
                    }
                },
            ),
        ]
    )


def test_si_y_mientras_cubren_casos_normales_y_de_frontera(client) -> None:
    email = "lab-fase6@ejemplo.test"
    register(client, email=email)
    before = Execution.objects.count()
    _mark_done_before(email, "Partes de una decisión")

    classify = _spec("Partes de una decisión")
    rules = classify["restrictions"]
    assert isinstance(rules, dict)
    started = _start(client, "Partes de una decisión")
    attempt_id = started["attempt"]["id"]
    _stage(client, attempt_id, "comprender", {"ack": True})
    choices = {item["id"]: item["category"] for item in rules["items"]}
    graded = _stage(client, attempt_id, "razonar", {"choices": choices})
    assert graded["correct"] is True
    _close(client, attempt_id)

    order = _spec("Orden del Si")
    order_rules = order["restrictions"]
    assert isinstance(order_rules, dict)
    started = _start(client, "Orden del Si")
    attempt_id = started["attempt"]["id"]
    _stage(client, attempt_id, "comprender", {"ack": True})
    graded = _stage(client, attempt_id, "razonar", {"order": order_rules["solution"]})
    assert graded["correct"] is True
    _close(client, attempt_id)

    predict = _spec("La rama del cero")
    predict_rules = predict["restrictions"]
    assert isinstance(predict_rules, dict)
    started = _start(client, "La rama del cero")
    attempt_id = started["attempt"]["id"]
    raw = json.dumps(started["challenge"])
    assert "accepted" not in raw
    assert "Sino" in started["challenge"]["task"]["source"]
    _stage(client, attempt_id, "comprender", {"ack": True})
    answer = _stage(client, attempt_id, "razonar", {"text": "cero"})
    assert answer["correct"] is True
    ran = client.post(f"/api/v1/learning/attempts/{attempt_id}/run/", {}, format="json")
    assert ran.status_code == 200, ran.content
    assert ran.json()["output"] == "cero\n"
    _close(client, attempt_id)

    started = _start(client, "Mayor de edad")
    attempt_id = started["attempt"]["id"]
    _stage(client, attempt_id, "comprender", {"ack": True})
    _stage(client, attempt_id, "razonar", {"text": "sino"})
    checked = client.post(
        f"/api/v1/learning/attempts/{attempt_id}/check/",
        {"workspace": MAYOR},
        format="json",
    )
    assert checked.status_code == 200, checked.content
    body = checked.json()
    assert body["passed"] is True
    assert {case["kind"] for case in body["cases"]} == {"normal", "boundary"}
    assert all(case["passed"] for case in body["cases"])
    _close(client, attempt_id)

    _mark_done_before(email, "Contar positivos")
    started = _start(client, "Contar positivos")
    attempt_id = started["attempt"]["id"]
    _stage(client, attempt_id, "comprender", {"ack": True})
    _stage(client, attempt_id, "razonar", {"text": "mientras"})
    missing = client.post(
        f"/api/v1/learning/attempts/{attempt_id}/check/",
        {"workspace": _link([_block("traza_definir", "d", {"NOMBRE": "n", "TIPO": "entero"})])},
        format="json",
    )
    assert missing.status_code == 200
    assert missing.json()["passed"] is False
    assert any("Ciclo mientras" in item["message"] for item in missing.json()["diagnostics"])
    checked = client.post(
        f"/api/v1/learning/attempts/{attempt_id}/check/",
        {"workspace": _contar()},
        format="json",
    )
    assert checked.status_code == 200, checked.content
    body = checked.json()
    assert body["passed"] is True
    assert {case["name"] for case in body["cases"]} == {
        "dos positivos",
        "solo el cero",
        "un negativo",
    }
    assert all(case["passed"] for case in body["cases"])
    _close(client, attempt_id)
    assert Execution.objects.count() == before


def _menu() -> dict[str, object]:
    return _link(
        [
            _block("traza_definir", "d", {"NOMBRE": "opcion", "TIPO": "entero"}),
            _block("traza_leer", "lee", {"NOMBRE": "opcion"}),
            _block(
                "traza_segun",
                "sg",
                inputs={
                    "VALOR": {
                        "block": _block(
                            "traza_variable", "vo", {"NOMBRE": "opcion", "TIPO": "entero"}
                        )
                    },
                    "CASO1": {"block": _block("traza_entero", "c1", {"VALOR": 1})},
                    "HACER1": {
                        "block": _block(
                            "traza_escribir",
                            "e1",
                            inputs={
                                "VALOR": {"block": _block("traza_cadena", "t1", {"VALOR": "uno"})}
                            },
                        )
                    },
                    "CASO2": {"block": _block("traza_entero", "c2", {"VALOR": 2})},
                    "HACER2": {
                        "block": _block(
                            "traza_escribir",
                            "e2",
                            inputs={
                                "VALOR": {"block": _block("traza_cadena", "t2", {"VALOR": "dos"})}
                            },
                        )
                    },
                    "OTRO": {
                        "block": _block(
                            "traza_escribir",
                            "e0",
                            inputs={
                                "VALOR": {"block": _block("traza_cadena", "t0", {"VALOR": "otro"})}
                            },
                        )
                    },
                },
            ),
        ]
    )


def _contar_hasta() -> dict[str, object]:
    return _link(
        [
            _block("traza_definir", "dn", {"NOMBRE": "n", "TIPO": "entero"}),
            _block("traza_definir", "di", {"NOMBRE": "i", "TIPO": "entero"}),
            _block("traza_leer", "lee", {"NOMBRE": "n"}),
            _block(
                "traza_para",
                "p",
                {"NOMBRE": "i"},
                {
                    "DESDE": {"block": _block("traza_entero", "a", {"VALOR": 1})},
                    "HASTA": {
                        "block": _block("traza_variable", "vn", {"NOMBRE": "n", "TIPO": "entero"})
                    },
                    "PASO": {"block": _block("traza_entero", "s", {"VALOR": 1})},
                    "CUERPO": {
                        "block": _block(
                            "traza_escribir",
                            "e",
                            inputs={
                                "VALOR": {
                                    "block": _block(
                                        "traza_variable", "vi", {"NOMBRE": "i", "TIPO": "entero"}
                                    )
                                }
                            },
                        )
                    },
                },
            ),
        ]
    )


def _subir() -> dict[str, object]:
    step = _block(
        "traza_asignar",
        "suma",
        {"NOMBRE": "n"},
        {
            "VALOR": {
                "block": _block(
                    "traza_aritmetica",
                    "op",
                    {"OPERADOR": "add"},
                    {
                        "IZQUIERDA": {
                            "block": _block(
                                "traza_variable", "vn", {"NOMBRE": "n", "TIPO": "entero"}
                            )
                        },
                        "DERECHA": {"block": _block("traza_entero", "uno", {"VALOR": 1})},
                    },
                )
            }
        },
    )
    step["next"] = {
        "block": _block(
            "traza_escribir",
            "e",
            inputs={
                "VALOR": {
                    "block": _block("traza_variable", "vo", {"NOMBRE": "n", "TIPO": "entero"})
                }
            },
        )
    }
    return _link(
        [
            _block("traza_definir", "dt", {"NOMBRE": "tope", "TIPO": "entero"}),
            _block("traza_definir", "dn", {"NOMBRE": "n", "TIPO": "entero"}),
            _block("traza_leer", "lee", {"NOMBRE": "tope"}),
            _block(
                "traza_asignar",
                "cero",
                {"NOMBRE": "n"},
                {"VALOR": {"block": _block("traza_entero", "z", {"VALOR": 0})}},
            ),
            _block(
                "traza_repetir",
                "r",
                inputs={
                    "CUERPO": {"block": step},
                    "CONDICION": {
                        "block": _block(
                            "traza_relacional",
                            "c",
                            {"OPERADOR": "eq"},
                            {
                                "IZQUIERDA": {
                                    "block": _block(
                                        "traza_variable", "vn2", {"NOMBRE": "n", "TIPO": "entero"}
                                    )
                                },
                                "DERECHA": {
                                    "block": _block(
                                        "traza_variable", "vt", {"NOMBRE": "tope", "TIPO": "entero"}
                                    )
                                },
                            },
                        )
                    },
                },
            ),
        ]
    )


def _check(client, attempt_id: str, workspace: dict[str, object]) -> dict:
    response = client.post(
        f"/api/v1/learning/attempts/{attempt_id}/check/",
        {"workspace": workspace},
        format="json",
    )
    assert response.status_code == 200, response.content
    return response.json()


def test_segun_para_y_repetir(client) -> None:
    email = "lab-segun@ejemplo.test"
    register(client, email=email)
    before = Execution.objects.count()
    _mark_done_before(email, "Partes de un Segun")

    rules = _spec("Partes de un Segun")["restrictions"]
    assert isinstance(rules, dict)
    started = _start(client, "Partes de un Segun")
    attempt_id = started["attempt"]["id"]
    _stage(client, attempt_id, "comprender", {"ack": True})
    choices = {item["id"]: item["category"] for item in rules["items"]}
    assert _stage(client, attempt_id, "razonar", {"choices": choices})["correct"] is True
    _close(client, attempt_id)

    _mark_done_before(email, "Qué caso se escribe")
    started = _start(client, "Qué caso se escribe")
    attempt_id = started["attempt"]["id"]
    assert "Segun" in started["challenge"]["task"]["source"]
    assert "accepted" not in json.dumps(started["challenge"])
    _stage(client, attempt_id, "comprender", {"ack": True})
    assert _stage(client, attempt_id, "razonar", {"text": "dos"})["correct"] is True
    ran = client.post(f"/api/v1/learning/attempts/{attempt_id}/run/", {}, format="json")
    assert ran.status_code == 200, ran.content
    assert ran.json()["output"] == "dos\n"
    _close(client, attempt_id)

    _mark_done_before(email, "Menú de una opción")
    started = _start(client, "Menú de una opción")
    attempt_id = started["attempt"]["id"]
    _stage(client, attempt_id, "comprender", {"ack": True})
    _stage(client, attempt_id, "razonar", {"text": "De Otro Modo"})
    menu = _check(client, attempt_id, _menu())
    assert menu["passed"] is True
    assert {case["kind"] for case in menu["cases"]} == {"normal", "boundary"}
    assert all(case["passed"] for case in menu["cases"])
    _close(client, attempt_id)

    _mark_done_before(email, "Contar hasta n")
    started = _start(client, "Contar hasta n")
    attempt_id = started["attempt"]["id"]
    _stage(client, attempt_id, "comprender", {"ack": True})
    _stage(client, attempt_id, "razonar", {"text": "finpara"})
    counted = _check(client, attempt_id, _contar_hasta())
    assert counted["passed"] is True
    assert {case["name"] for case in counted["cases"]} == {"hasta tres", "hasta uno"}
    _close(client, attempt_id)

    _mark_done_before(email, "Subir hasta el tope")
    started = _start(client, "Subir hasta el tope")
    attempt_id = started["attempt"]["id"]
    _stage(client, attempt_id, "comprender", {"ack": True})
    _stage(client, attempt_id, "razonar", {"text": "al final"})
    missing = _check(
        client,
        attempt_id,
        _link([_block("traza_definir", "d", {"NOMBRE": "n", "TIPO": "entero"})]),
    )
    assert missing["passed"] is False
    assert any("Ciclo repetir" in item["message"] for item in missing["diagnostics"])
    climbed = _check(client, attempt_id, _subir())
    assert climbed["passed"] is True
    assert all(case["passed"] for case in climbed["cases"])
    _close(client, attempt_id)
    assert Execution.objects.count() == before


def test_arreglos_y_funciones(client) -> None:
    from apps.learning.path_data import _DOBLAR, _definir, _escribir, _first, _variable

    email = "lab-fase7@ejemplo.test"
    register(client, email=email)
    before = Execution.objects.count()
    _mark_done_before(email, "Casilla, tamaño y valor")

    rules = _spec("Casilla, tamaño y valor")["restrictions"]
    assert isinstance(rules, dict)
    started = _start(client, "Casilla, tamaño y valor")
    attempt_id = started["attempt"]["id"]
    _stage(client, attempt_id, "comprender", {"ack": True})
    choices = {item["id"]: item["category"] for item in rules["items"]}
    assert _stage(client, attempt_id, "razonar", {"choices": choices})["correct"] is True
    _close(client, attempt_id)

    _mark_done_before(email, "La casilla uno")
    started = _start(client, "La casilla uno")
    attempt_id = started["attempt"]["id"]
    assert "datos[1]" in started["challenge"]["task"]["source"]
    _stage(client, attempt_id, "comprender", {"ack": True})
    assert _stage(client, attempt_id, "razonar", {"text": "8"})["correct"] is True
    ran = client.post(f"/api/v1/learning/attempts/{attempt_id}/run/", {}, format="json")
    assert ran.status_code == 200, ran.content
    assert ran.json()["output"] == "8\n"
    _close(client, attempt_id)

    _mark_done_before(email, "La primera y la última")
    started = _start(client, "La primera y la última")
    attempt_id = started["attempt"]["id"]
    _stage(client, attempt_id, "comprender", {"ack": True})
    _stage(client, attempt_id, "razonar", {"text": "corchetes"})
    extremos = _check(client, attempt_id, _extremos())
    assert extremos["passed"] is True
    assert {case["name"] for case in extremos["cases"]} == {"cuatro y uno", "ceros"}
    _close(client, attempt_id)

    _mark_done_before(email, "El doble de tres")
    started = _start(client, "El doble de tres")
    attempt_id = started["attempt"]["id"]
    assert "Doblar" in started["challenge"]["task"]["source"]
    _stage(client, attempt_id, "comprender", {"ack": True})
    assert _stage(client, attempt_id, "razonar", {"text": "6"})["correct"] is True
    ran = client.post(f"/api/v1/learning/attempts/{attempt_id}/run/", {}, format="json")
    assert ran.json()["output"] == "6\n"
    _close(client, attempt_id)

    _mark_done_before(email, "Doblar lo leído")
    started = _start(client, "Doblar lo leído")
    attempt_id = started["attempt"]["id"]
    _stage(client, attempt_id, "comprender", {"ack": True})
    _stage(client, attempt_id, "razonar", {"text": "FinFuncion"})
    doblar = _check(
        client,
        attempt_id,
        {
            "blocks": {
                "languageVersion": 0,
                "blocks": [
                    json.loads(json.dumps(_DOBLAR)),
                    _first(
                        [
                            _definir("dnum", "numero", "entero"),
                            _block("traza_leer", "lee", {"NOMBRE": "numero"}),
                            _escribir(
                                "e",
                                {
                                    "type": "traza_llamada",
                                    "id": "ll",
                                    "fields": {"NOMBRE": "Doblar", "TIPO": "entero"},
                                    "extraState": {"argumentos": 1},
                                    "inputs": {
                                        "ARG1": {
                                            "block": _variable("vnum", "numero"),
                                        }
                                    },
                                },
                            ),
                        ]
                    ),
                ],
            }
        },
    )
    assert doblar["passed"] is True, doblar
    _close(client, attempt_id)

    _mark_done_before(email, "Sumar uno por referencia")
    started = _start(client, "Sumar uno por referencia")
    attempt_id = started["attempt"]["id"]
    _stage(client, attempt_id, "comprender", {"ack": True})
    _stage(client, attempt_id, "razonar", {"text": "referencia"})
    missing = _check(
        client,
        attempt_id,
        _link([_block("traza_definir", "d", {"NOMBRE": "edad", "TIPO": "entero"})]),
    )
    assert missing["passed"] is False
    assert any("Funciones" in item["message"] for item in missing["diagnostics"])
    subido = _check(client, attempt_id, _incrementar())
    assert subido["passed"] is True, subido
    assert Execution.objects.count() == before


def _extremos() -> dict[str, object]:
    from apps.learning.path_data import _arit, _dimension, _entero, _escribir, _indice, _leer_indice

    return _link(
        [
            _block("traza_definir", "d", {"NOMBRE": "datos", "TIPO": "entero"}),
            _dimension("dim", "datos", _entero("tam", 3)),
            _leer_indice("l1", "datos", _entero("i1", 1)),
            _leer_indice("l2", "datos", _entero("i2", 2)),
            _leer_indice("l3", "datos", _entero("i3", 3)),
            _escribir(
                "e",
                _arit(
                    "op",
                    "add",
                    _indice("c1", "datos", _entero("a", 1)),
                    _indice("c3", "datos", _entero("c", 3)),
                ),
            ),
        ]
    )


def _incrementar() -> dict[str, object]:
    from apps.learning.path_data import (
        _arit,
        _asignar,
        _definir,
        _entero,
        _escribir,
        _first,
        _variable,
    )

    procedure = {
        "type": "traza_procedimiento",
        "id": "proc",
        "fields": {"NOMBRE": "Incrementar", "PARAM1": "n", "MODO1": "referencia"},
        "extraState": {"parametros": 1},
        "inputs": {
            "CUERPO": {
                "block": _first(
                    [
                        _definir("dn", "n", "entero"),
                        _asignar(
                            "ae",
                            "n",
                            _arit("sum", "add", _variable("vn", "n"), _entero("uno", 1)),
                        ),
                    ]
                )
            }
        },
    }
    llamada = {
        "type": "traza_llamar",
        "id": "lz",
        "fields": {"NOMBRE": "Incrementar"},
        "extraState": {"argumentos": 1},
        "inputs": {"ARG1": {"block": _variable("va", "edad")}},
    }
    return {
        "blocks": {
            "languageVersion": 0,
            "blocks": [
                procedure,
                _first(
                    [
                        _definir("de", "edad", "entero"),
                        _block("traza_leer", "lee", {"NOMBRE": "edad"}),
                        llamada,
                        _escribir("e", _variable("vo", "edad")),
                    ]
                ),
            ],
        }
    }


def _finish_until(client, title: str) -> None:
    order = []
    for unit in PATH["units"]:
        assert isinstance(unit, dict)
        order.extend(challenge["title"] for challenge in unit["challenges"])
    for name in order:
        if name == title:
            return
        spec = _spec(name)
        started = _start(client, name)
        attempt_id = started["attempt"]["id"]
        _stage(client, attempt_id, "comprender", {"ack": True})
        restrictions = spec["restrictions"]
        assert isinstance(restrictions, dict)
        if spec["activity_type"] == "classify":
            choices = {item["id"]: item["category"] for item in restrictions["items"]}
            _stage(client, attempt_id, "razonar", {"choices": choices})
        elif spec["activity_type"] == "order":
            _stage(client, attempt_id, "razonar", {"order": restrictions["solution"]})
        _close(client, attempt_id)
