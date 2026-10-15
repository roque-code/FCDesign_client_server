from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_profile_role"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="points",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
