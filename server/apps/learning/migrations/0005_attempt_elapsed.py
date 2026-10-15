from django.db import migrations, models


def backfill_elapsed(apps, schema_editor):
    Attempt = apps.get_model("learning", "ChallengeAttempt")
    pending = Attempt.objects.exclude(finished_at=None).filter(elapsed_seconds=None)
    for row in pending.iterator():
        row.elapsed_seconds = max(0, int((row.finished_at - row.started_at).total_seconds()))
        row.save(update_fields=["elapsed_seconds"])


class Migration(migrations.Migration):
    dependencies = [
        ("learning", "0004_challenge_time_limit"),
    ]

    operations = [
        migrations.AddField(
            model_name="challengeattempt",
            name="elapsed_seconds",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.RunPython(backfill_elapsed, migrations.RunPython.noop),
    ]
