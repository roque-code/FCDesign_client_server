"""Diagnósticos con posición, fragmento y sugerencia."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from language_core.ast_nodes import SourceSpan

Severity = Literal["error", "warning", "info"]


@dataclass(frozen=True)
class Diagnostic:
    """Un aviso que se puede mostrar en el editor."""

    severity: Severity
    code: str
    message: str
    span: SourceSpan
    snippet: str
    suggestion: str | None = None


def line_snippet(source: str, line: int) -> str:
    """Devuelve el texto de una línea, sin el salto final."""
    lines = source.splitlines()
    if line < 1 or line > len(lines):
        return ""
    return lines[line - 1]


def make_diagnostic(
    source: str,
    severity: Severity,
    code: str,
    message: str,
    span: SourceSpan,
    suggestion: str | None = None,
) -> Diagnostic:
    """Construye un diagnóstico y adjunta el fragmento de la línea."""
    return Diagnostic(
        severity=severity,
        code=code,
        message=message,
        span=span,
        snippet=line_snippet(source, span.start_line),
        suggestion=suggestion,
    )
