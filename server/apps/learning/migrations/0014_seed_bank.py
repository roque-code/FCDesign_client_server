from django.db import migrations

from apps.learning.bank_data import BANK_DESCRIPTION, BANK_NAME, build_bank


def seed_bank(apps, schema_editor):
    LearningPath = apps.get_model("learning", "LearningPath")
    LearningUnit = apps.get_model("learning", "LearningUnit")
    Challenge = apps.get_model("learning", "Challenge")
    ChallengeTestCase = apps.get_model("learning", "ChallengeTestCase")
    Hint = apps.get_model("learning", "Hint")
    Concept = apps.get_model("learning", "Concept")
    data = build_bank()
    existing = LearningPath.objects.filter(name=BANK_NAME).first()
    if existing is None:
        last = (
            LearningPath.objects.order_by("-position").values_list("position", flat=True).first()
            or 0
        )
        position = last + 1
    else:
        position = existing.position
    path, _created = LearningPath.objects.update_or_create(
        name=BANK_NAME,
        defaults={
            "description": data["description"] or BANK_DESCRIPTION,
            "position": position,
            "is_published": True,
            "is_bank": True,
            "owner": None,
        },
    )
    previous = None
    kept: set[str] = set()
    for unit_data in data["units"]:
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
            kept.add(challenge_data["title"])
            challenge, _created = Challenge.objects.update_or_create(
                unit=unit,
                title=challenge_data["title"],
                defaults={
                    "prompt": challenge_data["prompt"],
                    "activity_type": challenge_data["activity_type"],
                    "difficulty": challenge_data["difficulty"],
                    "points": challenge_data["points"],
                    "allowed_blocks": challenge_data["allowed_blocks"],
                    "restrictions": challenge_data["restrictions"],
                    "position": challenge_data["position"],
                    "is_published": True,
                    "time_limit_seconds": challenge_data["time_limit_seconds"],
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
        Challenge.objects.filter(unit=unit).exclude(title__in=kept).delete()


def unseed_bank(apps, schema_editor):
    LearningPath = apps.get_model("learning", "LearningPath")
    LearningUnit = apps.get_model("learning", "LearningUnit")
    ChallengeAttempt = apps.get_model("learning", "ChallengeAttempt")
    path = LearningPath.objects.filter(name=BANK_NAME).first()
    if path is None:
        return
    ChallengeAttempt.objects.filter(challenge__unit__path=path).delete()
    LearningUnit.objects.filter(path=path).update(prerequisite=None)
    path.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("learning", "0013_learningpath_is_bank"),
    ]

    operations = [
        migrations.RunPython(seed_bank, unseed_bank),
    ]
