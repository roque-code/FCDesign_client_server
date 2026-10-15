"""Una ejecución se guarda con su consola. Las líneas del recorrido no."""

from dataclasses import asdict

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record
from apps.executions.live import (
    advance,
    feed,
    forget_user,
    peek,
    replace_session,
    signal_pause,
    signal_stop,
    store,
)
from apps.executions.models import Execution, ExecutionEvent
from apps.executions.runner import run_in_process
from apps.language.services import (
    core_profile_from_config,
    diagnostic_payload,
    profile_for_algorithm,
)
from apps.projects.services import create_version, get_algorithm
from config.errors import DomainError
from config.ratelimit import allow
from language_core.debugger import DebugRejected, open_debug
from language_core.diagnostics import Diagnostic
from language_core.runtime import Limits


def execution_payload(execution: Execution, diagnostics: list | None = None) -> dict[str, object]:
    output = "".join(
        execution.events.filter(kind="output").order_by("sequence").values_list("text", flat=True)
    )
    supplied = diagnostics is not None
    if diagnostics is None:
        diagnostics = [
            {
                "severity": "error",
                "code": event.code,
                "message": event.text,
                "line": event.line,
                "column": event.column,
                "suggestion": event.suggestion or None,
            }
            for event in execution.events.filter(kind="error").order_by("sequence")
        ]
    data: dict[str, object] = {
        "id": str(execution.id),
        "algorithm_id": str(execution.algorithm_id),
        "status": execution.status,
        "output": output,
        "instruction_count": execution.instruction_count,
        "version_number": execution.version_number,
        "pending_input": execution.pending_input,
        "diagnostics": diagnostics,
    }
    if settings.EXECUTION_RUNNER == "redis":
        from apps.executions.bus import fetch_state

        remote = fetch_state(str(execution.id))
        if remote is None:
            return data
        return _overlay(data, remote, supplied)
    live = peek(str(execution.id))
    if live is None:
        return data
    snap = live.session.snapshot()
    data["debug"] = live.interactive
    data["status"] = snap["status"]
    data["output"] = snap["output"]
    data["instruction_count"] = snap["instruction_count"]
    data["pending_input"] = snap["pending_input"]
    data["line"] = snap["line"]
    data["column"] = snap["column"]
    data["scope"] = snap["scope"]
    data["variables"] = snap["variables"]
    data["call_stack"] = snap["call_stack"]
    data["last_condition"] = snap["last_condition"]
    data["breakpoints"] = snap["breakpoints"]
    data["event_cursor"] = snap["event_cursor"]
    if not supplied:
        rows = snap["diagnostics"]
        if isinstance(rows, tuple):
            data["diagnostics"] = [
                diagnostic_payload(item)
                for item in rows
                if isinstance(item, Diagnostic) and item.severity in ("error", "warning")
            ]
    return data


def start_execution(user, algorithm_id, ip_address: str | None) -> tuple[Execution, list]:
    """Deja la ejecución en pausa para que la consola reciba cada fotograma.

    Borrar Pantalla y Esperar solo se ven si el cliente ya escucha el flujo
    antes de ordenar Continuar. Correr todo el programa aquí devolvería
    únicamente el último fotograma.
    """
    allow("execution.start", str(user.pk))
    _forget(user.pk, "editor")
    with transaction.atomic():
        algorithm = get_algorithm(user, algorithm_id)
        version = create_version(algorithm, user, "Ejecución")
        profile, config = profile_for_algorithm(algorithm)
        algorithm.profile_snapshot = config
        algorithm.save(update_fields=["profile_snapshot", "updated_at"])
        execution = Execution.objects.create(
            algorithm=algorithm,
            version_number=version.number,
            user=user,
            status="running",
            source=algorithm.source,
            profile_config=config,
            limits=asdict(Limits.from_profile(profile)),
        )
        record(
            "execution.start",
            actor=user,
            object_type="execution",
            object_id=str(execution.id),
            metadata={"algorithm_id": str(algorithm.id), "version": version.number},
            ip_address=ip_address,
        )
    if settings.EXECUTION_RUNNER == "redis":
        return _launch_remote(
            execution, user.pk, profile_config=config, breakpoints=set(), interactive=False
        )
    session = open_debug(execution.source, profile)
    store(str(execution.id), user.pk, session, interactive=False)
    _sync(execution, session)
    diagnostics = [diagnostic_payload(item) for item in session.diagnostics]
    return execution, diagnostics


