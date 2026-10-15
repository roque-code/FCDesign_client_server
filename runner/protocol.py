"""Claves y sobres JSON que comparten el proceso web y el runner."""

from __future__ import annotations

import json
from collections.abc import Mapping

from language_core.ast_nodes import SourceSpan
from language_core.diagnostics import Diagnostic, Severity

JOBS = "traza:jobs"
HEARTBEAT = "traza:hb"
TERMINAL_EVENTS = frozenset({"finished", "error", "cancelled"})
TERMINAL_STATUS = frozenset({"completed", "error", "cancelled", "timeout"})
STATE_TTL = 7200


def cmd_key(execution_id: str) -> str:
    return f"traza:cmd:{execution_id}"


def signal_key(execution_id: str) -> str:
    return f"traza:signal:{execution_id}"


def events_key(execution_id: str) -> str:
    return f"traza:events:{execution_id}"


def wake_key(execution_id: str) -> str:
    return f"traza:wake:{execution_id}"


def state_key(execution_id: str) -> str:
    return f"traza:state:{execution_id}"


def meta_key(execution_id: str) -> str:
    return f"traza:meta:{execution_id}"


def reply_key(token: str) -> str:
    return f"traza:reply:{token}"


def lock_key(execution_id: str) -> str:
    return f"traza:lock:{execution_id}"


def user_key(user_id: int, kind: str) -> str:
    return f"traza:user:{user_id}:{kind}"


def diagnostic_to_json(item: Diagnostic) -> dict[str, object]:
    return {
        "severity": item.severity,
        "code": item.code,
        "message": item.message,
        "line": item.span.start_line,
        "column": item.span.start_col,
        "end_line": item.span.end_line,
        "end_column": item.span.end_col,
        "snippet": item.snippet,
        "suggestion": item.suggestion,
    }


def diagnostic_from_json(data: Mapping[str, object]) -> Diagnostic:
    severity = data.get("severity")
    chosen: Severity = severity if severity in ("error", "warning", "info") else "error"
    line = data.get("line")
    column = data.get("column")
    end_line = data.get("end_line")
    end_column = data.get("end_column")
    suggestion = data.get("suggestion")
    snippet = data.get("snippet")
    return Diagnostic(
        severity=chosen,
        code=str(data.get("code") or ""),
        message=str(data.get("message") or ""),
        span=SourceSpan(
            start_line=line if isinstance(line, int) else 1,
            start_col=column if isinstance(column, int) else 1,
            end_line=end_line if isinstance(end_line, int) else 1,
            end_col=end_column if isinstance(end_column, int) else 1,
        ),
        snippet=snippet if isinstance(snippet, str) else "",
        suggestion=suggestion if isinstance(suggestion, str) else None,
    )


def event_for_wire(event: Mapping[str, object]) -> dict[str, object]:
    """Quita la consola acumulada. El cliente junta el texto nuevo de cada evento."""
    return {key: value for key, value in event.items() if key != "output"}


def sse_frame(event: Mapping[str, object], execution_id: str) -> str:
    payload = event_for_wire(event)
    payload.pop("id", None)
    payload["execution_id"] = execution_id
    data = json.dumps(payload, ensure_ascii=False)
    return f"id: {event['id']}\nevent: {event['event']}\ndata: {data}\n\n"
