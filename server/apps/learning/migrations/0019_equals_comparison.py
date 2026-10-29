"""Pasa las comparaciones guardadas de = a ==.

= asigna, igual que <-. == compara. Los programas ya guardados usaban = para
comparar; esta migración les deja ese significado.
"""

from django.db import migrations

_PAIRS = ("<-", "<=", ">=", "!=", "<>", "==")
_CODE_MARKS = ("entonces", "finsi", "finmientras", "hasta que", "algoritmo")
_QUESTION = "¿Qué símbolo guarda un valor en una variable?"
_PHRASES = (
    (
        "La flecha guarda. El igual y los signos >, < comparan.",
        "<- y = guardan un valor. == compara. También comparan > y <.",
    ),
    (
        "n <- 3 y total <- total + 1 asignan. n = 3 y edad >= 18 comparan.",
        "n <- 3 y n = 3 asignan. n == 3 y edad >= 18 comparan.",
    ),
    (
        "El símbolo de asignación no es el igual de una comparación.",
        "Puedes asignar con <- o con =. Para comparar si dos valores son iguales se usa ==.",
    ),
    (
        "+ y MOD son aritméticos, > y = son relacionales, Y y NO son lógicos.",
        "+ y MOD son aritméticos, > y == son relacionales, Y y NO son lógicos.",
    ),
    ("Si a = b, escrito dentro del Sino", "Si a == b, escrito dentro del Sino"),
    ("Si no, preguntar si a = b", "Si no, preguntar si a == b"),
    ("La condición n = 0 se cumple", "La condición n == 0 se cumple"),
)


def _rewrite(text: str) -> str:
    out: list[str] = []
    index = 0
    size = len(text)
    quote = ""
    while index < size:
        char = text[index]
        if quote:
            out.append(char)
            if char == "\\" and index + 1 < size:
                out.append(text[index + 1])
                index += 2
                continue
            if char == quote:
                quote = ""
            index += 1
            continue
        if char in "\"'":
            quote = char
            out.append(char)
            index += 1
            continue
        if text.startswith("//", index):
            end = text.find("\n", index)
            if end < 0:
                out.append(text[index:])
                break
            out.append(text[index:end])
            index = end
            continue
        if text.startswith("/*", index):
            end = text.find("*/", index + 2)
            if end < 0:
                out.append(text[index:])
                break
            out.append(text[index : end + 2])
            index = end + 2
            continue
        pair = text[index : index + 2]
        if pair in _PAIRS:
            out.append(pair)
            index += 2
            continue
        if char == "=":
            out.append("==")
            index += 1
            continue
        out.append(char)
        index += 1
    return "".join(out)


def _phrases(text: str) -> str:
    for old, new in _PHRASES:
        text = text.replace(old, new)
    return text


def _code(text: str) -> str:
    folded = text.casefold()
    if any(mark in folded for mark in _CODE_MARKS):
        return _rewrite(text)
    return text


def _text(value: str, *, program: bool) -> str:
    updated = _phrases(value)
    if program:
        return _rewrite(updated)
    return _code(updated)


def _walk(value, *, program: bool = False):
    if isinstance(value, str):
        return _text(value, program=program)
    if isinstance(value, list):
        return [_walk(item) for item in value]
    if isinstance(value, dict):
        updated = {key: _walk(item) for key, item in value.items()}
        text = updated.get("text")
        category = updated.get("category")
        if text == "n = 3" and category == "comparación":
            updated["text"] = "n == 3"
        elif text == "=" and category == "relacional":
            updated["text"] = "=="
        if updated.get("question") == _QUESTION and isinstance(updated.get("accepted"), list):
            accepted = list(updated["accepted"])
            if "=" not in accepted:
                accepted.append("=")
            updated["accepted"] = accepted
        return updated
    return value


def _store_text(model, field: str) -> None:
    for row in model.objects.all().iterator():
        current = getattr(row, field) or ""
        updated = _text(current, program=True)
        if updated != current:
            setattr(row, field, updated)
            row.save(update_fields=[field])


def _store_json(model, field: str) -> None:
    for row in model.objects.all().iterator():
        current = getattr(row, field)
        updated = _walk(current)
        if updated != current:
            setattr(row, field, updated)
            row.save(update_fields=[field])


def promote_comparisons(apps, schema_editor):
    Algorithm = apps.get_model("projects", "Algorithm")
    AlgorithmVersion = apps.get_model("projects", "AlgorithmVersion")
    Practice = apps.get_model("learning", "Practice")
    Snapshot = apps.get_model("learning", "WorkspaceSnapshot")
    Challenge = apps.get_model("learning", "Challenge")
    Hint = apps.get_model("learning", "Hint")
    _store_text(Algorithm, "source")
    _store_text(AlgorithmVersion, "source")
    _store_text(Practice, "source")
    _store_text(Snapshot, "pseudocode")
    _store_text(Challenge, "prompt")
    _store_json(Challenge, "restrictions")
    _store_text(Hint, "body")


class Migration(migrations.Migration):
    dependencies = [
        ("learning", "0018_path_entry_repeat"),
        ("projects", "0002_language_options"),
    ]

    operations = [
        migrations.RunPython(promote_comparisons, migrations.RunPython.noop),
    ]
