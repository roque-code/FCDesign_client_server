"""Catálogo de funciones que un nivel puede encender.

Una función nueva se agrega aquí. La pantalla de administrador la muestra sola
y cada plan guarda en la base si la tiene encendida. El valor por defecto de
un plan nuevo es apagado.
"""

from __future__ import annotations

from dataclasses import dataclass

STUDENT = "student"
TEACHER = "teacher"
BOTH = frozenset({STUDENT, TEACHER})
TEACHERS = frozenset({TEACHER})


@dataclass(frozen=True)
class Feature:
    key: str
    label: str
    audiences: frozenset[str]


FEATURES: tuple[Feature, ...] = (
    Feature("editor", "Editor", BOTH),
    Feature("diagram", "Ver diagrama", BOTH),
    Feature("compose", "Armar diagrama", BOTH),
    Feature("validate", "Validar", BOTH),
    Feature("translate", "Traducir", BOTH),
    Feature("execute", "Ejecutar", BOTH),
    Feature("debug", "Depurar", BOTH),
    Feature("download", "Descargar código", BOTH),
    Feature("paste", "Pegar", BOTH),
    Feature("lab", "Laboratorio", BOTH),
    Feature("lab_route", "Ruta", BOTH),
    Feature("lab_practice", "Práctica libre", BOTH),
    Feature("communities", "Comunidades", TEACHERS),
    Feature("lab_bank", "Banco", TEACHERS),
    Feature("lab_routes", "Rutas", TEACHERS),
    Feature("lab_progress", "Avance", TEACHERS),
)

_BY_KEY = {item.key: item for item in FEATURES}


def features_for(audience: str) -> tuple[Feature, ...]:
    return tuple(item for item in FEATURES if audience in item.audiences)


def known_key(audience: str, key: str) -> bool:
    item = _BY_KEY.get(key)
    return item is not None and audience in item.audiences
