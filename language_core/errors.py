"""Excepciones internas del intérprete.

Los mensajes que ve el estudiante son diagnósticos, no estas clases.
"""

from __future__ import annotations

from language_core.diagnostics import Diagnostic


class ExecFault(Exception):
    """Error de ejecución que detiene el programa del estudiante."""

    def __init__(self, diagnostic: Diagnostic) -> None:
        self.diagnostic = diagnostic
        super().__init__(diagnostic.message)


class Cancelled(Exception):
    """La ejecución fue cancelada por el conductor."""
