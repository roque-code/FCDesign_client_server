from django.db import migrations

from apps.learning.path_data import PATH


def seed_path(apps, schema_editor):
    LearningPath = apps.get_model("learning", "LearningPath")
    LearningUnit = apps.get_model("learning", "LearningUnit")
    Challenge = apps.get_model("learning", "Challenge")
    ChallengeTestCase = apps.get_model("learning", "ChallengeTestCase")
    Hint = apps.get_model("learning", "Hint")
    Concept = apps.get_model("learning", "Concept")
    path, _created = LearningPath.objects.update_or_create(
        name=PATH["name"],
        defaults={
            "description": PATH["description"],
            "position": PATH["position"],
            "is_published": True,
        },
    )
    previous = None
    for unit_data in PATH["units"]:
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


def unseed_path(apps, schema_editor):
    LearningPath = apps.get_model("learning", "LearningPath")
    ChallengeAttempt = apps.get_model("learning", "ChallengeAttempt")
    path = LearningPath.objects.filter(name=PATH["name"]).first()
    if path is None:
        return
    ChallengeAttempt.objects.filter(challenge__unit__path=path).delete()
    path.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("learning", "0002_seed_concepts"),
    ]

    operations = [
        migrations.RunPython(seed_path, unseed_path),
    ]
