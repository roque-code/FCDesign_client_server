"""Carga retos de un CSV. El formato depende del tipo de reto."""

from __future__ import annotations

import csv
import io

from django.db import transaction

from apps.learning.authoring import create_challenge
from apps.learning.catalog import CONCEPTS
from config.errors import DomainError

_MAX_BYTES = 200_000
_MAX_ROWS = 80
_TYPES = {
    "clasificar": "classify",
    "classify": "classify",
    "ordenar": "order",
    "order": "order",
    "construir": "build",
    "build": "build",
    "predecir": "predict",
    "predict": "predict",
}
_ALIASES = {
    "type": "tipo",
    "title": "titulo",
    "prompt": "enunciado",
    "concept": "concepto",
    "difficulty": "dificultad",
    "points": "puntos",
    "minutes": "minutos",
    "question": "pregunta",
    "answers": "respuestas",
    "source": "pseudocodigo",
    "categories": "categorias",
    "items": "frases",
    "steps": "instrucciones",
    "hint1": "pista1",
    "hint2": "pista2",
    "hint3": "pista3",
    "hint4": "pista4",
    "hint5": "pista5",
}
_COMMON = ["tipo", "titulo", "enunciado", "concepto", "dificultad", "puntos", "minutos"]
_HINTS = ["pista1", "pista2", "pista3", "pista4", "pista5"]
_SPECIFIC = {
    "clasificar": ["categorias", "frases"],
    "ordenar": ["instrucciones"],
    "construir": ["pregunta", "respuestas"]
    + [name for index in range(1, 7) for name in (f"caso{index}_entradas", f"caso{index}_salida")],
    "predecir": ["pregunta", "respuestas", "pseudocodigo"],
}
_NOTES = {
    "clasificar": (
        "categorias separa los nombres con |. "
        "frases usa texto => categoria y separa las frases con |."
    ),
    "ordenar": "instrucciones van en el orden correcto, separadas con |.",
    "construir": (
        "respuestas separa las opciones con |. "
        "Cada caso usa casoN_entradas (valores separados con |) y casoN_salida. "
        "Los casos van del 1 al 6, sin huecos. "
        "En la salida, \\n es un salto de línea. "
        "El reto abre código, diagrama y bloques. "
        "La salida esperada es el texto completo: cada Leer también escribe el dato."
    ),
    "predecir": (
        "respuestas separa las opciones con |. "
        "pseudocodigo es el programa. \\n es un salto de línea. "
        "El algoritmo se llama Laboratorio y no usa Leer."
    ),
}


def formats_payload() -> dict[str, object]:
    return {
        "types": [
            {
                "tipo": kind,
                "columns": _COMMON + _SPECIFIC[kind] + _HINTS,
                "notes": _NOTES[kind],
                "example": template_csv(kind),
            }
            for kind in ("clasificar", "ordenar", "construir", "predecir")
        ]
    }


def template_csv(kind: str) -> str:
    columns = _columns(kind)
    row = _example(kind)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerow({column: row.get(column, "") for column in columns})
    return buffer.getvalue()


def import_challenges(teacher, text: object) -> dict[str, object]:
    if not isinstance(text, str) or not text.strip():
        raise DomainError("El archivo CSV está vacío.")
    if len(text.encode("utf-8")) > _MAX_BYTES:
        raise DomainError("El archivo CSV es demasiado grande.")
    rows = _rows(text)
    if len(rows) > _MAX_ROWS:
        raise DomainError(f"El archivo admite hasta {_MAX_ROWS} retos.")
    problems: list[str] = []
    payloads: list[tuple[int, dict[str, object]]] = []
    for line, row in rows:
        try:
            payloads.append((line, _payload(row)))
        except DomainError as exc:
            problems.append(f"Fila {line}: {exc.message}")
    if problems:
        raise DomainError("No se importó ningún reto. " + " ".join(problems[:8]))
    created: list[dict[str, object]] = []
    with transaction.atomic():
        for line, payload in payloads:
            try:
                created.append(create_challenge(teacher, payload))
            except DomainError as exc:
                raise DomainError(f"No se importó ningún reto. Fila {line}: {exc.message}") from exc
    return {"created": len(created), "titles": [item["title"] for item in created]}


