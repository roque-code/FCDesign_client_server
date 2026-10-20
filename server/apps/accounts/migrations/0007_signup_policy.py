from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0006_user_session_key"),
    ]

    operations = [
        migrations.CreateModel(
            name="SignupPolicy",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "student",
                    models.BooleanField(default=True, verbose_name="alta de alumno"),
                ),
                (
                    "teacher",
                    models.BooleanField(default=True, verbose_name="alta de docente"),
                ),
            ],
            options={
                "verbose_name": "altas",
                "verbose_name_plural": "altas",
            },
        ),
    ]
