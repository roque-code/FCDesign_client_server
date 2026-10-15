"""Un docente arma una ruta, crea sus retos y la asigna."""

from __future__ import annotations

import uuid

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Prefetch, Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.accounts.models import Profile
from apps.accounts.services import clean_label
from apps.classroom.models import Community, Membership
from apps.learning.bank_data import BANK_NAME
from apps.learning.models import (
    Challenge,
    ChallengeAttempt,
    ChallengeTestCase,
    Concept,
    Hint,
    HintUsage,
    LearningPath,
    LearningUnit,
    PathAssignment,
    PathEntry,
)
from config.errors import DomainError
from language_core.block_adapter import adapt_workspace
from language_core.block_import import workspace_from_source

NOT_FOUND = "not_found"
_MISSING_PATH = "No se encontró la ruta."
_MISSING_CHALLENGE = "Ese reto no está en el catálogo."


def _require_teacher(user) -> None:
    if user.profile.role != Profile.TEACHER:
        raise DomainError("Solo un docente puede armar rutas.", status_code=403)


def _owned(teacher, path_id) -> LearningPath:
    _require_teacher(teacher)
    try:
        path = LearningPath.objects.get(pk=path_id, owner=teacher, is_bank=False)
    except (LearningPath.DoesNotExist, ValueError, TypeError, ValidationError) as exc:
        raise DomainError(_MISSING_PATH, code=NOT_FOUND, status_code=404) from exc
    return path


def _catalog():
    return Challenge.objects.filter(
        is_published=True,
        unit__path__is_published=True,
        unit__path__owner__isnull=True,
    ).select_related("unit__concept")


def _iso(value) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _challenge_row(
    challenge: Challenge,
    position: int | None = None,
    entry: PathEntry | None = None,
) -> dict[str, object]:
    row: dict[str, object] = {
        "id": str(challenge.id),
        "title": challenge.title,
        "activity_type": challenge.activity_type,
        "concept": challenge.unit.concept.name,
        "points": challenge.points,
        "difficulty": challenge.difficulty,
        "owned": challenge.unit.path.is_bank and challenge.unit.path.owner_id is not None,
    }
    if position is not None:
        row["position"] = position
    if entry is not None:
        row["opens_at"] = _iso(entry.opens_at)
        row["closes_at"] = _iso(entry.closes_at)
        row["withdrawn"] = entry.withdrawn
    return row


def _own_challenges(teacher):
    return Challenge.objects.filter(
        is_published=True,
        unit__path__is_bank=True,
        unit__path__owner=teacher,
    ).select_related("unit__concept", "unit__path")


def _placeable(teacher):
    return Challenge.objects.filter(is_published=True).filter(
        Q(unit__path__owner__isnull=True, unit__path__is_published=True)
        | Q(unit__path__is_bank=True, unit__path__owner=teacher)
    )


def catalog_payload(teacher) -> dict[str, object]:
    _require_teacher(teacher)
    own = [
        _challenge_row(challenge)
        for challenge in _own_challenges(teacher).order_by("title")
    ]
    system = [
        _challenge_row(challenge)
        for challenge in _catalog()
        .select_related("unit__path")
        .order_by("unit__position", "position")
    ]
    concepts = [
        {"key": concept.key, "name": concept.name} for concept in Concept.objects.order_by("name")
    ]
    return {"results": own + system, "concepts": concepts}


