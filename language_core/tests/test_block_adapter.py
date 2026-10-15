"""JSON de bloques, árbol y texto tienen que coincidir al volver a parsear."""

import pytest

from language_core.ast_nodes import dump
from language_core.block_adapter import MAX_BLOCKS, MAX_DEPTH, adapt_workspace
from language_core.grammar import STRICT
from language_core.lexer import lex
from language_core.parser import parse
from language_core.pseudocode import render


def block(
    type_name: str,
    block_id: str,
    fields: dict[str, object] | None = None,
    inputs: dict[str, object] | None = None,
) -> dict[str, object]:
    data: dict[str, object] = {"type": type_name, "id": block_id}
    if fields is not None:
        data["fields"] = fields
    if inputs is not None:
        data["inputs"] = inputs
    return data


def value(child: dict[str, object]) -> dict[str, object]:
    return {"block": child}


def chain(*blocks: dict[str, object]) -> dict[str, object]:
    for earlier, later in zip(blocks, blocks[1:], strict=False):
        earlier["next"] = {"block": later}
    return blocks[0]


def workspace(*tops: dict[str, object]) -> dict[str, object]:
    return {"blocks": {"languageVersion": 0, "blocks": list(tops)}}


def var(name: str, type_name: str, block_id: str) -> dict[str, object]:
    return block("traza_variable", block_id, {"NOMBRE": name, "TIPO": type_name})


def whole(number: int, block_id: str) -> dict[str, object]:
    return block("traza_entero", block_id, {"VALOR": number})


def _reparse(source: str):
    lexed = lex(source)
    assert lexed.diagnostics == ()
    program, diagnostics = parse(lexed.tokens, source, STRICT)
    assert diagnostics == ()
    assert program is not None
    return program


def _errors(adapted) -> list[str]:
    return [item.code for item in adapted.diagnostics if item.severity == "error"]


def test_round_trip_of_the_first_cut() -> None:
    addition = block(
        "traza_aritmetica",
        "suma",
        {"OPERADOR": "add"},
        {"IZQUIERDA": value(var("n", "entero", "vn")), "DERECHA": value(whole(2, "dos"))},
    )
    product = block(
        "traza_aritmetica",
        "producto",
        {"OPERADOR": "mul"},
        {"IZQUIERDA": value(addition), "DERECHA": value(whole(-3, "menos"))},
    )
    divided = block(
        "traza_aritmetica",
        "cociente",
        {"OPERADOR": "idiv"},
        {"IZQUIERDA": value(var("n", "entero", "vn2")), "DERECHA": value(whole(2, "divisor"))},
    )
    remainder = block(
        "traza_aritmetica",
        "resto",
        {"OPERADOR": "mod"},
        {"IZQUIERDA": value(var("n", "entero", "vn3")), "DERECHA": value(whole(2, "modulo"))},
    )
    compared = block(
        "traza_relacional",
        "mayor",
        {"OPERADOR": "gt"},
        {"IZQUIERDA": value(var("n", "entero", "vn4")), "DERECHA": value(whole(0, "cero"))},
    )
    other = block(
        "traza_relacional",
        "menor",
        {"OPERADOR": "lt"},
        {"IZQUIERDA": value(var("n", "entero", "vn5")), "DERECHA": value(whole(10, "diez"))},
    )
    both = block(
        "traza_logica",
        "ambos",
        {"OPERADOR": "and"},
        {"IZQUIERDA": value(compared), "DERECHA": value(other)},
    )
    denied = block("traza_no", "niega", inputs={"VALOR": value(both)})
    joined = block(
        "traza_unir",
        "une",
        inputs={
            "IZQUIERDA": value(block("traza_cadena", "texto-a", {"VALOR": 'di "hola"'})),
            "DERECHA": value(block("traza_cadena", "texto-b", {"VALOR": "\n"})),
        },
    )
    root = chain(
        block("traza_definir", "def-n", {"NOMBRE": "n", "TIPO": "entero"}),
        block("traza_definir", "def-activo", {"NOMBRE": "activo", "TIPO": "logico"}),
        block("traza_definir", "def-texto", {"NOMBRE": "texto", "TIPO": "cadena"}),
        block("traza_leer", "lee", {"NOMBRE": "n"}),
        block("traza_asignar", "asigna-producto", {"NOMBRE": "n"}, {"VALOR": value(product)}),
        block("traza_asignar", "asigna-div", {"NOMBRE": "n"}, {"VALOR": value(divided)}),
        block("traza_asignar", "asigna-mod", {"NOMBRE": "n"}, {"VALOR": value(remainder)}),
        block("traza_asignar", "asigna-flag", {"NOMBRE": "activo"}, {"VALOR": value(denied)}),
        block("traza_asignar", "asigna-texto", {"NOMBRE": "texto"}, {"VALOR": value(joined)}),
        block(
            "traza_escribir",
            "escribe-texto",
            inputs={"VALOR": value(var("texto", "cadena", "vtexto"))},
        ),
        block(
            "traza_escribir",
            "escribe-flag",
            inputs={"VALOR": value(var("activo", "logico", "vflag"))},
        ),
        block(
            "traza_escribir",
            "escribe-letra",
            inputs={"VALOR": value(block("traza_caracter", "letra", {"VALOR": "'"}))},
        ),
        block(
            "traza_escribir",
            "escribe-real",
            inputs={"VALOR": value(block("traza_real", "pi", {"VALOR": 1}))},
        ),
    )
    adapted = adapt_workspace(workspace(root))
    assert adapted.program is not None
    assert _errors(adapted) == []
    assert render(adapted.program) == adapted.source
    assert "(n + 2) * -3" in adapted.source
    assert "n DIV 2" in adapted.source
    assert "n MOD 2" in adapted.source
    assert "NO (n > 0 Y n < 10)" in adapted.source
    assert 'Concatenar("di \\"hola\\"", "\\n")' in adapted.source
    assert "Escribir '\\'';" in adapted.source
    assert "Escribir 1.0;" in adapted.source
    assert dump(_reparse(adapted.source)) == dump(adapted.program)

    define = next(item for item in adapted.bindings if item.block_id == "def-n")
    assert define.line == 2
    assert define.column == 5
    assert adapted.source.splitlines()[1][4:].startswith("Definir")
    number = next(item for item in adapted.bindings if item.block_id == "menos")
    line = adapted.source.splitlines()[number.line - 1]
    assert line[number.column - 1 :].startswith("-3")


