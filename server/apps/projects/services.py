"""Proyectos, carpetas, algoritmos, versiones y enlaces."""

import hashlib
import secrets
import unicodedata
from datetime import datetime

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.audit.services import record
from apps.editor.models import EditorPreference
from apps.language.models import LanguageProfile
from apps.language.services import clean_language_option, resolved_options
from apps.projects.models import Algorithm, AlgorithmVersion, Folder, Project, ShareLink
from config.errors import DomainError

NOT_FOUND = "not_found"


def clean_name(value: object) -> str:
    if not isinstance(value, str):
        raise DomainError("El nombre no es válido.")
    name = value.strip()
    if not name:
        raise DomainError("El nombre no puede estar vacío.")
    if len(name) > 120:
        raise DomainError("El nombre admite hasta 120 caracteres.")
    if any(unicodedata.category(ch) == "Cc" for ch in name):
        raise DomainError("El nombre contiene caracteres de control.")
    return name


def clean_source(value: object) -> str:
    if not isinstance(value, str):
        raise DomainError("El fuente no es válido.")
    if len(value.encode("utf-8")) > settings.MAX_SOURCE_BYTES:
        raise DomainError("El fuente supera 64 KiB.", code="source_too_large")
    return value


def clean_description(value: object) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise DomainError("La descripción no es válida.")
    if any(unicodedata.category(ch) == "Cc" and ch not in "\n\t" for ch in value):
        raise DomainError("La descripción contiene caracteres de control.")
    return value


def _profile(key: object) -> LanguageProfile:
    chosen = key if isinstance(key, str) and key else "strict"
    try:
        return LanguageProfile.objects.get(key=chosen)
    except LanguageProfile.DoesNotExist as exc:
        raise DomainError("No se encontró el perfil.", code=NOT_FOUND, status_code=404) from exc


def get_project(user, project_id) -> Project:
    try:
        return Project.objects.get(id=project_id, owner=user)
    except Project.DoesNotExist as exc:
        raise DomainError("No se encontró el proyecto.", code=NOT_FOUND, status_code=404) from exc


def get_algorithm(user, algorithm_id) -> Algorithm:
    try:
        return Algorithm.objects.select_related("project", "language_profile", "folder").get(
            id=algorithm_id,
            owner=user,
            project__deleted_at__isnull=True,
        )
    except Algorithm.DoesNotExist as exc:
        raise DomainError("No se encontró el algoritmo.", code=NOT_FOUND, status_code=404) from exc


def get_readable_algorithm(user, algorithm_id) -> Algorithm:
    """El dueño, o un docente de una comunidad donde ese dueño es alumno."""
    try:
        algorithm = Algorithm.objects.select_related("project", "language_profile", "folder").get(
            id=algorithm_id,
            project__deleted_at__isnull=True,
        )
    except Algorithm.DoesNotExist as exc:
        raise DomainError("No se encontró el algoritmo.", code=NOT_FOUND, status_code=404) from exc
    if algorithm.owner_id == user.id:
        return algorithm
    from apps.classroom.services import teacher_has_student

    if teacher_has_student(user, algorithm.owner_id):
        return algorithm
    raise DomainError("No se encontró el algoritmo.", code=NOT_FOUND, status_code=404)


def project_payload(project: Project) -> dict[str, object]:
    return {
        "id": str(project.id),
        "name": project.name,
        "description": project.description,
        "visibility": project.visibility,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }


def folder_payload(folder: Folder) -> dict[str, object]:
    return {
        "id": str(folder.id),
        "project_id": str(folder.project_id),
        "parent_id": None if folder.parent_id is None else str(folder.parent_id),
        "name": folder.name,
        "created_at": folder.created_at,
    }


def algorithm_payload(algorithm: Algorithm) -> dict[str, object]:
    return {
        "id": str(algorithm.id),
        "project_id": str(algorithm.project_id),
        "folder_id": None if algorithm.folder_id is None else str(algorithm.folder_id),
        "name": algorithm.name,
        "source": algorithm.source,
        "language_profile": algorithm.language_profile.key,
        **resolved_options(algorithm.language_profile, algorithm.language_options),
        "current_version": algorithm.current_version,
        "updated_at": algorithm.updated_at,
    }


