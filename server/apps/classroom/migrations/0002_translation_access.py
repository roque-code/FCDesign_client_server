from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("classroom", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="community",
            name="translation_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="membership",
            name="translation_enabled",
            field=models.BooleanField(default=None, null=True),
        ),
    ]
