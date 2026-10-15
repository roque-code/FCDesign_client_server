"""El laboratorio ejecuta el árbol. El texto solo se compara."""

import random
import time

from language_core.ast_nodes import Program, dump
from language_core.block_adapter import adapt_workspace
from language_core.debugger import open_program
from language_core.grammar import STRICT
from language_core.interpreter import Interpreter, compile_source, execute_source
from language_core.runtime import Cancellation, Limits

SOURCE = """Algoritmo Laboratorio
    Definir precio Como Entero;
    precio <- 10;
    Escribir precio;
FinAlgoritmo
"""

LOOP = """Algoritmo P
    Definir n Como Entero;
    n <- 1;
    Mientras n > 0 Hacer
        n <- n + 1;
    FinMientras
FinAlgoritmo
"""


def _workspace() -> dict[str, object]:
    return {
        "blocks": {
            "languageVersion": 0,
            "blocks": [
                {
                    "type": "traza_definir",
                    "id": "d1",
                    "fields": {"NOMBRE": "precio", "TIPO": "entero"},
                    "next": {
                        "block": {
                            "type": "traza_asignar",
                            "id": "a1",
                            "fields": {"NOMBRE": "precio"},
                            "inputs": {
                                "VALOR": {
                                    "block": {
                                        "type": "traza_entero",
                                        "id": "n1",
                                        "fields": {"VALOR": 10},
                                    }
                                }
                            },
                            "next": {
                                "block": {
                                    "type": "traza_escribir",
                                    "id": "e1",
                                    "inputs": {
                                        "VALOR": {
                                            "block": {
                                                "type": "traza_variable",
                                                "id": "v1",
                                                "fields": {"NOMBRE": "precio", "TIPO": "entero"},
                                            }
                                        }
                                    },
                                }
                            },
                        }
                    },
                }
            ],
        }
    }


def _trace(program: Program, source: str) -> list[tuple[str, object]]:
    interpreter = Interpreter(
        program,
        source,
        STRICT,
        Limits.from_profile(STRICT),
        Cancellation(),
        time.monotonic,
        random.Random(0),
    )
    rows: list[tuple[str, object]] = []
    step = interpreter.run()
    try:
        while True:
            event = next(step)
            if event.kind == "line":
                rows.append(("line", event.line))
            elif event.kind == "output":
                rows.append(("output", event.payload.get("text")))
            elif event.kind in ("finished", "error", "cancelled"):
                rows.append((event.kind, event.line))
    except StopIteration:
        return rows
    return rows


def test_block_program_matches_the_example_events() -> None:
    adapted = adapt_workspace(_workspace())
    assert isinstance(adapted.program, Program)
    assert adapted.source == SOURCE
    compiled = compile_source(SOURCE)
    assert isinstance(compiled.program, Program)
    assert dump(compiled.program) == dump(adapted.program)
    assert _trace(adapted.program, adapted.source) == _trace(compiled.program, SOURCE)
    assert execute_source(SOURCE).output == "10\n"


def test_assignment_binding_lands_on_the_line_event() -> None:
    adapted = adapt_workspace(_workspace())
    assert isinstance(adapted.program, Program)
    assign = next(item for item in adapted.bindings if item.block_id == "a1")
    rows = _trace(adapted.program, adapted.source)
    assert ("line", assign.line) in rows
    session = open_program(adapted.program, "esto no es el programa", adapted.diagnostics)
    assert session.status == "paused"
    assert session.line == 2
    session.command("step")
    assert session.line == assign.line
    session.command("continue")
    assert session.status == "completed"
    assert session.snapshot()["output"] == "10\n"
    names = {event["event"] for event in session.events}
    assert "paused" in names
    assert "output" in names
    assert "finished" in names
    assert names <= {
        "paused",
        "output",
        "input_requested",
        "input_rejected",
        "warning",
        "error",
        "cancelled",
        "finished",
        "call",
        "return",
    }


def test_open_program_refuses_semantic_errors() -> None:
    adapted = adapt_workspace(
        {
            "blocks": {
                "blocks": [
                    {
                        "type": "traza_asignar",
                        "id": "a1",
                        "fields": {"NOMBRE": "precio"},
                        "inputs": {
                            "VALOR": {
                                "block": {
                                    "type": "traza_entero",
                                    "id": "n1",
                                    "fields": {"VALOR": 1},
                                }
                            }
                        },
                    }
                ]
            }
        }
    )
    session = open_program(adapted.program, adapted.source, adapted.diagnostics)
    assert session.interpreter is None
    assert session.status == "error"
    assert any(item.code == "E0301" for item in session.diagnostics)