def version_payload(version: AlgorithmVersion) -> dict[str, object]:
    return {
        "number": version.number,
        "source": version.source,
        "message": version.message,
        "created_at": version.created_at,
    }


@transaction.atomic
def create_project(user, data: dict, ip_address: str | None) -> Project:
    from apps.billing.services import ensure_quota

    ensure_quota(user, "project")
    if Project.objects.filter(owner=user).count() >= settings.MAX_PROJECTS_PER_USER:
        raise DomainError("Llegaste al máximo de proyectos.")
    visibility = data.get("visibility", "private")
    if visibility not in ("private", "unlisted"):
        raise DomainError("La visibilidad debe ser privada o no listada.")
    project = Project(
        owner=user,
        name=clean_name(data.get("name")),
        description=clean_description(data.get("description")),
        visibility=visibility,
    )
    try:
        project.save()
    except IntegrityError as exc:
        raise DomainError("Ya tienes un proyecto con ese nombre.") from exc
    record(
        "project.create",
        actor=user,
        object_type="project",
        object_id=str(project.id),
        metadata={"name": project.name},
        ip_address=ip_address,
    )
    return project


@transaction.atomic
def update_project(project: Project, data: dict) -> Project:
    if "name" in data:
        project.name = clean_name(data.get("name"))
    if "description" in data:
        project.description = clean_description(data.get("description"))
    if "visibility" in data:
        visibility = data.get("visibility")
        if visibility not in ("private", "unlisted"):
            raise DomainError("La visibilidad debe ser privada o no listada.")
        project.visibility = visibility
    try:
        project.save()
    except IntegrityError as exc:
        raise DomainError("Ya tienes un proyecto con ese nombre.") from exc
    return project


def soft_delete_project(project: Project, user, ip_address: str | None) -> None:
    project.deleted_at = timezone.now()
    project.save(update_fields=["deleted_at", "updated_at"])
    record(
        "project.delete",
        actor=user,
        object_type="project",
        object_id=str(project.id),
        metadata={},
        ip_address=ip_address,
    )


def restore_project(user, project_id) -> Project:
    try:
        project = Project.all_objects.get(id=project_id, owner=user, deleted_at__isnull=False)
    except Project.DoesNotExist as exc:
        raise DomainError("No se encontró el proyecto.", code=NOT_FOUND, status_code=404) from exc
    project.deleted_at = None
    try:
        project.save(update_fields=["deleted_at", "updated_at"])
    except IntegrityError as exc:
        raise DomainError("Ya tienes un proyecto con ese nombre.") from exc
    return project


def _folder_in_project(project: Project, folder_id) -> Folder:
    try:
        folder = Folder.objects.get(id=folder_id, project=project)
    except Folder.DoesNotExist as exc:
        raise DomainError("No se encontró la carpeta.", code=NOT_FOUND, status_code=404) from exc
    return folder


def assert_parent(project: Project, parent: Folder | None, moving_id=None) -> None:
    if parent is None:
        return
    if parent.project_id != project.id:
        raise DomainError("No se encontró la carpeta.", code=NOT_FOUND, status_code=404)
    seen: set = set()
    depth = 0
    current: Folder | None = parent
    while current is not None:
        if current.id in seen or (moving_id is not None and current.id == moving_id):
            raise DomainError("Una carpeta no puede estar dentro de sí misma.")
        seen.add(current.id)
        depth += 1
        current = current.parent
    if depth + 1 > settings.MAX_FOLDER_DEPTH:
        raise DomainError("La carpeta supera la profundidad máxima de 8.")


@transaction.atomic
def create_folder(project: Project, data: dict) -> Folder:
    parent = None
    if data.get("parent_id"):
        parent = _folder_in_project(project, data.get("parent_id"))
    assert_parent(project, parent)
    folder = Folder(project=project, parent=parent, name=clean_name(data.get("name")))
    try:
        folder.save()
    except IntegrityError as exc:
        raise DomainError("Ya existe una carpeta con ese nombre.") from exc
    return folder


