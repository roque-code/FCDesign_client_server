import secrets

from django.db import migrations, models

_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def fill_codes(apps, schema_editor):
    del schema_editor
    community = apps.get_model("classroom", "Community")
    used = set(community.objects.exclude(join_code="").values_list("join_code", flat=True))
    for row in community.objects.filter(join_code__isnull=True):
        while True:
            code = "".join(secrets.choice(_ALPHABET) for _ in range(6))
            if code not in used:
                used.add(code)
                row.join_code = code
                row.save(update_fields=["join_code"])
                break


class Migration(migrations.Migration):
    dependencies = [
        ("classroom", "0003_paste_access"),
    ]

    operations = [
        migrations.AddField(
            model_name="community",
            name="join_code",
            field=models.CharField(max_length=8, null=True),
        ),
        migrations.RunPython(fill_codes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="community",
            name="join_code",
            field=models.CharField(max_length=8, unique=True),
        ),
    ]
