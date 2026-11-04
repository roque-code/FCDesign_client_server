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
    group: str
    subject: str


FEATURES: tuple[Feature, ...] = (
    Feature("subject_fundamentos", "Fundamentos", BOTH, "subjects", "fundamentos"),
    Feature("editor", "Editor", BOTH, "editor", "fundamentos"),
    Feature("diagram", "Ver diagrama", BOTH, "editor", "fundamentos"),
    Feature("compose", "Armar diagrama", BOTH, "editor", "fundamentos"),
    Feature("nassi", "Diagrama Nassi-Shneiderman", BOTH, "editor", "fundamentos"),
    Feature("validate", "Validar", BOTH, "editor", "fundamentos"),
    Feature("translate", "Traducir", BOTH, "editor", "fundamentos"),
    Feature("languages", "Lenguajes", BOTH, "editor", "fundamentos"),
    Feature("execute", "Ejecutar", BOTH, "editor", "fundamentos"),
    Feature("debug", "Depurar", BOTH, "editor", "fundamentos"),
    Feature("download", "Descargar código", BOTH, "editor", "fundamentos"),
    Feature("paste", "Pegar", BOTH, "editor", "fundamentos"),
    Feature("lab", "Laboratorio", BOTH, "lab", "fundamentos"),
    Feature("lab_route", "Ruta", BOTH, "lab", "fundamentos"),
    Feature("lab_practice", "Práctica libre", BOTH, "lab", "fundamentos"),
    Feature("lab_bank", "Banco", TEACHERS, "lab", "fundamentos"),
    Feature("lab_routes", "Rutas", TEACHERS, "lab", "fundamentos"),
    Feature("lab_progress", "Avance", TEACHERS, "lab", "fundamentos"),
    Feature("subject_bases", "Bases de datos", BOTH, "subjects", "bases"),
    Feature("subject_objetos", "Programación orientada a objetos", BOTH, "subjects", "objetos"),
    Feature("subject_software", "Ingeniería de software", BOTH, "subjects", "software"),
    Feature("exams_fundamentos", "Exámenes", BOTH, "menus", "fundamentos"),
    Feature("chat_fundamentos", "Mensajes", BOTH, "menus", "fundamentos"),
    Feature("exams_bases", "Exámenes", BOTH, "menus", "bases"),
    Feature("chat_bases", "Mensajes", BOTH, "menus", "bases"),
    Feature("exams_objetos", "Exámenes", BOTH, "menus", "objetos"),
    Feature("chat_objetos", "Mensajes", BOTH, "menus", "objetos"),
    Feature("exams_software", "Exámenes", BOTH, "menus", "software"),
    Feature("chat_software", "Mensajes", BOTH, "menus", "software"),
    Feature("communities", "Comunidades", TEACHERS, "classroom", "shared"),
)

_BY_KEY = {item.key: item for item in FEATURES}


def features_for(audience: str) -> tuple[Feature, ...]:
    return tuple(item for item in FEATURES if audience in item.audiences)


def known_key(audience: str, key: str) -> bool:
    item = _BY_KEY.get(key)
    return item is not None and audience in item.audiences