@transaction.atomic
def update_folder(folder: Folder, data: dict) -> Folder:
    parent = folder.parent
    if "parent_id" in data:
        parent_id = data.get("parent_id")
        parent = None if not parent_id else _folder_in_project(folder.project, parent_id)
    assert_parent(folder.project, parent, moving_id=folder.id)
    if "name" in data:
        folder.name = clean_name(data.get("name"))
    folder.parent = parent
    try:
        folder.save()
    except IntegrityError as exc:
        raise DomainError("Ya existe una carpeta con ese nombre.") from exc
    return folder


def soft_delete_folder(folder: Folder) -> None:
    folder.deleted_at = timezone.now()
    folder.save(update_fields=["deleted_at"])
    for child in Folder.objects.filter(parent=folder):
        soft_delete_folder(child)


def get_folder(user, folder_id) -> Folder:
    try:
        return Folder.objects.select_related("project").get(
            id=folder_id,
            project__owner=user,
            project__deleted_at__isnull=True,
        )
    except Folder.DoesNotExist as exc:
        raise DomainError("No se encontró la carpeta.", code=NOT_FOUND, status_code=404) from exc


def _optional_folder(project: Project, folder_id) -> Folder | None:
    if not folder_id:
        return None
    return _folder_in_project(project, folder_id)


@transaction.atomic
def create_algorithm(user, data: dict) -> Algorithm:
    from apps.billing.services import ensure_quota

    ensure_quota(user, "algorithm")
    project = get_project(user, data.get("project_id"))
    if Algorithm.objects.filter(project=project).count() >= settings.MAX_ALGORITHMS_PER_PROJECT:
        raise DomainError("Llegaste al máximo de algoritmos en este proyecto.")
    source = clean_source(
        data.get("source", _blank_source(data.get("name"), _preference_locale(user)))
    )
    options = _account_language_options(user)
    if "require_semicolons" in data or "index_base" in data:
        options = clean_language_option(options, data)
    algorithm = Algorithm(
        project=project,
        folder=_optional_folder(project, data.get("folder_id")),
        owner=user,
        name=clean_name(data.get("name")),
        source=source,
        language_profile=_profile(data.get("language_profile")),
        language_options=options,
    )
    if algorithm.owner_id != project.owner_id:
        raise DomainError("El algoritmo no pertenece al dueño del proyecto.")
    try:
        algorithm.save()
    except IntegrityError as exc:
        raise DomainError("Ya existe un algoritmo con ese nombre.") from exc
    return algorithm


def _account_language_options(user) -> dict[str, object]:
    """Reglas que la cuenta eligió. No reescribe algoritmos que ya existen."""
    try:
        preference = user.editor_preference
    except EditorPreference.DoesNotExist:
        return {}
    base = preference.index_base
    if base not in (0, 1):
        base = 1
    return {"require_semicolons": preference.require_semicolons, "index_base": base}


def _preference_locale(user) -> str:
    try:
        locale = user.editor_preference.locale
    except EditorPreference.DoesNotExist:
        return "es"
    return locale if locale in ("es", "en") else "es"


def _blank_source(name: object, locale: str = "es") -> str:
    title = "Nuevo"
    if isinstance(name, str) and name.strip():
        title = "".join(ch for ch in name.strip() if ch.isalnum()) or "Nuevo"
    if locale == "en":
        return f'Algorithm {title}\n    Write "Hello";\nEndAlgorithm\n'
    return f'Algoritmo {title}\n    Escribir "Hola";\nFinAlgoritmo\n'


@transaction.atomic
def update_algorithm(algorithm: Algorithm, data: dict) -> Algorithm:
    if "name" in data:
        algorithm.name = clean_name(data.get("name"))
    if "source" in data:
        algorithm.source = clean_source(data.get("source"))
        algorithm.flowchart = None
    if "folder_id" in data:
        algorithm.folder = _optional_folder(algorithm.project, data.get("folder_id"))
    if "language_profile" in data:
        algorithm.language_profile = _profile(data.get("language_profile"))
        algorithm.flowchart = None
    if "require_semicolons" in data or "index_base" in data:
        locked = Algorithm.objects.select_for_update().get(pk=algorithm.pk)
        algorithm.language_options = clean_language_option(locked.language_options, data)
        algorithm.flowchart = None
    try:
        algorithm.save()
    except IntegrityError as exc:
        raise DomainError("Ya existe un algoritmo con ese nombre.") from exc
    return algorithm


