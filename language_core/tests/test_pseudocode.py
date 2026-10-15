"""La impresora y el parser tienen que describir el mismo árbol."""

from decimal import Decimal

import pytest

from language_core.ast_nodes import (
    Algorithm,
    AssignStmt,
    BinaryExpr,
    CallExpr,
    CallStmt,
    DefineStmt,
    IndexExpr,
    LiteralExpr,
    LValue,
    NameExpr,
    Program,
    ReadStmt,
    SourceSpan,
    Stmt,
    UnaryExpr,
    WriteStmt,
    dump,
)
from language_core.grammar import STRICT
from language_core.lexer import lex
from language_core.parser import parse
from language_core.pseudocode import format_real, quote_text, render

SPAN = SourceSpan(1, 1, 1, 1)


def _program(*statements: Stmt) -> Program:
    return Program(Algorithm("Laboratorio", SPAN, statements, SPAN), (), (), SPAN)


def _reparse(source: str) -> Program:
    lexed = lex(source)
    assert lexed.diagnostics == ()
    program, diagnostics = parse(lexed.tokens, source, STRICT)
    assert diagnostics == ()
    assert program is not None
    return program


def test_render_uses_strict_words_and_round_trips() -> None:
    value = BinaryExpr(
        "add",
        NameExpr("precio", SPAN),
        LiteralExpr("entero", 2, "2", SPAN),
        SPAN,
    )
    program = _program(
        DefineStmt(("precio",), (SPAN,), "entero", SPAN),
        ReadStmt((LValue("precio", (), SPAN),), SPAN),
        AssignStmt(LValue("precio", (), SPAN), value, SPAN),
        WriteStmt((NameExpr("precio", SPAN),), SPAN),
    )
    source = render(program)
    assert source == (
        "Algoritmo Laboratorio\n"
        "    Definir precio Como Entero;\n"
        "    Leer precio;\n"
        "    precio <- precio + 2;\n"
        "    Escribir precio;\n"
        "FinAlgoritmo\n"
    )
    assert dump(_reparse(source)) == dump(program)


def test_right_subtraction_keeps_parentheses() -> None:
    inner = BinaryExpr("sub", NameExpr("b", SPAN), NameExpr("c", SPAN), SPAN)
    outer = BinaryExpr("sub", NameExpr("a", SPAN), inner, SPAN)
    program = _program(AssignStmt(LValue("total", (), SPAN), outer, SPAN))
    source = render(program)
    assert "total <- a - (b - c);" in source
    assert dump(_reparse(source)) == dump(program)


def test_left_subtraction_does_not_need_parentheses() -> None:
    inner = BinaryExpr("sub", NameExpr("a", SPAN), NameExpr("b", SPAN), SPAN)
    outer = BinaryExpr("sub", inner, NameExpr("c", SPAN), SPAN)
    program = _program(AssignStmt(LValue("total", (), SPAN), outer, SPAN))
    source = render(program)
    assert "total <- a - b - c;" in source
    assert dump(_reparse(source)) == dump(program)


def test_negative_and_positive_signs_round_trip() -> None:
    negative = UnaryExpr("neg", LiteralExpr("entero", 3, "3", SPAN), SPAN)
    positive = UnaryExpr("pos", LiteralExpr("real", 1, "1.0", SPAN), SPAN)
    program = _program(
        AssignStmt(LValue("a", (), SPAN), negative, SPAN),
        AssignStmt(LValue("b", (), SPAN), positive, SPAN),
    )
    source = render(program)
    assert "a <- -3;" in source
    assert "b <- +1.0;" in source
    assert dump(_reparse(source)) == dump(program)


def test_call_round_trips() -> None:
    call = CallExpr(
        "Concatenar",
        (
            LiteralExpr("cadena", "a", '"a"', SPAN),
            LiteralExpr("cadena", 'di "hola"', '"di \\"hola"', SPAN),
        ),
        SPAN,
    )
    program = _program(WriteStmt((call,), SPAN))
    source = render(program)
    assert 'Escribir Concatenar("a", "di \\"hola");' in source
    assert dump(_reparse(source)) == dump(program)


def test_escapes_fractional_reals_and_right_associativity() -> None:
    assert quote_text("a\\b\t", '"') == '"a\\\\b\\t"'
    assert format_real(Decimal("2.50")) == "2.5"
    assert format_real(Decimal(4)) == "4.0"
    with pytest.raises(ValueError):
        quote_text("\x01", "'")
    inner = BinaryExpr("pow", NameExpr("b", SPAN), NameExpr("c", SPAN), SPAN)
    nested = BinaryExpr("pow", inner, NameExpr("a", SPAN), SPAN)
    program = _program(AssignStmt(LValue("total", (), SPAN), nested, SPAN))
    source = render(program)
    assert "total <- (b ^ c) ^ a;" in source
    assert dump(_reparse(source)) == dump(program)


def test_render_round_trips_arrays_and_calls() -> None:
    cell = LiteralExpr("entero", 1, "1", SPAN)
    target = LValue("datos", (cell,), SPAN)
    index = IndexExpr("datos", (cell,), SPAN)
    program = _program(
        AssignStmt(target, LiteralExpr("entero", 8, "8", SPAN), SPAN),
        WriteStmt((index,), SPAN),
        CallStmt(CallExpr("Mostrar", (), SPAN), SPAN),
    )
    source = render(program)
    assert "datos[1] <- 8;" in source
    assert "Escribir datos[1];" in source
    assert "Mostrar();" in source
    assert dump(_reparse(source)) == dump(program)
