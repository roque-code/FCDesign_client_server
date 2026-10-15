from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("learning", "0011_path_assignment"),
    ]

    operations = [
        migrations.AddField(
            model_name="pathentry",
            name="opens_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="pathentry",
            name="closes_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="pathentry",
            name="withdrawn",
            field=models.BooleanField(default=False),
        ),
    ]