def test_blocks_run_the_false_branch_and_skip_a_while() -> None:
    false_branch = {
        "blocks": {
            "languageVersion": 0,
            "blocks": [
                {
                    "type": "traza_definir",
                    "id": "d",
                    "fields": {"NOMBRE": "n", "TIPO": "entero"},
                    "next": {
                        "block": {
                            "type": "traza_asignar",
                            "id": "a",
                            "fields": {"NOMBRE": "n"},
                            "inputs": {
                                "VALOR": {
                                    "block": {
                                        "type": "traza_entero",
                                        "id": "z",
                                        "fields": {"VALOR": 0},
                                    }
                                }
                            },
                            "next": {
                                "block": {
                                    "type": "traza_si_sino",
                                    "id": "si",
                                    "inputs": {
                                        "CONDICION": {
                                            "block": {
                                                "type": "traza_relacional",
                                                "id": "c",
                                                "fields": {"OPERADOR": "gt"},
                                                "inputs": {
                                                    "IZQUIERDA": {
                                                        "block": {
                                                            "type": "traza_variable",
                                                            "id": "vn",
                                                            "fields": {
                                                                "NOMBRE": "n",
                                                                "TIPO": "entero",
                                                            },
                                                        }
                                                    },
                                                    "DERECHA": {
                                                        "block": {
                                                            "type": "traza_entero",
                                                            "id": "cero",
                                                            "fields": {"VALOR": 0},
                                                        }
                                                    },
                                                },
                                            }
                                        },
                                        "ENTONCES": {
                                            "block": {
                                                "type": "traza_escribir",
                                                "id": "ep",
                                                "inputs": {
                                                    "VALOR": {
                                                        "block": {
                                                            "type": "traza_cadena",
                                                            "id": "tp",
                                                            "fields": {"VALOR": "positivo"},
                                                        }
                                                    }
                                                },
                                            }
                                        },
                                        "SINO": {
                                            "block": {
                                                "type": "traza_escribir",
                                                "id": "ec",
                                                "inputs": {
                                                    "VALOR": {
                                                        "block": {
                                                            "type": "traza_cadena",
                                                            "id": "tc",
                                                            "fields": {"VALOR": "cero"},
                                                        }
                                                    }
                                                },
                                            }
                                        },
                                    },
                                }
                            },
                        }
                    },
                }
            ],
        }
    }
    skipped = {
        "blocks": {
            "languageVersion": 0,
            "blocks": [
                {
                    "type": "traza_definir",
                    "id": "d",
                    "fields": {"NOMBRE": "n", "TIPO": "entero"},
                    "next": {
                        "block": {
                            "type": "traza_asignar",
                            "id": "a",
                            "fields": {"NOMBRE": "n"},
                            "inputs": {
                                "VALOR": {
                                    "block": {
                                        "type": "traza_entero",
                                        "id": "z",
                                        "fields": {"VALOR": 0},
                                    }
                                }
                            },
                            "next": {
                                "block": {
                                    "type": "traza_mientras",
                                    "id": "ciclo",
                                    "inputs": {
                                        "CONDICION": {
                                            "block": {
                                                "type": "traza_relacional",
                                                "id": "c",
                                                "fields": {"OPERADOR": "gt"},
                                                "inputs": {
                                                    "IZQUIERDA": {
                                                        "block": {
                                                            "type": "traza_variable",
                                                            "id": "vn",
                                                            "fields": {
                                                                "NOMBRE": "n",
                                                                "TIPO": "entero",
                                                            },
                                                        }
                                                    },
                                                    "DERECHA": {
                                                        "block": {
                                                            "type": "traza_entero",
                                                            "id": "cero",
                                                            "fields": {"VALOR": 0},
                                                        }
                                                    },
                                                },
                                            }
                                        },
                                        "CUERPO": {
                                            "block": {
                                                "type": "traza_escribir",
                                                "id": "e",
                                                "inputs": {
                                                    "VALOR": {
                                                        "block": {
                                                            "type": "traza_cadena",
                                                            "id": "t",
                                                            "fields": {"VALOR": "entra"},
                                                        }
                                                    }
                                                },
                                            }
                                        },
                                    },
                                    "next": {
                                        "block": {
                                            "type": "traza_escribir",
                                            "id": "fin",
                                            "inputs": {
                                                "VALOR": {
                                                    "block": {
                                                        "type": "traza_variable",
                                                        "id": "vo",
                                                        "fields": {"NOMBRE": "n", "TIPO": "entero"},
                                                    }
                                                }
                                            },
                                        }
                                    },
                                }
                            },
                        }
                    },
                }
            ],
        }
    }
    false_program = adapt_workspace(false_branch)
    assert isinstance(false_program.program, Program)
    assert execute_source(false_program.source).output == "cero\n"
    skip_program = adapt_workspace(skipped)
    assert isinstance(skip_program.program, Program)
    assert execute_source(skip_program.source).output == "0\n"
    session = open_program(skip_program.program, skip_program.source, skip_program.diagnostics)
    session.command("continue")
    assert session.status == "completed"
    assert session.snapshot()["output"] == "0\n"