def bank_payload(teacher) -> dict[str, object]:
    """El banco compartido, con el enunciado y la solución, solo para el docente."""
    _require_teacher(teacher)
    path = (
        LearningPath.objects.filter(name=BANK_NAME, is_bank=True, owner__isnull=True)
        .prefetch_related(
            Prefetch(
                "units",
                queryset=LearningUnit.objects.select_related("concept")
                .order_by("position")
                .prefetch_related(
                    Prefetch(
                        "challenges",
                        queryset=Challenge.objects.filter(is_published=True)
                        .select_related("unit__path", "unit__concept")
                        .order_by("position")
                        .prefetch_related(
                            Prefetch("hints", queryset=Hint.objects.order_by("level", "position")),
                            Prefetch(
                                "test_cases",
                                queryset=ChallengeTestCase.objects.order_by("position"),
                            ),
                        ),
                    )
                ),
            )
        )
        .first()
    )
    units: list[dict[str, object]] = []
    grouped: dict[str, dict[str, object]] = {}
    if path is not None:
        for unit in path.units.all():
            cards = [_bank_challenge(challenge) for challenge in unit.challenges.all()]
            if not cards:
                continue
            row = {"title": unit.title, "concept": unit.concept.name, "challenges": cards}
            units.append(row)
            grouped[unit.concept.name] = row
    own = (
        _own_challenges(teacher)
        .select_related("unit__path", "unit__concept")
        .order_by("unit__position", "position")
        .prefetch_related(
            Prefetch("hints", queryset=Hint.objects.order_by("level", "position")),
            Prefetch("test_cases", queryset=ChallengeTestCase.objects.order_by("position")),
        )
    )
    for challenge in own:
        card = _bank_challenge(challenge)
        name = challenge.unit.concept.name
        row = grouped.get(name)
        if row is None:
            row = {"title": challenge.unit.title, "concept": name, "challenges": []}
            units.append(row)
            grouped[name] = row
        challenges = row["challenges"]
        assert isinstance(challenges, list)
        challenges.append(card)
    if path is None:
        return {"name": BANK_NAME, "description": "", "units": units}
    return {"name": path.name, "description": path.description, "units": units}


def _bank_challenge(challenge: Challenge) -> dict[str, object]:
    restrictions = challenge.restrictions if isinstance(challenge.restrictions, dict) else {}
    raw_items = restrictions.get("items")
    rows = [item for item in raw_items if isinstance(item, dict)] if isinstance(raw_items, list) else []
    if challenge.activity_type == Challenge.ORDER:
        by_id = {str(item.get("id")): str(item.get("text", "")) for item in rows}
        solution = restrictions.get("solution")
        ordered = solution if isinstance(solution, list) else []
        shown = [{"text": by_id.get(str(item_id), ""), "category": ""} for item_id in ordered]
    else:
        shown = [
            {"text": str(item.get("text", "")), "category": str(item.get("category", ""))}
            for item in rows
        ]
    cases = list(challenge.test_cases.all())
    case = cases[0] if cases else None
    source = restrictions.get("source")
    hints = [hint.body for hint in challenge.hints.all()]
    categories = restrictions.get("categories")
    accepted = restrictions.get("accepted")
    return {
        "id": str(challenge.id),
        "title": challenge.title,
        "prompt": challenge.prompt,
        "activity_type": challenge.activity_type,
        "concept": challenge.unit.concept.name,
        "difficulty": challenge.difficulty,
        "points": challenge.points,
        "position": challenge.position,
        "time_limit_seconds": challenge.time_limit_seconds,
        "categories": categories if isinstance(categories, list) else [],
        "items": shown,
        "question": restrictions.get("question") or "",
        "accepted": accepted if isinstance(accepted, list) else [],
        "inputs": [] if case is None else list(case.inputs),
        "expected_output": "" if case is None else case.expected_output,
        "source": source if isinstance(source, str) else "",
        "hints": hints,
        "allowed_blocks": list(challenge.allowed_blocks),
        "owned": challenge.unit.path.owner_id is not None,
    }


def _detail(path: LearningPath) -> dict[str, object]:
    entries = path.entries.select_related(
        "challenge__unit__concept", "challenge__unit__path"
    ).order_by("position")
    communities = []
    students = []
    assignments = path.assignments.select_related("community", "student__profile").order_by(
        "created_at"
    )
    for item in assignments:
        if item.community_id is not None and item.community is not None:
            communities.append({"id": str(item.community_id), "name": item.community.name})
        elif item.student_id is not None and item.student is not None:
            students.append(
                {
                    "id": item.student_id,
                    "display_name": item.student.profile.display_name,
                    "email": item.student.email,
                }
            )
    return {
        "id": str(path.id),
        "name": path.name,
        "description": path.description,
        "is_published": path.is_published,
        "challenges": [
            _challenge_row(entry.challenge, entry.position, entry) for entry in entries
        ],
        "communities": communities,
        "students": students,
    }


