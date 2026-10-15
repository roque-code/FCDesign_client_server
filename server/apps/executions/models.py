import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class Execution(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    algorithm = models.ForeignKey(
        "projects.Algorithm",
        on_delete=models.PROTECT,
        related_name="executions",
    )
    version_number = models.PositiveIntegerField(null=True, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="executions",
    )
    status = models.CharField(max_length=32)
    source = models.TextField(blank=True)
    profile_config = models.JSONField(default=dict)
    limits = models.JSONField(default=dict)
    pending_input = models.JSONField(null=True, blank=True)
    instruction_count = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "-started_at"], name="exec_user_started"),
            models.Index(fields=["algorithm", "-started_at"], name="exec_alg_started"),
            models.Index(fields=["status"], name="exec_status"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    status__in=[
                        "queued",
                        "running",
                        "waiting_input",
                        "paused",
                        "completed",
                        "error",
                        "cancelled",
                        "timeout",
                    ]
                ),
                name="execution_status",
            ),
        ]


class ExecutionEvent(models.Model):
    execution = models.ForeignKey(Execution, on_delete=models.CASCADE, related_name="events")
    sequence = models.PositiveIntegerField()
    kind = models.CharField(max_length=16)
    text = models.TextField(blank=True)
    line = models.PositiveIntegerField(null=True, blank=True)
    column = models.PositiveIntegerField(null=True, blank=True)
    code = models.CharField(max_length=16, blank=True)
    suggestion = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["execution", "sequence"], name="uniq_event_sequence"),
            models.CheckConstraint(
                condition=Q(kind__in=["output", "input", "error", "status"]),
                name="execution_event_kind",
            ),
        ]
        ordering = ["sequence"]
