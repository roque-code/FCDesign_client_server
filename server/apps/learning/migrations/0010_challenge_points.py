from django.db import migrations, models
from django.db.models import Q


def assign_points(apps, schema_editor):
    Challenge = apps.get_model("learning", "Challenge")
    Attempt = apps.get_model("learning", "ChallengeAttempt")
    Profile = apps.get_model("accounts", "Profile")
    for challenge in Challenge.objects.all():
        challenge.points = challenge.difficulty * 10
        challenge.save(update_fields=["points"])
    totals: dict[int, int] = {}
    seen: set[tuple[int, str]] = set()
    for attempt in Attempt.objects.filter(status="completed"):
        key = (attempt.user_id, str(attempt.challenge_id))
        if key in seen:
            continue
        seen.add(key)
        prize = Challenge.objects.values_list("points", flat=True).get(pk=attempt.challenge_id)
        totals[attempt.user_id] = totals.get(attempt.user_id, 0) + int(prize)
    for user_id, total in totals.items():
        Profile.objects.filter(user_id=user_id).update(points=total)


class Migration(migrations.Migration):
    dependencies = [
        ("learning", "0009_arrays_functions"),
        ("accounts", "0003_profile_points"),
    ]

    operations = [
        migrations.AddField(
            model_name="challenge",
            name="points",
            field=models.PositiveSmallIntegerField(default=10),
        ),
        migrations.AddConstraint(
            model_name="challenge",
            constraint=models.CheckConstraint(
                condition=Q(points__gte=1, points__lte=500),
                name="challenge_points",
            ),
        ),
        migrations.RunPython(assign_points, migrations.RunPython.noop),
    ]