def _audience_sizes(path_ids: list) -> dict:
    rows = PathAssignment.objects.filter(path_id__in=path_ids).values_list(
        "path_id", "student_id", "community_id"
    )
    community_ids = {community_id for _, _, community_id in rows if community_id is not None}
    members: dict = {}
    if community_ids:
        for community_id, user_id in Membership.objects.filter(
            community_id__in=community_ids
        ).values_list("community_id", "user_id"):
            members.setdefault(community_id, set()).add(user_id)
    people: dict = {}
    for path_id, student_id, community_id in rows:
        bucket = people.setdefault(path_id, set())
        if student_id is not None:
            bucket.add(student_id)
        if community_id is not None:
            bucket.update(members.get(community_id, ()))
    return {path_id: len(ids) for path_id, ids in people.items()}


def list_paths(teacher) -> dict[str, object]:
    _require_teacher(teacher)
    paths = list(
        teacher.learning_paths.filter(is_bank=False)
        .annotate(
            challenge_count=Count("entries", distinct=True),
            community_count=Count("assignments__community", distinct=True),
        )
        .order_by("name")
    )
    audience = _audience_sizes([path.id for path in paths])
    return {
        "results": [
            {
                "id": str(path.id),
                "name": path.name,
                "description": path.description,
                "is_published": path.is_published,
                "challenge_count": path.challenge_count,
                "community_count": path.community_count,
                "student_count": audience.get(path.id, 0),
            }
            for path in paths
        ]
    }


def _description(value: object) -> str:
    if value is None:
        return ""
    return clean_label(value, field="La descripción", limit=2000, required=False)


@transaction.atomic
def create_path(teacher, data: dict) -> dict[str, object]:
    _require_teacher(teacher)
    name = clean_label(data.get("name"), field="El nombre", limit=120, required=True)
    description = _description(data.get("description", ""))
    last = (
        LearningPath.objects.select_for_update().order_by("-position").values_list(
            "position", flat=True
        ).first()
    )
    path = LearningPath(
        name=name,
        description=description,
        position=(last or 0) + 1,
        is_published=False,
        owner=teacher,
    )
    try:
        path.save()
    except IntegrityError as exc:
        raise DomainError("Ya existe una ruta con ese nombre.") from exc
    return _detail(path)


def path_detail(teacher, path_id) -> dict[str, object]:
    return _detail(_owned(teacher, path_id))


def update_path(teacher, path_id, data: dict) -> dict[str, object]:
    path = _owned(teacher, path_id)
    if "name" in data:
        path.name = clean_label(data.get("name"), field="El nombre", limit=120, required=True)
    if "description" in data:
        path.description = _description(data.get("description"))
    if "is_published" in data:
        published = data.get("is_published")
        if not isinstance(published, bool):
            raise DomainError("Indica si la ruta está publicada.")
        path.is_published = published
    try:
        path.save()
    except IntegrityError as exc:
        raise DomainError("Ya existe una ruta con ese nombre.") from exc
    return _detail(path)


def delete_path(teacher, path_id) -> None:
    _owned(teacher, path_id).delete()


def _uuid_list(values: object, *, message: str) -> list[uuid.UUID]:
    if not isinstance(values, list):
        raise DomainError(message)
    found: list[uuid.UUID] = []
    for item in values:
        if not isinstance(item, str):
            raise DomainError(message)
        try:
            found.append(uuid.UUID(item))
        except ValueError as exc:
            raise DomainError(message) from exc
    if len(found) != len(set(found)):
        raise DomainError("Hay un elemento repetido.")
    if len(found) > 60:
        raise DomainError("La ruta tiene demasiados retos.")
    return found