def _columns(kind: str) -> list[str]:
    if kind not in _SPECIFIC:
        raise DomainError("El tipo de plantilla no existe.")
    return _COMMON + _SPECIFIC[kind] + _HINTS


def _rows(text: str) -> list[tuple[int, dict[str, str]]]:
    sample = text.lstrip("\ufeff")
    header = sample.splitlines()[0] if sample.splitlines() else ""
    delimiter = ";" if header.count(";") > header.count(",") else ","
    reader = csv.DictReader(io.StringIO(sample), delimiter=delimiter)
    if reader.fieldnames is None:
        raise DomainError("El CSV no tiene encabezado.")
    reader.fieldnames = [_header(name) for name in reader.fieldnames]
    if "tipo" not in reader.fieldnames:
        raise DomainError("Falta la columna tipo.")
    rows: list[tuple[int, dict[str, str]]] = []
    for raw in reader:
        if raw is None:
            continue
        values = {key: (value or "").strip() for key, value in raw.items() if key}
        if not any(values.values()):
            continue
        rows.append((reader.line_num, values))
    if not rows:
        raise DomainError("El CSV no trae retos.")
    return rows


def _header(name: str | None) -> str:
    text = (name or "").strip().lstrip("\ufeff").casefold()
    return _ALIASES.get(text, text)


def _payload(row: dict[str, str]) -> dict[str, object]:
    kind = row.get("tipo", "").casefold()
    activity = _TYPES.get(kind)
    if activity is None:
        raise DomainError("El tipo de reto no existe.")
    hints = [row[name] for name in _HINTS if row.get(name)]
    payload: dict[str, object] = {
        "title": row.get("titulo", ""),
        "prompt": row.get("enunciado", ""),
        "activity_type": activity,
        "concept": _concept(row.get("concepto", "")),
        "difficulty": _number(row.get("dificultad", ""), "La dificultad", 1, 5, default=1),
        "points": _number(row.get("puntos", ""), "Los puntos", 1, 500, default=10),
        "time_limit_seconds": _minutes(row.get("minutos", "")),
        "hints": hints,
    }
    if activity == "classify":
        payload["categories"] = _pieces(row.get("categorias", ""), "Las categorías")
        payload["items"] = _labeled(row.get("frases", ""))
    elif activity == "order":
        payload["items"] = _pieces(row.get("instrucciones", ""), "Las instrucciones")
    elif activity == "build":
        payload["question"] = row.get("pregunta", "")
        payload["accepted"] = _pieces(row.get("respuestas", ""), "Las respuestas")
        payload["cases"] = _cases(row)
        payload["tools"] = ["codigo", "diagrama", "bloques"]
    else:
        payload["question"] = row.get("pregunta", "")
        payload["accepted"] = _pieces(row.get("respuestas", ""), "Las respuestas")
        payload["source"] = _unescape(row.get("pseudocodigo", ""))
    return payload


def _concept(value: str) -> str:
    text = value.strip()
    if not text:
        raise DomainError("Falta el concepto.")
    folded = text.casefold()
    for key, name in CONCEPTS:
        if folded in {key.casefold(), name.casefold()}:
            return key
    raise DomainError("El concepto no existe.")


def _number(value: str, field: str, low: int, high: int, *, default: int) -> int:
    text = value.strip()
    if not text:
        return default
    if not text.isdigit():
        raise DomainError(f"{field} no es válido.")
    number = int(text)
    if number < low or number > high:
        raise DomainError(f"{field} no es válido.")
    return number


def _minutes(value: str) -> int | None:
    text = value.strip()
    if not text:
        return None
    if not text.isdigit():
        raise DomainError("Los minutos no son válidos.")
    minutes = int(text)
    if minutes < 1 or minutes > 1440:
        raise DomainError("Los minutos no son válidos.")
    return minutes * 60


