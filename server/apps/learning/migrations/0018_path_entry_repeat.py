from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("learning", "0017_challenge_weights"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="pathentry",
            name="uniq_path_entry_challenge",
        ),
    ]