@transaction.atomic
def set_challenges(teacher, path_id, challenge_ids: object) -> dict[str, object]:
    path = LearningPath.objects.select_for_update().get(pk=_owned(teacher, path_id).pk)
    ids = _uuid_list(challenge_ids, message=_MISSING_CHALLENGE)
    allowed = set(_placeable(teacher).filter(pk__in=ids).values_list("pk", flat=True))
    if set(ids) != allowed:
        raise DomainError(_MISSING_CHALLENGE)
    kept = {
        entry.challenge_id: (entry.opens_at, entry.closes_at, entry.withdrawn)
        for entry in path.entries.all()
    }
    path.entries.all().delete()
    rows = []
    for index, challenge_id in enumerate(ids, start=1):
        opens_at, closes_at, withdrawn = kept.get(challenge_id, (None, None, False))
        rows.append(
            PathEntry(
                path=path,
                challenge_id=challenge_id,
                position=index,
                opens_at=opens_at,
                closes_at=closes_at,
                withdrawn=withdrawn,
            )
        )
    PathEntry.objects.bulk_create(rows)
    return _detail(path)


def _moment(value: object, field: str):
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise DomainError(f"{field} no es válida.")
    parsed = parse_datetime(value)
    if parsed is None:
        raise DomainError(f"{field} no es válida.")
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


@transaction.atomic
def update_entry(teacher, path_id, challenge_id, data: dict) -> dict[str, object]:
    path = LearningPath.objects.select_for_update().get(pk=_owned(teacher, path_id).pk)
    try:
        entry = path.entries.get(challenge_id=challenge_id)
    except (PathEntry.DoesNotExist, ValueError, TypeError, ValidationError) as exc:
        raise DomainError(_MISSING_CHALLENGE, code=NOT_FOUND, status_code=404) from exc
    if "opens_at" in data:
        entry.opens_at = _moment(data.get("opens_at"), "La fecha de inicio")
    if "closes_at" in data:
        entry.closes_at = _moment(data.get("closes_at"), "La fecha de término")
    if "withdrawn" in data:
        withdrawn = data.get("withdrawn")
        if not isinstance(withdrawn, bool):
            raise DomainError("Indica si el reto está retirado.")
        entry.withdrawn = withdrawn
    if entry.opens_at is not None and entry.closes_at is not None and entry.opens_at >= entry.closes_at:
        raise DomainError("El inicio tiene que ser anterior al término.")
    entry.save()
    return _detail(path)


def _student_ids(values: object) -> list[int]:
    if not isinstance(values, list):
        raise DomainError("La lista de alumnos no es válida.")
    found: list[int] = []
    for item in values:
        if isinstance(item, bool) or not isinstance(item, int):
            raise DomainError("El alumno no es válido.")
        found.append(item)
    if len(found) != len(set(found)):
        raise DomainError("Hay un alumno repetido.")
    return found


@transaction.atomic
def set_assignments(
    teacher, path_id, community_ids: object, student_ids: object
) -> dict[str, object]:
    path = LearningPath.objects.select_for_update().get(pk=_owned(teacher, path_id).pk)
    community_keys = _uuid_list(community_ids, message="No se encontró la comunidad.")
    people = _student_ids(student_ids)
    communities = list(Community.objects.filter(pk__in=community_keys, owner=teacher))
    if len(communities) != len(community_keys):
        raise DomainError("No se encontró la comunidad.", code=NOT_FOUND, status_code=404)
    students = list(
        get_user_model().objects.select_related("profile").filter(pk__in=people)
    )
    if len(students) != len(people):
        raise DomainError("No se encontró al alumno.", code=NOT_FOUND, status_code=404)
    member_ids = set(
        Membership.objects.filter(community__owner=teacher, user_id__in=people).values_list(
            "user_id", flat=True
        )
    )
    for student in students:
        if student.profile.role != Profile.STUDENT or student.pk not in member_ids:
            raise DomainError(
                "Ese alumno no está en una comunidad tuya.",
                code=NOT_FOUND,
                status_code=404,
            )
    path.assignments.all().delete()
    PathAssignment.objects.bulk_create(
        [PathAssignment(path=path, community=community) for community in communities]
        + [PathAssignment(path=path, student=student) for student in students]
    )
    if communities or students:
        path.is_published = True
        path.save(update_fields=["is_published", "updated_at"])
    return _detail(path)