def _pieces(value: str, field: str) -> list[str]:
    parts = [part.strip() for part in value.split("|") if part.strip()]
    if not parts:
        raise DomainError(f"Falta {field}.")
    return parts


def _labeled(value: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for part in _pieces(value, "las frases"):
        if "=>" not in part:
            raise DomainError("Cada frase se escribe como texto => categoria.")
        text, category = part.split("=>", 1)
        text = text.strip()
        category = category.strip()
        if not text or not category:
            raise DomainError("Cada frase se escribe como texto => categoria.")
        rows.append({"text": text, "category": category})
    return rows


def _cases(row: dict[str, str]) -> list[dict[str, object]]:
    cases: list[dict[str, object]] = []
    seen_blank = False
    for index in range(1, 7):
        raw_inputs = row.get(f"caso{index}_entradas", "")
        raw_output = row.get(f"caso{index}_salida", "")
        if not raw_inputs and not raw_output:
            seen_blank = True
            continue
        if seen_blank:
            raise DomainError("Los casos van seguidos, del 1 en adelante.")
        if not raw_output:
            raise DomainError(f"Falta la salida del caso {index}.")
        inputs = [part.strip() for part in raw_inputs.split("|")] if raw_inputs else []
        inputs = [part for part in inputs if part]
        cases.append({"inputs": inputs, "expected_output": _unescape(raw_output)})
    if not cases:
        raise DomainError("Agrega al menos un caso con su salida.")
    return cases


def _unescape(value: str) -> str:
    return value.replace("\\n", "\n").replace("\\t", "\t")


def _example(kind: str) -> dict[str, str]:
    common = {
        "tipo": kind,
        "titulo": "",
        "enunciado": "",
        "concepto": "io",
        "dificultad": "1",
        "puntos": "10",
        "minutos": "",
        "pista1": "",
    }
    if kind == "clasificar":
        common.update(
            {
                "titulo": "Señales del dato",
                "enunciado": "Separa lo que entra, lo que se calcula y lo que se muestra.",
                "categorias": "entrada|proceso|salida",
                "frases": "Leer un nombre => entrada|Sumar dos precios => proceso|Mostrar el total => salida",
                "pista1": "Fíjate quién produce el dato.",
            }
        )
    elif kind == "ordenar":
        common.update(
            {
                "titulo": "Pasos del saludo",
                "enunciado": "Ordena las instrucciones para guardar un saludo y mostrarlo.",
                "concepto": "assignment",
                "instrucciones": "Definir saludo como cadena|Guardar hola en saludo|Escribir saludo",
                "pista1": "Primero se declara, después se guarda y al final se muestra.",
            }
        )
    elif kind == "construir":
        common.update(
            {
                "titulo": "El doble leído",
                "enunciado": "Lee un entero y escribe su doble.",
                "concepto": "operator",
                "dificultad": "2",
                "puntos": "15",
                "minutos": "15",
                "pregunta": "¿Qué operador multiplica?",
                "respuestas": "*|por",
                "caso1_entradas": "6",
                "caso1_salida": "6\\n12",
                "caso2_entradas": "0",
                "caso2_salida": "0\\n0",
                "caso3_entradas": "4",
                "caso3_salida": "4\\n8",
                "pista1": "Multiplica el número por dos.",
            }
        )
    else:
        common.update(
            {
                "titulo": "Después de sumar uno",
                "enunciado": "Anticipa el número que se escribe.",
                "concepto": "assignment",
                "dificultad": "2",
                "puntos": "15",
                "pregunta": "¿Qué número se escribe?",
                "respuestas": "5",
                "pseudocodigo": "\\n".join(
                    [
                        "Algoritmo Laboratorio",
                        "Definir n Como Entero;",
                        "n <- 4;",
                        "n <- n + 1;",
                        "Escribir n;",
                        "FinAlgoritmo",
                    ]
                ),
                "pista1": "Sigue el valor de n línea por línea.",
            }
        )
    return common