def test_left_nested_subtraction_matches_the_tree() -> None:
    inner = block(
        "traza_aritmetica",
        "resta-izq",
        {"OPERADOR": "sub"},
        {"IZQUIERDA": value(var("a", "entero", "va")), "DERECHA": value(var("b", "entero", "vb"))},
    )
    outer = block(
        "traza_aritmetica",
        "resta",
        {"OPERADOR": "sub"},
        {"IZQUIERDA": value(inner), "DERECHA": value(var("c", "entero", "vc"))},
    )
    root = chain(
        block("traza_definir", "da", {"NOMBRE": "a", "TIPO": "entero"}),
        block("traza_definir", "db", {"NOMBRE": "b", "TIPO": "entero"}),
        block("traza_definir", "dc", {"NOMBRE": "c", "TIPO": "entero"}),
        block("traza_asignar", "asigna", {"NOMBRE": "a"}, {"VALOR": value(outer)}),
        block("traza_escribir", "sale", inputs={"VALOR": value(var("a", "entero", "va2"))}),
    )
    adapted = adapt_workspace(workspace(root))
    assert adapted.program is not None
    assert "a <- a - b - c;" in adapted.source
    assert render(adapted.program) == adapted.source
    assert dump(_reparse(adapted.source)) == dump(adapted.program)


def test_right_nested_subtraction_is_parenthesized() -> None:
    inner = block(
        "traza_aritmetica",
        "resta-der",
        {"OPERADOR": "sub"},
        {"IZQUIERDA": value(var("b", "entero", "vb")), "DERECHA": value(var("c", "entero", "vc"))},
    )
    outer = block(
        "traza_aritmetica",
        "resta",
        {"OPERADOR": "sub"},
        {"IZQUIERDA": value(var("a", "entero", "va")), "DERECHA": value(inner)},
    )
    root = chain(
        block("traza_definir", "da", {"NOMBRE": "a", "TIPO": "entero"}),
        block("traza_definir", "db", {"NOMBRE": "b", "TIPO": "entero"}),
        block("traza_definir", "dc", {"NOMBRE": "c", "TIPO": "entero"}),
        block("traza_asignar", "asigna", {"NOMBRE": "a"}, {"VALOR": value(outer)}),
    )
    adapted = adapt_workspace(workspace(root))
    assert adapted.program is not None
    assert "a <- a - (b - c);" in adapted.source
    assert dump(_reparse(adapted.source)) == dump(adapted.program)


