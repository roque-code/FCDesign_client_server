from django.db import transaction

from apps.editor.models import EditorPreference
from config.errors import DomainError


def preference_payload(preference: EditorPreference) -> dict[str, object]:
    return {
        "theme": preference.theme,
        "font_size": preference.font_size,
        "keymap": preference.keymap,
        "indent_size": preference.indent_size,
        "autosave": preference.autosave,
        "locale": preference.locale,
        "require_semicolons": preference.require_semicolons,
        "index_base": preference.index_base,
    }


@transaction.atomic
def update_preference(preference: EditorPreference, data: dict[str, object]) -> EditorPreference:
    preference = EditorPreference.objects.select_for_update().get(pk=preference.pk)
    if "theme" in data:
        theme = data["theme"]
        if theme not in ("light", "dark"):
            raise DomainError("El tema debe ser claro u oscuro.")
        preference.theme = str(theme)
    if "font_size" in data:
        size = data["font_size"]
        if not isinstance(size, int) or isinstance(size, bool) or not 12 <= size <= 28:
            raise DomainError("El cuerpo debe estar entre 12 y 28.")
        preference.font_size = size
    if "keymap" in data:
        if data["keymap"] != "default":
            raise DomainError("Ese mapa de teclado no está disponible.")
        preference.keymap = "default"
    if "indent_size" in data:
        indent = data["indent_size"]
        if indent not in (2, 4, 8):
            raise DomainError("La sangría debe ser 2, 4 u 8.")
        preference.indent_size = int(indent)
    if "autosave" in data:
        if not isinstance(data["autosave"], bool):
            raise DomainError("El autoguardado debe ser sí o no.")
        preference.autosave = data["autosave"]
    if "locale" in data:
        locale = data["locale"]
        if locale not in ("es", "en"):
            raise DomainError("El idioma debe ser español o inglés.")
        preference.locale = str(locale)
    if "require_semicolons" in data:
        semicolons = data["require_semicolons"]
        if not isinstance(semicolons, bool):
            raise DomainError("El punto y coma debe ser obligatorio u opcional.")
        preference.require_semicolons = semicolons
    if "index_base" in data:
        base = data["index_base"]
        if isinstance(base, bool) or base not in (0, 1):
            raise DomainError("El índice del arreglo empieza en 0 o en 1.")
        preference.index_base = base
    preference.save()
    return preference
