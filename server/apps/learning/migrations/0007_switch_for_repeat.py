from django.db import migrations

from apps.learning.catalog import CONCEPTS
from apps.learning.path_data import PATH

ADDED = ("switch", "for", "repeat")


def add_units(apps, schema_editor):
    Concept = apps.get_model("learning", "Concept")
    LearningPath = apps.get_model("learning", "LearningPath")
    LearningUnit = apps.get_model("learning", "LearningUnit")
    Challenge = apps.get_model("learning", "Challenge")
    ChallengeTestCase = apps.get_model("learning", "ChallengeTestCase")
    Hint = apps.get_model("learning", "Hint")
    for key, name in CONCEPTS:
        if key in ADDED:
            Concept.objects.update_or_create(key=key, defaults={"name": name})
    path = LearningPath.objects.get(name=PATH["name"])
    path.description = PATH["description"]
    path.save(update_fields=["description"])
    previous = (
        LearningUnit.objects.filter(path=path)
        .exclude(concept__key__in=ADDED)
        .order_by("position")
        .last()
    )
    for unit_data in PATH["units"]:
        if unit_data["concept"] not in ADDED:
            continue
        concept = Concept.objects.get(key=unit_data["concept"])
        unit, _created = LearningUnit.objects.update_or_create(
            path=path,
            title=unit_data["title"],
            defaults={
                "concept": concept,
                "position": unit_data["position"],
                "prerequisite": previous,
            },
        )
        previous = unit
        for challenge_data in unit_data["challenges"]:
            challenge, _created = Challenge.objects.update_or_create(
                unit=unit,
                title=challenge_data["title"],
                defaults={
                    "prompt": challenge_data["prompt"],
                    "activity_type": challenge_data["activity_type"],
                    "difficulty": challenge_data["difficulty"],
                    "time_limit_seconds": challenge_data["time_limit_seconds"],
                    "allowed_blocks": challenge_data["allowed_blocks"],
                    "restrictions": challenge_data["restrictions"],
                    "position": challenge_data["position"],
                    "is_published": True,
                },
            )
            challenge.test_cases.all().delete()
            challenge.hints.all().delete()
            for case in challenge_data["cases"]:
                ChallengeTestCase.objects.create(
                    challenge=challenge,
                    name=case["name"],
                    inputs=case["inputs"],
                    expected_output=case["expected_output"],
                    kind=case["kind"],
                    position=case["position"],
                )
            for hint in challenge_data["hints"]:
                Hint.objects.create(
                    challenge=challenge,
                    level=hint["level"],
                    body=hint["body"],
                    position=hint["position"],
                )


def remove_units(apps, schema_editor):
    LearningPath = apps.get_model("learning", "LearningPath")
    LearningUnit = apps.get_model("learning", "LearningUnit")
    ChallengeAttempt = apps.get_model("learning", "ChallengeAttempt")
    Concept = apps.get_model("learning", "Concept")
    path = LearningPath.objects.filter(name=PATH["name"]).first()
    if path is not None:
        units = LearningUnit.objects.filter(path=path, concept__key__in=ADDED).order_by("-position")
        for unit in units:
            ChallengeAttempt.objects.filter(challenge__unit=unit).delete()
            unit.delete()
        path.description = (
            "Variables, asignación, entrada, salida, operadores, decisiones y ciclos."
        )
        path.save(update_fields=["description"])
    Concept.objects.filter(key__in=ADDED).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("learning", "0006_control_challenges"),
    ]

    operations = [
        migrations.RunPython(add_units, remove_units),
    ]
