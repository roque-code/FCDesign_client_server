from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_profile_avatar"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="session_key",
            field=models.CharField(
                blank=True, default="", max_length=40, verbose_name="sesión activa"
            ),
        ),
    ]