def test_a_block_while_that_does_not_finish_is_cut() -> None:
    spinning = {
        "blocks": {
            "languageVersion": 0,
            "blocks": [
                {
                    "type": "traza_definir",
                    "id": "d",
                    "fields": {"NOMBRE": "n", "TIPO": "entero"},
                    "next": {
                        "block": {
                            "type": "traza_asignar",
                            "id": "a",
                            "fields": {"NOMBRE": "n"},
                            "inputs": {
                                "VALOR": {
                                    "block": {
                                        "type": "traza_entero",
                                        "id": "uno",
                                        "fields": {"VALOR": 1},
                                    }
                                }
                            },
                            "next": {
                                "block": {
                                    "type": "traza_mientras",
                                    "id": "ciclo",
                                    "inputs": {
                                        "CONDICION": {
                                            "block": {
                                                "type": "traza_relacional",
                                                "id": "c",
                                                "fields": {"OPERADOR": "gt"},
                                                "inputs": {
                                                    "IZQUIERDA": {
                                                        "block": {
                                                            "type": "traza_variable",
                                                            "id": "vn",
                                                            "fields": {
                                                                "NOMBRE": "n",
                                                                "TIPO": "entero",
                                                            },
                                                        }
                                                    },
                                                    "DERECHA": {
                                                        "block": {
                                                            "type": "traza_entero",
                                                            "id": "cero",
                                                            "fields": {"VALOR": 0},
                                                        }
                                                    },
                                                },
                                            }
                                        },
                                        "CUERPO": {
                                            "block": {
                                                "type": "traza_asignar",
                                                "id": "suma",
                                                "fields": {"NOMBRE": "n"},
                                                "inputs": {
                                                    "VALOR": {
                                                        "block": {
                                                            "type": "traza_aritmetica",
                                                            "id": "op",
                                                            "fields": {"OPERADOR": "add"},
                                                            "inputs": {
                                                                "IZQUIERDA": {
                                                                    "block": {
                                                                        "type": "traza_variable",
                                                                        "id": "vn2",
                                                                        "fields": {
                                                                            "NOMBRE": "n",
                                                                            "TIPO": "entero",
                                                                        },
                                                                    }
                                                                },
                                                                "DERECHA": {
                                                                    "block": {
                                                                        "type": "traza_entero",
                                                                        "id": "paso",
                                                                        "fields": {"VALOR": 1},
                                                                    }
                                                                },
                                                            },
                                                        }
                                                    }
                                                },
                                            }
                                        },
                                    },
                                }
                            },
                        }
                    },
                }
            ],
        }
    }
    adapted = adapt_workspace(spinning)
    assert isinstance(adapted.program, Program)
    session = open_program(
        adapted.program,
        adapted.source,
        adapted.diagnostics,
        limits=Limits(max_instructions=30),
    )
    session.command("continue")
    assert session.status == "error"
    assert any(item.code == "E0410" for item in session.diagnostics)


def test_open_program_cuts_a_nonterminating_loop() -> None:
    compiled = compile_source(LOOP)
    assert compiled.program is not None
    session = open_program(
        compiled.program,
        LOOP,
        compiled.diagnostics,
        limits=Limits(max_instructions=30),
    )
    session.command("continue")
    assert session.status == "error"
    assert session.events[-1]["event"] == "error"
    assert any(item.code == "E0410" for item in session.diagnostics)
