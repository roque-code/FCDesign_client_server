"""Cada tipo de pregunta suma lo que corresponde."""

from decimal import Decimal

from apps.exams.grading import grade_question

POINT = Decimal("2")


def test_opcion_unica_y_varias():
    payload = {"options": [{"id": "a", "correct": False}, {"id": "b", "correct": True}]}
    assert grade_question("choice", payload, {"option": "b"}, POINT).score == POINT
    assert grade_question("choice", payload, {"option": "a"}, POINT).score == 0
    multi = {
        "options": [
            {"id": "a", "correct": True},
            {"id": "b", "correct": False},
            {"id": "c", "correct": True},
        ]
    }
    full = grade_question("multi", multi, {"options": ["a", "c"]}, POINT)
    partial = grade_question("multi", multi, {"options": ["a"]}, POINT)
    wrong = grade_question("multi", multi, {"options": ["a", "b", "c"]}, POINT)
    assert full.score == POINT
    assert partial.score == Decimal("1.00")
    assert wrong.score == Decimal("0.00")


def test_verdadero_corto_y_numero():
    assert grade_question("true_false", {"correct": True}, {"value": True}, POINT).correct is True
    assert grade_question("true_false", {"correct": True}, {"value": False}, POINT).score == 0
    short = grade_question(
        "short", {"answers": [{"text": "Sena", "fraction": 100}]}, {"text": " séna "}, POINT
    )
    assert short.score == POINT
    sensitive = grade_question(
        "short",
        {"answers": [{"text": "Sena", "fraction": 100}], "case_sensitive": True},
        {"text": "sena"},
        POINT,
    )
    assert sensitive.score == 0
    number = grade_question(
        "numerical",
        {"answers": [{"value": 3.14, "tolerance": 0.01, "fraction": 100}]},
        {"value": "3,15"},
        POINT,
    )
    assert number.score == POINT
    outside = grade_question(
        "numerical",
        {"answers": [{"value": 3.14, "tolerance": 0.01, "fraction": 100}]},
        {"value": "4"},
        POINT,
    )
    assert outside.score == 0


def test_abierta_relacionar_ordenar_y_huecos():
    essay = grade_question("essay", {"rubric": ""}, {"text": "porque llueve"}, POINT)
    assert essay.pending is True
    assert grade_question("essay", {}, {"text": "  "}, POINT).pending is False
    pairs = {"pairs": [{"id": "p1", "left": "perro", "right": "dog"}]}
    assert grade_question("matching", pairs, {"pairs": {"p1": "p1"}}, POINT).score == POINT
    order = {"items": [{"id": "i1"}, {"id": "i2"}]}
    assert grade_question("order", order, {"order": ["i1", "i2"]}, POINT).correct is True
    assert grade_question("order", order, {"order": ["i2", "i1"]}, POINT).score == 0
    cloze = {"blanks": [{"id": "1", "answers": ["azul"]}]}
    assert grade_question("cloze", cloze, {"blanks": {"1": "Azul"}}, POINT).score == POINT


def test_reto_con_caso():
    payload = {
        "cases": [
            {"name": "hola", "inputs": [], "expected": "Hola mundo", "points": 1, "hidden": False},
            {"name": "oculto", "inputs": [], "expected": "Hola mundo", "points": 1, "hidden": True},
        ]
    }
    source = 'Algoritmo Hola\n    Escribir "Hola mundo";\nFinAlgoritmo\n'
    mark = grade_question("case", payload, {"source": source}, POINT)
    assert mark.correct is True
    assert mark.score == POINT
    assert mark.detail["cases"][1]["hidden"] is True
    empty = grade_question("case", payload, {"source": ""}, POINT)
    assert empty.score == 0
    broken = grade_question("case", payload, {"source": "esto no compila"}, POINT)
    assert broken.score == 0