@transaction.atomic
def submit_input(user, execution_id, text: object) -> tuple[Execution, list]:
    if not isinstance(text, str):
        raise DomainError("El dato no es válido.")
    try:
        execution = Execution.objects.select_related("algorithm").get(id=execution_id, user=user)
    except Execution.DoesNotExist as exc:
        raise DomainError(
            "No se encontró la ejecución.", code="not_found", status_code=404
        ) from exc
    if execution.status != "waiting_input":
        raise DomainError("Esta ejecución ya no espera datos.", code="conflict", status_code=409)
    limit = int(execution.limits.get("max_string_length", 100_000))
    if len(text) > limit:
        raise DomainError("El dato es demasiado largo.")
    previous = list(
        execution.events.filter(kind="input").order_by("sequence").values_list("text", flat=True)
    )
    stored_name = str(execution.profile_config.get("profile_key") or "strict")
    profile = core_profile_from_config(stored_name, execution.profile_config)
    if settings.EXECUTION_RUNNER == "redis":
        return _remote_input(execution, text)
    live = peek(str(execution.id))
    if live is not None:
        try:
            feed(live, text)
        except DebugRejected as exc:
            raise DomainError(exc.message, code="conflict", status_code=409) from exc
        _sync(execution, live.session)
        diagnostics = [diagnostic_payload(item) for item in live.session.diagnostics]
        return execution, diagnostics
    result, count = run_in_process(execution.source, previous + [text], profile)
    rejected = any(item.code == "E0406" and item.severity == "error" for item in result.diagnostics)
    accepted = previous if rejected else [*previous, text]
    diagnostics = [diagnostic_payload(item) for item in result.diagnostics]
    _apply(execution, result, count, accepted)
    return execution, diagnostics


def get_execution(user, execution_id) -> Execution:
    try:
        return Execution.objects.get(id=execution_id, user=user)
    except Execution.DoesNotExist as exc:
        raise DomainError(
            "No se encontró la ejecución.", code="not_found", status_code=404
        ) from exc


def start_debug(user, algorithm_id, breakpoints: set[int], ip_address: str | None):
    allow("execution.start", str(user.pk))
    _forget(user.pk, "editor")
    with transaction.atomic():
        algorithm = get_algorithm(user, algorithm_id)
        version = create_version(algorithm, user, "Depuración")
        profile, config = profile_for_algorithm(algorithm)
        algorithm.profile_snapshot = config
        algorithm.save(update_fields=["profile_snapshot", "updated_at"])
        execution = Execution.objects.create(
            algorithm=algorithm,
            version_number=version.number,
            user=user,
            status="running",
            source=algorithm.source,
            profile_config=config,
            limits=asdict(Limits.from_profile(profile)),
        )
        record(
            "execution.start",
            actor=user,
            object_type="execution",
            object_id=str(execution.id),
            metadata={"algorithm_id": str(algorithm.id), "version": version.number, "debug": True},
            ip_address=ip_address,
        )
    if settings.EXECUTION_RUNNER == "redis":
        return _launch_remote(
            execution, user.pk, profile_config=config, breakpoints=breakpoints, interactive=True
        )
    session = open_debug(execution.source, profile, breakpoints)
    store(str(execution.id), user.pk, session)
    _sync(execution, session)
    diagnostics = [diagnostic_payload(item) for item in session.diagnostics]
    return execution, diagnostics


