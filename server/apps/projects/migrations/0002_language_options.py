from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="algorithm",
            name="language_options",
            field=models.JSONField(default=dict),
        ),
    ]
