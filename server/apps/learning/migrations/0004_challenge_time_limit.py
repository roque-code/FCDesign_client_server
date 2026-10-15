from django.db import migrations, models
from django.db.models import Q

from apps.learning.path_data import PATH


def apply_times(apps, schema_editor):
    Challenge = apps.get_model("learning", "Challenge")
    units = PATH["units"]
    assert isinstance(units, list)
    for unit in units:
        assert isinstance(unit, dict)
        for item in unit["challenges"]:
            assert isinstance(item, dict)
            Challenge.objects.filter(title=item["title"], unit__path__name=PATH["name"]).update(
                time_limit_seconds=item.get("time_limit_seconds")
            )


def clear_times(apps, schema_editor):
    Challenge = apps.get_model("learning", "Challenge")
    Challenge.objects.filter(unit__path__name=PATH["name"]).update(time_limit_seconds=None)


class Migration(migrations.Migration):
    dependencies = [
        ("learning", "0003_seed_path"),
    ]

    operations = [
        migrations.AddField(
            model_name="challenge",
            name="time_limit_seconds",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddConstraint(
            model_name="challenge",
            constraint=models.CheckConstraint(
                condition=Q(time_limit_seconds__isnull=True)
                | Q(time_limit_seconds__gte=1, time_limit_seconds__lte=86400),
                name="challenge_time_limit",
            ),
        ),
        migrations.RunPython(apply_times, clear_times),
    ]
