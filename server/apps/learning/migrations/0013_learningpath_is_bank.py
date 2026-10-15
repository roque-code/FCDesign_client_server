from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("learning", "0012_path_entry_window"),
    ]

    operations = [
        migrations.AddField(
            model_name="learningpath",
            name="is_bank",
            field=models.BooleanField(default=False),
        ),
    ]
