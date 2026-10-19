"""Carga retos de un CSV. El formato depende del tipo de reto."""

from __future__ import annotations

import csv
import io

from django.db import transaction
from django.db.models import Q

from apps.learning.authoring import create_challenge
from apps.learning.bank_data import BANK_NAME
from apps.learning.catalog import CONCEPTS
from apps.learning.contest_data import CONTEST_BANK_NAME
from apps.learning.models import Challenge
from config.errors import DomainError
from language_core.block_adapter import adapt_workspace

_MAX_BYTES = 1_000_000
_MAX_ROWS = 250
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


def export_challenges(teacher, kind: str, shelf: str) -> dict[str, object]:
    """CSV de un tipo, listo para que otro docente lo vuelva a cargar."""
    if kind not in _SPECIFIC:
        raise DomainError("El tipo de plantilla no existe.")
    if shelf not in {"catalogo", "concurso"}:
        raise DomainError("El banco no existe.")
    challenges = _export_queryset(teacher, _TYPES[kind], shelf)
    if not challenges:
        raise DomainError("No hay retos de ese tipo para descargar.")
    columns = _columns(kind)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    for challenge in challenges:
        writer.writerow(_export_row(challenge, kind))
    filename = f"retos-{kind}.csv" if shelf == "catalogo" else f"retos-{kind}-concurso.csv"
    return {
        "tipo": kind,
        "filename": filename,
        "count": len(challenges),
        "csv": buffer.getvalue(),
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


def _escape_cell(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n").replace("\t", "\\t")


def _export_queryset(teacher, activity: str, shelf: str) -> list[Challenge]:
    base = (
        Challenge.objects.filter(is_published=True, activity_type=activity)
        .select_related("unit__concept", "unit__path")
        .prefetch_related("hints", "test_cases")
    )
    if shelf == "concurso":
        chosen = base.filter(
            unit__path__name=CONTEST_BANK_NAME,
            unit__path__is_bank=True,
            unit__path__owner__isnull=True,
        )
    else:
        chosen = base.filter(
            Q(
                unit__path__name=BANK_NAME,
                unit__path__is_bank=True,
                unit__path__owner__isnull=True,
            )
            | Q(unit__path__is_bank=True, unit__path__owner=teacher)
        )
    return list(chosen.order_by("unit__position", "position", "title"))


def _export_row(challenge: Challenge, kind: str) -> dict[str, str]:
    restrictions = challenge.restrictions if isinstance(challenge.restrictions, dict) else {}
    seconds = challenge.time_limit_seconds
    row: dict[str, str] = {
        "tipo": kind,
        "titulo": challenge.title,
        "enunciado": challenge.prompt,
        "concepto": str(challenge.unit.concept_id),
        "dificultad": str(challenge.difficulty),
        "puntos": str(challenge.points),
        "minutos": "" if seconds is None else str(max(1, round(seconds / 60))),
    }
    hints = sorted(challenge.hints.all(), key=lambda hint: (hint.level, hint.position))
    for index, hint in enumerate(hints[:5], start=1):
        row[f"pista{index}"] = hint.body
    if kind == "clasificar":
        categories = restrictions.get("categories")
        items = restrictions.get("items")
        row["categorias"] = "|".join(str(item) for item in categories) if isinstance(categories, list) else ""
        phrases = []
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    phrases.append(f"{item.get('text', '')} => {item.get('category', '')}")
        row["frases"] = "|".join(phrases)
    elif kind == "ordenar":
        items = restrictions.get("items")
        rows = [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []
        by_id = {str(item.get("id")): str(item.get("text", "")) for item in rows}
        solution = restrictions.get("solution")
        ordered = solution if isinstance(solution, list) and solution else [item.get("id") for item in rows]
        row["instrucciones"] = "|".join(by_id.get(str(item_id), "") for item_id in ordered)
    elif kind == "construir":
        accepted = restrictions.get("accepted")
        row["pregunta"] = str(restrictions.get("question") or "")
        row["respuestas"] = "|".join(str(item) for item in accepted) if isinstance(accepted, list) else ""
        cases = sorted(challenge.test_cases.all(), key=lambda case: case.position)[:6]
        for index, case in enumerate(cases, start=1):
            inputs = case.inputs if isinstance(case.inputs, list) else []
            row[f"caso{index}_entradas"] = "|".join(str(item) for item in inputs)
            row[f"caso{index}_salida"] = _escape_cell(case.expected_output)
    else:
        accepted = restrictions.get("accepted")
        row["pregunta"] = str(restrictions.get("question") or "")
        row["respuestas"] = "|".join(str(item) for item in accepted) if isinstance(accepted, list) else ""
        source = restrictions.get("source")
        if not isinstance(source, str) or not source:
            starter = restrictions.get("starter")
            source = adapt_workspace(starter).source if isinstance(starter, dict) else ""
        row["pseudocodigo"] = _escape_cell(source)
    return row


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
