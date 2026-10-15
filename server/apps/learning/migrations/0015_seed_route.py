from django.db import migrations

from apps.learning.bank_data import BANK_NAME, ROUTE_DESCRIPTION, ROUTE_NAME


def seed_route(apps, schema_editor):
    LearningPath = apps.get_model("learning", "LearningPath")
    PathEntry = apps.get_model("learning", "PathEntry")
    Challenge = apps.get_model("learning", "Challenge")
    bank = LearningPath.objects.get(name=BANK_NAME)
    challenges = list(
        Challenge.objects.filter(unit__path=bank, is_published=True).order_by(
            "unit__position", "position"
        )
    )
    if len(challenges) != 200:
        raise RuntimeError("La ruta espera los 200 retos del banco.")
    existing = LearningPath.objects.filter(name=ROUTE_NAME).first()
    if existing is None:
        last = (
            LearningPath.objects.order_by("-position").values_list("position", flat=True).first()
            or 0
        )
        position = last + 1
    else:
        position = existing.position
    path, _created = LearningPath.objects.update_or_create(
        name=ROUTE_NAME,
        defaults={
            "description": ROUTE_DESCRIPTION,
            "position": position,
            "is_published": True,
            "is_bank": False,
            "owner": None,
        },
    )
    PathEntry.objects.filter(path=path).delete()
    PathEntry.objects.bulk_create(
        [
            PathEntry(
                path=path,
                challenge=challenge,
                position=index,
                opens_at=None,
                closes_at=None,
                withdrawn=False,
            )
            for index, challenge in enumerate(challenges, start=1)
        ]
    )


def unseed_route(apps, schema_editor):
    LearningPath = apps.get_model("learning", "LearningPath")
    path = LearningPath.objects.filter(name=ROUTE_NAME).first()
    if path is not None:
        path.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("learning", "0014_seed_bank"),
    ]

    operations = [
        migrations.RunPython(seed_route, unseed_route),
    ]
