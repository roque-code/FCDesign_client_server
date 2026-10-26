from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0002_subscription_browser_allowed"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="plan",
            name="max_executions_per_day",
            field=models.PositiveIntegerField(blank=True, default=3, null=True),
        ),
        migrations.CreateModel(
            name="DailyExecution",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("day", models.DateField()),
                ("count", models.PositiveIntegerField(default=0)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="daily_executions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="dailyexecution",
            constraint=models.UniqueConstraint(
                fields=("user", "day"), name="uniq_daily_execution"
            ),
        ),
    ]
