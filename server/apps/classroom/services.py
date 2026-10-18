"""Un docente agrupa cuentas que ya existen. No se crean usuarios desde aquí."""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Q

from apps.accounts.models import Profile, User
from apps.accounts.services import clean_label
from apps.audit.services import record
from apps.classroom.models import Community, Membership
from config.errors import DomainError

NOT_FOUND = "not_found"


def require_teacher(user: User) -> None:
    if user.profile.role != Profile.TEACHER:
        raise DomainError("Solo un docente puede gestionar comunidades.", status_code=403)


def person_payload(
    user: User,
    *,
    member: bool | None = None,
    translation_enabled: bool | None = None,
    paste_enabled: bool | None = None,
) -> dict[str, object]:
    profile = user.profile
    payload: dict[str, object] = {
        "id": user.pk,
        "display_name": profile.display_name,
        "email": user.email,
        "role": profile.role,
    }
    if member is not None:
        payload["member"] = member
    if translation_enabled is not None:
        payload["translation_enabled"] = translation_enabled
    if paste_enabled is not None:
        payload["paste_enabled"] = paste_enabled
    return payload


def _counts(community: Community) -> tuple[int, int]:
    rows = community.memberships.aggregate(
        students=Count("id", filter=Q(user__profile__role=Profile.STUDENT)),
        teachers=Count("id", filter=Q(user__profile__role=Profile.TEACHER)),
    )
    return int(rows["students"] or 0), int(rows["teachers"] or 0)


def community_summary(community: Community) -> dict[str, object]:
    students, teachers = _counts(community)
    return {
        "id": str(community.id),
        "name": community.name,
        "student_count": students,
        "teacher_count": teachers,
        "translation_enabled": community.translation_enabled,
        "paste_enabled": community.paste_enabled,
    }


def _split(community: Community) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    students: list[dict[str, object]] = []
    teachers: list[dict[str, object]] = []
    memberships = community.memberships.select_related("user__profile").order_by(
        "user__profile__display_name",
        "user__email",
    )
    for item in memberships:
        enabled = None
        paste = None
        if item.user.profile.role != Profile.TEACHER:
            choice = item.translation_enabled
            enabled = community.translation_enabled if choice is None else choice
            paste_choice = item.paste_enabled
            paste = community.paste_enabled if paste_choice is None else paste_choice
        person = person_payload(item.user, translation_enabled=enabled, paste_enabled=paste)
        if item.user.profile.role == Profile.TEACHER:
            teachers.append(person)
        else:
            students.append(person)
    return students, teachers


def community_detail(community: Community) -> dict[str, object]:
    students, teachers = _split(community)
    return {
        "id": str(community.id),
        "name": community.name,
        "student_count": len(students),
        "teacher_count": len(teachers),
        "translation_enabled": community.translation_enabled,
        "paste_enabled": community.paste_enabled,
        "students": students,
        "teachers": teachers,
    }


def list_communities(user: User) -> list[dict[str, object]]:
    require_teacher(user)
    communities = user.communities.all().order_by("name")
    return [community_summary(item) for item in communities]


def get_community(user: User, community_id) -> Community:
    require_teacher(user)
    try:
        return Community.objects.get(pk=community_id, owner=user)
    except (Community.DoesNotExist, ValueError, TypeError, ValidationError) as exc:
        raise DomainError("No se encontró la comunidad.", code=NOT_FOUND, status_code=404) from exc


def create_community(user: User, data: dict, ip_address: str | None) -> Community:
    require_teacher(user)
    if user.communities.count() >= settings.MAX_COMMUNITIES_PER_TEACHER:
        raise DomainError("Llegaste al máximo de comunidades.")
    name = clean_label(data.get("name"), field="El nombre", limit=80, required=True)
    community = Community(owner=user, name=name)
    try:
        with transaction.atomic():
            community.save()
    except IntegrityError as exc:
        raise DomainError("Ya tienes una comunidad con ese nombre.") from exc
    record(
        "community.create",
        actor=user,
        object_type="community",
        object_id=str(community.id),
        metadata={"name": name},
        ip_address=ip_address,
    )
    return community


def delete_community(user: User, community_id, ip_address: str | None) -> None:
    community = get_community(user, community_id)
    community_id_text = str(community.id)
    community.delete()
    record(
        "community.delete",
        actor=user,
        object_type="community",
        object_id=community_id_text,
        metadata={},
        ip_address=ip_address,
    )


