"""Normaliza las preguntas antes de guardarlas."""

from __future__ import annotations

import json
import secrets
from decimal import Decimal, InvalidOperation

from apps.exams.grading import money
from config.errors import DomainError

KINDS = {
    "choice",
    "multi",
    "true_false",
    "short",
    "numerical",
    "essay",
    "matching",
    "order",
    "cloze",
    "case",
}


def clean_text(value: object, *, field: str, limit: int, required: bool) -> str:
    if value is None or value == "":
        if required:
            raise DomainError(f"Falta {field}.")
        return ""
    if not isinstance(value, str):
        raise DomainError(f"{field} no es válido.")
    text = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if required and not text:
        raise DomainError(f"Falta {field}.")
    if any(ord(character) < 32 and character not in "\n\t" for character in text):
        raise DomainError(f"{field} contiene caracteres de control.")
    if len(text) > limit:
        raise DomainError(f"{field} es demasiado largo.")
    return text


def clean_points(value: object, *, field: str = "El puntaje") -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise DomainError(f"{field} no es válido.")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise DomainError(f"{field} no es válido.") from exc
    if not number.is_finite():
        raise DomainError(f"{field} no es válido.")
    number = money(number)
    if number < Decimal("0.01") or number > Decimal(100):
        raise DomainError(f"{field} no es válido.")
    return number


def _token(value: object) -> str:
    if (
        isinstance(value, str)
        and value
        and len(value) <= 16
        and all(ch.isalnum() or ch in "_-" for ch in value)
    ):
        return value
    return secrets.token_hex(4)


def _rows(value: object, *, field: str, limit: int) -> list:
    if not isinstance(value, list) or not value or len(value) > limit:
        raise DomainError(f"{field} no es válido.")
    return value


