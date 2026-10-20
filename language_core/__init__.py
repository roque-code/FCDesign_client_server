"""Núcleo del pseudolenguaje Aulivana-FCDdesign.

Este paquete no importa Django. La validación y la ejecución recorren un AST.
"""

from language_core.grammar import FLEXIBLE, STRICT, LanguageProfile
from language_core.interpreter import CompileResult, ExecutionResult, compile_source, execute_source

__all__ = [
    "FLEXIBLE",
    "STRICT",
    "CompileResult",
    "ExecutionResult",
    "LanguageProfile",
    "compile_source",
    "execute_source",
]
