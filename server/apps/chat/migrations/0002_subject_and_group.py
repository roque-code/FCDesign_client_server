from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def attach_scope(apps, schema_editor):
    del schema_editor
    Conversation = apps.get_model("chat", "Conversation")
    Membership = apps.get_model("classroom", "Membership")
    for row in Conversation.objects.all():
        membership = (
            Membership.objects.filter(community__owner_id=row.teacher_id, user_id=row.student_id)
            .order_by("community__name")
            .first()
        )
        if membership is None:
            row.delete()
            continue
        row.subject = "fundamentos"
        row.kind = "personal"
        row.community_id = membership.community_id
        row.save(update_fields=["subject", "kind", "community"])


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0001_initial"),
        ("classroom", "0004_community_join_code"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="conversation",
            name="kind",
            field=models.CharField(default="personal", max_length=16),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="conversation",
            name="subject",
            field=models.CharField(default="fundamentos", max_length=32),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="conversation",
            name="community",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="conversations",
                to="classroom.community",
            ),
        ),
        migrations.AlterField(
            model_name="conversation",
            name="student",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="chat_as_student",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="conversation",
            name="teacher",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="chat_as_teacher",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(attach_scope, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="conversation",
            name="community",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="conversations",
                to="classroom.community",
            ),
        ),
        migrations.RemoveConstraint(model_name="conversation", name="uniq_chat_pair"),
        migrations.AddConstraint(
            model_name="conversation",
            constraint=models.UniqueConstraint(
                condition=models.Q(("kind", "personal")),
                fields=("subject", "community", "teacher", "student"),
                name="uniq_chat_personal",
            ),
        ),
        migrations.AddConstraint(
            model_name="conversation",
            constraint=models.UniqueConstraint(
                condition=models.Q(("kind", "group")),
                fields=("subject", "community"),
                name="uniq_chat_group",
            ),
        ),
        migrations.AddConstraint(
            model_name="conversation",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("subject__in", ["fundamentos", "bases", "objetos", "software"]),
                    models.Q(
                        models.Q(
                            ("community__isnull", False),
                            ("kind", "personal"),
                            ("student__isnull", False),
                            ("teacher__isnull", False),
                        ),
                        models.Q(
                            ("community__isnull", False),
                            ("kind", "group"),
                            ("student__isnull", True),
                            ("teacher__isnull", True),
                        ),
                        _connector="OR",
                    ),
                ),
                name="chat_conversation_shape",
            ),
        ),
    ]