def control_execution(user, execution_id, action: object, breakpoints: set[int] | None):
    if not isinstance(action, str) or action not in {
        "step",
        "step_in",
        "step_out",
        "continue",
        "pause",
        "stop",
        "restart",
        "breakpoints",
    }:
        raise DomainError("La orden no es válida.")
    execution = get_execution(user, execution_id)
    if settings.EXECUTION_RUNNER == "redis":
        return _remote_control(execution, action, breakpoints)
    live = peek(str(execution.id))
    if live is None:
        raise DomainError(
            "La sesión de depuración ya no está en memoria. Vuelve a depurar.",
            code="conflict",
            status_code=409,
        )
    if action == "pause":
        signal_pause(live)
        return execution, [diagnostic_payload(item) for item in live.session.diagnostics]
    if action == "stop":
        signal_stop(live)
    if action == "restart":
        profile = core_profile_from_config(
            str(execution.profile_config.get("profile_key") or "strict"),
            execution.profile_config,
        )
        marks = breakpoints if breakpoints is not None else set(live.session.breakpoints)
        session = open_debug(execution.source, profile, marks)
        replace_session(live, session)
        _sync(execution, session)
        return execution, [diagnostic_payload(item) for item in session.diagnostics]
    try:
        advance(live, action, breakpoints)
    except DebugRejected as exc:
        raise DomainError(exc.message, code="conflict", status_code=409) from exc
    _sync(execution, live.session)
    return execution, [diagnostic_payload(item) for item in live.session.diagnostics]


def inspect_array(user, execution_id, name: object, start: object, count: object) -> dict:
    if not isinstance(name, str) or not name:
        raise DomainError("El arreglo no es válido.")
    if isinstance(start, bool) or not isinstance(start, int) or start < 0:
        raise DomainError("El inicio del tramo no es válido.")
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise DomainError("El tamaño del tramo no es válido.")
    execution = get_execution(user, execution_id)
    if settings.EXECUTION_RUNNER == "redis":
        from apps.executions.bus import BusRejected, BusTimeout
        from apps.executions.bus import inspect as inspect_remote

        try:
            return inspect_remote(str(execution.id), name, start, count)
        except BusTimeout as exc:
            raise DomainError(exc.message, code="conflict", status_code=409) from exc
        except BusRejected as exc:
            raise DomainError(exc.message) from exc
    live = peek(str(execution.id))
    if live is None:
        raise DomainError(
            "La sesión de depuración ya no está en memoria. Vuelve a depurar.",
            code="conflict",
            status_code=409,
        )
    try:
        return live.session.inspect(name, start, count)
    except DebugRejected as exc:
        raise DomainError(exc.message) from exc


def breakpoint_set(value: object) -> set[int]:
    if value is None:
        return set()
    if not isinstance(value, list):
        raise DomainError("Los puntos de interrupción no son válidos.")
    lines: set[int] = set()
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int) or item < 1:
            raise DomainError("Los puntos de interrupción no son válidos.")
        lines.add(item)
    if len(lines) > 200:
        raise DomainError("Hay demasiados puntos de interrupción.")
    return lines


def _sync(execution: Execution, session) -> None:
    snap = session.snapshot()

    class _Result:
        status = snap["status"]
        output = snap["output"]
        diagnostics = snap["diagnostics"]
        pending_input = snap["pending_input"]

    _apply(execution, _Result(), int(snap["instruction_count"]), list(session.inputs))


def _apply(execution: Execution, result, count: int, inputs: list[str]) -> None:
    execution.status = result.status
    execution.instruction_count = count
    execution.pending_input = result.pending_input
    execution.finished_at = None if result.status in ("waiting_input", "paused") else timezone.now()
    execution.save(update_fields=["status", "instruction_count", "pending_input", "finished_at"])
    execution.events.all().delete()
    rows: list[ExecutionEvent] = []
    sequence = 1
    if result.output:
        rows.append(
            ExecutionEvent(
                execution=execution, sequence=sequence, kind="output", text=result.output
            )
        )
        sequence += 1
    for entered in inputs:
        rows.append(
            ExecutionEvent(execution=execution, sequence=sequence, kind="input", text=entered)
        )
        sequence += 1
    for item in result.diagnostics:
        if item.severity != "error":
            continue
        rows.append(
            ExecutionEvent(
                execution=execution,
                sequence=sequence,
                kind="error",
                text=item.message,
                line=item.span.start_line,
                column=item.span.start_col,
                code=item.code,
                suggestion=item.suggestion or "",
            )
        )
        sequence += 1
    rows.append(
        ExecutionEvent(execution=execution, sequence=sequence, kind="status", text=result.status)
    )
    ExecutionEvent.objects.bulk_create(rows)


