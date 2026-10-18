from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("classroom", "0002_translation_access"),
    ]

    operations = [
        migrations.AddField(
            model_name="community",
            name="paste_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="membership",
            name="paste_enabled",
            field=models.BooleanField(default=None, null=True),
        ),
    ]