def test_empty_workspace_is_an_empty_algorithm() -> None:
    adapted = adapt_workspace(workspace())
    assert adapted.program is not None
    assert adapted.diagnostics == ()
    assert adapted.source == "Algoritmo Laboratorio\nFinAlgoritmo\n"
    assert render(adapted.program) == adapted.source
    assert dump(_reparse(adapted.source)) == dump(adapted.program)


def test_two_stacks_keep_workspace_order() -> None:
    adapted = adapt_workspace(
        workspace(
            block("traza_definir", "uno", {"NOMBRE": "a", "TIPO": "entero"}),
            block("traza_definir", "dos", {"NOMBRE": "b", "TIPO": "real"}),
        )
    )
    assert adapted.program is not None
    lines = adapted.source.splitlines()
    assert lines[1] == "    Definir a Como Entero;"
    assert lines[2] == "    Definir b Como Real;"


def test_type_mismatch_warns_and_keeps_the_tree() -> None:
    root = chain(
        block("traza_definir", "def", {"NOMBRE": "precio", "TIPO": "entero"}),
        block(
            "traza_escribir",
            "sale",
            inputs={"VALOR": value(var("precio", "real", "vp"))},
        ),
    )
    adapted = adapt_workspace(workspace(root))
    assert adapted.program is not None
    assert _errors(adapted) == []
    assert any(item.code == "L0101" for item in adapted.diagnostics)
    assert dump(_reparse(adapted.source)) == dump(adapted.program)


def test_semantic_error_keeps_the_program() -> None:
    undeclared = adapt_workspace(
        workspace(
            block(
                "traza_escribir",
                "sale",
                inputs={"VALOR": value(var("precio", "entero", "vp"))},
            )
        )
    )
    assert undeclared.program is not None
    assert "E0301" in _errors(undeclared)
    assert dump(_reparse(undeclared.source)) == dump(undeclared.program)

    mixed = chain(
        block("traza_definir", "def", {"NOMBRE": "precio", "TIPO": "entero"}),
        block(
            "traza_asignar",
            "asigna",
            {"NOMBRE": "precio"},
            {
                "VALOR": value(
                    block(
                        "traza_aritmetica",
                        "suma",
                        {"OPERADOR": "add"},
                        {
                            "IZQUIERDA": value(
                                block("traza_logico", "flag", {"VALOR": "verdadero"})
                            ),
                            "DERECHA": value(whole(1, "uno")),
                        },
                    )
                )
            },
        ),
    )
    adapted = adapt_workspace(workspace(mixed))
    assert adapted.program is not None
    assert "E0305" in _errors(adapted)
    assert dump(_reparse(adapted.source)) == dump(adapted.program)


@pytest.mark.parametrize(
    ("data", "code"),
    [
        ({"blocks": "no"}, "L0005"),
        (workspace(block("traza_desconocido", "x")), "L0001"),
        (workspace(block("traza_si", "x")), "L0002"),
        (workspace(block("traza_asignar", "a", {"NOMBRE": "precio"})), "L0002"),
        (workspace(block("traza_entero", "n", {"VALOR": 1})), "L0004"),
        (
            workspace(
                block(
                    "traza_asignar",
                    "a",
                    {"NOMBRE": "precio"},
                    {
                        "VALOR": value(
                            block("traza_definir", "d", {"NOMBRE": "precio", "TIPO": "entero"})
                        )
                    },
                )
            ),
            "L0004",
        ),
        (workspace(block("traza_definir", "d", {"NOMBRE": "Si", "TIPO": "entero"})), "L0003"),
        (workspace(block("traza_definir", "d", {"NOMBRE": "precio", "TIPO": "matriz"})), "L0002"),
        (workspace(block("traza_definir", "", {"NOMBRE": "precio", "TIPO": "entero"})), "L0002"),
        (workspace(block("traza_entero", "n")), "L0004"),
    ],
)
def test_structural_errors_do_not_build_a_program(data: dict[str, object], code: str) -> None:
    adapted = adapt_workspace(data)
    assert adapted.program is None
    assert adapted.source == ""
    assert adapted.diagnostics[0].code == code


def test_duplicate_block_id_is_rejected() -> None:
    first = block("traza_definir", "mismo", {"NOMBRE": "a", "TIPO": "entero"})
    second = block("traza_definir", "mismo", {"NOMBRE": "b", "TIPO": "entero"})
    first["next"] = {"block": second}
    adapted = adapt_workspace(workspace(first))
    assert adapted.program is None
    assert adapted.diagnostics[0].code == "L0006"


