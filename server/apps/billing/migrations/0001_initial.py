import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def seed_plans(apps, schema_editor):
    Plan = apps.get_model("billing", "Plan")
    Profile = apps.get_model("accounts", "Profile")
    Subscription = apps.get_model("billing", "Subscription")
    from apps.billing.services import seed_definitions

    rows = {}
    for item in seed_definitions():
        plan = Plan.objects.create(id=uuid.uuid4(), currency="MXN", is_active=True, **item)
        if plan.is_default:
            rows[plan.audience] = plan
    for profile in Profile.objects.all():
        if profile.role == "admin":
            continue
        audience = profile.role if profile.role in rows else "student"
        Subscription.objects.get_or_create(
            user_id=profile.user_id, defaults={"plan": rows[audience]}
        )


def drop_plans(apps, schema_editor):
    apps.get_model("billing", "Subscription").objects.all().delete()
    apps.get_model("billing", "Plan").objects.all().delete()


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("accounts", "0005_profile_avatar"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Plan",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("code", models.SlugField(max_length=32)),
                ("name", models.CharField(max_length=80)),
                ("audience", models.CharField(max_length=16)),
                ("price_cents", models.PositiveIntegerField(default=0)),
                ("currency", models.CharField(default="MXN", max_length=3)),
                ("period_days", models.PositiveIntegerField(default=0)),
                ("browser_allowed", models.BooleanField(default=False)),
                ("max_projects", models.PositiveIntegerField(blank=True, null=True)),
                ("max_algorithms", models.PositiveIntegerField(blank=True, null=True)),
                ("features", models.JSONField(default=dict)),
                ("is_default", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["audience", "sort_order", "name"]},
        ),
        migrations.CreateModel(
            name="Subscription",
            fields=[
                (
                    "id",
                    models.BigAutoField(auto_created=True, primary_key=True, serialize=False),
                ),
                ("paid_until", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "plan",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="subscriptions",
                        to="billing.plan",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subscription",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="plan",
            constraint=models.UniqueConstraint(fields=("audience", "code"), name="uniq_plan_code"),
        ),
        migrations.AddConstraint(
            model_name="plan",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_default", True)),
                fields=("audience",),
                name="uniq_default_plan",
            ),
        ),
        migrations.AddConstraint(
            model_name="plan",
            constraint=models.CheckConstraint(
                condition=models.Q(("audience__in", ["student", "teacher"])),
                name="plan_audience",
            ),
        ),
        migrations.RunPython(seed_plans, drop_plans),
    ]