def _forget(user_id: int, kind: str) -> None:
    if settings.EXECUTION_RUNNER == "redis":
        from apps.executions.bus import drop_kind

        drop_kind(user_id, kind)
    if kind == "editor":
        forget_user(user_id)


def _launch_remote(
    execution, user_id: int, *, profile_config, breakpoints: set[int], interactive: bool
):
    from apps.executions.bus import BusRejected, BusTimeout, launch

    try:
        remote = launch(
            user_id=user_id,
            source=execution.source,
            profile=profile_config,
            breakpoints=breakpoints,
            interactive=interactive,
            kind="editor",
            execution_id=str(execution.id),
        )
    except BusTimeout as exc:
        raise DomainError(exc.message, code="conflict", status_code=409) from exc
    except BusRejected as exc:
        raise DomainError(exc.message, code="conflict", status_code=409) from exc
    _sync_remote(execution, remote)
    diagnostics = remote.get("diagnostics")
    return execution, diagnostics if isinstance(diagnostics, list) else []


def _remote_input(execution: Execution, text: str):
    from apps.executions.bus import BusRejected, BusTimeout, command

    try:
        remote = command(str(execution.id), "input", text=text)
    except BusTimeout as exc:
        raise DomainError(exc.message, code="conflict", status_code=409) from exc
    except BusRejected as exc:
        raise DomainError(exc.message, code="conflict", status_code=409) from exc
    _sync_remote(execution, remote)
    diagnostics = remote.get("diagnostics")
    return execution, diagnostics if isinstance(diagnostics, list) else []


def _remote_control(execution: Execution, action: str, breakpoints: set[int] | None):
    from apps.executions.bus import BusRejected, BusTimeout, command, signal

    if action == "pause":
        signal(str(execution.id), "pause")
        return execution, []
    if action == "stop":
        signal(str(execution.id), "stop")
    fields: dict[str, object] = {}
    if breakpoints is not None:
        fields["breakpoints"] = sorted(breakpoints)
    try:
        remote = command(str(execution.id), action, **fields)
    except BusTimeout as exc:
        raise DomainError(exc.message, code="conflict", status_code=409) from exc
    except BusRejected as exc:
        raise DomainError(exc.message, code="conflict", status_code=409) from exc
    _sync_remote(execution, remote)
    diagnostics = remote.get("diagnostics")
    return execution, diagnostics if isinstance(diagnostics, list) else []


def _overlay(
    data: dict[str, object], remote: dict[str, object], supplied: bool
) -> dict[str, object]:
    data["debug"] = bool(remote.get("interactive"))
    data["status"] = remote.get("status")
    data["output"] = remote.get("output")
    data["instruction_count"] = remote.get("instruction_count")
    data["pending_input"] = remote.get("pending_input")
    data["line"] = remote.get("line")
    data["column"] = remote.get("column")
    data["scope"] = remote.get("scope")
    data["variables"] = remote.get("variables")
    data["call_stack"] = remote.get("call_stack")
    data["last_condition"] = remote.get("last_condition")
    data["breakpoints"] = remote.get("breakpoints")
    data["event_cursor"] = remote.get("event_cursor")
    if not supplied:
        rows = remote.get("diagnostics")
        if isinstance(rows, list):
            data["diagnostics"] = [
                item
                for item in rows
                if isinstance(item, dict) and item.get("severity") in ("error", "warning")
            ]
    return data


def _sync_remote(execution: Execution, remote: dict[str, object]) -> None:
    from runner.protocol import diagnostic_from_json

    rows = remote.get("diagnostics")
    notes = (
        [diagnostic_from_json(item) for item in rows if isinstance(item, dict)]
        if isinstance(rows, list)
        else []
    )
    entered = remote.get("inputs")
    accepted = (
        [item for item in entered if isinstance(item, str)] if isinstance(entered, list) else []
    )

    class _Result:
        status = remote.get("status")
        output = remote.get("output") if isinstance(remote.get("output"), str) else ""
        diagnostics = notes
        pending_input = remote.get("pending_input")

    count = remote.get("instruction_count")
    _apply(
        execution,
        _Result(),
        count if isinstance(count, int) else 0,
        accepted,
    )
