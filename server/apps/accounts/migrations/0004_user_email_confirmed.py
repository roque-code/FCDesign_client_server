from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_profile_points"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="email_confirmed",
            field=models.BooleanField(default=True, verbose_name="correo confirmado"),
        ),
    ]
