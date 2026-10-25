from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("learning", "0016_seed_contest"),
    ]

    operations = [
        migrations.AddField(
            model_name="challenge",
            name="weights",
            field=models.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="pathentry",
            name="weights",
            field=models.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="challengeattempt",
            name="path",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="attempts",
                to="learning.learningpath",
            ),
        ),
    ]
