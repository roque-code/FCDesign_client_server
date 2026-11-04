"""Enciende en los niveles ya guardados las opciones que antes no tenían interruptor."""

from django.db import migrations

_OPEN = {
    "subject_fundamentos": True,
    "subject_bases": True,
    "subject_objetos": False,
    "subject_software": False,
    "exams": True,
    "chat": True,
}


def grant_existing(apps, schema_editor):
    Plan = apps.get_model("billing", "Plan")
    for plan in Plan.objects.all():
        features = dict(plan.features or {})
        for key, value in _OPEN.items():
            features.setdefault(key, value)
        features.setdefault("nassi", features.get("compose") is True)
        plan.features = features
        plan.save(update_fields=["features"])


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0003_plan_max_executions_per_day"),
    ]

    operations = [
        migrations.RunPython(grant_existing, migrations.RunPython.noop),
    ]
