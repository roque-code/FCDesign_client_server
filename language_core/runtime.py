"""Valores, límites y eventos de una ejecución."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from language_core.ast_nodes import Program, TypeName
from language_core.diagnostics import Diagnostic
from language_core.grammar import LanguageProfile

EventKind = Literal[
    "line",
    "output",
    "input_requested",
    "input_rejected",
    "warning",
    "error",
    "cancelled",
    "finished",
    "call",
    "return",
    "clear",
    "delay",
]


def format_array(array: ArrayValue) -> str:
    """Texto corto de un arreglo para la consola de variables."""
    from language_core.type_system import format_value

    texts = [format_value(array.type_name, cell.value) for cell in array.cells]
    width = array.lengths[-1] if array.lengths else 1
    if len(array.lengths) <= 1:
        return "[" + ", ".join(texts) + "]"
    rows = [
        "[" + ", ".join(texts[start : start + width]) + "]" for start in range(0, len(texts), width)
    ]
    return "[" + ", ".join(rows) + "]"


@dataclass(frozen=True)
class Value:
    """Un valor del lenguaje con su tipo, no solo el objeto de Python."""

    type_name: TypeName
    value: object


@dataclass
class ArrayValue:
    """Arreglo en orden por filas. Cada índice se comprueba por separado."""

    type_name: TypeName
    lengths: tuple[int, ...]
    base: int
    cells: list[Value]


@dataclass
class Cell:
    """Celda de una variable. `value` vacío significa que aún no se asignó."""

    type_name: TypeName
    value: Value | None = None
    array: ArrayValue | None = None
    dimensions: int | None = None
    slot_index: int | None = None
    slot_owner: ArrayValue | None = None


@dataclass(frozen=True)
class Limits:
    """Topes lógicos. El contenedor de producción añade los del sistema."""

    max_instructions: int = 100_000
    max_time_ms: int = 5_000
    max_call_depth: int = 100
    max_array_cells: int = 10_000
    max_string_length: int = 100_000
    max_output_chars: int = 256_000

    @classmethod
    def from_profile(cls, profile: LanguageProfile) -> Limits:
        return cls(
            max_instructions=profile.max_instructions,
            max_time_ms=profile.max_time_ms,
            max_call_depth=profile.max_call_depth,
            max_array_cells=profile.max_array_cells,
            max_string_length=profile.max_string_length,
            max_output_chars=profile.max_output_chars,
        )


class Cancellation:
    """Bandera que el conductor puede activar entre sentencias."""

    def __init__(self) -> None:
        self.requested = False

    def cancel(self) -> None:
        self.requested = True


@dataclass(frozen=True)
class RuntimeEvent:
    """Un hecho de la ejecución, listo para la consola o el depurador."""

    kind: EventKind
    line: int | None = None
    column: int | None = None
    scope: str | None = None
    payload: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class CompileResult:
    """Resultado de léxico, sintaxis y semántica, sin ejecutar."""

    program: Program | None
    diagnostics: tuple[Diagnostic, ...]


@dataclass(frozen=True)
class ExecutionResult:
    """Salida, variables y diagnósticos después de conducir el intérprete."""

    status: Literal["completed", "error", "waiting_input", "cancelled", "timeout"]
    output: str
    diagnostics: tuple[Diagnostic, ...]
    variables: dict[str, str]
    pending_input: dict[str, str] | None = None