def test_chained_comparison_is_not_a_program() -> None:
    inner = block(
        "traza_relacional",
        "interna",
        {"OPERADOR": "lt"},
        {"IZQUIERDA": value(var("a", "entero", "va")), "DERECHA": value(var("b", "entero", "vb"))},
    )
    outer = block(
        "traza_relacional",
        "externa",
        {"OPERADOR": "lt"},
        {"IZQUIERDA": value(inner), "DERECHA": value(var("c", "entero", "vc"))},
    )
    root = chain(
        block("traza_definir", "da", {"NOMBRE": "a", "TIPO": "entero"}),
        block("traza_escribir", "sale", inputs={"VALOR": value(outer)}),
    )
    adapted = adapt_workspace(workspace(root))
    assert adapted.program is None
    assert adapted.diagnostics[0].code == "L0004"


def test_decimal_integer_and_bad_character_fail() -> None:
    decimal = chain(
        block("traza_definir", "d", {"NOMBRE": "n", "TIPO": "entero"}),
        block(
            "traza_asignar",
            "a",
            {"NOMBRE": "n"},
            {"VALOR": value(block("traza_entero", "n", {"VALOR": 1.5}))},
        ),
    )
    adapted = adapt_workspace(workspace(decimal))
    assert adapted.program is None
    assert adapted.diagnostics[0].code == "L0002"

    letter = block(
        "traza_escribir",
        "sale",
        inputs={"VALOR": value(block("traza_caracter", "c", {"VALOR": "ab"}))},
    )
    adapted = adapt_workspace(workspace(letter))
    assert adapted.diagnostics[0].code == "L0002"


def test_block_limits() -> None:
    first = block("traza_definir", "b0", {"NOMBRE": "v0", "TIPO": "entero"})
    cursor = first
    for index in range(1, MAX_BLOCKS + 1):
        nxt = block("traza_definir", f"b{index}", {"NOMBRE": f"v{index}", "TIPO": "entero"})
        cursor["next"] = {"block": nxt}
        cursor = nxt
    adapted = adapt_workspace(workspace(first))
    assert adapted.program is None
    assert adapted.diagnostics[0].code == "L0006"

    child: dict[str, object] = block("traza_logico", "flag", {"VALOR": "falso"})
    for index in range(MAX_DEPTH + 2):
        child = block("traza_no", f"no-{index}", inputs={"VALOR": value(child)})
    deep = chain(
        block("traza_definir", "d", {"NOMBRE": "activo", "TIPO": "logico"}),
        block("traza_asignar", "a", {"NOMBRE": "activo"}, {"VALOR": value(child)}),
    )
    adapted = adapt_workspace(workspace(deep))
    assert adapted.program is None
    assert adapted.diagnostics[0].code == "L0006"


def test_remaining_operators_and_literals_round_trip() -> None:
    compared = block(
        "traza_logica",
        "o",
        {"OPERADOR": "or"},
        {
            "IZQUIERDA": value(
                block(
                    "traza_relacional",
                    "eq",
                    {"OPERADOR": "eq"},
                    {
                        "IZQUIERDA": value(var("año", "entero", "vn")),
                        "DERECHA": value(whole(1, "uno")),
                    },
                )
            ),
            "DERECHA": value(
                block(
                    "traza_relacional",
                    "lte",
                    {"OPERADOR": "lte"},
                    {
                        "IZQUIERDA": value(var("_base", "real", "vb")),
                        "DERECHA": value(block("traza_real", "tope", {"VALOR": -2.5})),
                    },
                )
            ),
        },
    )
    divided = block(
        "traza_aritmetica",
        "div",
        {"OPERADOR": "div"},
        {
            "IZQUIERDA": value(var("_base", "real", "vb2")),
            "DERECHA": value(block("traza_real", "medio", {"VALOR": " 2 "})),
        },
    )
    root = chain(
        block("traza_definir", "dn", {"NOMBRE": "año", "TIPO": "entero"}),
        block("traza_definir", "db", {"NOMBRE": "_base", "TIPO": "real"}),
        block("traza_definir", "dt", {"NOMBRE": "texto", "TIPO": "cadena"}),
        block("traza_definir", "da", {"NOMBRE": "activo", "TIPO": "logico"}),
        block("traza_asignar", "an", {"NOMBRE": "año"}, {"VALOR": value(whole(1, "literal"))}),
        block("traza_asignar", "ab", {"NOMBRE": "_base"}, {"VALOR": value(divided)}),
        block(
            "traza_asignar",
            "at",
            {"NOMBRE": "texto"},
            {"VALOR": value(block("traza_cadena", "texto", {"VALOR": "a\\b\t"}))},
        ),
        block("traza_asignar", "aa", {"NOMBRE": "activo"}, {"VALOR": value(compared)}),
        block(
            "traza_escribir",
            "sale",
            inputs={
                "VALOR": value(
                    block(
                        "traza_relacional",
                        "gte",
                        {"OPERADOR": "gte"},
                        {
                            "IZQUIERDA": value(var("_base", "real", "vb3")),
                            "DERECHA": value(block("traza_real", "cero", {"VALOR": 0})),
                        },
                    )
                )
            },
        ),
    )
    adapted = adapt_workspace(workspace(root))
    assert adapted.program is not None, [item.message for item in adapted.diagnostics]
    assert _errors(adapted) == []
    assert " O " in adapted.source
    assert "/ " in adapted.source
    assert "-2.5" in adapted.source
    assert render(adapted.program) == adapted.source
    assert dump(_reparse(adapted.source)) == dump(adapted.program)


