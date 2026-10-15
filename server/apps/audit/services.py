"""Registro de acciones. El metadato no lleva secretos ni el fuente completo."""

from apps.audit.models import AuditEvent


def record(
    action: str,
    *,
    actor,
    object_type: str,
    object_id: str,
    metadata: dict | None = None,
    ip_address: str | None = None,
) -> AuditEvent:
    return AuditEvent.objects.create(
        actor=actor,
        action=action,
        object_type=object_type,
        object_id=object_id,
        metadata=metadata or {},
        ip_address=ip_address,
    )
