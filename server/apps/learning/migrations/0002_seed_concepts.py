from django.db import migrations

from apps.learning.catalog import CONCEPTS


def seed_concepts(apps, schema_editor):
    Concept = apps.get_model("learning", "Concept")
    for key, name in CONCEPTS:
        Concept.objects.update_or_create(key=key, defaults={"name": name})


def unseed_concepts(apps, schema_editor):
    Concept = apps.get_model("learning", "Concept")
    Concept.objects.filter(key__in=[key for key, _name in CONCEPTS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("learning", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_concepts, unseed_concepts),
    ]