def soft_delete_algorithm(algorithm: Algorithm, user, ip_address: str | None) -> None:
    algorithm.deleted_at = timezone.now()
    algorithm.save(update_fields=["deleted_at", "updated_at"])
    record(
        "algorithm.delete",
        actor=user,
        object_type="algorithm",
        object_id=str(algorithm.id),
        metadata={},
        ip_address=ip_address,
    )


def create_version(
    algorithm: Algorithm, user, message: str, *, force: bool = False
) -> AlgorithmVersion:
    last = algorithm.versions.order_by("-number").first()
    if last is not None and last.source == algorithm.source and not force:
        return last
    number = 1 if last is None else last.number + 1
    version = AlgorithmVersion.objects.create(
        algorithm=algorithm,
        number=number,
        source=algorithm.source,
        message=message[:200],
        created_by=user,
    )
    algorithm.current_version = number
    algorithm.save(update_fields=["current_version", "updated_at"])
    return version


def save_algorithm(algorithm: Algorithm, user, message: str) -> AlgorithmVersion:
    return create_version(algorithm, user, message or "Guardado")


def restore_version(algorithm: Algorithm, user, number: int) -> AlgorithmVersion:
    try:
        version = algorithm.versions.get(number=number)
    except AlgorithmVersion.DoesNotExist as exc:
        raise DomainError("No se encontró la versión.", code=NOT_FOUND, status_code=404) from exc
    algorithm.source = version.source
    algorithm.flowchart = None
    algorithm.save(update_fields=["source", "flowchart", "updated_at"])
    return create_version(algorithm, user, f"Restauración de la versión {number}", force=True)


def parse_expiry(value: object) -> datetime | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise DomainError("La caducidad no es válida.")
    parsed = parse_datetime(value)
    if parsed is None:
        raise DomainError("La caducidad no es válida.")
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


@transaction.atomic
def create_share(
    user, *, algorithm=None, project=None, expires_at=None, ip_address=None
) -> tuple[ShareLink, str]:
    if (algorithm is None) == (project is None):
        raise DomainError("El enlace debe apuntar a un algoritmo o a un proyecto.")
    token = secrets.token_urlsafe(32)
    link = ShareLink.objects.create(
        algorithm=algorithm,
        project=project,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        created_by=user,
        expires_at=expires_at,
    )
    record(
        "share.create",
        actor=user,
        object_type="share",
        object_id=str(link.id),
        metadata={},
        ip_address=ip_address,
    )
    return link, token


def revoke_share(user, link_id) -> None:
    try:
        link = ShareLink.objects.get(id=link_id, created_by=user)
    except ShareLink.DoesNotExist as exc:
        raise DomainError("No se encontró el enlace.", code=NOT_FOUND, status_code=404) from exc
    link.revoked_at = timezone.now()
    link.save(update_fields=["revoked_at"])


def read_share(token: str) -> dict[str, object]:
    digest = hashlib.sha256(token.encode()).hexdigest()
    try:
        link = ShareLink.objects.select_related("algorithm", "project").get(token_hash=digest)
    except ShareLink.DoesNotExist as exc:
        raise DomainError("No se encontró el enlace.", code=NOT_FOUND, status_code=404) from exc
    if link.revoked_at is not None or (
        link.expires_at is not None and link.expires_at <= timezone.now()
    ):
        raise DomainError("No se encontró el enlace.", code=NOT_FOUND, status_code=404)
    if link.algorithm_id is not None:
        algorithm = link.algorithm
        if (
            algorithm is None
            or algorithm.deleted_at is not None
            or algorithm.project.deleted_at is not None
        ):
            raise DomainError("No se encontró el enlace.", code=NOT_FOUND, status_code=404)
        return {
            "kind": "algorithm",
            "name": algorithm.name,
            "source": algorithm.source,
            "project_name": algorithm.project.name,
        }
    project = link.project
    if project is None or project.deleted_at is not None:
        raise DomainError("No se encontró el enlace.", code=NOT_FOUND, status_code=404)
    algorithms = [
        {"name": item.name, "source": item.source}
        for item in project.algorithms.filter(deleted_at__isnull=True).order_by("name")
    ]
    return {"kind": "project", "name": project.name, "algorithms": algorithms}
