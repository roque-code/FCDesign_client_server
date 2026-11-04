"""Los archivos de Moodle, GIFT, Forms y JSON entran y salen."""

import json

import pytest

from apps.exams.exchange import dump_exam, parse_exam, sniff
from config.errors import DomainError

MOODLE = """<?xml version="1.0" encoding="UTF-8"?>
<quiz>
  <question type="multichoice">
    <name><text>Capital</text></name>
    <questiontext format="html"><text><![CDATA[<p>¿Capital?</p>]]></text></questiontext>
    <defaultgrade>2</defaultgrade>
    <single>true</single>
    <answer fraction="0"><text>Lyon</text></answer>
    <answer fraction="100"><text>París</text></answer>
  </question>
  <question type="truefalse">
    <questiontext format="html"><text>El cielo es azul</text></questiontext>
    <answer fraction="100"><text>true</text></answer>
    <answer fraction="0"><text>false</text></answer>
  </question>
  <question type="shortanswer">
    <questiontext format="html"><text>Río</text></questiontext>
    <usecase>0</usecase>
    <answer fraction="100"><text>Sena</text></answer>
  </question>
  <question type="numerical">
    <questiontext format="html"><text>Mitad</text></questiontext>
    <answer fraction="100"><text>5</text><tolerance>0.1</tolerance></answer>
  </question>
  <question type="essay">
    <questiontext format="html"><text>Explica</text></questiontext>
    <graderinfo format="html"><text>Claridad</text></graderinfo>
  </question>
  <question type="matching">
    <questiontext format="html"><text>Une</text></questiontext>
    <subquestion><text>perro</text><answer><text>dog</text></answer></subquestion>
    <subquestion><text>gato</text><answer><text>cat</text></answer></subquestion>
  </question>
  <question type="category"><category><text>top</text></category></question>
</quiz>
"""


def test_moodle_y_gift_reconocen_preguntas():
    parsed = parse_exam("moodle", MOODLE)
    kinds = [item["kind"] for item in parsed.questions]
    assert kinds == ["choice", "true_false", "short", "numerical", "essay", "matching"]
    assert parsed.questions[0]["points"] == 2
    assert parsed.questions[0]["payload"]["options"][1]["correct"] is True
    gift = parse_exam(
        "gift",
        "::Capital:: ¿Capital? {=París ~Lyon}\n\n¿Cierto? {T}\n\nRío {=Sena}\n\nMitad {#5:0.1}\n\n"
        "Une {=perro -> dog =gato -> cat}\n",
    )
    assert [item["kind"] for item in gift.questions] == [
        "choice",
        "true_false",
        "short",
        "numerical",
        "matching",
    ]


def test_csv_forms_y_json():
    csv_text = (
        "kind,points,prompt,text,correct,extra\n"
        "choice,1,¿Capital?,París,1,\n"
        "choice,1,¿Capital?,Lyon,0,\n"
        "short,1,Río,Sena,1,\n"
        "order,2,Ordena,,,uno|dos\n"
    )
    parsed = parse_exam("csv", csv_text)
    assert [item["kind"] for item in parsed.questions] == ["choice", "short", "order"]
    forms = (
        "Type,Points,Question,Option 1,Option 2,Correct\n"
        "Choice,1,Capital,Paris,Lyon,1\n"
        "Ranking,1,Pasos,Abrir,Cerrar,\n"
        "Text,1,Río,,,Sena\n"
    )
    assert [item["kind"] for item in parse_exam("forms", forms).questions] == [
        "choice",
        "order",
        "short",
    ]
    raw = json.dumps(
        {
            "title": "Parcial",
            "duration_minutes": 30,
            "questions": [{"kind": "essay", "prompt": "Di"}],
        }
    )
    loaded = parse_exam("json", raw)
    assert loaded.title == "Parcial"
    assert loaded.settings["duration_minutes"] == 30
    assert sniff(MOODLE) == "moodle"
    assert sniff(raw) == "json"
    assert sniff(csv_text) == "csv"


def test_exportar_conserva_lo_que_el_formato_puede():
    questions = [
        {
            "kind": "choice",
            "prompt": "¿Capital?",
            "points": 1,
            "feedback": "",
            "payload": {
                "options": [
                    {"id": "a", "text": "París", "correct": True},
                    {"id": "b", "text": "Lyon", "correct": False},
                ]
            },
        },
        {
            "kind": "case",
            "prompt": "Saluda",
            "points": 2,
            "feedback": "",
            "payload": {"statement": "Saluda", "starter": "", "cases": []},
        },
    ]
    _name, moodle, _media = dump_exam("moodle", "Parcial", "", {}, questions)
    assert "multichoice" in moodle
    assert "Saluda" in moodle
    _name, gift, _media = dump_exam("gift", "Parcial", "", {}, questions)
    assert "París" in gift
    assert gift.startswith("//") or "¿Capital?" in gift
    _name, body, _media = dump_exam("json", "Parcial", "Lee", {"attempts_allowed": 2}, questions)
    saved = json.loads(body)
    assert saved["questions"][1]["kind"] == "case"
    assert saved["attempts_allowed"] == 2
    with pytest.raises(DomainError):
        dump_exam("gift", "Reto", "", {}, [questions[1]])
    with pytest.raises(DomainError):
        parse_exam("moodle", "<quiz></quiz>")
    with pytest.raises(DomainError):
        parse_exam("json", "{")
