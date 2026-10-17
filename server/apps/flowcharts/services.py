"""Caché del grafo. Las coordenadas las calcula el cliente."""

import hashlib

from apps.language.services import diagnostic_payload, profile_for_algorithm
from apps.projects.models import Algorithm
from language_core.flowchart import build
from language_core.interpreter import compile_source


def flowchart_payload(algorithm: Algorithm, *, persist: bool = True) -> dict[str, object]:
    profile, _config = profile_for_algorithm(algorithm)
    marker = f"{int(profile.require_semicolons)}\n{profile.index_base}"
    digest = hashlib.sha256(
        f"v4\n{algorithm.language_profile.key}\n{marker}\n{algorithm.source}".encode()
    ).hexdigest()
    cached = algorithm.flowchart
    if isinstance(cached, dict) and cached.get("source_hash") == digest:
        graph = cached.get("graph")
        diagnostics = cached.get("diagnostics")
        if isinstance(graph, dict) and isinstance(diagnostics, list):
            return {"graph": graph, "diagnostics": diagnostics}
    compiled = compile_source(algorithm.source, profile)
    diagnostics = [diagnostic_payload(item) for item in compiled.diagnostics]
    if compiled.program is None:
        if persist and algorithm.flowchart is not None:
            algorithm.flowchart = None
            algorithm.save(update_fields=["flowchart"])
        return {"graph": None, "diagnostics": diagnostics}
    graph = build(compiled.program).as_dict()
    if persist:
        algorithm.flowchart = {"source_hash": digest, "graph": graph, "diagnostics": diagnostics}
        algorithm.save(update_fields=["flowchart"])
    return {"graph": graph, "diagnostics": diagnostics}
