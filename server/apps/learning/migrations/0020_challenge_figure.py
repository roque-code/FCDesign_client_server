from django.conf import settings
from django.db import migrations, models
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("learning", "0019_equals_comparison"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ChallengeFigure",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("content", models.BinaryField()),
                ("content_type", models.CharField(max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "challenge",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.CASCADE,
                        related_name="figures",
                        to="learning.challenge",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="challenge_figures",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