def _block(value: object, field: str, limit: int, *, required: bool) -> str:
    if value is None or value == "":
        if required:
            raise DomainError(f"Falta {field}.")
        return ""
    if not isinstance(value, str):
        raise DomainError(f"{field} no es válido.")
    text = value.strip()
    if required and not text:
        raise DomainError(f"Falta {field}.")
    if any(ord(char) < 32 and char not in "\n\t" for char in text):
        raise DomainError(f"{field} contiene caracteres de control.")
    if len(text) > limit:
        raise DomainError(f"{field} es demasiado largo.")
    return text


def _whole(value: object, field: str, low: int, high: int, *, default: int | None = None) -> int | None:
    if value is None or value == "":
        if default is None:
            return None
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        raise DomainError(f"{field} no es válido.")
    if value < low or value > high:
        raise DomainError(f"{field} no es válido.")
    return value


def _phrases(value: object, field: str, *, minimum: int) -> list[str]:
    if not isinstance(value, list):
        raise DomainError(f"{field} no es válido.")
    rows: list[str] = []
    for item in value:
        text = _block(item, field, 240, required=True)
        rows.append(text)
    if len(rows) < minimum:
        raise DomainError(f"{field} necesita al menos {minimum}.")
    if len(rows) > 12:
        raise DomainError(f"{field} tiene demasiados elementos.")
    return rows


def _bank(teacher) -> LearningPath:
    found = LearningPath.objects.filter(owner=teacher, is_bank=True).first()
    if found is not None:
        return found
    last = (
        LearningPath.objects.select_for_update()
        .order_by("-position")
        .values_list("position", flat=True)
        .first()
    )
    try:
        return LearningPath.objects.create(
            name=f"banco interno {teacher.pk}",
            description="",
            position=(last or 0) + 1,
            is_published=True,
            is_bank=True,
            owner=teacher,
        )
    except IntegrityError:
        again = LearningPath.objects.filter(owner=teacher, is_bank=True).first()
        if again is None:
            raise
        return again


def _concept(value: object) -> Concept:
    if not isinstance(value, str) or not value:
        raise DomainError("Elige un concepto.")
    try:
        return Concept.objects.get(pk=value)
    except Concept.DoesNotExist as exc:
        raise DomainError("Elige un concepto.") from exc


def _unit_for(teacher, concept: Concept) -> LearningUnit:
    path = _bank(teacher)
    found = path.units.filter(concept=concept).first()
    if found is not None:
        return found
    last = path.units.order_by("-position").values_list("position", flat=True).first()
    return LearningUnit.objects.create(
        path=path,
        title=concept.name,
        concept=concept,
        position=(last or 0) + 1,
    )


def _activity(value: object) -> str:
    if value not in Challenge.ACTIVITY_TYPES:
        raise DomainError("Elige el tipo de reto.")
    return value


def _output(value: object) -> str:
    text = _block(value, "La salida esperada", 4000, required=True)
    if not text.endswith("\n"):
        text += "\n"
    return text


def _inputs(value: object) -> list[str]:
    if value is None or value == "":
        return []
    if not isinstance(value, list):
        raise DomainError("Las entradas no son válidas.")
    rows = [_block(item, "Las entradas", 240, required=True) for item in value]
    if len(rows) > 12:
        raise DomainError("Las entradas tienen demasiados elementos.")
    return rows