def test_bad_fields_are_structural() -> None:
    cases = [
        block(
            "traza_asignar",
            "a",
            {"NOMBRE": "n"},
            {"VALOR": value(block("traza_entero", "n", {"VALOR": "no"}))},
        ),
        block(
            "traza_asignar",
            "a",
            {"NOMBRE": "n"},
            {"VALOR": value(block("traza_entero", "n", {"VALOR": True}))},
        ),
        block(
            "traza_asignar",
            "a",
            {"NOMBRE": "n"},
            {"VALOR": value(block("traza_real", "n", {"VALOR": "Infinity"}))},
        ),
        block(
            "traza_escribir",
            "e",
            inputs={"VALOR": value(block("traza_cadena", "c", {"VALOR": 1}))},
        ),
        block(
            "traza_escribir",
            "e",
            inputs={"VALOR": value(block("traza_cadena", "c", {"VALOR": "\x01"}))},
        ),
        block(
            "traza_escribir",
            "e",
            inputs={"VALOR": value(block("traza_caracter", "c", {"VALOR": "\x01"}))},
        ),
        block(
            "traza_escribir",
            "e",
            inputs={"VALOR": value(block("traza_logico", "c", {"VALOR": "quizas"}))},
        ),
        block(
            "traza_escribir",
            "e",
            inputs={
                "VALOR": value(
                    block(
                        "traza_aritmetica",
                        "op",
                        {"OPERADOR": "pow"},
                        {
                            "IZQUIERDA": value(whole(1, "i")),
                            "DERECHA": value(whole(2, "d")),
                        },
                    )
                )
            },
        ),
        block(
            "traza_escribir",
            "e",
            inputs={
                "VALOR": value(
                    block(
                        "traza_relacional",
                        "op",
                        {"OPERADOR": "parecido"},
                        {
                            "IZQUIERDA": value(whole(1, "i")),
                            "DERECHA": value(whole(2, "d")),
                        },
                    )
                )
            },
        ),
        block(
            "traza_escribir",
            "e",
            inputs={
                "VALOR": value(
                    block(
                        "traza_logica",
                        "op",
                        {"OPERADOR": "xor"},
                        {
                            "IZQUIERDA": value(block("traza_logico", "p", {"VALOR": "falso"})),
                            "DERECHA": value(block("traza_logico", "q", {"VALOR": "falso"})),
                        },
                    )
                )
            },
        ),
        block("traza_definir", "d", {"NOMBRE": "1a", "TIPO": "entero"}),
        {"type": "bloque-" + "x" * 40, "id": "largo"},
    ]
    for item in cases:
        adapted = adapt_workspace(workspace(item))
        assert adapted.program is None
        assert adapted.diagnostics[0].code in {"L0001", "L0002", "L0003"}


def test_alternate_workspace_shapes() -> None:
    defined = block("traza_definir", "d", {"NOMBRE": "n", "TIPO": "entero"})
    adapted = adapt_workspace({"blocks": [defined]})
    assert adapted.program is not None
    assert "Definir n Como Entero;" in adapted.source
    assert adapt_workspace({"blocks": [1]}).diagnostics[0].code == "L0005"
    assert adapt_workspace({1: "x"}).diagnostics[0].code == "L0005"
    empty = adapt_workspace({})
    assert empty.program is not None
    assert empty.source.startswith("Algoritmo Laboratorio")
    assert adapt_workspace({"blocks": None}).source == empty.source


def test_algorithm_name_must_be_an_identifier() -> None:
    adapted = adapt_workspace(workspace(), algorithm_name="Si")
    assert adapted.program is None
    assert adapted.diagnostics[0].code == "L0003"