def _registered(user_id: object) -> User:
    if isinstance(user_id, bool) or not isinstance(user_id, int | str):
        raise DomainError("Esa persona no está registrada.", code=NOT_FOUND, status_code=404)
    try:
        return User.objects.select_related("profile").get(pk=user_id)
    except (User.DoesNotExist, ValueError, TypeError) as exc:
        raise DomainError(
            "Esa persona no está registrada.",
            code=NOT_FOUND,
            status_code=404,
        ) from exc


@transaction.atomic
def add_member(user: User, community_id, user_id: object, ip_address: str | None) -> User:
    require_teacher(user)
    try:
        community = Community.objects.select_for_update().get(pk=community_id, owner=user)
    except (Community.DoesNotExist, ValueError, TypeError, ValidationError) as exc:
        raise DomainError("No se encontró la comunidad.", code=NOT_FOUND, status_code=404) from exc
    member = _registered(user_id)
    if member.pk == user.pk:
        raise DomainError("No puedes agregarte a tu propia comunidad.")
    if community.memberships.count() >= settings.MAX_MEMBERS_PER_COMMUNITY:
        raise DomainError("La comunidad llegó al máximo de personas.")
    try:
        with transaction.atomic():
            Membership.objects.create(community=community, user=member)
    except IntegrityError as exc:
        raise DomainError("Esa persona ya está en la comunidad.") from exc
    record(
        "community.member_add",
        actor=user,
        object_type="community",
        object_id=str(community.id),
        metadata={"user_id": member.pk},
        ip_address=ip_address,
    )
    return member


def remove_member(user: User, community_id, user_id, ip_address: str | None) -> None:
    community = get_community(user, community_id)
    deleted, _ignored = community.memberships.filter(user_id=user_id).delete()
    if not deleted:
        raise DomainError("Esa persona no está en la comunidad.", code=NOT_FOUND, status_code=404)
    record(
        "community.member_remove",
        actor=user,
        object_type="community",
        object_id=str(community.id),
        metadata={"user_id": user_id},
        ip_address=ip_address,
    )


def translation_allowed(user: User) -> bool:
    from apps.billing.services import allows

    if not allows(user, "translate"):
        return False
    if user.profile.role == Profile.TEACHER:
        return True
    memberships = list(Membership.objects.filter(user=user).select_related("community"))
    if not memberships:
        return True
    for item in memberships:
        choice = item.translation_enabled
        allowed = item.community.translation_enabled if choice is None else choice
        if not allowed:
            return False
    return True


def paste_allowed(user: User) -> bool:
    from apps.billing.services import allows

    if not allows(user, "paste"):
        return False
    if user.profile.role == Profile.TEACHER:
        return True
    memberships = list(Membership.objects.filter(user=user).select_related("community"))
    if not memberships:
        return True
    for item in memberships:
        choice = item.paste_enabled
        allowed = item.community.paste_enabled if choice is None else choice
        if not allowed:
            return False
    return True


def _enabled_flag(value: object, message: str) -> bool:
    if not isinstance(value, bool):
        raise DomainError(message)
    return value


@transaction.atomic
def set_community_translation(
    user: User,
    community_id,
    enabled: object,
    ip_address: str | None,
) -> Community:
    flag = _enabled_flag(enabled, "Indica si la traducción queda habilitada.")
    community = get_community(user, community_id)
    community.translation_enabled = flag
    community.save(update_fields=["translation_enabled", "updated_at"])
    community.memberships.filter(user__profile__role=Profile.STUDENT).update(
        translation_enabled=None
    )
    record(
        "community.translation",
        actor=user,
        object_type="community",
        object_id=str(community.id),
        metadata={"translation_enabled": flag},
        ip_address=ip_address,
    )
    return community


def set_member_translation(
    user: User,
    community_id,
    user_id,
    enabled: object,
    ip_address: str | None,
) -> Community:
    flag = _enabled_flag(enabled, "Indica si la traducción queda habilitada.")
    community = get_community(user, community_id)
    try:
        membership = community.memberships.select_related("user__profile").get(user_id=user_id)
    except Membership.DoesNotExist as exc:
        raise DomainError(
            "Esa persona no está en la comunidad.",
            code=NOT_FOUND,
            status_code=404,
        ) from exc
    if membership.user.profile.role != Profile.STUDENT:
        raise DomainError("La traducción se ajusta para un alumno.")
    membership.translation_enabled = flag
    membership.save(update_fields=["translation_enabled"])
    record(
        "community.member_translation",
        actor=user,
        object_type="community",
        object_id=str(community.id),
        metadata={"user_id": membership.user_id, "translation_enabled": flag},
        ip_address=ip_address,
    )
    return community