def _body(data: dict) -> tuple[str, dict[str, object], list[ChallengeTestCase]]:
    activity = _activity(data.get("activity_type"))
    restrictions: dict[str, object]
    cases: list[ChallengeTestCase] = []
    if activity == Challenge.CLASSIFY:
        categories = _phrases(data.get("categories"), "Las categorías", minimum=2)
        raw_items = data.get("items")
        if not isinstance(raw_items, list):
            raise DomainError("Agrega las frases del reto.")
        items: list[dict[str, str]] = []
        for index, item in enumerate(raw_items, start=1):
            if not isinstance(item, dict):
                raise DomainError("Agrega las frases del reto.")
            text = _block(item.get("text"), "La frase", 240, required=True)
            category = item.get("category")
            if category not in categories:
                raise DomainError("Cada frase tiene que ir en una categoría.")
            items.append({"id": f"e{index}", "text": text, "category": str(category)})
        if len(items) < 2:
            raise DomainError("Las frases necesitan al menos 2.")
        if len(items) > 12:
            raise DomainError("Las frases tienen demasiados elementos.")
        restrictions = {"categories": categories, "items": items}
    elif activity == Challenge.ORDER:
        texts = _phrases(data.get("items"), "Las instrucciones", minimum=2)
        items = [{"id": f"e{index}", "text": text} for index, text in enumerate(texts, start=1)]
        restrictions = {"items": items, "solution": [item["id"] for item in items]}
    elif activity == Challenge.BUILD:
        question = _block(data.get("question"), "La pregunta", 240, required=True)
        accepted = _phrases(data.get("accepted"), "Las respuestas", minimum=1)
        restrictions = {"question": question, "accepted": accepted, "tools": _tools(data)}
        cases.extend(_cases(data))
    else:
        question = _block(data.get("question"), "La pregunta", 240, required=True)
        accepted = _phrases(data.get("accepted"), "Las respuestas", minimum=1)
        source = _block(data.get("source"), "El pseudocódigo", 8000, required=True)
        imported = workspace_from_source(source)
        errors = [item for item in imported.diagnostics if item.severity == "error"]
        if errors:
            raise DomainError(errors[0].message)
        restrictions = {
            "question": question,
            "accepted": accepted,
            "source": source,
            "starter": imported.workspace,
        }
    return activity, restrictions, cases


_TOOL_BLOCKS = frozenset(
    {
        "traza_definir",
        "traza_asignar",
        "traza_variable",
        "traza_leer",
        "traza_escribir",
        "traza_borrar_pantalla",
        "traza_esperar",
        "traza_unir",
        "traza_entero",
        "traza_real",
        "traza_cadena",
        "traza_caracter",
        "traza_logico",
        "traza_aritmetica",
        "traza_relacional",
        "traza_logica",
        "traza_no",
        "traza_si",
        "traza_si_sino",
        "traza_segun",
        "traza_mientras",
        "traza_para",
        "traza_repetir",
        "traza_dimension",
        "traza_indice",
        "traza_asignar_indice",
        "traza_leer_indice",
        "traza_funcion",
        "traza_procedimiento",
        "traza_llamada",
        "traza_llamar",
    }
)


_TOOL_ORDER = ("codigo", "diagrama", "bloques")


def _tools(data: dict) -> list[str]:
    raw = data.get("tools")
    if raw is None:
        return ["bloques"]
    if not isinstance(raw, list):
        raise DomainError("Las herramientas no son válidas.")
    if any(not isinstance(item, str) or item not in _TOOL_ORDER for item in raw):
        raise DomainError("Hay una herramienta que no existe.")
    chosen = [name for name in _TOOL_ORDER if name in raw]
    if not chosen:
        raise DomainError("Elige al menos una herramienta.")
    return chosen


def _cases(data: dict) -> list[ChallengeTestCase]:
    raw = data.get("cases")
    if raw is None:
        return [
            ChallengeTestCase(
                name="esperado",
                inputs=_inputs(data.get("inputs")),
                expected_output=_output(data.get("expected_output")),
                kind=ChallengeTestCase.NORMAL,
                position=1,
            )
        ]
    if not isinstance(raw, list) or not raw:
        raise DomainError("Agrega al menos un caso con su salida esperada.")
    if len(raw) > 6:
        raise DomainError("Puedes agregar hasta 6 casos.")
    cases: list[ChallengeTestCase] = []
    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise DomainError("Agrega al menos un caso con su salida esperada.")
        cases.append(
            ChallengeTestCase(
                name=f"Caso {index}",
                inputs=_inputs(item.get("inputs")),
                expected_output=_output(item.get("expected_output")),
                kind=ChallengeTestCase.NORMAL,
                position=index,
            )
        )
    return cases


def _allowed_blocks(data: dict, activity: str) -> list[str]:
    if activity != Challenge.BUILD:
        return []
    raw = data.get("allowed_blocks")
    if raw is None or raw == "":
        return []
    if not isinstance(raw, list):
        raise DomainError("Los bloques no son válidos.")
    chosen: list[str] = []
    for item in raw:
        if not isinstance(item, str) or item not in _TOOL_BLOCKS:
            raise DomainError("Hay un bloque que no existe.")
        if item not in chosen:
            chosen.append(item)
    return chosen