def _compare(operator: str, ident: str) -> dict[str, object]:
    return block(
        "traza_relacional",
        ident,
        {"OPERADOR": operator},
        {
            "IZQUIERDA": value(var("n", "entero", f"v{ident}")),
            "DERECHA": value(whole(0, f"z{ident}")),
        },
    )


def test_if_and_while_round_trip_including_the_false_branch() -> None:
    branch = block(
        "traza_si_sino",
        "si",
        inputs={
            "CONDICION": value(_compare("gt", "c")),
            "ENTONCES": value(
                block(
                    "traza_escribir",
                    "ep",
                    inputs={"VALOR": value(block("traza_cadena", "tp", {"VALOR": "positivo"}))},
                )
            ),
            "SINO": value(
                block(
                    "traza_escribir",
                    "ec",
                    inputs={"VALOR": value(block("traza_cadena", "tc", {"VALOR": "cero"}))},
                )
            ),
        },
    )
    empty = block(
        "traza_si",
        "vacio",
        inputs={"CONDICION": value(block("traza_logico", "flag", {"VALOR": "falso"}))},
    )
    loop = block(
        "traza_mientras",
        "ciclo",
        inputs={
            "CONDICION": value(_compare("gt", "cm")),
            "CUERPO": value(
                chain(
                    block(
                        "traza_escribir",
                        "em",
                        inputs={"VALOR": value(var("n", "entero", "vn3"))},
                    ),
                    block(
                        "traza_asignar",
                        "baja",
                        {"NOMBRE": "n"},
                        {
                            "VALOR": value(
                                block(
                                    "traza_aritmetica",
                                    "resta",
                                    {"OPERADOR": "sub"},
                                    {
                                        "IZQUIERDA": value(var("n", "entero", "vn4")),
                                        "DERECHA": value(whole(1, "uno")),
                                    },
                                )
                            )
                        },
                    ),
                )
            ),
        },
    )
    root = chain(
        block("traza_definir", "def-n", {"NOMBRE": "n", "TIPO": "entero"}),
        block("traza_asignar", "cero", {"NOMBRE": "n"}, {"VALOR": value(whole(0, "inicio"))}),
        branch,
        empty,
        loop,
        block("traza_escribir", "fin", inputs={"VALOR": value(var("n", "entero", "vn5"))}),
    )
    adapted = adapt_workspace(workspace(root))
    assert _errors(adapted) == []
    assert adapted.program is not None
    assert "Sino" in adapted.source
    assert "FinMientras" in adapted.source
    assert dump(_reparse(adapted.source)) == dump(adapted.program)
    assert dump(_reparse(render(adapted.program))) == dump(adapted.program)
    inner = next(item for item in adapted.bindings if item.block_id == "ec")
    outer = next(item for item in adapted.bindings if item.block_id == "si")
    assert inner.line > outer.line


