"""Copia exámenes y mensajes a cada materia.

El interruptor único sigue en el JSON por si hay que leerlo, y cada materia
recibe el mismo valor que ese interruptor tenía.
"""

from django.db import migrations

_SUBJECTS = ("fundamentos", "bases", "objetos", "software")


def grant_menus(apps, schema_editor):
    Plan = apps.get_model("billing", "Plan")
    for plan in Plan.objects.all():
        features = dict(plan.features or {})
        exams = features.get("exams", True) is True
        chat = features.get("chat", True) is True
        for subject in _SUBJECTS:
            features.setdefault(f"exams_{subject}", exams)
            features.setdefault(f"chat_{subject}", chat)
        features.pop("exams", None)
        features.pop("chat", None)
        plan.features = features
        plan.save(update_fields=["features"])


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0004_plan_subject_and_tools"),
    ]

    operations = [
        migrations.RunPython(grant_menus, migrations.RunPython.noop),
    ]
