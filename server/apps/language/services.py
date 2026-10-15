"""Perfiles persistidos y la forma en que el editor muestra un diagnóstico."""

from typing import Any

from config.errors import DomainError
from language_core.diagnostics import Diagnostic
from language_core.grammar import LanguageProfile

_FLAGS = (
    "index_base",
    "require_semicolons",
    "require_declarations",
    "implicit_widening",
    "allow_equals_assignment",
    "allow_globals",
    "beginner_warnings",
    "max_instructions",
    "max_call_depth",
    "max_array_cells",
    "max_time_ms",
    "max_string_length",
    "max_output_chars",
)

STRICT_CONFIG: dict[str, object] = {
    "index_base": 1,
    "require_semicolons": True,
    "require_declarations": True,
    "implicit_widening": True,
    "allow_equals_assignment": False,
    "allow_globals": False,
    "beginner_warnings": True,
    "max_instructions": 100_000,
    "max_call_depth": 100,
    "max_array_cells": 10_000,
    "max_time_ms": 5_000,
    "max_string_length": 100_000,
    "max_output_chars": 256_000,
}

FLEXIBLE_CONFIG: dict[str, object] = {
    **STRICT_CONFIG,
    "require_semicolons": False,
    "require_declarations": False,
    "allow_equals_assignment": True,
    "beginner_warnings": False,
}

PROFILES: tuple[tuple[str, str, dict[str, object]], ...] = (
    ("strict", "Estricto", STRICT_CONFIG),
    ("flexible", "Flexible", FLEXIBLE_CONFIG),
)


def seed_profiles(sender, **kwargs) -> None:
    from apps.language.models import LanguageProfile as StoredProfile

    if getattr(sender, "label", None) != "language":
        return
    for key, name, config in PROFILES:
        StoredProfile.objects.update_or_create(
            key=key,
            defaults={"name": name, "config": config, "is_system": True},
        )


def core_profile(stored) -> LanguageProfile:
    return core_profile_from_config(stored.key, stored.config)


def resolved_options(stored, options: object) -> dict[str, object]:
    """El perfil aporta el valor inicial. El algoritmo puede cambiar estas dos reglas."""
    config = stored.config if isinstance(stored.config, dict) else {}
    chosen = options if isinstance(options, dict) else {}
    semicolons = chosen.get("require_semicolons", config.get("require_semicolons", True))
    base = chosen.get("index_base", config.get("index_base", 1))
    if not isinstance(semicolons, bool):
        semicolons = True
    if isinstance(base, bool) or base not in (0, 1):
        base = 1
    return {"require_semicolons": semicolons, "index_base": base}


def profile_for_algorithm(algorithm) -> tuple[LanguageProfile, dict[str, Any]]:
    options = resolved_options(algorithm.language_profile, algorithm.language_options)
    config = dict(algorithm.language_profile.config)
    config.update(options)
    config["profile_key"] = algorithm.language_profile.key
    return core_profile_from_config(algorithm.language_profile.key, config), config


def clean_language_option(current: object, data: dict[str, Any]) -> dict[str, object]:
    options = dict(current) if isinstance(current, dict) else {}
    if "require_semicolons" in data:
        semicolons = data["require_semicolons"]
        if not isinstance(semicolons, bool):
            raise DomainError("El punto y coma debe ser obligatorio u opcional.")
        options["require_semicolons"] = semicolons
    if "index_base" in data:
        base = data["index_base"]
        if isinstance(base, bool) or base not in (0, 1):
            raise DomainError("El índice del arreglo empieza en 0 o en 1.")
        options["index_base"] = base
    return options


def core_profile_from_config(name: str, config: dict[str, Any]) -> LanguageProfile:
    values = {flag: config[flag] for flag in _FLAGS}
    return LanguageProfile(name=name, **values)


def diagnostic_payload(item: Diagnostic) -> dict[str, object]:
    return {
        "severity": item.severity,
        "code": item.code,
        "message": item.message,
        "line": item.span.start_line,
        "column": item.span.start_col,
        "end_line": item.span.end_line,
        "end_column": item.span.end_col,
        "snippet": item.snippet,
        "suggestion": item.suggestion,
    }