def test_segun_para_and_repeat_round_trip() -> None:
    menu = block(
        "traza_segun",
        "sg",
        inputs={
            "VALOR": value(var("opcion", "entero", "vo")),
            "CASO1": value(whole(1, "c1")),
            "HACER1": value(
                block(
                    "traza_escribir",
                    "e1",
                    inputs={"VALOR": value(block("traza_cadena", "t1", {"VALOR": "uno"}))},
                )
            ),
            "CASO2": value(whole(2, "c2")),
            "HACER2": value(
                block(
                    "traza_escribir",
                    "e2",
                    inputs={"VALOR": value(block("traza_cadena", "t2", {"VALOR": "dos"}))},
                )
            ),
            "OTRO": value(
                block(
                    "traza_escribir",
                    "e0",
                    inputs={"VALOR": value(block("traza_cadena", "t0", {"VALOR": "otro"}))},
                )
            ),
        },
    )
    counted = block(
        "traza_para",
        "p",
        {"NOMBRE": "i"},
        {
            "DESDE": value(whole(1, "desde")),
            "HASTA": value(var("n", "entero", "vn")),
            "PASO": value(whole(1, "paso")),
            "CUERPO": value(
                block(
                    "traza_escribir",
                    "ei",
                    inputs={"VALOR": value(var("i", "entero", "vi"))},
                )
            ),
        },
    )
    body = chain(
        block(
            "traza_asignar",
            "suma",
            {"NOMBRE": "n"},
            {
                "VALOR": value(
                    block(
                        "traza_aritmetica",
                        "op",
                        {"OPERADOR": "add"},
                        {
                            "IZQUIERDA": value(var("n", "entero", "vn2")),
                            "DERECHA": value(whole(1, "uno")),
                        },
                    )
                )
            },
        ),
        block(
            "traza_escribir",
            "en",
            inputs={"VALOR": value(var("n", "entero", "vn3"))},
        ),
    )
    repeat = block(
        "traza_repetir",
        "r",
        inputs={
            "CUERPO": value(body),
            "CONDICION": value(_compare("eq", "fin")),
        },
    )
    root = chain(
        block("traza_definir", "do", {"NOMBRE": "opcion", "TIPO": "entero"}),
        block("traza_definir", "dn", {"NOMBRE": "n", "TIPO": "entero"}),
        block("traza_definir", "di", {"NOMBRE": "i", "TIPO": "entero"}),
        block("traza_asignar", "cero", {"NOMBRE": "n"}, {"VALOR": value(whole(0, "z"))}),
        menu,
        counted,
        repeat,
    )
    adapted = adapt_workspace(workspace(root))
    assert _errors(adapted) == []
    assert adapted.program is not None
    assert "De Otro Modo:" in adapted.source
    assert "FinPara" in adapted.source
    assert "Hasta Que" in adapted.source
    assert dump(_reparse(adapted.source)) == dump(adapted.program)
    assert dump(_reparse(render(adapted.program))) == dump(adapted.program)
    labeled = adapt_workspace(
        workspace(
            block(
                "traza_segun",
                "sg",
                inputs={
                    "VALOR": value(whole(1, "sel")),
                    "CASO1": value(var("n", "entero", "vn")),
                    "HACER1": value(
                        block("traza_escribir", "e", inputs={"VALOR": value(whole(1, "uno"))})
                    ),
                    "CASO2": value(whole(2, "dos")),
                    "HACER2": value(
                        block("traza_escribir", "e2", inputs={"VALOR": value(whole(2, "dosw"))})
                    ),
                    "OTRO": value(
                        block("traza_escribir", "e0", inputs={"VALOR": value(whole(0, "cero"))})
                    ),
                },
            )
        )
    )
    assert labeled.program is not None
    assert "E0315" in _errors(labeled)
    negative = adapt_workspace(
        workspace(
            block(
                "traza_segun",
                "sg",
                inputs={
                    "VALOR": value(whole(1, "sel")),
                    "CASO1": value(whole(-1, "menos")),
                    "HACER1": value(
                        block("traza_escribir", "e", inputs={"VALOR": value(whole(1, "uno"))})
                    ),
                },
            )
        )
    )
    assert "E0315" not in _errors(negative)
    assert negative.program is not None
    assert "-1:" in negative.source


def test_segun_reads_each_case_named_in_its_extra_state() -> None:
    def arm(ident: str, number: int) -> dict[str, object]:
        return value(
            block(
                "traza_escribir",
                ident,
                inputs={"VALOR": value(block("traza_cadena", f"t{ident}", {"VALOR": str(number)}))},
            )
        )

    menu = block(
        "traza_segun",
        "sg",
        inputs={
            "VALOR": value(var("opcion", "entero", "vo")),
            "CASO1": value(whole(1, "c1")),
            "HACER1": arm("e1", 1),
            "CASO2": value(whole(2, "c2")),
            "HACER2": arm("e2", 2),
            "CASO3": value(whole(3, "c3")),
            "HACER3": arm("e3", 3),
            "OTRO": arm("e0", 0),
        },
    )
    menu["extraState"] = {"casos": 3}
    root = chain(
        block("traza_definir", "d", {"NOMBRE": "opcion", "TIPO": "entero"}),
        menu,
    )
    adapted = adapt_workspace(workspace(root))
    assert _errors(adapted) == []
    assert adapted.program is not None
    assert "3:" in adapted.source
    assert dump(_reparse(adapted.source)) == dump(adapted.program)
    incomplete = block(
        "traza_segun",
        "sg",
        inputs={
            "VALOR": value(whole(1, "sel")),
            "CASO1": value(whole(1, "c1")),
            "HACER1": arm("e1", 1),
            "CASO2": value(whole(2, "c2")),
            "HACER2": arm("e2", 2),
            "OTRO": arm("e0", 0),
        },
    )
    incomplete["extraState"] = {"casos": 3}
    missing = adapt_workspace(workspace(incomplete))
    assert missing.program is None
    assert "L0002" in _errors(missing)


