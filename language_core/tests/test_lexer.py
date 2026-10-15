"""Pruebas del analizador léxico."""

from language_core.grammar import (
    KEYWORD_DISPLAY,
    KEYWORDS,
    STDLIB_DISPLAY,
    STDLIB_NAMES,
    canonicalize,
)
from language_core.lexer import lex
from language_core.tokens import TokenKind


def test_keywords_ignore_case_and_accents() -> None:
    result = lex("Algoritmo Lógico\n")
    kinds = [
        (token.kind, token.canonical, token.lexeme)
        for token in result.tokens
        if token.kind is not TokenKind.EOF
    ]
    assert kinds[0][0] is TokenKind.KEYWORD
    assert kinds[0][1] == "algoritmo"
    assert kinds[0][2] == "Algoritmo"
    assert kinds[1][1] == "logico"
    assert kinds[1][2] == "Lógico"
    assert result.diagnostics == ()


def test_identifiers_keep_accents_and_differ() -> None:
    result = lex("año ano\n")
    names = [token.lexeme for token in result.tokens if token.kind is TokenKind.IDENT]
    assert names == ["año", "ano"]
    assert canonicalize("año") == "ano"
    assert names[0] != names[1]


def test_identifier_column_counts_codepoints() -> None:
    result = lex("Definir muñeco Como Cadena;\n")
    name = next(token for token in result.tokens if token.lexeme == "muñeco")
    assert name.span.start_line == 1
    assert name.span.start_col == 9
    assert name.span.end_col == 14


def test_string_escapes_and_char() -> None:
    result = lex(r'"hola\n\"x\"" ' + "'A'\n")
    string = result.tokens[0]
    char = result.tokens[1]
    assert string.kind is TokenKind.STRING
    assert string.value == 'hola\n"x"'
    assert char.kind is TokenKind.CHAR
    assert char.value == "A"


def test_unclosed_string_comment_and_char() -> None:
    string = lex('"hola\n')
    assert string.diagnostics[0].code == "E0102"
    assert string.diagnostics[0].span.start_line == 1
    comment = lex("/* sin cierre\n")
    assert comment.diagnostics[0].code == "E0103"
    assert comment.diagnostics[0].suggestion
    char = lex("'AB'\n")
    assert char.diagnostics[0].code == "E0106"


def test_unknown_character_and_bad_real() -> None:
    unknown = lex("@\n")
    assert unknown.diagnostics[0].code == "E0101"
    assert unknown.diagnostics[0].span.start_col == 1
    real = lex("9.\n")
    assert real.diagnostics[0].code == "E0104"
    assert real.tokens[0].kind is TokenKind.INT


def test_number_too_long() -> None:
    result = lex("1" * 4097)
    assert result.diagnostics[0].code == "E0107"


def test_symbols_and_boolean_literals() -> None:
    result = lex("a <- 1 <> 2 <= 3 >= 4 != 5 % 6^\n")
    kinds = [token.kind for token in result.tokens if token.kind is not TokenKind.EOF]
    assert TokenKind.ASSIGN in kinds
    assert TokenKind.NEQ in kinds
    assert TokenKind.LTE in kinds
    assert TokenKind.GTE in kinds
    logic = lex("Verdadero Falso\n")
    assert logic.tokens[0].value is True
    assert logic.tokens[1].value is False


def test_line_and_block_comments_are_skipped() -> None:
    result = lex("// nota\nAlgoritmo /* bloque */ X\n")
    words = [token.lexeme for token in result.tokens if token.kind is not TokenKind.EOF]
    assert words == ["Algoritmo", "X"]
    assert result.diagnostics == ()


def test_crlf_unclosed_char_and_dangling_escape() -> None:
    folded = lex("Algoritmo\r\nX\r\n")
    assert [token.lexeme for token in folded.tokens if token.kind is not TokenKind.EOF] == [
        "Algoritmo",
        "X",
    ]
    assert folded.tokens[1].span.start_line == 2
    assert lex("'A").diagnostics[0].code == "E0106"
    assert lex('"\\').diagnostics[0].code == "E0102"


def test_underscore_and_digits_in_names() -> None:
    result = lex("_a1\n")
    assert result.tokens[0].kind is TokenKind.IDENT
    assert result.tokens[0].lexeme == "_a1"


def test_bad_escape() -> None:
    result = lex(r'"\q"')
    assert result.diagnostics[0].code == "E0105"
    assert result.tokens[0].value == "q"


def test_english_spellings_use_the_spanish_canonical() -> None:
    from language_core.dialect import ALIASES, ENGLISH, SPANISH, resolve_keyword

    assert set(ENGLISH) == set(KEYWORDS)
    assert {canonicalize(word) for word in SPANISH.values()} == set(KEYWORDS)
    for folded, canonical in ALIASES.items():
        assert folded not in KEYWORDS
        assert resolve_keyword(folded) == canonical
    result = lex("Algorithm True False If\n")
    words = [token for token in result.tokens if token.kind is not TokenKind.EOF]
    assert [token.canonical for token in words] == ["algoritmo", "verdadero", "falso", "si"]
    assert words[1].value is True
    assert words[2].value is False
    assert result.diagnostics == ()


def test_display_words_match_the_lexer_tables() -> None:
    assert {canonicalize(word) for word in KEYWORD_DISPLAY} == set(KEYWORDS)
    assert {canonicalize(word) for word in STDLIB_DISPLAY} == set(STDLIB_NAMES)
    assert len(KEYWORD_DISPLAY) == len(KEYWORDS)
    assert "Caracter" in KEYWORD_DISPLAY
    assert len(STDLIB_DISPLAY) == len(STDLIB_NAMES)
