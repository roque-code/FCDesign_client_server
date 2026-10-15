"""Analizador léxico.

Las palabras clave se reconocen sin distinguir mayúsculas ni acentos.
El lexema original se conserva. Los identificadores no se pliegan.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from decimal import Decimal

from language_core.ast_nodes import SourceSpan
from language_core.diagnostics import Diagnostic, make_diagnostic
from language_core.dialect import resolve_keyword
from language_core.grammar import canonicalize
from language_core.tokens import Token, TokenKind

MAX_NUMBER_DIGITS = 4096


@dataclass(frozen=True)
class LexResult:
    """Tokens, incluido EOF, y los diagnósticos léxicos."""

    tokens: tuple[Token, ...]
    diagnostics: tuple[Diagnostic, ...]


class Lexer:
    """Recorre el fuente una vez y produce tokens."""

    def __init__(self, source: str) -> None:
        self.source = source.lstrip("\ufeff")
        self.length = len(self.source)
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: list[Token] = []
        self.diagnostics: list[Diagnostic] = []

    def scan(self) -> LexResult:
        while not self._eof():
            self._skip_space_and_comments()
            if self._eof():
                break
            self._scan_token()
        eof_span = SourceSpan(self.line, self.col, self.line, self.col)
        self.tokens.append(Token(TokenKind.EOF, "", "", eof_span))
        return LexResult(tuple(self.tokens), tuple(self.diagnostics))

    def _eof(self) -> bool:
        return self.pos >= self.length

    def _peek(self, offset: int = 0) -> str:
        index = self.pos + offset
        if index >= self.length:
            return ""
        return self.source[index]

    def _advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\r":
            if self._peek() == "\n":
                self.pos += 1
            self.line += 1
            self.col = 1
            return "\n"
        if ch == "\n":
            self.line += 1
            self.col = 1
            return "\n"
        self.col += 1
        return ch

    def _span_from(self, line: int, col: int) -> SourceSpan:
        return SourceSpan(line, col, self.line, self.col - 1)

    def _error(
        self, code: str, message: str, span: SourceSpan, suggestion: str | None = None
    ) -> None:
        self.diagnostics.append(
            make_diagnostic(self.source, "error", code, message, span, suggestion)
        )

    def _skip_space_and_comments(self) -> None:
        while not self._eof():
            ch = self._peek()
            if ch in " \t\n\r":
                self._advance()
                continue
            if ch == "/" and self._peek(1) == "/":
                while not self._eof() and self._peek() not in "\n\r":
                    self._advance()
                continue
            if ch == "/" and self._peek(1) == "*":
                self._skip_block_comment()
                continue
            break

    def _skip_block_comment(self) -> None:
        start_line, start_col = self.line, self.col
        self._advance()
        self._advance()
        while not self._eof():
            if self._peek() == "*" and self._peek(1) == "/":
                self._advance()
                self._advance()
                return
            self._advance()
        self._error(
            "E0103",
            "El comentario que empieza aquí no tiene cierre.",
            SourceSpan(start_line, start_col, start_line, start_col + 1),
            "Cierra el comentario con */.",
        )

    def _scan_token(self) -> None:
        start_line, start_col = self.line, self.col
        ch = self._peek()
        if _is_ident_start(ch):
            self._scan_word(start_line, start_col)
            return
        if ch.isdigit():
            self._scan_number(start_line, start_col)
            return
        if ch == '"':
            self._scan_string(start_line, start_col)
            return
        if ch == "'":
            self._scan_char(start_line, start_col)
            return
        self._scan_symbol(start_line, start_col)

    def _scan_word(self, start_line: int, start_col: int) -> None:
        chars: list[str] = []
        while not self._eof() and _is_ident_continue(self._peek()):
            chars.append(self._advance())
        lexeme = "".join(chars)
        span = self._span_from(start_line, start_col)
        resolved = resolve_keyword(canonicalize(lexeme))
        if resolved is not None:
            value: object | None = None
            if resolved == "verdadero":
                value = True
            elif resolved == "falso":
                value = False
            self.tokens.append(Token(TokenKind.KEYWORD, lexeme, resolved, span, value))
            return
        self.tokens.append(Token(TokenKind.IDENT, lexeme, lexeme, span))

    def _scan_number(self, start_line: int, start_col: int) -> None:
        chars: list[str] = []
        while self._peek().isdigit():
            chars.append(self._advance())
        is_real = False
        if self._peek() == "." and self._peek(1).isdigit():
            is_real = True
            chars.append(self._advance())
            while self._peek().isdigit():
                chars.append(self._advance())
        elif self._peek() == ".":
            dot_line, dot_col = self.line, self.col
            self._advance()
            self._error(
                "E0104",
                "Un número real necesita dígitos después del punto.",
                SourceSpan(dot_line, dot_col, dot_line, dot_col),
                "Escribe el número como 9.5, con dígitos a ambos lados del punto.",
            )
        lexeme = "".join(chars)
        span = self._span_from(start_line, start_col)
        digits = len(lexeme.replace(".", ""))
        if digits > MAX_NUMBER_DIGITS:
            self._error(
                "E0107",
                "Este número es demasiado largo.",
                span,
                f"Usa como máximo {MAX_NUMBER_DIGITS} dígitos.",
            )
            return
        if is_real:
            self.tokens.append(Token(TokenKind.REAL, lexeme, lexeme, span, Decimal(lexeme)))
            return
        self.tokens.append(Token(TokenKind.INT, lexeme, lexeme, span, int(lexeme)))

    def _scan_string(self, start_line: int, start_col: int) -> None:
        start_pos = self.pos
        self._advance()
        value, ok = self._scan_quoted('"')
        span = self._span_from(start_line, start_col)
        if not ok:
            self._error(
                "E0102",
                "La cadena no está cerrada.",
                SourceSpan(start_line, start_col, start_line, start_col),
                'Cierra el texto con ". Las cadenas no ocupan más de una línea.',
            )
        lexeme = self.source[start_pos : self.pos]
        self.tokens.append(Token(TokenKind.STRING, lexeme, lexeme, span, value))

    def _scan_char(self, start_line: int, start_col: int) -> None:
        start_pos = self.pos
        self._advance()
        value, ok = self._scan_quoted("'")
        span = self._span_from(start_line, start_col)
        if not ok:
            self._error(
                "E0106",
                "El carácter no está cerrado.",
                SourceSpan(start_line, start_col, start_line, start_col),
                "Un carácter se escribe entre comillas simples, por ejemplo 'A'.",
            )
        elif len(value) != 1:
            self._error(
                "E0106",
                "Un carácter debe contener exactamente un símbolo.",
                span,
                "Si el texto es más largo, usa comillas dobles para una cadena.",
            )
        lexeme = self.source[start_pos : self.pos]
        self.tokens.append(Token(TokenKind.CHAR, lexeme, lexeme, span, value))

    def _scan_quoted(self, quote: str) -> tuple[str, bool]:
        chars: list[str] = []
        closed = False
        while not self._eof():
            ch = self._peek()
            if ch in "\n\r":
                break
            self._advance()
            if ch == quote:
                closed = True
                break
            if ch == "\\":
                if self._eof() or self._peek() in "\n\r":
                    break
                escape = self._advance()
                mapped = _ESCAPE.get(escape)
                if mapped is None:
                    esc_col = self.col - 1
                    self._error(
                        "E0105",
                        f"La secuencia \\{escape} no es un escape válido.",
                        SourceSpan(self.line, esc_col, self.line, self.col - 1),
                        'Puedes usar \\\\, \\", \\n y \\t.',
                    )
                    chars.append(escape)
                else:
                    chars.append(mapped)
                continue
            chars.append(ch)
        return "".join(chars), closed

    def _scan_symbol(self, start_line: int, start_col: int) -> None:
        ch = self._advance()
        kind: TokenKind | None = None
        lexeme = ch
        if ch == "<":
            if self._peek() == "-":
                lexeme += self._advance()
                kind = TokenKind.ASSIGN
            elif self._peek() == "=":
                lexeme += self._advance()
                kind = TokenKind.LTE
            elif self._peek() == ">":
                lexeme += self._advance()
                kind = TokenKind.NEQ
            else:
                kind = TokenKind.LT
        elif ch == ">":
            if self._peek() == "=":
                lexeme += self._advance()
                kind = TokenKind.GTE
            else:
                kind = TokenKind.GT
        elif ch == "!" and self._peek() == "=":
            lexeme += self._advance()
            kind = TokenKind.NEQ
        elif ch == "=":
            kind = TokenKind.EQ
        elif ch == "+":
            kind = TokenKind.PLUS
        elif ch == "-":
            kind = TokenKind.MINUS
        elif ch == "*":
            kind = TokenKind.STAR
        elif ch == "/":
            kind = TokenKind.SLASH
        elif ch == "%":
            kind = TokenKind.PERCENT
        elif ch == "^":
            kind = TokenKind.CARET
        elif ch == "(":
            kind = TokenKind.LPAREN
        elif ch == ")":
            kind = TokenKind.RPAREN
        elif ch == "[":
            kind = TokenKind.LBRACK
        elif ch == "]":
            kind = TokenKind.RBRACK
        elif ch == ",":
            kind = TokenKind.COMMA
        elif ch == ";":
            kind = TokenKind.SEMICOLON
        elif ch == ":":
            kind = TokenKind.COLON
        if kind is None:
            span = SourceSpan(start_line, start_col, start_line, start_col)
            self._error(
                "E0101",
                f"No reconozco el carácter {ch!r}.",
                span,
                "Revisa si quedó un símbolo que el lenguaje no usa.",
            )
            return
        span = self._span_from(start_line, start_col)
        self.tokens.append(Token(kind, lexeme, lexeme, span))


_ESCAPE = {"\\": "\\", '"': '"', "'": "'", "n": "\n", "t": "\t"}


def _is_ident_start(ch: str) -> bool:
    return ch == "_" or unicodedata.category(ch).startswith("L")


def _is_ident_continue(ch: str) -> bool:
    if ch == "_":
        return True
    category = unicodedata.category(ch)
    return category.startswith("L") or category == "Nd"


def lex(source: str) -> LexResult:
    """Analiza `source` y devuelve tokens y diagnósticos."""
    return Lexer(source).scan()