def test_arrays_and_functions_round_trip() -> None:
    function = block(
        "traza_funcion",
        "fn",
        {"RESULTADO": "resultado", "NOMBRE": "Doblar", "PARAM1": "n", "MODO1": "valor"},
        {
            "CUERPO": value(
                chain(
                    block("traza_definir", "dr", {"NOMBRE": "resultado", "TIPO": "entero"}),
                    block("traza_definir", "dn", {"NOMBRE": "n", "TIPO": "entero"}),
                    block(
                        "traza_asignar",
                        "as",
                        {"NOMBRE": "resultado"},
                        {
                            "VALOR": value(
                                block(
                                    "traza_aritmetica",
                                    "mul",
                                    {"OPERADOR": "mul"},
                                    {
                                        "IZQUIERDA": value(var("n", "entero", "vn")),
                                        "DERECHA": value(whole(2, "dos")),
                                    },
                                )
                            )
                        },
                    ),
                )
            )
        },
    )
    function["extraState"] = {"parametros": 1}
    procedure = block(
        "traza_procedimiento",
        "proc",
        {"NOMBRE": "Incrementar", "PARAM1": "edad", "MODO1": "referencia"},
        {
            "CUERPO": value(
                chain(
                    block("traza_definir", "de", {"NOMBRE": "edad", "TIPO": "entero"}),
                    block(
                        "traza_asignar",
                        "ae",
                        {"NOMBRE": "edad"},
                        {
                            "VALOR": value(
                                block(
                                    "traza_aritmetica",
                                    "sum",
                                    {"OPERADOR": "add"},
                                    {
                                        "IZQUIERDA": value(var("edad", "entero", "ve")),
                                        "DERECHA": value(whole(1, "uno")),
                                    },
                                )
                            )
                        },
                    ),
                )
            )
        },
    )
    procedure["extraState"] = {"parametros": 1}
    cell = block(
        "traza_indice",
        "celda",
        {"NOMBRE": "datos", "TIPO": "entero"},
        {"INDICE1": value(whole(1, "i1"))},
    )
    call = block(
        "traza_llamada",
        "ll",
        {"NOMBRE": "Doblar", "TIPO": "entero"},
        {"ARG1": value(whole(3, "tres"))},
    )
    call["extraState"] = {"argumentos": 1}
    algorithm = chain(
        block("traza_definir", "dd", {"NOMBRE": "datos", "TIPO": "entero"}),
        block(
            "traza_dimension",
            "dim",
            {"NOMBRE": "datos", "TIPO": "entero"},
            {"TAMANO1": value(whole(3, "tam"))},
        ),
        block(
            "traza_asignar_indice",
            "ai",
            {"NOMBRE": "datos"},
            {"INDICE1": value(whole(1, "i2")), "VALOR": value(whole(8, "ocho"))},
        ),
        block(
            "traza_leer_indice",
            "li",
            {"NOMBRE": "datos"},
            {"INDICE1": value(whole(2, "i3"))},
        ),
        block("traza_escribir", "ew", inputs={"VALOR": value(cell)}),
        block("traza_escribir", "ed", inputs={"VALOR": value(call)}),
        block("traza_definir", "dedad", {"NOMBRE": "edad", "TIPO": "entero"}),
        block(
            "traza_asignar",
            "aedad",
            {"NOMBRE": "edad"},
            {"VALOR": value(whole(17, "diecisiete"))},
        ),
        block(
            "traza_llamar",
            "lz",
            {"NOMBRE": "Incrementar", "MODO1": "referencia"},
            {"ARG1": value(var("edad", "entero", "vcall"))},
        ),
    )
    adapted = adapt_workspace(workspace(function, procedure, algorithm))
    assert adapted.program is not None
    assert _errors(adapted) == []
    assert "Funcion resultado <- Doblar(n)" in adapted.source
    assert "Dimension datos[3] Como Entero;" in adapted.source
    assert "datos[1] <- 8;" in adapted.source
    assert "Leer datos[2];" in adapted.source
    assert "Doblar(3)" in adapted.source
    assert "Incrementar(edad);" in adapted.source
    assert "SubProceso Incrementar(edad Por Referencia)" in adapted.source
    assert render(adapted.program) == adapted.source
    assert dump(_reparse(adapted.source)) == dump(adapted.program)


def test_a_number_cannot_be_a_condition_and_a_value_cannot_be_missing() -> None:
    numeric = block(
        "traza_si",
        "si",
        inputs={
            "CONDICION": value(whole(1, "uno")),
            "ENTONCES": value(
                block("traza_escribir", "e", inputs={"VALOR": value(whole(1, "otro"))})
            ),
        },
    )
    adapted = adapt_workspace(workspace(numeric))
    assert adapted.program is not None
    assert "E0304" in _errors(adapted)
    missing = adapt_workspace(workspace(block("traza_mientras", "ciclo")))
    assert missing.program is None
    assert "L0002" in _errors(missing)
