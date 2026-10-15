"""Ejecutor de desarrollo.

Corre dentro del proceso de Django, con los mismos límites lógicos del núcleo.
No es el aislamiento de producción: si DEBUG es falso, se niega a arrancar.
"""

import random
import time

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from language_core.debugger import drive
from language_core.grammar import LanguageProfile
from language_core.interpreter import Interpreter, compile_source
from language_core.runtime import Cancellation, ExecutionResult, Limits


def run_in_process(
    source: str,
    inputs: list[str],
    profile: LanguageProfile,
) -> tuple[ExecutionResult, int]:
    if not settings.DEBUG or settings.EXECUTION_RUNNER != "inprocess":
        raise ImproperlyConfigured(
            "El ejecutor en proceso no está disponible cuando DEBUG es falso."
        )
    compiled = compile_source(source, profile)
    errors = [item for item in compiled.diagnostics if item.severity == "error"]
    if compiled.program is None or errors:
        return ExecutionResult("error", "", compiled.diagnostics, {}), 0
    limits = Limits.from_profile(profile)
    interpreter = Interpreter(
        compiled.program,
        source,
        profile,
        limits,
        Cancellation(),
        time.monotonic,
        random.Random(),
    )
    result = drive(interpreter.run(), list(inputs), compiled.diagnostics, interpreter.cells)
    return result, interpreter.instruction_count
