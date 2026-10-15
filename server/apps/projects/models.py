import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class AliveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="projects",
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    visibility = models.CharField(max_length=16, default="private")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = AliveManager()
    all_objects = models.Manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "name"],
                condition=Q(deleted_at__isnull=True),
                name="uniq_live_project_name",
            ),
            models.CheckConstraint(
                condition=Q(visibility__in=["private", "unlisted"]),
                name="project_visibility",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Folder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="folders")
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
    )
    name = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = AliveManager()
    all_objects = models.Manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "parent", "name"],
                condition=Q(deleted_at__isnull=True, parent__isnull=False),
                name="uniq_live_folder_child",
            ),
            models.UniqueConstraint(
                fields=["project", "name"],
                condition=Q(deleted_at__isnull=True, parent__isnull=True),
                name="uniq_live_folder_root",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Algorithm(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="algorithms")
    folder = models.ForeignKey(
        Folder,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="algorithms",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="algorithms",
    )
    name = models.CharField(max_length=120)
    source = models.TextField(blank=True)
    language_profile = models.ForeignKey(
        "language.LanguageProfile",
        on_delete=models.PROTECT,
        related_name="algorithms",
    )
    language_options = models.JSONField(default=dict)
    profile_snapshot = models.JSONField(default=dict)
    current_version = models.PositiveIntegerField(default=0)
    flowchart = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = AliveManager()
    all_objects = models.Manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "folder", "name"],
                condition=Q(deleted_at__isnull=True, folder__isnull=False),
                name="uniq_live_algorithm_folder",
            ),
            models.UniqueConstraint(
                fields=["project", "name"],
                condition=Q(deleted_at__isnull=True, folder__isnull=True),
                name="uniq_live_algorithm_root",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class AlgorithmVersion(models.Model):
    algorithm = models.ForeignKey(Algorithm, on_delete=models.CASCADE, related_name="versions")
    number = models.PositiveIntegerField()
    source = models.TextField(blank=True)
    message = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="algorithm_versions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["algorithm", "number"], name="uniq_algorithm_version"),
        ]
        ordering = ["number"]

    def __str__(self) -> str:
        return f"{self.algorithm_id}#{self.number}"


class ShareLink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    algorithm = models.ForeignKey(
        Algorithm,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="share_links",
    )
    project = models.ForeignKey(
        Project,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="share_links",
    )
    token_hash = models.CharField(max_length=64, unique=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="share_links",
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(algorithm__isnull=False, project__isnull=True)
                    | Q(algorithm__isnull=True, project__isnull=False)
                ),
                name="share_one_target",
            ),
        ]

    def __str__(self) -> str:
        return self.token_hash[:12]
