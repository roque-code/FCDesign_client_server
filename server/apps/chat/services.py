"""Quién puede escribir a quién, y el borrado al cumplirse la duración."""

from __future__ import annotations

import uuid
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import Count, F, OuterRef, Q, Subquery
from django.utils import timezone

from apps.accounts.models import Profile, User
from apps.chat.models import Conversation, Message, MessageLifetime, ReadCursor
from apps.classroom.models import Community, Membership
from config.errors import DomainError

NOT_FOUND = "not_found"
MAX_BODY = 2000
MIN_HOURS = 1
MAX_HOURS = 24 * 365


def lifetime() -> MessageLifetime:
    row, _created = MessageLifetime.objects.get_or_create(pk=1, defaults={"hours": 24})
    return row


def lifetime_payload(row: MessageLifetime | None = None) -> dict[str, int]:
    current = lifetime() if row is None else row
    return {"hours": current.hours}


def cutoff():
    return timezone.now() - timedelta(hours=lifetime().hours)


def purge_expired() -> int:
    count, _details = Message.objects.filter(created_at__lt=cutoff()).delete()
    return count


@transaction.atomic
def update_lifetime(data: dict) -> MessageLifetime:
    if "hours" not in data:
        raise DomainError("Indica la duración en horas.")
    hours = data["hours"]
    if isinstance(hours, bool) or not isinstance(hours, int) or not MIN_HOURS <= hours <= MAX_HOURS:
        raise DomainError("La duración se indica en horas, de 1 a 8760.")
    lifetime()
    row = MessageLifetime.objects.select_for_update().get(pk=1)
    row.hours = hours
    row.save(update_fields=["hours"])
    purge_expired()
    return row


def require_chat_user(user: User) -> str:
    role = user.profile.role
    if role not in (Profile.STUDENT, Profile.TEACHER):
        raise DomainError("Solo un alumno o un docente puede usar los mensajes.", status_code=403)
    return role


def clean_subject(value: object) -> str:
    if not isinstance(value, str) or value not in Conversation.SUBJECTS:
        raise DomainError("La materia no es válida.")
    return value


def communities_for(user: User, subject: str):
    require_chat_user(user)
    role = user.profile.role
    if role == Profile.TEACHER:
        owned = Community.objects.filter(owner=user, subject=subject)
        joined = Community.objects.filter(
            memberships__user=user,
            owner__profile__role=Profile.TEACHER,
            subject=subject,
        )
        ids = set(owned.values_list("id", flat=True)) | set(joined.values_list("id", flat=True))
        return (
            Community.objects.filter(id__in=ids, subject=subject)
            .select_related("owner__profile")
            .order_by("name")
        )
    return (
        Community.objects.filter(
            memberships__user=user,
            owner__profile__role=Profile.TEACHER,
            subject=subject,
        )
        .select_related("owner__profile")
        .order_by("name")
        .distinct()
    )


def can_see(user: User, community: Community) -> bool:
    if community.owner_id == user.pk:
        return user.profile.role == Profile.TEACHER
    return Membership.objects.filter(community=community, user=user).exists()


def peers(user: User, community: Community) -> list[User] | None:
    """Personas con las que se puede hablar en privado dentro del grupo.

    El docente ve a los alumnos. El alumno ve a los docentes del grupo.
    """
    if not can_see(user, community):
        return None
    students = [
        row.user
        for row in Membership.objects.filter(
            community=community, user__profile__role=Profile.STUDENT
        )
        .exclude(user=user)
        .select_related("user__profile")
        .order_by("user__profile__display_name")
    ]
    if user.profile.role == Profile.TEACHER:
        return students
    teachers: list[User] = []
    owner = community.owner
    if owner.profile.role == Profile.TEACHER and owner.pk != user.pk:
        teachers.append(owner)
    for row in (
        Membership.objects.filter(community=community, user__profile__role=Profile.TEACHER)
        .exclude(user=user)
        .select_related("user__profile")
        .order_by("user__profile__display_name")
    ):
        if row.user_id != owner.pk:
            teachers.append(row.user)
    return teachers


def load_community(user: User, community_id: object, subject: str | None = None) -> Community:
    if not isinstance(community_id, str):
        raise DomainError("Elige un grupo.")
    try:
        parsed = uuid.UUID(community_id)
    except ValueError:
        raise DomainError("Elige un grupo.") from None
    try:
        community = Community.objects.select_related("owner__profile").get(pk=parsed)
    except Community.DoesNotExist:
        raise DomainError("Ese grupo no es tuyo.") from None
    if peers(user, community) is None:
        raise DomainError("Ese grupo no es tuyo.")
    if subject is not None and community.subject != subject:
        raise DomainError("Ese grupo no es de esta materia.")
    return community