def _hint_bodies(data: dict) -> list[str]:
    raw = data.get("hints")
    if raw is None:
        single = _block(data.get("hint", ""), "La pista", 500, required=False)
        return [single] if single else []
    if not isinstance(raw, list):
        raise DomainError("Las pistas no son válidas.")
    bodies = [_block(item, "La pista", 500, required=False) for item in raw]
    bodies = [body for body in bodies if body]
    if len(bodies) > 5:
        raise DomainError("Puedes agregar hasta 5 pistas.")
    return bodies


def _apply_content(challenge: Challenge, data: dict) -> None:
    activity, restrictions, cases = _body(data)
    challenge.activity_type = activity
    challenge.restrictions = restrictions
    challenge.allowed_blocks = _allowed_blocks(data, activity)
    challenge.test_cases.all().delete()
    for case in cases:
        case.challenge = challenge
    if cases:
        ChallengeTestCase.objects.bulk_create(cases)
    _sync_hints(challenge, _hint_bodies(data))
    challenge.save(update_fields=["activity_type", "restrictions", "allowed_blocks", "updated_at"])


def _sync_hints(challenge: Challenge, bodies: list[str]) -> None:
    existing = {(hint.level, hint.position): hint for hint in challenge.hints.all()}
    used = set(HintUsage.objects.filter(hint__challenge=challenge).values_list("hint_id", flat=True))
    kept: set = set()
    for index, body in enumerate(bodies, start=1):
        hint = existing.get((index, 1))
        if hint is None:
            hint = Hint.objects.create(challenge=challenge, level=index, body=body, position=1)
        elif hint.body != body:
            hint.body = body
            hint.save(update_fields=["body"])
        kept.add(hint.id)
    for hint in existing.values():
        if hint.id in kept:
            continue
        if hint.id in used:
            raise DomainError("Un alumno ya pidió una pista que estás quitando.")
        hint.delete()


def _draft(challenge: Challenge) -> dict[str, object]:
    restrictions = challenge.restrictions if isinstance(challenge.restrictions, dict) else {}
    raw_items = restrictions.get("items")
    rows = [item for item in raw_items if isinstance(item, dict)] if isinstance(raw_items, list) else []
    if challenge.activity_type == Challenge.ORDER:
        by_id = {str(item.get("id")): str(item.get("text", "")) for item in rows}
        solution = restrictions.get("solution")
        ordered = solution if isinstance(solution, list) else []
        rows = [{"text": by_id.get(str(item_id), ""), "category": ""} for item_id in ordered]
    stored_cases = list(challenge.test_cases.order_by("position"))
    case = stored_cases[0] if stored_cases else None
    source = restrictions.get("source")
    if not isinstance(source, str):
        starter = restrictions.get("starter")
        source = adapt_workspace(starter).source if isinstance(starter, dict) else ""
    hints = list(challenge.hints.order_by("level", "position").values_list("body", flat=True))
    categories = restrictions.get("categories")
    accepted = restrictions.get("accepted")
    tools = restrictions.get("tools")
    return {
        "id": str(challenge.id),
        "title": challenge.title,
        "prompt": challenge.prompt,
        "activity_type": challenge.activity_type,
        "concept": challenge.unit.concept_id,
        "difficulty": challenge.difficulty,
        "points": challenge.points,
        "time_limit_seconds": challenge.time_limit_seconds,
        "owned": True,
        "categories": categories if isinstance(categories, list) else [],
        "items": [
            {
                "text": item.get("text", ""),
                "category": item.get("category", ""),
            }
            for item in rows
        ],
        "question": restrictions.get("question") or "",
        "accepted": accepted if isinstance(accepted, list) else [],
        "inputs": [] if case is None else list(case.inputs),
        "expected_output": "" if case is None else case.expected_output,
        "cases": [
            {
                "name": item.name,
                "inputs": list(item.inputs),
                "expected_output": item.expected_output,
            }
            for item in stored_cases
        ],
        "tools": tools if isinstance(tools, list) else [],
        "source": source,
        "hint": hints[0] if hints else "",
        "hints": hints,
        "allowed_blocks": list(challenge.allowed_blocks),
    }