@transaction.atomic
def set_community_paste(
    user: User,
    community_id,
    enabled: object,
    ip_address: str | None,
) -> Community:
    flag = _enabled_flag(enabled, "Indica si se puede pegar texto.")
    community = get_community(user, community_id)
    community.paste_enabled = flag
    community.save(update_fields=["paste_enabled", "updated_at"])
    community.memberships.filter(user__profile__role=Profile.STUDENT).update(paste_enabled=None)
    record(
        "community.paste",
        actor=user,
        object_type="community",
        object_id=str(community.id),
        metadata={"paste_enabled": flag},
        ip_address=ip_address,
    )
    return community


def set_member_paste(
    user: User,
    community_id,
    user_id,
    enabled: object,
    ip_address: str | None,
) -> Community:
    flag = _enabled_flag(enabled, "Indica si se puede pegar texto.")
    community = get_community(user, community_id)
    try:
        membership = community.memberships.select_related("user__profile").get(user_id=user_id)
    except Membership.DoesNotExist as exc:
        raise DomainError(
            "Esa persona no está en la comunidad.",
            code=NOT_FOUND,
            status_code=404,
        ) from exc
    if membership.user.profile.role != Profile.STUDENT:
        raise DomainError("El pegado se ajusta para un alumno.")
    membership.paste_enabled = flag
    membership.save(update_fields=["paste_enabled"])
    record(
        "community.member_paste",
        actor=user,
        object_type="community",
        object_id=str(community.id),
        metadata={"user_id": membership.user_id, "paste_enabled": flag},
        ip_address=ip_address,
    )
    return community


def search_people(user: User, query: object, community_id) -> list[dict[str, object]]:
    community = get_community(user, community_id)
    if not isinstance(query, str):
        raise DomainError("Escribe al menos dos letras.")
    text = query.strip()
    if len(text) < 2:
        raise DomainError("Escribe al menos dos letras.")
    if any(ord(ch) < 32 for ch in text):
        raise DomainError("La búsqueda contiene caracteres de control.")
    found = (
        User.objects.select_related("profile")
        .exclude(pk=user.pk)
        .filter(Q(email__icontains=text) | Q(profile__display_name__icontains=text))
        .order_by("profile__display_name", "email")[:20]
    )
    present = set(community.memberships.values_list("user_id", flat=True))
    return [person_payload(item, member=item.pk in present) for item in found]


def teacher_has_student(teacher: User, student_id: int) -> bool:
    profile = getattr(teacher, "profile", None)
    if profile is None or profile.role != Profile.TEACHER:
        return False
    return Membership.objects.filter(
        community__owner=teacher,
        user_id=student_id,
        user__profile__role=Profile.STUDENT,
    ).exists()


def classroom_students(teacher: User) -> list[dict[str, object]]:
    require_teacher(teacher)
    memberships = (
        Membership.objects.filter(
            community__owner=teacher,
            user__profile__role=Profile.STUDENT,
        )
        .select_related("user__profile", "community")
        .order_by("user__profile__display_name", "user__email", "community__name")
    )
    grouped: dict[int, dict[str, object]] = {}
    for item in memberships:
        row = grouped.get(item.user_id)
        if row is None:
            row = {
                "id": item.user_id,
                "display_name": item.user.profile.display_name,
                "email": item.user.email,
                "communities": [],
            }
            grouped[item.user_id] = row
        names = row["communities"]
        assert isinstance(names, list)
        names.append(item.community.name)
    return list(grouped.values())


def student_projects(teacher: User, user_id: int) -> dict[str, object]:
    from apps.projects.services import algorithm_payload, project_payload

    require_teacher(teacher)
    if not teacher_has_student(teacher, user_id):
        raise DomainError("No se encontró al alumno.", code=NOT_FOUND, status_code=404)
    student = User.objects.select_related("profile").get(pk=user_id)
    projects: list[dict[str, object]] = []
    for project in student.projects.all().order_by("name"):
        algorithms = project.algorithms.select_related("language_profile", "folder").order_by(
            "name"
        )
        payload = project_payload(project)
        payload["algorithms"] = [algorithm_payload(item) for item in algorithms]
        projects.append(payload)
    return {"student": person_payload(student), "projects": projects}