def pair_ids(user: User, person: User) -> tuple[int, int]:
    if user.profile.role == Profile.TEACHER and person.profile.role == Profile.STUDENT:
        return user.pk, person.pk
    if user.profile.role == Profile.STUDENT and person.profile.role == Profile.TEACHER:
        return person.pk, user.pk
    raise DomainError("Esa persona no está en tus grupos.")


def message_payload(message: Message) -> dict[str, object]:
    return {
        "id": str(message.id),
        "sender_id": message.sender_id,
        "sender_name": message.sender.profile.display_name,
        "body": message.body,
        "created_at": message.created_at.isoformat(),
    }


def _messages(conversation: Conversation) -> list[dict[str, object]]:
    rows = conversation.messages.select_related("sender__profile").order_by("created_at", "id")
    return [message_payload(row) for row in rows]


def latest_messages(conversation_ids: list) -> dict:
    if not conversation_ids:
        return {}
    rows = (
        Message.objects.filter(conversation_id__in=conversation_ids)
        .select_related("sender__profile")
        .order_by("conversation_id", "-created_at", "-id")
        .distinct("conversation_id")
    )
    return {row.conversation_id: row for row in rows}


def unread_counts(user: User, conversation_ids: list) -> dict:
    if not conversation_ids:
        return {}
    seen = ReadCursor.objects.filter(user=user, conversation_id=OuterRef("conversation_id")).values(
        "read_at"
    )[:1]
    rows = (
        Message.objects.filter(conversation_id__in=conversation_ids)
        .exclude(sender=user)
        .annotate(seen_at=Subquery(seen))
        .filter(Q(seen_at__isnull=True) | Q(created_at__gt=F("seen_at")))
        .values("conversation_id")
        .annotate(total=Count("id"))
    )
    return {row["conversation_id"]: row["total"] for row in rows}


def mark_read(user: User, conversation: Conversation) -> None:
    latest = (
        conversation.messages.order_by("-created_at", "-id")
        .values_list("created_at", flat=True)
        .first()
    )
    stamp = latest or timezone.now()
    row, created = ReadCursor.objects.get_or_create(
        conversation=conversation,
        user=user,
        defaults={"read_at": stamp},
    )
    if not created and row.read_at < stamp:
        row.read_at = stamp
        row.save(update_fields=["read_at"])


def _person_payload(
    person: User, conversation: Conversation | None, last: dict, unread: dict
) -> dict[str, object]:
    message = last.get(conversation.id) if conversation is not None else None
    return {
        "id": person.pk,
        "display_name": person.profile.display_name,
        "role": person.profile.role,
        "conversation_id": str(conversation.id) if conversation is not None else None,
        "last_message": message_payload(message) if message is not None else None,
        "unread": unread.get(conversation.id, 0) if conversation is not None else 0,
    }


def list_board(user: User, subject: object) -> dict[str, object]:
    purge_expired()
    require_chat_user(user)
    chosen = clean_subject(subject)
    from apps.billing.services import ensure_menu, ensure_subject

    ensure_subject(user, chosen)
    ensure_menu(user, "chat", chosen)
    groups = list(communities_for(user, chosen))
    conversations = list(
        Conversation.objects.filter(subject=chosen, community__in=groups, community__subject=chosen)
    )
    last = latest_messages([item.id for item in conversations])
    pending = unread_counts(user, [item.id for item in conversations])
    group_thread: dict = {}
    personal: dict[tuple, Conversation] = {}
    for item in conversations:
        if item.kind == Conversation.GROUP:
            group_thread[item.community_id] = item
        elif item.teacher_id and item.student_id:
            personal[(item.community_id, item.teacher_id, item.student_id)] = item
    results = []
    for community in groups:
        people = peers(user, community) or []
        listed = []
        for person in people:
            try:
                teacher_id, student_id = pair_ids(user, person)
            except DomainError:
                continue
            listed.append(
                _person_payload(
                    person,
                    personal.get((community.id, teacher_id, student_id)),
                    last,
                    pending,
                )
            )
        conversation = group_thread.get(community.id)
        message = last.get(conversation.id) if conversation is not None else None
        results.append(
            {
                "id": str(community.id),
                "name": community.name,
                "conversation_id": str(conversation.id) if conversation is not None else None,
                "last_message": message_payload(message) if message is not None else None,
                "unread": pending.get(conversation.id, 0) if conversation is not None else 0,
                "people": listed,
            }
        )
    return {"hours": lifetime().hours, "subject": chosen, "groups": results}


