"""Tokens del lexer."""

from __future__ import annotations

import enum
from dataclasses import dataclass

from language_core.ast_nodes import SourceSpan


class TokenKind(enum.Enum):
    """Clases de token. Las palabras clave usan KEYWORD y un canónico."""

    EOF = "eof"
    IDENT = "ident"
    KEYWORD = "keyword"
    INT = "int"
    REAL = "real"
    STRING = "string"
    CHAR = "char"
    ASSIGN = "assign"
    PLUS = "plus"
    MINUS = "minus"
    STAR = "star"
    SLASH = "slash"
    PERCENT = "percent"
    CARET = "caret"
    EQ = "eq"
    NEQ = "neq"
    LT = "lt"
    GT = "gt"
    LTE = "lte"
    GTE = "gte"
    LPAREN = "lparen"
    RPAREN = "rparen"
    LBRACK = "lbrack"
    RBRACK = "rbrack"
    COMMA = "comma"
    SEMICOLON = "semicolon"
    COLON = "colon"


@dataclass(frozen=True)
class Token:
    """Un lexema con su posición.

    En un identificador, `canonical` conserva el texto original.
    En una palabra clave, `canonical` está plegado sin acentos.
    `value` guarda el literal ya decodificado, cuando existe.
    """

    kind: TokenKind
    lexeme: str
    canonical: str
    span: SourceSpan
    value: object | None = None

    def is_kw(self, name: str) -> bool:
        """Indica si este token es la palabra clave canónica indicada."""
        return self.kind is TokenKind.KEYWORD and self.canonical == name