def _editable_challenge(teacher, challenge_id) -> Challenge:
    """Reto del banco del docente o del banco compartido."""
    _require_teacher(teacher)
    try:
        challenge = Challenge.objects.select_related("unit__path", "unit__concept").get(
            pk=challenge_id,
            is_published=True,
        )
    except (Challenge.DoesNotExist, ValueError, TypeError, ValidationError) as exc:
        raise DomainError("No se encontró el reto.", code=NOT_FOUND, status_code=404) from exc
    path = challenge.unit.path
    mine = path.is_bank and path.owner_id == teacher.id
    shared = path.is_bank and path.owner_id is None and path.name == BANK_NAME
    if not mine and not shared:
        raise DomainError("No se encontró el reto.", code=NOT_FOUND, status_code=404)
    return challenge


def _unit_on(path: LearningPath, concept: Concept) -> LearningUnit:
    found = path.units.filter(concept=concept).first()
    if found is not None:
        return found
    last = path.units.order_by("-position").values_list("position", flat=True).first()
    return LearningUnit.objects.create(
        path=path,
        title=concept.name,
        concept=concept,
        position=(last or 0) + 1,
    )


def _fill(
    challenge: Challenge,
    teacher,
    data: dict,
    keep_path: LearningPath | None = None,
) -> None:
    challenge.title = clean_label(data.get("title"), field="El título", limit=120, required=True)
    challenge.prompt = _block(data.get("prompt"), "El enunciado", 4000, required=True)
    concept = _concept(data.get("concept"))
    difficulty = _whole(data.get("difficulty"), "La dificultad", 1, 5, default=1)
    points = _whole(data.get("points"), "Los puntos", 1, 500, default=10)
    limit = _whole(data.get("time_limit_seconds"), "El tiempo", 1, 86400)
    assert difficulty is not None and points is not None
    unit = _unit_for(teacher, concept) if keep_path is None else _unit_on(keep_path, concept)
    if challenge.unit_id != unit.id:
        last = unit.challenges.order_by("-position").values_list("position", flat=True).first()
        challenge.position = (last or 0) + 1
        challenge.unit = unit
    challenge.difficulty = difficulty
    challenge.points = points
    challenge.time_limit_seconds = limit
    challenge.is_published = True


@transaction.atomic
def create_challenge(teacher, data: dict) -> dict[str, object]:
    _require_teacher(teacher)
    if not isinstance(data, dict):
        raise DomainError("El reto no es válido.")
    challenge = Challenge(position=1, activity_type=_activity(data.get("activity_type")))
    _fill(challenge, teacher, data)
    try:
        challenge.save()
    except IntegrityError as exc:
        raise DomainError("Ya existe un reto con ese título.") from exc
    _apply_content(challenge, data)
    return _draft(challenge)


@transaction.atomic
def update_challenge(teacher, challenge_id, data: dict) -> dict[str, object]:
    if not isinstance(data, dict):
        raise DomainError("El reto no es válido.")
    challenge = _editable_challenge(teacher, challenge_id)
    shared = challenge.unit.path
    _fill(challenge, teacher, data, keep_path=shared if shared.owner_id is None else None)
    try:
        challenge.save()
    except IntegrityError as exc:
        raise DomainError("Ya existe un reto con ese título.") from exc
    _apply_content(challenge, data)
    return _draft(challenge)


def read_challenge(teacher, challenge_id) -> dict[str, object]:
    return _draft(_editable_challenge(teacher, challenge_id))


@transaction.atomic
def delete_challenge(teacher, challenge_id) -> None:
    """Quita el reto del banco. Si ya hay intentos, lo oculta y lo saca de las rutas."""
    challenge = _editable_challenge(teacher, challenge_id)
    if ChallengeAttempt.objects.filter(challenge=challenge).exists():
        PathEntry.objects.filter(challenge=challenge).delete()
        challenge.is_published = False
        challenge.save(update_fields=["is_published", "updated_at"])
        return
    challenge.delete()