def get_conversation(user: User, conversation_id) -> Conversation:
    require_chat_user(user)
    try:
        conversation = Conversation.objects.select_related(
            "community__owner__profile", "teacher__profile", "student__profile"
        ).get(pk=conversation_id)
    except (Conversation.DoesNotExist, ValueError, TypeError):
        raise DomainError(
            "No se encontró la conversación.", code=NOT_FOUND, status_code=404
        ) from None
    community = conversation.community
    visible = peers(user, community)
    if conversation.kind == Conversation.PERSONAL:
        if user.pk not in (conversation.teacher_id, conversation.student_id):
            raise DomainError("No se encontró la conversación.", code=NOT_FOUND, status_code=404)
        if visible is None:
            raise DomainError("Ya no estás en ese grupo.", status_code=403)
        other = (
            conversation.student_id
            if user.pk == conversation.teacher_id
            else conversation.teacher_id
        )
        if other not in {person.pk for person in visible}:
            raise DomainError("Esa persona ya no está en tus grupos.", status_code=403)
        return conversation
    if visible is None:
        raise DomainError("Ya no estás en ese grupo.", status_code=403)
    return conversation


def thread_payload(conversation: Conversation, user: User) -> dict[str, object]:
    peer_id = None
    if conversation.kind == Conversation.PERSONAL:
        peer_id = (
            conversation.student_id
            if user.pk == conversation.teacher_id
            else conversation.teacher_id
        )
    return {
        "id": str(conversation.id),
        "kind": conversation.kind,
        "subject": conversation.subject,
        "community_id": str(conversation.community_id),
        "peer_id": peer_id,
        "messages": _messages(conversation),
    }


def _open_group(subject: str, community: Community) -> Conversation:
    existing = Conversation.objects.filter(
        kind=Conversation.GROUP, subject=subject, community=community
    ).first()
    if existing is not None:
        return existing
    try:
        return Conversation.objects.create(
            kind=Conversation.GROUP, subject=subject, community=community
        )
    except IntegrityError:
        return Conversation.objects.get(
            kind=Conversation.GROUP, subject=subject, community=community
        )


@transaction.atomic
def open_thread(
    user: User, subject: object, community_id: object, user_id: object
) -> dict[str, object]:
    purge_expired()
    require_chat_user(user)
    chosen = clean_subject(subject)
    from apps.billing.services import ensure_menu, ensure_subject

    ensure_subject(user, chosen)
    ensure_menu(user, "chat", chosen)
    community = load_community(user, community_id, chosen)
    if user_id is None:
        conversation = _open_group(chosen, community)
    else:
        if isinstance(user_id, bool) or not isinstance(user_id, int):
            raise DomainError("Elige a una persona de tus grupos.")
        person = next((item for item in (peers(user, community) or []) if item.pk == user_id), None)
        if person is None:
            raise DomainError("Esa persona no está en tus grupos.")
        teacher_id, student_id = pair_ids(user, person)
        conversation, _created = Conversation.objects.get_or_create(
            kind=Conversation.PERSONAL,
            subject=chosen,
            community=community,
            teacher_id=teacher_id,
            student_id=student_id,
        )
    conversation = Conversation.objects.select_related(
        "community__owner__profile", "teacher__profile", "student__profile"
    ).get(pk=conversation.pk)
    mark_read(user, conversation)
    return thread_payload(conversation, user)


def list_messages(user: User, conversation_id) -> dict[str, object]:
    purge_expired()
    conversation = get_conversation(user, conversation_id)
    mark_read(user, conversation)
    return {"results": _messages(conversation)}


def clean_body(value: object) -> str:
    if not isinstance(value, str):
        raise DomainError("Escribe un mensaje.")
    text = value.strip()
    if not text:
        raise DomainError("Escribe un mensaje.")
    if len(text) > MAX_BODY:
        raise DomainError("El mensaje es demasiado largo.")
    return text


@transaction.atomic
def send_message(user: User, conversation_id, data: dict) -> dict[str, object]:
    purge_expired()
    conversation = get_conversation(user, conversation_id)
    body = clean_body(data.get("body"))
    message = Message.objects.create(conversation=conversation, sender=user, body=body)
    Conversation.objects.filter(pk=conversation.pk).update(updated_at=timezone.now())
    message = Message.objects.select_related("sender__profile").get(pk=message.pk)
    return message_payload(message)
