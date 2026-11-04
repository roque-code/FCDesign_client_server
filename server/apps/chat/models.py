"""Conversación personal o de grupo, separada por materia."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class MessageLifetime(models.Model):
    """Una sola fila. El administrador define cuántas horas vive un mensaje."""

    hours = models.PositiveIntegerField(default=24)

    class Meta:
        verbose_name = "duración de mensajes"
        verbose_name_plural = "duración de mensajes"
        constraints = [
            models.CheckConstraint(
                condition=Q(hours__gte=1, hours__lte=8760),
                name="chat_lifetime_hours_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.hours} h"


class Conversation(models.Model):
    PERSONAL = "personal"
    GROUP = "group"
    SUBJECTS = ("fundamentos", "bases", "objetos", "software")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kind = models.CharField(max_length=16)
    subject = models.CharField(max_length=32)
    community = models.ForeignKey(
        "classroom.Community",
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_as_teacher",
        null=True,
        blank=True,
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_as_student",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["subject", "community", "teacher", "student"],
                condition=Q(kind="personal"),
                name="uniq_chat_personal",
            ),
            models.UniqueConstraint(
                fields=["subject", "community"],
                condition=Q(kind="group"),
                name="uniq_chat_group",
            ),
            models.CheckConstraint(
                condition=Q(subject__in=["fundamentos", "bases", "objetos", "software"])
                & (
                    Q(
                        kind="personal",
                        community__isnull=False,
                        teacher__isnull=False,
                        student__isnull=False,
                    )
                    | Q(
                        kind="group",
                        community__isnull=False,
                        teacher__isnull=True,
                        student__isnull=True,
                    )
                ),
                name="chat_conversation_shape",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.kind} {self.subject} {self.community_id}"


class ReadCursor(models.Model):
    """Hasta qué momento esta persona ya vio la conversación."""

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="read_cursors",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_read_cursors",
    )
    read_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["conversation", "user"], name="uniq_chat_read"),
        ]


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_messages_sent",
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["created_at"], name="chat_message_created_idx"),
            models.Index(fields=["conversation", "created_at"], name="chat_message_thread_idx"),
        ]

    def __str__(self) -> str:
        return str(self.id)
