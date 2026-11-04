"""Calificación automática. La pregunta abierta queda para el docente."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def as_number(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(money(value))


@dataclass(frozen=True)
class Mark:
    score: Decimal
    pending: bool
    correct: bool | None
    detail: dict[str, object]


def grade_question(kind: str, payload: dict, answer: object, points: Decimal) -> Mark:
    given = answer if isinstance(answer, dict) else {}
    if kind == "choice":
        return _choice(payload, given, points, single=True)
    if kind == "multi":
        return _choice(payload, given, points, single=False)
    if kind == "true_false":
        return _true_false(payload, given, points)
    if kind == "short":
        return _short(payload, given, points)
    if kind == "numerical":
        return _numerical(payload, given, points)
    if kind == "essay":
        return _essay(given, points)
    if kind == "matching":
        return _matching(payload, given, points)
    if kind == "order":
        return _order(payload, given, points)
    if kind == "cloze":
        return _cloze(payload, given, points)
    if kind == "case":
        return _case(payload, given, points)
    return Mark(Decimal("0"), False, False, {})


def _scale(points: Decimal, fraction: Decimal) -> Decimal:
    if fraction < 0:
        fraction = Decimal(0)
    if fraction > 1:
        fraction = Decimal(1)
    return money(points * fraction)


def _choice(payload: dict, answer: dict, points: Decimal, *, single: bool) -> Mark:
    options = payload.get("options") or []
    correct = {item["id"] for item in options if item.get("correct")}
    wrong = {item["id"] for item in options if not item.get("correct")}
    if single:
        selected = answer.get("option")
        picked = {selected} if isinstance(selected, str) else set()
    else:
        raw = answer.get("options")
        picked = {item for item in raw if isinstance(item, str)} if isinstance(raw, list) else set()
    if not correct:
        return Mark(Decimal("0"), False, False, {"picked": sorted(picked)})
    if single:
        ok = picked == correct
        return Mark(points if ok else Decimal("0"), False, ok, {"picked": sorted(picked)})
    hits = picked & correct
    misses = picked & wrong
    fraction = Decimal(len(hits)) / Decimal(len(correct))
    if wrong and misses:
        fraction -= Decimal(len(misses)) / Decimal(len(wrong))
    score = _scale(points, fraction)
    return Mark(score, False, score == points and not misses, {"picked": sorted(picked)})


def _true_false(payload: dict, answer: dict, points: Decimal) -> Mark:
    value = answer.get("value")
    if not isinstance(value, bool):
        return Mark(Decimal("0"), False, False, {})
    ok = value is payload.get("correct")
    return Mark(points if ok else Decimal("0"), False, ok, {"value": value})


def _fold(text: str, *, case_sensitive: bool) -> str:
    collapsed = " ".join(text.replace("\r\n", "\n").replace("\r", "\n").split())
    if case_sensitive:
        return collapsed
    folded = unicodedata.normalize("NFKC", collapsed).casefold()
    return "".join(
        ch for ch in unicodedata.normalize("NFD", folded) if unicodedata.category(ch) != "Mn"
    )


def _short(payload: dict, answer: dict, points: Decimal) -> Mark:
    text = answer.get("text")
    if not isinstance(text, str):
        text = ""
    sensitive = payload.get("case_sensitive") is True
    given = _fold(text, case_sensitive=sensitive)
    best = Decimal(0)
    if given:
        for item in payload.get("answers") or []:
            accepted = item.get("text")
            if not isinstance(accepted, str):
                continue
            if _fold(accepted, case_sensitive=sensitive) != given:
                continue
            fraction = Decimal(str(item.get("fraction", 100))) / Decimal(100)
            if fraction > best:
                best = fraction
    return Mark(_scale(points, best), False, best == 1, {})


def _number(value: object) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float, Decimal)):
        raw = str(value)
    elif isinstance(value, str):
        raw = value.strip().replace(",", ".")
        if not raw:
            return None
    else:
        return None
    try:
        number = Decimal(raw)
    except Exception:
        return None
    if not number.is_finite():
        return None
    return number


def _numerical(payload: dict, answer: dict, points: Decimal) -> Mark:
    given = _number(answer.get("value"))
    best = Decimal(0)
    if given is not None:
        for item in payload.get("answers") or []:
            expected = _number(item.get("value"))
            if expected is None:
                continue
            tolerance = _number(item.get("tolerance"))
            if tolerance is None or tolerance < 0:
                tolerance = Decimal(0)
            if abs(given - expected) <= tolerance:
                fraction = Decimal(str(item.get("fraction", 100))) / Decimal(100)
                if fraction > best:
                    best = fraction
    return Mark(_scale(points, best), False, best == 1, {})


def _essay(answer: dict, points: Decimal) -> Mark:
    text = answer.get("text")
    if not isinstance(text, str) or not text.strip():
        return Mark(Decimal("0"), False, False, {})
    return Mark(Decimal("0"), True, None, {"words": len(text.split())})


def _matching(payload: dict, answer: dict, points: Decimal) -> Mark:
    pairs = payload.get("pairs") or []
    given = answer.get("pairs")
    mapping = given if isinstance(given, dict) else {}
    if not pairs:
        return Mark(Decimal("0"), False, False, {})
    hits = 0
    for pair in pairs:
        if mapping.get(pair["id"]) == pair["id"]:
            hits += 1
    fraction = Decimal(hits) / Decimal(len(pairs))
    return Mark(
        _scale(points, fraction), False, hits == len(pairs), {"hits": hits, "total": len(pairs)}
    )


def _order(payload: dict, answer: dict, points: Decimal) -> Mark:
    items = payload.get("items") or []
    given = answer.get("order")
    sequence = [item for item in given if isinstance(item, str)] if isinstance(given, list) else []
    expected = [item["id"] for item in items]
    if not expected:
        return Mark(Decimal("0"), False, False, {})
    hits = sum(
        1
        for index, item in enumerate(expected)
        if index < len(sequence) and sequence[index] == item
    )
    if len(sequence) != len(expected):
        hits = min(hits, len(expected))
    fraction = Decimal(hits) / Decimal(len(expected))
    return Mark(_scale(points, fraction), False, sequence == expected, {})


def _cloze(payload: dict, answer: dict, points: Decimal) -> Mark:
    blanks = payload.get("blanks") or []
    given = answer.get("blanks")
    mapping = given if isinstance(given, dict) else {}
    if not blanks:
        return Mark(Decimal("0"), False, False, {})
    hits = 0
    for blank in blanks:
        text = mapping.get(blank["id"])
        if not isinstance(text, str):
            continue
        folded = _fold(text, case_sensitive=False)
        accepted = {
            _fold(item, case_sensitive=False)
            for item in blank.get("answers") or []
            if isinstance(item, str)
        }
        if folded and folded in accepted:
            hits += 1
    fraction = Decimal(hits) / Decimal(len(blanks))
    return Mark(
        _scale(points, fraction), False, hits == len(blanks), {"hits": hits, "total": len(blanks)}
    )


def _same(output: str, expected: str) -> bool:
    def norm(text: str) -> str:
        return text.replace("\r\n", "\n").replace("\r", "\n").rstrip()

    return norm(output) == norm(expected)


def _run_case(source: str, case: dict) -> tuple[bool, str]:
    if not source.strip():
        return False, ""
    inputs = [str(item) for item in case.get("inputs") or []]
    try:
        from language_core import execute_source

        result = execute_source(source, inputs)
    except Exception:
        return False, ""
    if result.status != "completed":
        message = ""
        for item in result.diagnostics:
            if item.severity == "error":
                message = item.message
                break
        return False, (message or result.status)[:2000]
    output = result.output[:2000]
    return _same(result.output, str(case.get("expected") or "")), output


def _case(payload: dict, answer: dict, points: Decimal) -> Mark:
    source = answer.get("source")
    if not isinstance(source, str):
        source = ""
    cases = list(payload.get("cases") or [])
    if not cases:
        return Mark(Decimal("0"), False, False, {"cases": []})
    weights: list[Decimal] = []
    for case in cases:
        weight = _number(case.get("points"))
        weights.append(weight if weight is not None and weight > 0 else Decimal(1))
    total = sum(weights, Decimal(0))
    earned = Decimal(0)
    rows: list[dict[str, object]] = []
    all_ok = bool(source.strip())
    for case, weight in zip(cases, weights, strict=True):
        ok, output = _run_case(source, case)
        if ok and source.strip():
            earned += points * weight / total
        else:
            all_ok = False
        rows.append(
            {
                "name": str(case.get("name") or ""),
                "ok": ok and bool(source.strip()),
                "hidden": case.get("hidden") is True,
                "output": output,
                "expected": str(case.get("expected") or ""),
            }
        )
    return Mark(money(earned) if source.strip() else Decimal("0"), False, all_ok, {"cases": rows})
