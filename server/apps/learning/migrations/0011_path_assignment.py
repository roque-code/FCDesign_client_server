import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("classroom", "0001_initial"),
        ("learning", "0010_challenge_points"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="learningpath",
            name="owner",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="learning_paths",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.CreateModel(
            name="PathEntry",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("position", models.PositiveIntegerField()),
                (
                    "challenge",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="path_entries",
                        to="learning.challenge",
                    ),
                ),
                (
                    "path",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entries",
                        to="learning.learningpath",
                    ),
                ),
            ],
            options={"ordering": ["path", "position"]},
        ),
        migrations.AddConstraint(
            model_name="pathentry",
            constraint=models.UniqueConstraint(
                fields=("path", "position"), name="uniq_path_entry_position"
            ),
        ),
        migrations.AddConstraint(
            model_name="pathentry",
            constraint=models.UniqueConstraint(
                fields=("path", "challenge"), name="uniq_path_entry_challenge"
            ),
        ),
        migrations.CreateModel(
            name="PathAssignment",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "community",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="path_assignments",
                        to="classroom.community",
                    ),
                ),
                (
                    "path",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assignments",
                        to="learning.learningpath",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="path_assignments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="pathassignment",
            constraint=models.CheckConstraint(
                condition=models.Q(community__isnull=False, student__isnull=True)
                | models.Q(community__isnull=True, student__isnull=False),
                name="path_assignment_target",
            ),
        ),
        migrations.AddConstraint(
            model_name="pathassignment",
            constraint=models.UniqueConstraint(
                condition=models.Q(community__isnull=False),
                fields=("path", "community"),
                name="uniq_path_community",
            ),
        ),
        migrations.AddConstraint(
            model_name="pathassignment",
            constraint=models.UniqueConstraint(
                condition=models.Q(student__isnull=False),
                fields=("path", "student"),
                name="uniq_path_student",
            ),
        ),
    ]
