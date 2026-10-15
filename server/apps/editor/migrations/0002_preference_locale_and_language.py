from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("editor", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="editorpreference",
            name="locale",
            field=models.CharField(default="es", max_length=8),
        ),
        migrations.AddField(
            model_name="editorpreference",
            name="require_semicolons",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="editorpreference",
            name="index_base",
            field=models.PositiveSmallIntegerField(default=1),
        ),
    ]
