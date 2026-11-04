"""Importa y exporta exámenes en JSON, Moodle XML, GIFT, CSV y Forms."""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass
from html import escape, unescape
from xml.etree import ElementTree

from config.errors import DomainError

FORMATS = ("json", "moodle", "gift", "csv", "forms")


@dataclass(frozen=True)
class ParsedExam:
    title: str
    instructions: str
    settings: dict[str, object]
    questions: list[dict[str, object]]


def sniff(text: str) -> str:
    sample = text.lstrip()
    if sample.startswith("<"):
        return "moodle"
    if sample.startswith("{") or sample.startswith("["):
        return "json"
    first = sample.splitlines()[0].lower() if sample else ""
    if "kind" in first and "prompt" in first:
        return "csv"
    if "question" in first and "type" in first:
        return "forms"
    if "{" in sample:
        return "gift"
    raise DomainError("No se reconoce el formato.")


def parse_exam(fmt: str, text: str) -> ParsedExam:
    if fmt not in FORMATS:
        raise DomainError("No se reconoce el formato.")
    if fmt == "json":
        return _json(text)
    if fmt == "moodle":
        return _moodle(text)
    if fmt == "gift":
        return _gift(text)
    if fmt == "forms":
        return _forms(text)
    return _csv(text)


def dump_exam(
    fmt: str, title: str, instructions: str, settings: dict, questions: list[dict]
) -> tuple[str, str, str]:
    if fmt == "json":
        body = {
            "format": "aulivana-exam",
            "version": 1,
            "title": title,
            "instructions": instructions,
            **settings,
            "questions": questions,
        }
        return (
            f"{_slug(title)}.json",
            json.dumps(body, ensure_ascii=False, indent=2),
            "application/json",
        )
    if fmt == "moodle":
        return f"{_slug(title)}.xml", _moodle_xml(questions), "application/xml"
    if fmt == "gift":
        return f"{_slug(title)}.gift.txt", _gift_text(questions), "text/plain"
    raise DomainError("No se reconoce el formato.")