def clean_questions(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise DomainError("Las preguntas no son válidas.")
    if len(value) > 60:
        raise DomainError("Hay demasiadas preguntas.")
    return [clean_question(item) for item in value]


def clean_question(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise DomainError("La pregunta no es válida.")
    kind = value.get("kind")
    if kind not in KINDS:
        raise DomainError("El tipo de pregunta no es válido.")
    payload = value.get("payload")
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise DomainError("La pregunta no es válida.")
    cleaned = {
        "kind": kind,
        "prompt": clean_text(value.get("prompt"), field="el enunciado", limit=4000, required=True),
        "points": clean_points(value.get("points", 1)),
        "feedback": clean_text(
            value.get("feedback"), field="la retroalimentación", limit=1000, required=False
        ),
        "payload": _payload(kind, payload),
    }
    if len(json.dumps(cleaned["payload"])) > 40000:
        raise DomainError("La pregunta es demasiado grande.")
    return cleaned


def clean_answer(value: object) -> dict:
    if not isinstance(value, dict):
        raise DomainError("La respuesta no es válida.")
    try:
        raw = json.dumps(value)
    except (TypeError, ValueError) as exc:
        raise DomainError("La respuesta no es válida.") from exc
    if len(raw) > 30000:
        raise DomainError("La respuesta es demasiado larga.")
    return value


def _payload(kind: str, payload: dict) -> dict:
    if kind in {"choice", "multi"}:
        return _options(payload, single=kind == "choice")
    if kind == "true_false":
        if not isinstance(payload.get("correct"), bool):
            raise DomainError("Indica si la respuesta es verdadero o falso.")
        return {"correct": payload["correct"]}
    if kind == "short":
        return _short(payload)
    if kind == "numerical":
        return _numerical(payload)
    if kind == "essay":
        return {
            "rubric": clean_text(
                payload.get("rubric"), field="la rúbrica", limit=2000, required=False
            )
        }
    if kind == "matching":
        return _pairs(payload)
    if kind == "order":
        return _items(payload)
    if kind == "cloze":
        return _cloze(payload)
    return _case(payload)


def _options(payload: dict, *, single: bool) -> dict:
    rows = _rows(payload.get("options"), field="Las opciones", limit=10)
    options = []
    seen: set[str] = set()
    for item in rows:
        if not isinstance(item, dict):
            raise DomainError("Las opciones no son válidas.")
        token = _token(item.get("id"))
        if token in seen:
            token = secrets.token_hex(4)
        seen.add(token)
        options.append(
            {
                "id": token,
                "text": clean_text(item.get("text"), field="la opción", limit=500, required=True),
                "correct": item.get("correct") is True,
            }
        )
    correct = [item for item in options if item["correct"]]
    if single and len(correct) != 1:
        raise DomainError("Indica una respuesta correcta.")
    if not single and not correct:
        raise DomainError("Indica la respuesta correcta.")
    return {"options": options}


def _fraction(value: object) -> int:
    number = clean_points(value if value not in (None, "") else 100, field="El porcentaje")
    if number > 100:
        raise DomainError("El porcentaje no es válido.")
    whole = int(number)
    if Decimal(whole) != number:
        raise DomainError("El porcentaje no es válido.")
    return whole


def _short(payload: dict) -> dict:
    rows = _rows(payload.get("answers"), field="Las respuestas aceptadas", limit=12)
    answers = []
    for item in rows:
        if not isinstance(item, dict):
            raise DomainError("Las respuestas aceptadas no son válidas.")
        answers.append(
            {
                "text": clean_text(
                    item.get("text"), field="la respuesta", limit=300, required=True
                ),
                "fraction": _fraction(item.get("fraction", 100)),
            }
        )
    return {"answers": answers, "case_sensitive": payload.get("case_sensitive") is True}


def _numerical(payload: dict) -> dict:
    rows = _rows(payload.get("answers"), field="La respuesta numérica", limit=8)
    answers = []
    for item in rows:
        if not isinstance(item, dict):
            raise DomainError("La respuesta numérica no es válida.")
        value = item.get("value")
        tolerance = item.get("tolerance", 0)
        try:
            number = Decimal(str(value))
            slack = Decimal(str(tolerance if tolerance not in (None, "") else 0))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise DomainError("La respuesta numérica no es válida.") from exc
        if isinstance(value, bool) or not number.is_finite() or not slack.is_finite() or slack < 0:
            raise DomainError("La respuesta numérica no es válida.")
        answers.append(
            {
                "value": float(number),
                "tolerance": float(slack),
                "fraction": _fraction(item.get("fraction", 100)),
            }
        )
    return {"answers": answers}


def _pairs(payload: dict) -> dict:
    rows = _rows(payload.get("pairs"), field="Las parejas", limit=10)
    pairs = []
    seen: set[str] = set()
    for item in rows:
        if not isinstance(item, dict):
            raise DomainError("Las parejas no son válidas.")
        token = _token(item.get("id"))
        if token in seen:
            token = secrets.token_hex(4)
        seen.add(token)
        pairs.append(
            {
                "id": token,
                "left": clean_text(
                    item.get("left"), field="el enunciado", limit=300, required=True
                ),
                "right": clean_text(item.get("right"), field="la pareja", limit=300, required=True),
            }
        )
    return {"pairs": pairs}


def _items(payload: dict) -> dict:
    rows = _rows(payload.get("items"), field="El orden", limit=10)
    items = []
    seen: set[str] = set()
    for item in rows:
        if not isinstance(item, dict):
            raise DomainError("El orden no es válido.")
        token = _token(item.get("id"))
        if token in seen:
            token = secrets.token_hex(4)
        seen.add(token)
        items.append(
            {
                "id": token,
                "text": clean_text(item.get("text"), field="el elemento", limit=300, required=True),
            }
        )
    if len(items) < 2:
        raise DomainError("El orden necesita al menos dos elementos.")
    return {"items": items}


def _cloze(payload: dict) -> dict:
    text = clean_text(payload.get("text"), field="el texto", limit=4000, required=True)
    rows = _rows(payload.get("blanks"), field="Los huecos", limit=12)
    blanks = []
    seen: set[str] = set()
    for item in rows:
        if not isinstance(item, dict):
            raise DomainError("Los huecos no son válidos.")
        token = _token(item.get("id"))
        if token in seen:
            token = secrets.token_hex(4)
        seen.add(token)
        answers = item.get("answers")
        if not isinstance(answers, list) or not answers or len(answers) > 8:
            raise DomainError("Los huecos no son válidos.")
        blanks.append(
            {
                "id": token,
                "answers": [
                    clean_text(answer, field="la respuesta", limit=200, required=True)
                    for answer in answers
                ],
            }
        )
        if token not in text:
            raise DomainError("El texto no marca todos los huecos.")
    return {"text": text, "blanks": blanks}


def _case(payload: dict) -> dict:
    rows = _rows(payload.get("cases"), field="Los casos", limit=8)
    cases = []
    for item in rows:
        if not isinstance(item, dict):
            raise DomainError("Los casos no son válidos.")
        inputs = item.get("inputs")
        if inputs is None:
            inputs = []
        if not isinstance(inputs, list) or len(inputs) > 20:
            raise DomainError("Los casos no son válidos.")
        clean_inputs = []
        for raw in inputs:
            if not isinstance(raw, str) or len(raw) > 200:
                raise DomainError("Los casos no son válidos.")
            if any(ord(character) < 32 and character not in "\t" for character in raw):
                raise DomainError("Los casos no son válidos.")
            clean_inputs.append(raw)
        weight = item.get("points", 1)
        try:
            points = Decimal(str(weight))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise DomainError("El puntaje del caso no es válido.") from exc
        if isinstance(weight, bool) or not points.is_finite() or points <= 0 or points > 100:
            raise DomainError("El puntaje del caso no es válido.")
        cases.append(
            {
                "name": clean_text(item.get("name"), field="el caso", limit=80, required=True),
                "inputs": clean_inputs,
                "expected": clean_text(
                    item.get("expected"), field="la salida", limit=2000, required=False
                ),
                "points": float(money(points)),
                "hidden": item.get("hidden") is True,
            }
        )
    return {
        "statement": clean_text(
            payload.get("statement"), field="el enunciado", limit=4000, required=True
        ),
        "starter": clean_text(
            payload.get("starter"), field="el código inicial", limit=8000, required=False
        ),
        "cases": cases,
    }