def _slug(title: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", title).strip("-")
    return cleaned or "examen"


def _plain(value: str) -> str:
    text = re.sub(r"(?i)<br\s*/?>", "\n", value)
    text = re.sub(r"(?i)</p>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return unescape(text).strip()


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child_text(node: ElementTree.Element, *path: str) -> str:
    current: ElementTree.Element | None = node
    for name in path:
        if current is None:
            return ""
        current = next((child for child in list(current) if _local(child.tag) == name), None)
    if current is None or current.text is None:
        return ""
    return current.text


def _json(text: str) -> ParsedExam:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise DomainError("No se pudo leer el archivo.") from exc
    if isinstance(data, list):
        data = {"questions": data}
    if not isinstance(data, dict):
        raise DomainError("No se pudo leer el archivo.")
    questions = data.get("questions")
    if not isinstance(questions, list) or not questions:
        raise DomainError("El archivo no trae preguntas.")
    settings = {
        key: data[key]
        for key in (
            "duration_minutes",
            "attempts_allowed",
            "grading_method",
            "shuffle_questions",
            "shuffle_choices",
            "navigation",
            "one_per_page",
            "grade_to_pass",
            "show_grade",
        )
        if key in data
    }
    title = data.get("title") if isinstance(data.get("title"), str) else ""
    instructions = data.get("instructions") if isinstance(data.get("instructions"), str) else ""
    return ParsedExam(title.strip(), instructions, settings, questions)


def _moodle(text: str) -> ParsedExam:
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as exc:
        raise DomainError("No se pudo leer el archivo.") from exc
    questions: list[dict[str, object]] = []
    nodes = [root] if _local(root.tag) == "question" else list(root)
    for node in nodes:
        if _local(node.tag) != "question":
            continue
        kind = node.attrib.get("type", "")
        built = _moodle_question(node, kind)
        if built is not None:
            questions.append(built)
    if not questions:
        raise DomainError("El archivo no trae preguntas.")
    return ParsedExam("", "", {}, questions)


def _moodle_question(node: ElementTree.Element, kind: str) -> dict[str, object] | None:
    if kind in {"category", "description"}:
        return None
    prompt = _plain(_child_text(node, "questiontext", "text"))
    if not prompt:
        name = _plain(_child_text(node, "name", "text"))
        prompt = name
    points = _grade(node)
    feedback = _plain(_child_text(node, "generalfeedback", "text"))
    if kind == "multichoice":
        single = _child_text(node, "single").strip().lower() != "false"
        options = []
        for answer in list(node):
            if _local(answer.tag) != "answer":
                continue
            options.append(
                {
                    "text": _plain(_child_text(answer, "text") or answer.text or ""),
                    "correct": _fraction(answer.attrib.get("fraction")) > 0,
                }
            )
        options = [item for item in options if item["text"]]
        if len(options) < 2 or not any(item["correct"] for item in options):
            return None
        if single:
            marked = [item for item in options if item["correct"]]
            if len(marked) != 1:
                best = marked[0]
                options = [{**item, "correct": item is best} for item in options]
        return {
            "kind": "choice" if single else "multi",
            "prompt": prompt or "Pregunta",
            "points": points,
            "feedback": feedback,
            "payload": {"options": options},
        }
    if kind == "truefalse":
        correct = False
        for answer in list(node):
            if _local(answer.tag) != "answer":
                continue
            if _fraction(answer.attrib.get("fraction")) >= 100:
                correct = (
                    _child_text(answer, "text") or answer.text or ""
                ).strip().lower() == "true"
        return {
            "kind": "true_false",
            "prompt": prompt or "Pregunta",
            "points": points,
            "feedback": feedback,
            "payload": {"correct": correct},
        }
    if kind == "shortanswer":
        sensitive = _child_text(node, "usecase").strip() == "1"
        answers = []
        for answer in list(node):
            if _local(answer.tag) != "answer":
                continue
            text = _plain(_child_text(answer, "text") or answer.text or "")
            fraction = _fraction(answer.attrib.get("fraction"))
            if text and fraction > 0:
                answers.append({"text": text, "fraction": fraction})
        if not answers:
            return None
        return {
            "kind": "short",
            "prompt": prompt or "Pregunta",
            "points": points,
            "feedback": feedback,
            "payload": {"answers": answers, "case_sensitive": sensitive},
        }
    if kind == "numerical":
        answers = []
        for answer in list(node):
            if _local(answer.tag) != "answer":
                continue
            text = (_child_text(answer, "text") or answer.text or "").strip()
            tolerance = _child_text(answer, "tolerance") or "0"
            fraction = _fraction(answer.attrib.get("fraction"))
            if text and fraction > 0:
                answers.append({"value": text, "tolerance": tolerance, "fraction": fraction})
        if not answers:
            return None
        return {
            "kind": "numerical",
            "prompt": prompt or "Pregunta",
            "points": points,
            "feedback": feedback,
            "payload": {"answers": answers},
        }
    if kind == "essay":
        rubric = _plain(_child_text(node, "graderinfo", "text"))
        return {
            "kind": "essay",
            "prompt": prompt or "Pregunta",
            "points": points,
            "feedback": feedback,
            "payload": {"rubric": rubric},
        }
    if kind == "matching":
        pairs = []
        for sub in list(node):
            if _local(sub.tag) != "subquestion":
                continue
            left = _plain(_child_text(sub, "text") or "")
            right = _plain(_child_text(sub, "answer", "text"))
            if left and right:
                pairs.append({"left": left, "right": right})
        if len(pairs) < 2:
            return None
        return {
            "kind": "matching",
            "prompt": prompt or "Relaciona",
            "points": points,
            "feedback": feedback,
            "payload": {"pairs": pairs},
        }
    return None


def _grade(node: ElementTree.Element) -> object:
    raw = _child_text(node, "defaultgrade").strip()
    if not raw:
        return 1
    try:
        value = float(raw)
    except ValueError:
        return 1
    if value <= 0 or value > 100:
        return 1
    return value


def _fraction(value: str | None) -> int:
    if not value:
        return 0
    try:
        return int(float(value))
    except ValueError:
        return 0


def _gift(text: str) -> ParsedExam:
    lines = [line for line in text.splitlines() if not line.strip().startswith("//")]
    raw = "\n".join(lines)
    questions: list[dict[str, object]] = []
    for match in re.finditer(r"(?s)([^{]*?)\{(.*?)\}", raw):
        body = match.group(1).strip()
        answers = match.group(2).strip()
        if not body and not answers:
            continue
        built = _gift_question(body, answers)
        if built is not None:
            questions.append(built)
    if not questions:
        raise DomainError("El archivo no trae preguntas.")
    return ParsedExam("", "", {}, questions)


def _gift_title(body: str) -> tuple[str, str]:
    match = re.match(r"(?s)^::(.*?)::(.*)$", body.strip())
    if not match:
        return "", body.strip()
    return match.group(1).strip(), match.group(2).strip()


def _unescape_gift(text: str) -> str:
    return re.sub(r"\\([~=#{}:\\])", r"\1", text).strip()


def _gift_question(body: str, answers: str) -> dict[str, object] | None:
    _title, prompt = _gift_title(body)
    prompt = _unescape_gift(prompt)
    if not prompt:
        prompt = "Pregunta"
    token = answers.strip()
    folded = token.upper()
    if folded in {"T", "TRUE", "F", "FALSE"}:
        return {
            "kind": "true_false",
            "prompt": prompt,
            "points": 1,
            "feedback": "",
            "payload": {"correct": folded in {"T", "TRUE"}},
        }
    if token.startswith("#"):
        number = token[1:].split("=", 1)[0]
        value, _, tolerance = number.partition(":")
        return {
            "kind": "numerical",
            "prompt": prompt,
            "points": 1,
            "feedback": "",
            "payload": {
                "answers": [
                    {"value": value.strip(), "tolerance": tolerance.strip() or "0", "fraction": 100}
                ]
            },
        }
    parts = re.findall(r"([=~])([^~=]*)", token)
    if not parts:
        return None
    if any("->" in piece for _mark, piece in parts):
        pairs = []
        for mark, piece in parts:
            if mark != "=" or "->" not in piece:
                continue
            left, right = piece.split("->", 1)
            left, right = _unescape_gift(left), _unescape_gift(right)
            if left and right:
                pairs.append({"left": left, "right": right})
        if len(pairs) < 2:
            return None
        return {
            "kind": "matching",
            "prompt": prompt,
            "points": 1,
            "feedback": "",
            "payload": {"pairs": pairs},
        }
    corrects = [(mark, _unescape_gift(piece)) for mark, piece in parts if piece.strip()]
    right = [text for mark, text in corrects if mark == "=" and text]
    wrong = [text for mark, text in corrects if mark == "~" and text]
    if right and not wrong:
        return {
            "kind": "short",
            "prompt": prompt,
            "points": 1,
            "feedback": "",
            "payload": {
                "answers": [{"text": text, "fraction": 100} for text in right],
                "case_sensitive": False,
            },
        }
    options = [{"text": text, "correct": True} for text in right] + [
        {"text": text, "correct": False} for text in wrong
    ]
    if len(options) < 2 or not right:
        return None
    kind = "choice" if len(right) == 1 else "multi"
    return {
        "kind": kind,
        "prompt": prompt,
        "points": 1,
        "feedback": "",
        "payload": {"options": options},
    }


def _csv(text: str) -> ParsedExam:
    return ParsedExam("", "", {}, _csv_questions(text))


def _csv_questions(text: str) -> list[dict[str, object]]:
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise DomainError("El archivo no trae preguntas.")
    fields = {(name or "").strip().lower(): name for name in reader.fieldnames}
    questions: list[dict[str, object]] = []
    open_choice: dict[str, object] | None = None
    for row in reader:
        kind = _cell(row, fields, "kind").lower()
        prompt = _cell(row, fields, "prompt")
        points = _cell(row, fields, "points") or "1"
        text = _cell(row, fields, "text")
        correct = _cell(row, fields, "correct")
        extra = _cell(row, fields, "extra")
        if kind in {"choice", "multi"}:
            option = {"text": text, "correct": _yes(correct)}
            if open_choice and open_choice["kind"] == kind and open_choice["prompt"] == prompt:
                payload = open_choice["payload"]
                assert isinstance(payload, dict)
                options = payload["options"]
                assert isinstance(options, list)
                options.append(option)
                continue
            open_choice = {
                "kind": kind,
                "prompt": prompt or "Pregunta",
                "points": points,
                "feedback": "",
                "payload": {"options": [option]},
            }
            questions.append(open_choice)
            continue
        open_choice = None
        built = _csv_single(kind, prompt, points, text, correct, extra)
        if built is not None:
            questions.append(built)
    cleaned = [item for item in questions if _csv_ready(item)]
    if not cleaned:
        raise DomainError("El archivo no trae preguntas.")
    return cleaned


def _csv_ready(question: dict[str, object]) -> bool:
    if question["kind"] not in {"choice", "multi"}:
        return True
    payload = question["payload"]
    assert isinstance(payload, dict)
    options = payload["options"]
    assert isinstance(options, list)
    return len(options) >= 2 and any(
        isinstance(item, dict) and item.get("correct") for item in options
    )


def _csv_single(
    kind: str, prompt: str, points: str, text: str, correct: str, extra: str
) -> dict[str, object] | None:
    prompt = prompt or "Pregunta"
    if kind == "true_false":
        return {
            "kind": "true_false",
            "prompt": prompt,
            "points": points,
            "feedback": "",
            "payload": {"correct": _yes(correct or text)},
        }
    if kind == "short":
        answers = [piece.strip() for piece in (text or extra).split("|") if piece.strip()]
        if not answers:
            return None
        return {
            "kind": "short",
            "prompt": prompt,
            "points": points,
            "feedback": "",
            "payload": {
                "answers": [{"text": item, "fraction": 100} for item in answers],
                "case_sensitive": False,
            },
        }
    if kind == "numerical":
        if not text:
            return None
        return {
            "kind": "numerical",
            "prompt": prompt,
            "points": points,
            "feedback": "",
            "payload": {"answers": [{"value": text, "tolerance": correct or "0", "fraction": 100}]},
        }
    if kind == "essay":
        return {
            "kind": "essay",
            "prompt": prompt,
            "points": points,
            "feedback": "",
            "payload": {"rubric": extra},
        }
    if kind == "matching":
        pairs = []
        for piece in extra.split("|"):
            if "=" not in piece:
                continue
            left, right = piece.split("=", 1)
            if left.strip() and right.strip():
                pairs.append({"left": left.strip(), "right": right.strip()})
        if len(pairs) < 2:
            return None
        return {
            "kind": "matching",
            "prompt": prompt,
            "points": points,
            "feedback": "",
            "payload": {"pairs": pairs},
        }
    if kind == "order":
        items = [{"text": piece.strip()} for piece in extra.split("|") if piece.strip()]
        if len(items) < 2:
            return None
        return {
            "kind": "order",
            "prompt": prompt,
            "points": points,
            "feedback": "",
            "payload": {"items": items},
        }
    if kind == "cloze":
        blanks = []
        for piece in extra.split("|"):
            if "=" not in piece:
                continue
            ident, answers = piece.split("=", 1)
            blanks.append(
                {
                    "id": ident.strip(),
                    "answers": [item.strip() for item in answers.split("/") if item.strip()],
                }
            )
        if not blanks:
            return None
        return {
            "kind": "cloze",
            "prompt": prompt,
            "points": points,
            "feedback": "",
            "payload": {"text": text or prompt, "blanks": blanks},
        }
    return None


def _forms(text: str) -> ParsedExam:
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise DomainError("El archivo no trae preguntas.")
    fields = {(name or "").strip().lower(): name for name in reader.fieldnames}
    questions: list[dict[str, object]] = []
    for row in reader:
        kind = _cell(row, fields, "type").lower().replace("/", "").replace(" ", "").replace("_", "")
        prompt = _cell(row, fields, "question") or "Pregunta"
        points = _cell(row, fields, "points") or "1"
        options = []
        for index in range(1, 8):
            value = _cell(row, fields, f"option {index}") or _cell(row, fields, f"option{index}")
            if value:
                options.append(value)
        correct = _cell(row, fields, "correct")
        built = _forms_question(kind, prompt, points, options, correct)
        if built is not None:
            questions.append(built)
    if not questions:
        raise DomainError("El archivo no trae preguntas.")
    return ParsedExam("", "", {}, questions)


def _forms_question(
    kind: str, prompt: str, points: str, options: list[str], correct: str
) -> dict[str, object] | None:
    if kind in {"choice", "seleccion"}:
        marked = _marks(correct, options)
        if len(options) < 2 or not marked:
            return None
        payload = [
            {"text": text, "correct": index in marked}
            for index, text in enumerate(options, start=1)
        ]
        return {
            "kind": "choice" if len(marked) == 1 else "multi",
            "prompt": prompt,
            "points": points,
            "feedback": "",
            "payload": {"options": payload},
        }
    if kind in {"ranking", "orden", "order"}:
        items = [{"text": text} for text in options]
        if len(items) < 2:
            return None
        return {
            "kind": "order",
            "prompt": prompt,
            "points": points,
            "feedback": "",
            "payload": {"items": items},
        }
    if kind in {"truefalse", "verdaderofalso"}:
        return {
            "kind": "true_false",
            "prompt": prompt,
            "points": points,
            "feedback": "",
            "payload": {"correct": _yes(correct)},
        }
    if kind in {"number", "numerical", "numero"}:
        if not correct:
            return None
        return {
            "kind": "numerical",
            "prompt": prompt,
            "points": points,
            "feedback": "",
            "payload": {"answers": [{"value": correct, "tolerance": "0", "fraction": 100}]},
        }
    if kind in {"essay", "ensayo"}:
        return {
            "kind": "essay",
            "prompt": prompt,
            "points": points,
            "feedback": "",
            "payload": {"rubric": ""},
        }
    if kind in {"text", "texto", "short"}:
        if not correct:
            return None
        return {
            "kind": "short",
            "prompt": prompt,
            "points": points,
            "feedback": "",
            "payload": {"answers": [{"text": correct, "fraction": 100}], "case_sensitive": False},
        }
    return None


def _marks(correct: str, options: list[str]) -> set[int]:
    marks: set[int] = set()
    for piece in re.split(r"[|,]", correct):
        piece = piece.strip()
        if not piece:
            continue
        if piece.isdigit():
            marks.add(int(piece))
            continue
        for index, option in enumerate(options, start=1):
            if option.casefold() == piece.casefold():
                marks.add(index)
    return marks


def _yes(value: str) -> bool:
    return value.strip().casefold() in {"1", "true", "yes", "y", "si", "sí", "verdadero", "v"}


def _cell(row: dict[str, str | None], fields: dict[str, str], name: str) -> str:
    key = fields.get(name)
    if key is None:
        return ""
    value = row.get(key)
    return value.strip() if isinstance(value, str) else ""


def _moodle_xml(questions: list[dict]) -> str:
    parts = ['<?xml version="1.0" encoding="UTF-8"?>', "<quiz>"]
    exported = 0
    for question in questions:
        block = _moodle_block(question)
        if block:
            parts.append(block)
            exported += 1
    if exported == 0:
        raise DomainError("Este formato no conserva los retos. Usa JSON.")
    parts.append("</quiz>")
    return "\n".join(parts)


def _cdata(text: object) -> str:
    return escape("" if text is None else str(text))


def _moodle_block(question: dict) -> str:
    kind = question.get("kind")
    prompt = _cdata(question.get("prompt"))
    points = question.get("points", 1)
    feedback = _cdata(question.get("feedback"))
    payload = question.get("payload") if isinstance(question.get("payload"), dict) else {}
    head = (
        f"<name><text>{prompt[:80]}</text></name>"
        f'<questiontext format="html"><text>{prompt}</text></questiontext>'
        f'<generalfeedback format="html"><text>{feedback}</text></generalfeedback>'
        f"<defaultgrade>{points}</defaultgrade><penalty>0</penalty><hidden>0</hidden>"
    )
    if kind in {"choice", "multi"}:
        single = "true" if kind == "choice" else "false"
        answers = []
        for option in payload.get("options") or []:
            if not isinstance(option, dict):
                continue
            fraction = "100" if option.get("correct") else "0"
            answers.append(
                f'<answer fraction="{fraction}" format="html"><text>{_cdata(option.get("text"))}</text></answer>'
            )
        return f'<question type="multichoice">{head}<single>{single}</single>{"".join(answers)}</question>'
    if kind == "true_false":
        correct = payload.get("correct") is True
        true_fraction = "100" if correct else "0"
        false_fraction = "0" if correct else "100"
        return (
            f'<question type="truefalse">{head}'
            f'<answer fraction="{true_fraction}" format="moodle_auto_format"><text>true</text></answer>'
            f'<answer fraction="{false_fraction}" format="moodle_auto_format"><text>false</text></answer>'
            "</question>"
        )
    if kind == "short":
        usecase = "1" if payload.get("case_sensitive") else "0"
        answers = []
        for item in payload.get("answers") or []:
            if isinstance(item, dict):
                answers.append(
                    f'<answer fraction="{item.get("fraction", 100)}" format="moodle_auto_format">'
                    f'<text>{_cdata(item.get("text"))}</text></answer>'
                )
        return f'<question type="shortanswer">{head}<usecase>{usecase}</usecase>{"".join(answers)}</question>'
    if kind == "numerical":
        answers = []
        for item in payload.get("answers") or []:
            if isinstance(item, dict):
                answers.append(
                    f'<answer fraction="{item.get("fraction", 100)}">'
                    f'<text>{_cdata(item.get("value"))}</text>'
                    f'<tolerance>{_cdata(item.get("tolerance", 0))}</tolerance></answer>'
                )
        return f'<question type="numerical">{head}{"".join(answers)}</question>'
    if kind == "essay":
        rubric = _cdata(payload.get("rubric"))
        return (
            f'<question type="essay">{head}'
            f'<graderinfo format="html"><text>{rubric}</text></graderinfo></question>'
        )
    if kind == "matching":
        subs = []
        for pair in payload.get("pairs") or []:
            if isinstance(pair, dict):
                subs.append(
                    "<subquestion>"
                    f'<text>{_cdata(pair.get("left"))}</text>'
                    f'<answer><text>{_cdata(pair.get("right"))}</text></answer></subquestion>'
                )
        return f'<question type="matching">{head}{"".join(subs)}</question>'
    if kind == "case":
        statement = _cdata(payload.get("statement") or question.get("prompt"))
        return (
            f'<question type="essay">{head}'
            f'<graderinfo format="html"><text>{statement}</text></graderinfo></question>'
        )
    return ""


def _gift_text(questions: list[dict]) -> str:
    lines: list[str] = []
    for question in questions:
        line = _gift_line(question)
        if line:
            lines.append(line)
    if not any(not line.startswith("//") for line in lines):
        raise DomainError("Este formato no conserva los retos. Usa JSON.")
    return "\n\n".join(lines) + "\n"


def _gift_escape(text: object) -> str:
    raw = "" if text is None else str(text)
    return re.sub(r"([~=#{}:\\])", r"\\\1", raw.replace("\n", " "))


def _gift_line(question: dict) -> str:
    kind = question.get("kind")
    prompt = _gift_escape(question.get("prompt"))
    payload = question.get("payload") if isinstance(question.get("payload"), dict) else {}
    if kind == "true_false":
        return f"{prompt} {{{'T' if payload.get('correct') else 'F'}}}"
    if kind == "numerical":
        answers = payload.get("answers") or []
        if not answers or not isinstance(answers[0], dict):
            return ""
        first = answers[0]
        return f"{prompt} {{#{first.get('value')}:{first.get('tolerance', 0)}}}"
    if kind == "short":
        parts = []
        for item in payload.get("answers") or []:
            if isinstance(item, dict):
                parts.append(f"={_gift_escape(item.get('text'))}")
        return f"{prompt} {{{' '.join(parts)}}}" if parts else ""
    if kind in {"choice", "multi"}:
        parts = []
        for option in payload.get("options") or []:
            if isinstance(option, dict):
                mark = "=" if option.get("correct") else "~"
                parts.append(f"{mark}{_gift_escape(option.get('text'))}")
        return f"{prompt} {{{' '.join(parts)}}}" if parts else ""
    if kind == "matching":
        parts = []
        for pair in payload.get("pairs") or []:
            if isinstance(pair, dict):
                parts.append(
                    f"={_gift_escape(pair.get('left'))} -> {_gift_escape(pair.get('right'))}"
                )
        return f"{prompt} {{{' '.join(parts)}}}" if len(parts) >= 2 else ""
    if kind == "case":
        return f"// Reto (se conserva en JSON): {prompt}"
    return ""
