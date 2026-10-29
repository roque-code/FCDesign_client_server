"""Ruta inicial. Es un dato: otra ruta sería otro registro, no otro módulo.

Los bloques de esta carga son los que el laboratorio ya ejecuta: Si, Mientras, Segun, Para, Repetir, arreglos y funciones.
"""

from __future__ import annotations


def _first(blocks: list[dict[str, object]]) -> dict[str, object]:
    for earlier, later in zip(blocks, blocks[1:], strict=False):
        earlier["next"] = {"block": later}
    return blocks[0]


def _chain(blocks: list[dict[str, object]]) -> dict[str, object]:
    return {"blocks": {"languageVersion": 0, "blocks": [_first(blocks)]}}


def _stacks(*tops: dict[str, object]) -> dict[str, object]:
    return {"blocks": {"languageVersion": 0, "blocks": list(tops)}}


def _definir(ident: str, name: str, type_name: str) -> dict[str, object]:
    return {
        "type": "traza_definir",
        "id": ident,
        "fields": {"NOMBRE": name, "TIPO": type_name},
    }


def _entero(ident: str, value: int) -> dict[str, object]:
    return {"type": "traza_entero", "id": ident, "fields": {"VALOR": value}}


def _variable(ident: str, name: str) -> dict[str, object]:
    return {
        "type": "traza_variable",
        "id": ident,
        "fields": {"NOMBRE": name, "TIPO": "entero"},
    }


def _asignar(ident: str, name: str, value: dict[str, object]) -> dict[str, object]:
    return {
        "type": "traza_asignar",
        "id": ident,
        "fields": {"NOMBRE": name},
        "inputs": {"VALOR": {"block": value}},
    }


def _escribir(ident: str, value: dict[str, object]) -> dict[str, object]:
    return {"type": "traza_escribir", "id": ident, "inputs": {"VALOR": {"block": value}}}


def _arit(
    ident: str, operator: str, left: dict[str, object], right: dict[str, object]
) -> dict[str, object]:
    return {
        "type": "traza_aritmetica",
        "id": ident,
        "fields": {"OPERADOR": operator},
        "inputs": {"IZQUIERDA": {"block": left}, "DERECHA": {"block": right}},
    }


def _cadena(ident: str, text: str) -> dict[str, object]:
    return {"type": "traza_cadena", "id": ident, "fields": {"VALOR": text}}


def _rel(
    ident: str, operator: str, left: dict[str, object], right: dict[str, object]
) -> dict[str, object]:
    return {
        "type": "traza_relacional",
        "id": ident,
        "fields": {"OPERADOR": operator},
        "inputs": {"IZQUIERDA": {"block": left}, "DERECHA": {"block": right}},
    }


def _si_sino(
    ident: str,
    condition: dict[str, object],
    then_block: dict[str, object],
    else_block: dict[str, object],
) -> dict[str, object]:
    return {
        "type": "traza_si_sino",
        "id": ident,
        "inputs": {
            "CONDICION": {"block": condition},
            "ENTONCES": {"block": then_block},
            "SINO": {"block": else_block},
        },
    }


def _mientras(
    ident: str, condition: dict[str, object], body: dict[str, object]
) -> dict[str, object]:
    return {
        "type": "traza_mientras",
        "id": ident,
        "inputs": {"CONDICION": {"block": condition}, "CUERPO": {"block": body}},
    }


def _segun(
    ident: str,
    selector: dict[str, object],
    first: tuple[dict[str, object], dict[str, object]],
    second: tuple[dict[str, object], dict[str, object]],
    default: dict[str, object],
) -> dict[str, object]:
    return {
        "type": "traza_segun",
        "id": ident,
        "inputs": {
            "VALOR": {"block": selector},
            "CASO1": {"block": first[0]},
            "HACER1": {"block": first[1]},
            "CASO2": {"block": second[0]},
            "HACER2": {"block": second[1]},
            "OTRO": {"block": default},
        },
    }


def _para(
    ident: str,
    name: str,
    start: dict[str, object],
    end: dict[str, object],
    step: dict[str, object],
    body: dict[str, object],
) -> dict[str, object]:
    return {
        "type": "traza_para",
        "id": ident,
        "fields": {"NOMBRE": name},
        "inputs": {
            "DESDE": {"block": start},
            "HASTA": {"block": end},
            "PASO": {"block": step},
            "CUERPO": {"block": body},
        },
    }


def _dimension(ident: str, name: str, size: dict[str, object]) -> dict[str, object]:
    return {
        "type": "traza_dimension",
        "id": ident,
        "fields": {"NOMBRE": name, "TIPO": "entero"},
        "extraState": {"dimensiones": 1},
        "inputs": {"TAMANO1": {"block": size}},
    }


def _indice(ident: str, name: str, index: dict[str, object]) -> dict[str, object]:
    return {
        "type": "traza_indice",
        "id": ident,
        "fields": {"NOMBRE": name, "TIPO": "entero"},
        "extraState": {"dimensiones": 1},
        "inputs": {"INDICE1": {"block": index}},
    }


def _asignar_indice(
    ident: str, name: str, index: dict[str, object], value: dict[str, object]
) -> dict[str, object]:
    return {
        "type": "traza_asignar_indice",
        "id": ident,
        "fields": {"NOMBRE": name},
        "extraState": {"dimensiones": 1},
        "inputs": {"INDICE1": {"block": index}, "VALOR": {"block": value}},
    }


def _leer_indice(ident: str, name: str, index: dict[str, object]) -> dict[str, object]:
    return {
        "type": "traza_leer_indice",
        "id": ident,
        "fields": {"NOMBRE": name},
        "extraState": {"dimensiones": 1},
        "inputs": {"INDICE1": {"block": index}},
    }


def _repetir(
    ident: str, body: dict[str, object], condition: dict[str, object]
) -> dict[str, object]:
    return {
        "type": "traza_repetir",
        "id": ident,
        "inputs": {"CUERPO": {"block": body}, "CONDICION": {"block": condition}},
    }


def _hints(*bodies: tuple[int, str]) -> list[dict[str, object]]:
    return [{"level": level, "position": 1, "body": body} for level, body in bodies]


PREDICT_PLUS = _chain(
    [
        _definir("d", "n", "entero"),
        _asignar("a1", "n", _entero("n4", 4)),
        _asignar("a2", "n", _arit("s", "add", _variable("vn", "n"), _entero("n1", 1))),
        _escribir("e", _variable("vo", "n")),
    ]
)

PREDICT_MINUS = _chain(
    [
        _definir("d", "a", "entero"),
        _asignar("a1", "a", _entero("n10", 10)),
        _escribir("e", _arit("s", "sub", _variable("va", "a"), _entero("n3", 3))),
    ]
)

PREDICT_BRANCH = _chain(
    [
        _definir("d", "n", "entero"),
        _asignar("a", "n", _entero("z", 0)),
        _si_sino(
            "si",
            _rel("c", "gt", _variable("vn", "n"), _entero("cero", 0)),
            _escribir("ep", _cadena("tp", "positivo")),
            _escribir("ec", _cadena("tc", "cero")),
        ),
    ]
)

PREDICT_SKIP = _chain(
    [
        _definir("d", "n", "entero"),
        _asignar("a", "n", _entero("z", 0)),
        _mientras(
            "ciclo",
            _rel("c", "gt", _variable("vn", "n"), _entero("cero", 0)),
            _escribir("e", _cadena("t", "entra")),
        ),
        _escribir("fin", _variable("vo", "n")),
    ]
)

_REPEAT_BODY = _escribir("en", _variable("vn", "n"))
_REPEAT_BODY["next"] = {
    "block": _asignar("suma", "n", _arit("op", "add", _variable("vn2", "n"), _entero("uno", 1)))
}

PREDICT_CASE = _chain(
    [
        _definir("d", "opcion", "entero"),
        _asignar("a", "opcion", _entero("dos", 2)),
        _segun(
            "sg",
            _variable("vo", "opcion"),
            (_entero("c1", 1), _escribir("e1", _cadena("t1", "uno"))),
            (_entero("c2", 2), _escribir("e2", _cadena("t2", "dos"))),
            _escribir("e0", _cadena("t0", "otro")),
        ),
    ]
)

PREDICT_ONCE = _chain(
    [
        _definir("d", "i", "entero"),
        _para(
            "p",
            "i",
            _entero("desde", 1),
            _entero("hasta", 1),
            _entero("paso", 1),
            _escribir("e", _variable("vi", "i")),
        ),
    ]
)

PREDICT_REPEAT = _chain(
    [
        _definir("d", "n", "entero"),
        _asignar("a", "n", _entero("base", 1)),
        _repetir("r", _REPEAT_BODY, _rel("c", "gt", _variable("vn3", "n"), _entero("lim", 1))),
    ]
)

_DOBLAR: dict[str, object] = {
    "type": "traza_funcion",
    "id": "fn",
    "fields": {
        "RESULTADO": "resultado",
        "NOMBRE": "Doblar",
        "PARAM1": "n",
        "MODO1": "valor",
    },
    "extraState": {"parametros": 1},
    "inputs": {
        "CUERPO": {
            "block": _first(
                [
                    _definir("dr", "resultado", "entero"),
                    _definir("dn", "n", "entero"),
                    _asignar(
                        "as",
                        "resultado",
                        _arit("mul", "mul", _variable("vn", "n"), _entero("dos", 2)),
                    ),
                ]
            )
        }
    },
}

_LLAMADA_TRES: dict[str, object] = {
    "type": "traza_llamada",
    "id": "ll",
    "fields": {"NOMBRE": "Doblar", "TIPO": "entero"},
    "extraState": {"argumentos": 1},
    "inputs": {"ARG1": {"block": _entero("tres", 3)}},
}

PREDICT_CELL = _chain(
    [
        _definir("d", "datos", "entero"),
        _dimension("dim", "datos", _entero("tam", 1)),
        _asignar_indice("ai", "datos", _entero("i1", 1), _entero("ocho", 8)),
        _escribir("e", _indice("ix", "datos", _entero("i2", 1))),
    ]
)

PREDICT_DOUBLE = _stacks(_DOBLAR, _escribir("e", _LLAMADA_TRES))

PATH: dict[str, object] = {
    "name": "Fundamentos",
    "description": (
        "Variables, asignación, entrada, salida, operadores, decisiones, ciclos, "
        "opción múltiple, para, repetir, arreglos y funciones."
    ),
    "position": 1,
    "units": [
        {
            "title": "Variables",
            "concept": "variable",
            "position": 1,
            "challenges": [
                {
                    "title": "Qué entra y qué sale",
                    "time_limit_seconds": 180,
                    "prompt": (
                        "Una caja cobra un producto. Clasifica cada frase como entrada, "
                        "proceso, salida o restricción."
                    ),
                    "activity_type": "classify",
                    "difficulty": 1,
                    "position": 1,
                    "allowed_blocks": [],
                    "restrictions": {
                        "categories": ["entrada", "proceso", "salida", "restricción"],
                        "items": [
                            {
                                "id": "salida",
                                "text": "El total que se muestra",
                                "category": "salida",
                            },
                            {
                                "id": "entrada",
                                "text": "El precio que escribe la persona",
                                "category": "entrada",
                            },
                            {
                                "id": "restriccion",
                                "text": "El precio no puede ser negativo",
                                "category": "restricción",
                            },
                            {
                                "id": "proceso",
                                "text": "Multiplicar precio por cantidad",
                                "category": "proceso",
                            },
                        ],
                    },
                    "cases": [],
                    "hints": _hints(
                        (
                            1,
                            "Fíjate en quién produce el dato: la persona, el cálculo o la pantalla.",
                        ),
                        (2, "Una restricción dice qué no está permitido. No es un cálculo."),
                        (
                            5,
                            "Esta es la solución explicada: el precio escrito es entrada, "
                            "la multiplicación es proceso, el total es salida y el precio "
                            "negativo es una restricción.",
                        ),
                    ),
                },
                {
                    "title": "Orden para mostrar un precio",
                    "time_limit_seconds": 180,
                    "prompt": "Ordena las instrucciones para leer un precio y mostrarlo.",
                    "activity_type": "order",
                    "difficulty": 1,
                    "position": 2,
                    "allowed_blocks": [],
                    "restrictions": {
                        "items": [
                            {"id": "leer", "text": "Leer precio"},
                            {"id": "escribir", "text": "Escribir precio"},
                            {"id": "definir", "text": "Definir precio Como Entero"},
                        ],
                        "solution": ["definir", "leer", "escribir"],
                    },
                    "cases": [],
                    "hints": _hints(
                        (1, "Un programa declara el dato antes de usarlo."),
                        (2, "¿Qué tiene que existir antes de poder leer el precio?"),
                        (
                            5,
                            "Esta es la solución explicada: primero se define el precio, "
                            "después se lee y al final se escribe.",
                        ),
                    ),
                },
            ],
        },
        {
            "title": "Asignación",
            "concept": "assignment",
            "position": 2,
            "challenges": [
                {
                    "title": "Presentar un saludo",
                    "time_limit_seconds": 480,
                    "prompt": (
                        "Define una cadena llamada saludo, guárdale el texto hola y escríbela."
                    ),
                    "activity_type": "build",
                    "difficulty": 1,
                    "position": 1,
                    "allowed_blocks": [
                        "traza_definir",
                        "traza_asignar",
                        "traza_escribir",
                        "traza_variable",
                        "traza_cadena",
                    ],
                    "restrictions": {
                        "lock_build": True,
                        "question": "¿Qué símbolo guarda un valor en una variable?",
                        "accepted": ["<-", "="],
                        "required_blocks": ["traza_definir", "traza_asignar", "traza_escribir"],
                    },
                    "cases": [
                        {
                            "name": "hola",
                            "inputs": [],
                            "expected_output": "hola\n",
                            "kind": "normal",
                            "position": 1,
                        }
                    ],
                    "hints": _hints(
                        (1, "El texto va entre una definición y una escritura."),
                        (2, "Puedes asignar con <- o con =. Para comparar si dos valores son iguales se usa ==."),
                        (
                            5,
                            "Esta es la solución explicada: define saludo como cadena, "
                            "asígnale hola y escríbelo.",
                        ),
                    ),
                },
                {
                    "title": "Después de asignar",
                    "time_limit_seconds": 180,
                    "prompt": "Anticipa el número que se escribe. Después podrás ejecutarlo.",
                    "activity_type": "predict",
                    "difficulty": 2,
                    "position": 2,
                    "allowed_blocks": [],
                    "restrictions": {
                        "question": "¿Qué número se escribe?",
                        "accepted": ["5"],
                        "starter": PREDICT_PLUS,
                        "output": "5\n",
                    },
                    "cases": [],
                    "hints": _hints(
                        (1, "Sigue el valor de n línea por línea."),
                        (2, "La segunda asignación usa el valor que n ya tenía."),
                        (
                            5,
                            "Esta es la solución explicada: n empieza en 4 y luego suma 1, "
                            "así que se escribe 5.",
                        ),
                    ),
                },
            ],
        },
        {
            "title": "Entrada y salida",
            "concept": "io",
            "position": 3,
            "challenges": [
                {
                    "title": "Orden para preguntar el nombre",
                    "time_limit_seconds": 240,
                    "prompt": "Ordena las instrucciones para preguntar un nombre y mostrarlo.",
                    "activity_type": "order",
                    "difficulty": 2,
                    "position": 1,
                    "allowed_blocks": [],
                    "restrictions": {
                        "items": [
                            {"id": "leer", "text": "Leer nombre"},
                            {"id": "definir", "text": "Definir nombre Como Cadena"},
                            {"id": "escribir-nombre", "text": "Escribir nombre"},
                            {"id": "preguntar", "text": 'Escribir "Cómo te llamas?"'},
                        ],
                        "solution": ["definir", "preguntar", "leer", "escribir-nombre"],
                    },
                    "cases": [],
                    "hints": _hints(
                        (1, "La pregunta en pantalla ocurre antes de leer la respuesta."),
                        (2, "El nombre se declara antes de leerlo."),
                        (
                            5,
                            "Esta es la solución explicada: se define el nombre, se pregunta, "
                            "se lee y al final se escribe.",
                        ),
                    ),
                },
                {
                    "title": "Eco de un entero",
                    "time_limit_seconds": 480,
                    "prompt": "Define un entero llamado n, léelo y escríbelo.",
                    "activity_type": "build",
                    "difficulty": 2,
                    "position": 2,
                    "allowed_blocks": [
                        "traza_definir",
                        "traza_leer",
                        "traza_escribir",
                        "traza_variable",
                    ],
                    "restrictions": {
                        "lock_build": True,
                        "question": "¿Qué instrucción recibe un dato de quien usa el programa?",
                        "accepted": ["leer"],
                        "required_blocks": ["traza_definir", "traza_leer", "traza_escribir"],
                    },
                    "cases": [
                        {
                            "name": "ocho",
                            "inputs": ["8"],
                            "expected_output": "8\n8\n",
                            "kind": "normal",
                            "position": 1,
                        },
                        {
                            "name": "cero",
                            "inputs": ["0"],
                            "expected_output": "0\n0\n",
                            "kind": "boundary",
                            "position": 2,
                        },
                    ],
                    "hints": _hints(
                        (1, "Hace falta una variable antes de leer."),
                        (2, "Después de leer, escribe esa misma variable."),
                        (
                            5,
                            "Esta es la solución explicada: define n como entero, léelo y escríbelo.",
                        ),
                    ),
                },
            ],
        },
        {
            "title": "Operadores",
            "concept": "operator",
            "position": 4,
            "challenges": [
                {
                    "title": "Qué clase de operador es",
                    "time_limit_seconds": 180,
                    "prompt": "Clasifica cada expresión.",
                    "activity_type": "classify",
                    "difficulty": 2,
                    "position": 1,
                    "allowed_blocks": [],
                    "restrictions": {
                        "categories": ["aritmética", "comparación", "lógica"],
                        "items": [
                            {"id": "comparar", "text": "edad >= 18", "category": "comparación"},
                            {"id": "sumar", "text": "precio + 1", "category": "aritmética"},
                            {"id": "negar", "text": "NO activo", "category": "lógica"},
                            {"id": "unir", "text": "activo Y pagado", "category": "lógica"},
                        ],
                    },
                    "cases": [],
                    "hints": _hints(
                        (1, "Sumar y restar son cuentas. Comparar da un lógico."),
                        (2, "Y y NO combinan lógicos, no números."),
                        (
                            5,
                            "Esta es la solución explicada: precio + 1 es aritmética, "
                            "edad >= 18 es comparación, y NO activo y activo Y pagado son lógicas.",
                        ),
                    ),
                },
                {
                    "title": "El doble",
                    "time_limit_seconds": 480,
                    "prompt": "Lee un entero n y escribe su doble.",
                    "activity_type": "build",
                    "difficulty": 2,
                    "position": 2,
                    "allowed_blocks": [
                        "traza_definir",
                        "traza_leer",
                        "traza_escribir",
                        "traza_variable",
                        "traza_entero",
                        "traza_aritmetica",
                    ],
                    "restrictions": {
                        "lock_build": True,
                        "question": "¿Qué símbolo multiplica dos números?",
                        "accepted": ["*"],
                        "required_blocks": [
                            "traza_definir",
                            "traza_leer",
                            "traza_escribir",
                            "traza_aritmetica",
                        ],
                    },
                    "cases": [
                        {
                            "name": "tres",
                            "inputs": ["3"],
                            "expected_output": "3\n6\n",
                            "kind": "normal",
                            "position": 1,
                        },
                        {
                            "name": "cero",
                            "inputs": ["0"],
                            "expected_output": "0\n0\n",
                            "kind": "boundary",
                            "position": 2,
                        },
                    ],
                    "hints": _hints(
                        (1, "El doble es el número multiplicado por 2."),
                        (2, "Puedes escribir la cuenta directamente, sin otra variable."),
                        (
                            5,
                            "Esta es la solución explicada: define n, léelo y escribe n * 2.",
                        ),
                    ),
                },
                {
                    "title": "Cuánto se escribe",
                    "time_limit_seconds": 180,
                    "prompt": "Anticipa el número que se escribe. Después podrás ejecutarlo.",
                    "activity_type": "predict",
                    "difficulty": 3,
                    "position": 3,
                    "allowed_blocks": [],
                    "restrictions": {
                        "question": "¿Qué número se escribe?",
                        "accepted": ["7"],
                        "starter": PREDICT_MINUS,
                        "output": "7\n",
                    },
                    "cases": [],
                    "hints": _hints(
                        (1, "Primero se guarda 10 en a."),
                        (2, "Lo que se escribe es esa cantidad menos 3."),
                        (
                            5,
                            "Esta es la solución explicada: 10 menos 3 es 7, y eso es lo que se escribe.",
                        ),
                    ),
                },
                {
                    "title": "Total de la compra",
                    "time_limit_seconds": 600,
                    "prompt": (
                        "Lee precio y cantidad, ambos enteros, calcula el total y escríbelo."
                    ),
                    "activity_type": "build",
                    "difficulty": 3,
                    "position": 4,
                    "allowed_blocks": [
                        "traza_definir",
                        "traza_leer",
                        "traza_asignar",
                        "traza_escribir",
                        "traza_variable",
                        "traza_entero",
                        "traza_aritmetica",
                    ],
                    "restrictions": {
                        "lock_build": True,
                        "question": "¿Qué operación obtiene el total a partir del precio y la cantidad?",
                        "accepted": ["*", "multiplicacion", "multiplicación"],
                        "required_blocks": [
                            "traza_definir",
                            "traza_leer",
                            "traza_asignar",
                            "traza_escribir",
                        ],
                    },
                    "cases": [
                        {
                            "name": "dos por tres",
                            "inputs": ["2", "3"],
                            "expected_output": "2\n3\n6\n",
                            "kind": "normal",
                            "position": 1,
                        },
                        {
                            "name": "precio cero",
                            "inputs": ["0", "5"],
                            "expected_output": "0\n5\n0\n",
                            "kind": "boundary",
                            "position": 2,
                        },
                    ],
                    "hints": _hints(
                        (1, "Hacen falta tres datos: precio, cantidad y total."),
                        (2, "El total se guarda con una asignación después de las dos lecturas."),
                        (
                            5,
                            "Esta es la solución explicada: lee precio y cantidad, asigna "
                            "total <- precio * cantidad y escribe total.",
                        ),
                    ),
                },
            ],
        },
        {
            "title": "Decisiones",
            "concept": "if",
            "position": 5,
            "challenges": [
                {
                    "title": "Partes de una decisión",
                    "time_limit_seconds": 180,
                    "prompt": "Clasifica cada frase según el papel que cumple dentro de un Si.",
                    "activity_type": "classify",
                    "difficulty": 2,
                    "position": 1,
                    "allowed_blocks": [],
                    "restrictions": {
                        "categories": ["condición", "entonces", "sino", "cierre"],
                        "items": [
                            {
                                "id": "condicion",
                                "text": "edad >= 18",
                                "category": "condición",
                            },
                            {
                                "id": "entonces",
                                "text": "Escribir mayor cuando la comparación se cumple",
                                "category": "entonces",
                            },
                            {
                                "id": "sino",
                                "text": "Escribir menor cuando la comparación no se cumple",
                                "category": "sino",
                            },
                            {
                                "id": "cierre",
                                "text": "FinSi",
                                "category": "cierre",
                            },
                        ],
                    },
                    "cases": [],
                    "hints": _hints(
                        (
                            1,
                            "La condición es la comparación. Las ramas son lo que se hace después.",
                        ),
                        (
                            2,
                            "Sino es la rama de cuando la comparación es falsa. FinSi cierra el bloque.",
                        ),
                        (
                            5,
                            "Esta es la solución explicada: edad >= 18 es la condición, "
                            "escribir mayor es entonces, escribir menor es sino y FinSi es el cierre.",
                        ),
                    ),
                },
                {
                    "title": "Orden del Si",
                    "time_limit_seconds": 240,
                    "prompt": "Ordena las líneas de una decisión con dos ramas.",
                    "activity_type": "order",
                    "difficulty": 2,
                    "position": 2,
                    "allowed_blocks": [],
                    "restrictions": {
                        "items": [
                            {"id": "falso", "text": 'Escribir "menor"'},
                            {"id": "si", "text": "Si edad >= 18 Entonces"},
                            {"id": "finsi", "text": "FinSi"},
                            {"id": "verdadero", "text": 'Escribir "mayor"'},
                            {"id": "sino", "text": "Sino"},
                        ],
                        "solution": ["si", "verdadero", "sino", "falso", "finsi"],
                    },
                    "cases": [],
                    "hints": _hints(
                        (1, "El Si abre el bloque y FinSi lo cierra."),
                        (2, "La rama verdadera va antes de Sino."),
                        (
                            5,
                            "Esta es la solución explicada: Si, la escritura de mayor, "
                            "Sino, la escritura de menor y FinSi.",
                        ),
                    ),
                },
                {
                    "title": "La rama del cero",
                    "time_limit_seconds": 180,
                    "prompt": "Anticipa el texto que se escribe. Después podrás ejecutarlo.",
                    "activity_type": "predict",
                    "difficulty": 2,
                    "position": 3,
                    "allowed_blocks": [],
                    "restrictions": {
                        "question": "¿Qué texto se escribe?",
                        "accepted": ["cero"],
                        "starter": PREDICT_BRANCH,
                        "output": "cero\n",
                    },
                    "cases": [],
                    "hints": _hints(
                        (1, "n empieza en 0. Mira si la comparación se cumple."),
                        (2, "Si la comparación es falsa, se ejecuta la rama Sino."),
                        (
                            5,
                            "Esta es la solución explicada: 0 no es mayor que 0, "
                            "así que se escribe cero.",
                        ),
                    ),
                },
                {
                    "title": "Mayor de edad",
                    "time_limit_seconds": 480,
                    "prompt": (
                        "Lee un entero llamado edad. Si es mayor o igual que 18 escribe si; "
                        "si no, escribe no."
                    ),
                    "activity_type": "build",
                    "difficulty": 3,
                    "position": 4,
                    "allowed_blocks": [
                        "traza_definir",
                        "traza_leer",
                        "traza_escribir",
                        "traza_variable",
                        "traza_entero",
                        "traza_cadena",
                        "traza_relacional",
                        "traza_si_sino",
                    ],
                    "restrictions": {
                        "lock_build": True,
                        "question": "¿Qué palabra abre la rama de cuando la condición es falsa?",
                        "accepted": ["sino"],
                        "required_blocks": [
                            "traza_definir",
                            "traza_leer",
                            "traza_si_sino",
                            "traza_escribir",
                        ],
                    },
                    "cases": [
                        {
                            "name": "veinte",
                            "inputs": ["20"],
                            "expected_output": "20\nsi\n",
                            "kind": "normal",
                            "position": 1,
                        },
                        {
                            "name": "justo dieciocho",
                            "inputs": ["18"],
                            "expected_output": "18\nsi\n",
                            "kind": "boundary",
                            "position": 2,
                        },
                        {
                            "name": "diecisiete",
                            "inputs": ["17"],
                            "expected_output": "17\nno\n",
                            "kind": "boundary",
                            "position": 3,
                        },
                    ],
                    "hints": _hints(
                        (1, "La comparación usa >= y el 18."),
                        (2, "La rama verdadera escribe si. La otra escribe no."),
                        (
                            5,
                            "Esta es la solución explicada: lee edad y, si edad >= 18, "
                            "escribe si; si no, escribe no.",
                        ),
                    ),
                },
            ],
        },
        {
            "title": "Ciclo mientras",
            "concept": "while",
            "position": 6,
            "challenges": [
                {
                    "title": "Cuándo entra el ciclo",
                    "time_limit_seconds": 180,
                    "prompt": "La condición es n < 3. Clasifica cada situación.",
                    "activity_type": "classify",
                    "difficulty": 2,
                    "position": 1,
                    "allowed_blocks": [],
                    "restrictions": {
                        "categories": ["entra", "no entra", "termina"],
                        "items": [
                            {
                                "id": "entra",
                                "text": "n vale 1",
                                "category": "entra",
                            },
                            {
                                "id": "fuera",
                                "text": "n vale 3 antes de evaluar la condición",
                                "category": "no entra",
                            },
                            {
                                "id": "termina",
                                "text": "n llega a 3 dentro del ciclo",
                                "category": "termina",
                            },
                            {
                                "id": "sigue",
                                "text": "n vale 2 y todavía no se evaluó de nuevo",
                                "category": "entra",
                            },
                        ],
                    },
                    "cases": [],
                    "hints": _hints(
                        (1, "El cuerpo se ejecuta solo cuando la condición es verdadera."),
                        (2, "Si n ya vale 3, n < 3 es falso y el cuerpo no entra."),
                        (
                            5,
                            "Esta es la solución explicada: con 1 y con 2 el ciclo entra; "
                            "con 3 antes de evaluar no entra; cuando n llega a 3, termina.",
                        ),
                    ),
                },
                {
                    "title": "Orden del Mientras",
                    "time_limit_seconds": 240,
                    "prompt": "Ordena las líneas para restar n hasta cero y después escribirlo.",
                    "activity_type": "order",
                    "difficulty": 3,
                    "position": 2,
                    "allowed_blocks": [],
                    "restrictions": {
                        "items": [
                            {"id": "fin", "text": "FinMientras"},
                            {"id": "definir", "text": "Definir n Como Entero"},
                            {"id": "mientras", "text": "Mientras n > 0 Hacer"},
                            {"id": "escribir", "text": "Escribir n"},
                            {"id": "asignar", "text": "n <- 3"},
                            {"id": "restar", "text": "n <- n - 1"},
                        ],
                        "solution": ["definir", "asignar", "mientras", "restar", "fin", "escribir"],
                    },
                    "cases": [],
                    "hints": _hints(
                        (1, "n tiene que existir y tener un valor antes del ciclo."),
                        (
                            2,
                            "La resta va dentro del Mientras, y la escritura va después del cierre.",
                        ),
                        (
                            5,
                            "Esta es la solución explicada: se define n, se guarda 3, "
                            "se resta mientras n sea mayor que 0 y al final se escribe n.",
                        ),
                    ),
                },
                {
                    "title": "El ciclo que no entra",
                    "time_limit_seconds": 180,
                    "prompt": "Anticipa el número que se escribe. Después podrás ejecutarlo.",
                    "activity_type": "predict",
                    "difficulty": 3,
                    "position": 3,
                    "allowed_blocks": [],
                    "restrictions": {
                        "question": "¿Qué número se escribe?",
                        "accepted": ["0"],
                        "starter": PREDICT_SKIP,
                        "output": "0\n",
                    },
                    "cases": [],
                    "hints": _hints(
                        (1, "n empieza en 0. La condición pide que sea mayor que 0."),
                        (
                            2,
                            "Si la condición es falsa desde el principio, el cuerpo no se ejecuta.",
                        ),
                        (
                            5,
                            "Esta es la solución explicada: el ciclo no entra y se escribe el 0 inicial.",
                        ),
                    ),
                },
                {
                    "title": "Contar positivos",
                    "time_limit_seconds": 600,
                    "prompt": (
                        "Lee enteros hasta que llegue un 0. Cuenta cuántos fueron mayores que 0 "
                        "y escribe esa cantidad. El 0 no se cuenta."
                    ),
                    "activity_type": "build",
                    "difficulty": 4,
                    "position": 4,
                    "allowed_blocks": [
                        "traza_definir",
                        "traza_asignar",
                        "traza_leer",
                        "traza_escribir",
                        "traza_variable",
                        "traza_entero",
                        "traza_aritmetica",
                        "traza_relacional",
                        "traza_si",
                        "traza_mientras",
                    ],
                    "restrictions": {
                        "lock_build": True,
                        "question": "¿Qué instrucción repite el cuerpo mientras la condición se cumple?",
                        "accepted": ["mientras"],
                        "required_blocks": [
                            "traza_definir",
                            "traza_asignar",
                            "traza_leer",
                            "traza_mientras",
                            "traza_si",
                            "traza_escribir",
                        ],
                    },
                    "cases": [
                        {
                            "name": "dos positivos",
                            "inputs": ["2", "5", "0"],
                            "expected_output": "2\n5\n0\n2\n",
                            "kind": "normal",
                            "position": 1,
                        },
                        {
                            "name": "solo el cero",
                            "inputs": ["0"],
                            "expected_output": "0\n0\n",
                            "kind": "boundary",
                            "position": 2,
                        },
                        {
                            "name": "un negativo",
                            "inputs": ["-3", "0"],
                            "expected_output": "-3\n0\n0\n",
                            "kind": "boundary",
                            "position": 3,
                        },
                    ],
                    "hints": _hints(
                        (1, "Hacen falta el número leído y un contador que empiece en 0."),
                        (
                            2,
                            "El Mientras sigue mientras el número no sea 0. El Si cuenta solo si es mayor que 0.",
                        ),
                        (
                            5,
                            "Esta es la solución explicada: lee n mientras no sea 0; si n es mayor "
                            "que 0, suma 1 al contador; al salir, escribe el contador.",
                        ),
                    ),
                },
            ],
        },
        {
            "title": "Opción múltiple",
            "concept": "switch",
            "position": 7,
            "challenges": [
                {
                    "title": "Partes de un Segun",
                    "time_limit_seconds": 180,
                    "prompt": "Clasifica cada parte de una opción múltiple.",
                    "activity_type": "classify",
                    "difficulty": 2,
                    "position": 1,
                    "allowed_blocks": [],
                    "restrictions": {
                        "categories": ["selector", "caso", "otro", "cierre"],
                        "items": [
                            {
                                "id": "selector",
                                "text": "El valor que se compara",
                                "category": "selector",
                            },
                            {"id": "caso", "text": "1: Escribir uno", "category": "caso"},
                            {"id": "otro", "text": "De Otro Modo", "category": "otro"},
                            {"id": "cierre", "text": "FinSegun", "category": "cierre"},
                        ],
                    },
                    "cases": [],
                    "hints": _hints(
                        (1, "El selector es el valor que entra a Segun."),
                        (2, "De Otro Modo cubre lo que no coincidió con ningún caso."),
                        (
                            5,
                            "Esta es la solución explicada: el valor comparado es el selector, "
                            "1: es un caso, De Otro Modo es la rama restante y FinSegun cierra.",
                        ),
                    ),
                },
                {
                    "title": "Qué caso se escribe",
                    "time_limit_seconds": 180,
                    "prompt": "Anticipa el texto que se escribe. Después podrás ejecutarlo.",
                    "activity_type": "predict",
                    "difficulty": 2,
                    "position": 2,
                    "allowed_blocks": [],
                    "restrictions": {
                        "question": "¿Qué texto se escribe?",
                        "accepted": ["dos"],
                        "starter": PREDICT_CASE,
                        "output": "dos\n",
                    },
                    "cases": [],
                    "hints": _hints(
                        (1, "opcion vale 2. Busca el caso con esa etiqueta."),
                        (2, "Solo se ejecuta el caso que coincide. No cae al siguiente."),
                        (
                            5,
                            "Esta es la solución explicada: el 2 coincide con el segundo caso "
                            "y se escribe dos.",
                        ),
                    ),
                },
                {
                    "title": "Menú de una opción",
                    "time_limit_seconds": 600,
                    "prompt": (
                        "Lee un entero llamado opcion. Si es 1 escribe uno; si es 2 escribe dos; "
                        "en cualquier otro caso escribe otro."
                    ),
                    "activity_type": "build",
                    "difficulty": 3,
                    "position": 3,
                    "allowed_blocks": [
                        "traza_definir",
                        "traza_leer",
                        "traza_escribir",
                        "traza_variable",
                        "traza_entero",
                        "traza_cadena",
                        "traza_segun",
                    ],
                    "restrictions": {
                        "lock_build": True,
                        "question": "¿Qué palabras abren la rama que no coincidió con ningún caso?",
                        "accepted": ["deotromodo"],
                        "required_blocks": [
                            "traza_definir",
                            "traza_leer",
                            "traza_segun",
                            "traza_escribir",
                        ],
                    },
                    "cases": [
                        {
                            "name": "uno",
                            "inputs": ["1"],
                            "expected_output": "1\nuno\n",
                            "kind": "normal",
                            "position": 1,
                        },
                        {
                            "name": "dos",
                            "inputs": ["2"],
                            "expected_output": "2\ndos\n",
                            "kind": "normal",
                            "position": 2,
                        },
                        {
                            "name": "otro valor",
                            "inputs": ["9"],
                            "expected_output": "9\notro\n",
                            "kind": "boundary",
                            "position": 3,
                        },
                    ],
                    "hints": _hints(
                        (1, "Las etiquetas son los literales 1 y 2, no una comparación."),
                        (2, "El 9 no está en ningún caso: cae en De Otro Modo."),
                        (
                            5,
                            "Esta es la solución explicada: lee opcion y, segun ese valor, "
                            "escribe uno, dos u otro.",
                        ),
                    ),
                },
            ],
        },
        {
            "title": "Ciclo para",
            "concept": "for",
            "position": 8,
            "challenges": [
                {
                    "title": "Orden del Para",
                    "time_limit_seconds": 240,
                    "prompt": "Ordena las líneas para escribir i desde 1 hasta 3.",
                    "activity_type": "order",
                    "difficulty": 2,
                    "position": 1,
                    "allowed_blocks": [],
                    "restrictions": {
                        "items": [
                            {"id": "fin", "text": "FinPara"},
                            {"id": "definir", "text": "Definir i Como Entero"},
                            {"id": "escribir", "text": "Escribir i"},
                            {"id": "para", "text": "Para i <- 1 Hasta 3 Con Paso 1 Hacer"},
                        ],
                        "solution": ["definir", "para", "escribir", "fin"],
                    },
                    "cases": [],
                    "hints": _hints(
                        (1, "i tiene que estar definido antes del Para."),
                        (2, "Escribir i va dentro del ciclo, y FinPara lo cierra."),
                        (
                            5,
                            "Esta es la solución explicada: se define i, abre el Para, "
                            "se escribe i y se cierra con FinPara.",
                        ),
                    ),
                },
                {
                    "title": "Una sola vuelta",
                    "time_limit_seconds": 180,
                    "prompt": "Anticipa el número que se escribe. Después podrás ejecutarlo.",
                    "activity_type": "predict",
                    "difficulty": 2,
                    "position": 2,
                    "allowed_blocks": [],
                    "restrictions": {
                        "question": "¿Qué número se escribe?",
                        "accepted": ["1"],
                        "starter": PREDICT_ONCE,
                        "output": "1\n",
                    },
                    "cases": [],
                    "hints": _hints(
                        (1, "El inicio y el límite son el mismo número."),
                        (2, "Con paso 1, el cuerpo corre cuando i todavía no pasó el límite."),
                        (
                            5,
                            "Esta es la solución explicada: i va de 1 a 1, así que se escribe 1 una vez.",
                        ),
                    ),
                },
                {
                    "title": "Contar hasta n",
                    "time_limit_seconds": 600,
                    "prompt": (
                        "Lee un entero n. Con paso 1, escribe los enteros desde 1 hasta n, uno por línea."
                    ),
                    "activity_type": "build",
                    "difficulty": 3,
                    "position": 3,
                    "allowed_blocks": [
                        "traza_definir",
                        "traza_leer",
                        "traza_escribir",
                        "traza_variable",
                        "traza_entero",
                        "traza_para",
                    ],
                    "restrictions": {
                        "lock_build": True,
                        "question": "¿Qué palabra cierra el ciclo Para?",
                        "accepted": ["finpara"],
                        "required_blocks": [
                            "traza_definir",
                            "traza_leer",
                            "traza_para",
                            "traza_escribir",
                        ],
                    },
                    "cases": [
                        {
                            "name": "hasta tres",
                            "inputs": ["3"],
                            "expected_output": "3\n1\n2\n3\n",
                            "kind": "normal",
                            "position": 1,
                        },
                        {
                            "name": "hasta uno",
                            "inputs": ["1"],
                            "expected_output": "1\n1\n",
                            "kind": "boundary",
                            "position": 2,
                        },
                    ],
                    "hints": _hints(
                        (1, "Hacen falta n, que se lee, e i, que recorre el Para."),
                        (2, "El inicio es 1, el límite es n y el paso es 1."),
                        (
                            5,
                            "Esta es la solución explicada: lee n y, para i desde 1 hasta n "
                            "con paso 1, escribe i.",
                        ),
                    ),
                },
            ],
        },
        {
            "title": "Ciclo repetir",
            "concept": "repeat",
            "position": 9,
            "challenges": [
                {
                    "title": "Cuándo corre el cuerpo",
                    "time_limit_seconds": 180,
                    "prompt": "Clasifica cada frase como propia de Repetir o de Mientras.",
                    "activity_type": "classify",
                    "difficulty": 3,
                    "position": 1,
                    "allowed_blocks": [],
                    "restrictions": {
                        "categories": ["repetir", "mientras"],
                        "items": [
                            {
                                "id": "siempre",
                                "text": "El cuerpo se ejecuta al menos una vez",
                                "category": "repetir",
                            },
                            {
                                "id": "antes",
                                "text": "La condición se mira antes del cuerpo",
                                "category": "mientras",
                            },
                            {
                                "id": "despues",
                                "text": "La condición se mira después del cuerpo",
                                "category": "repetir",
                            },
                            {
                                "id": "falso",
                                "text": "Si la condición es falsa al empezar, el cuerpo no corre",
                                "category": "mientras",
                            },
                        ],
                    },
                    "cases": [],
                    "hints": _hints(
                        (1, "Repetir hace el cuerpo y después pregunta si ya terminó."),
                        (2, "Mientras pregunta primero. Si no se cumple, no entra."),
                        (
                            5,
                            "Esta es la solución explicada: ejecutar al menos una vez y mirar "
                            "la condición después son de Repetir. Mirarla antes, y no entrar "
                            "si ya es falsa, son de Mientras.",
                        ),
                    ),
                },
                {
                    "title": "Aunque ya cumpla",
                    "time_limit_seconds": 180,
                    "prompt": "Anticipa el número que se escribe. Después podrás ejecutarlo.",
                    "activity_type": "predict",
                    "difficulty": 3,
                    "position": 2,
                    "allowed_blocks": [],
                    "restrictions": {
                        "question": "¿Qué número se escribe?",
                        "accepted": ["1"],
                        "starter": PREDICT_REPEAT,
                        "output": "1\n",
                    },
                    "cases": [],
                    "hints": _hints(
                        (1, "n empieza en 1. El cuerpo corre antes de mirar Hasta Que."),
                        (2, "Se escribe el valor que n tiene al entrar al cuerpo."),
                        (
                            5,
                            "Esta es la solución explicada: el cuerpo escribe 1 y después "
                            "n pasa de 1, así que el ciclo se detiene.",
                        ),
                    ),
                },
                {
                    "title": "Subir hasta el tope",
                    "time_limit_seconds": 600,
                    "prompt": (
                        "Lee un entero llamado tope, mayor que 0. Desde 0, suma 1 y escribe "
                        "el nuevo valor, y repite eso hasta que el valor sea igual al tope."
                    ),
                    "activity_type": "build",
                    "difficulty": 4,
                    "position": 3,
                    "allowed_blocks": [
                        "traza_definir",
                        "traza_asignar",
                        "traza_leer",
                        "traza_escribir",
                        "traza_variable",
                        "traza_entero",
                        "traza_aritmetica",
                        "traza_relacional",
                        "traza_repetir",
                    ],
                    "restrictions": {
                        "lock_build": True,
                        "question": "¿La condición de Repetir se mira al principio o al final?",
                        "accepted": ["alfinal", "final"],
                        "required_blocks": [
                            "traza_definir",
                            "traza_asignar",
                            "traza_leer",
                            "traza_repetir",
                            "traza_escribir",
                        ],
                    },
                    "cases": [
                        {
                            "name": "tope tres",
                            "inputs": ["3"],
                            "expected_output": "3\n1\n2\n3\n",
                            "kind": "normal",
                            "position": 1,
                        },
                        {
                            "name": "tope uno",
                            "inputs": ["1"],
                            "expected_output": "1\n1\n",
                            "kind": "boundary",
                            "position": 2,
                        },
                    ],
                    "hints": _hints(
                        (1, "Hacen falta tope, que se lee, y otro entero que empieza en 0."),
                        (
                            2,
                            "Dentro de Repetir se suma 1 y se escribe. Hasta Que compara con tope.",
                        ),
                        (
                            5,
                            "Esta es la solución explicada: lee tope, deja n en 0 y repite "
                            "n <- n + 1 y escribir n hasta que n sea igual al tope.",
                        ),
                    ),
                },
            ],
        },
        {
            "title": "Arreglos",
            "concept": "array",
            "position": 10,
            "challenges": [
                {
                    "title": "Casilla, tamaño y valor",
                    "time_limit_seconds": 180,
                    "prompt": "Clasifica cada frase como índice, tamaño o valor.",
                    "activity_type": "classify",
                    "difficulty": 2,
                    "position": 1,
                    "allowed_blocks": [],
                    "restrictions": {
                        "categories": ["indice", "tamano", "valor"],
                        "items": [
                            {
                                "id": "casilla",
                                "text": "El número de la casilla que se lee o se escribe",
                                "category": "indice",
                            },
                            {
                                "id": "corchetes",
                                "text": "El número que va entre corchetes",
                                "category": "indice",
                            },
                            {
                                "id": "cuantas",
                                "text": "Cuántas casillas reserva Dimension",
                                "category": "tamano",
                            },
                            {
                                "id": "guardado",
                                "text": "Lo que hay guardado en una casilla",
                                "category": "valor",
                            },
                        ],
                    },
                    "cases": [],
                    "hints": _hints(
                        (1, "El índice elige la casilla. El tamaño dice cuántas hay."),
                        (2, "Entre corchetes va el índice. Dimension escribe el tamaño."),
                        (
                            5,
                            "Esta es la solución explicada: el número de casilla y lo que va "
                            "entre corchetes son el índice. Cuántas casillas hay es el tamaño. "
                            "Lo guardado es el valor.",
                        ),
                    ),
                },
                {
                    "title": "La casilla uno",
                    "time_limit_seconds": 180,
                    "prompt": "Anticipa el número que se escribe. Después podrás ejecutarlo.",
                    "activity_type": "predict",
                    "difficulty": 2,
                    "position": 2,
                    "allowed_blocks": [],
                    "restrictions": {
                        "question": "¿Qué número se escribe?",
                        "accepted": ["8"],
                        "starter": PREDICT_CELL,
                        "output": "8\n",
                    },
                    "cases": [],
                    "hints": _hints(
                        (1, "El arreglo tiene una casilla y ahí se guarda 8."),
                        (2, "Escribir lee esa misma casilla, la 1."),
                        (
                            5,
                            "Esta es la solución explicada: datos[1] vale 8 y eso es lo que se escribe.",
                        ),
                    ),
                },
                {
                    "title": "La primera y la última",
                    "time_limit_seconds": 600,
                    "prompt": (
                        "Declara un arreglo de 3 enteros llamado datos. Lee tres enteros y "
                        "guárdalos en las casillas 1, 2 y 3. Escribe la suma de la primera y la última."
                    ),
                    "activity_type": "build",
                    "difficulty": 3,
                    "position": 3,
                    "allowed_blocks": [
                        "traza_definir",
                        "traza_dimension",
                        "traza_leer_indice",
                        "traza_indice",
                        "traza_escribir",
                        "traza_entero",
                        "traza_aritmetica",
                    ],
                    "restrictions": {
                        "lock_build": True,
                        "question": "¿Entre qué signos se escribe el índice?",
                        "accepted": ["corchetes"],
                        "required_blocks": [
                            "traza_definir",
                            "traza_dimension",
                            "traza_leer_indice",
                            "traza_indice",
                            "traza_escribir",
                        ],
                    },
                    "cases": [
                        {
                            "name": "cuatro y uno",
                            "inputs": ["4", "9", "1"],
                            "expected_output": "4\n9\n1\n5\n",
                            "kind": "normal",
                            "position": 1,
                        },
                        {
                            "name": "ceros",
                            "inputs": ["0", "0", "0"],
                            "expected_output": "0\n0\n0\n0\n",
                            "kind": "boundary",
                            "position": 2,
                        },
                    ],
                    "hints": _hints(
                        (1, "Definir y Dimension usan el mismo nombre y el mismo tipo."),
                        (2, "Cada Leer guarda en una casilla. La suma usa la 1 y la 3."),
                        (
                            5,
                            "Esta es la solución explicada: datos tiene 3 casillas, se lee "
                            "cada una y se escribe datos[1] + datos[3].",
                        ),
                    ),
                },
            ],
        },
        {
            "title": "Funciones",
            "concept": "function",
            "position": 11,
            "challenges": [
                {
                    "title": "Función o procedimiento",
                    "time_limit_seconds": 180,
                    "prompt": "Clasifica cada frase como propia de una función o de un procedimiento.",
                    "activity_type": "classify",
                    "difficulty": 3,
                    "position": 1,
                    "allowed_blocks": [],
                    "restrictions": {
                        "categories": ["funcion", "procedimiento"],
                        "items": [
                            {
                                "id": "devuelve",
                                "text": "Devuelve un valor con un nombre de resultado",
                                "category": "funcion",
                            },
                            {
                                "id": "expresion",
                                "text": "Se usa dentro de una expresión",
                                "category": "funcion",
                            },
                            {
                                "id": "linea",
                                "text": "Se llama en su propia línea",
                                "category": "procedimiento",
                            },
                            {
                                "id": "referencia",
                                "text": "Puede modificar una variable por referencia",
                                "category": "procedimiento",
                            },
                        ],
                    },
                    "cases": [],
                    "hints": _hints(
                        (1, "La función calcula un resultado. El procedimiento hace una acción."),
                        (2, "Si cabe dentro de Escribir, es una función."),
                        (
                            5,
                            "Esta es la solución explicada: devolver un valor y usarse en una "
                            "expresión son de la función. Llamarse en su línea y modificar "
                            "por referencia son del procedimiento.",
                        ),
                    ),
                },
                {
                    "title": "El doble de tres",
                    "time_limit_seconds": 180,
                    "prompt": "Anticipa el número que se escribe. Después podrás ejecutarlo.",
                    "activity_type": "predict",
                    "difficulty": 3,
                    "position": 2,
                    "allowed_blocks": [],
                    "restrictions": {
                        "question": "¿Qué número se escribe?",
                        "accepted": ["6"],
                        "starter": PREDICT_DOUBLE,
                        "output": "6\n",
                    },
                    "cases": [],
                    "hints": _hints(
                        (1, "Doblar multiplica su parámetro por 2."),
                        (2, "La llamada usa el 3."),
                        (
                            5,
                            "Esta es la solución explicada: Doblar(3) devuelve 6 y eso se escribe.",
                        ),
                    ),
                },
                {
                    "title": "Doblar lo leído",
                    "time_limit_seconds": 600,
                    "prompt": (
                        "Define una función Doblar que reciba un entero y devuelva el doble. "
                        "Lee un entero y escribe Doblar de ese entero."
                    ),
                    "activity_type": "build",
                    "difficulty": 4,
                    "position": 3,
                    "allowed_blocks": [
                        "traza_funcion",
                        "traza_definir",
                        "traza_asignar",
                        "traza_leer",
                        "traza_escribir",
                        "traza_llamada",
                        "traza_variable",
                        "traza_entero",
                        "traza_aritmetica",
                    ],
                    "restrictions": {
                        "lock_build": True,
                        "question": "¿Qué palabra cierra una función?",
                        "accepted": ["finfuncion"],
                        "required_blocks": [
                            "traza_funcion",
                            "traza_definir",
                            "traza_asignar",
                            "traza_leer",
                            "traza_escribir",
                            "traza_llamada",
                        ],
                    },
                    "cases": [
                        {
                            "name": "el cuatro",
                            "inputs": ["4"],
                            "expected_output": "4\n8\n",
                            "kind": "normal",
                            "position": 1,
                        },
                        {
                            "name": "el uno",
                            "inputs": ["1"],
                            "expected_output": "1\n2\n",
                            "kind": "boundary",
                            "position": 2,
                        },
                    ],
                    "hints": _hints(
                        (1, "Dentro de la función se definen el resultado y el parámetro."),
                        (
                            2,
                            "El resultado es el parámetro por 2. Afuera se lee y se escribe la llamada.",
                        ),
                        (
                            5,
                            "Esta es la solución explicada: Doblar asigna resultado <- n * 2. "
                            "El algoritmo lee numero y escribe Doblar(numero).",
                        ),
                    ),
                },
                {
                    "title": "Sumar uno por referencia",
                    "time_limit_seconds": 600,
                    "prompt": (
                        "Define un procedimiento Incrementar con un entero por referencia. "
                        "Súmale 1. Lee una edad, llama al procedimiento y escribe la edad."
                    ),
                    "activity_type": "build",
                    "difficulty": 4,
                    "position": 4,
                    "allowed_blocks": [
                        "traza_procedimiento",
                        "traza_definir",
                        "traza_asignar",
                        "traza_leer",
                        "traza_escribir",
                        "traza_llamar",
                        "traza_variable",
                        "traza_entero",
                        "traza_aritmetica",
                    ],
                    "restrictions": {
                        "lock_build": True,
                        "question": "¿Qué palabra indica que el parámetro se puede modificar?",
                        "accepted": ["referencia", "porreferencia"],
                        "required_blocks": [
                            "traza_procedimiento",
                            "traza_definir",
                            "traza_asignar",
                            "traza_leer",
                            "traza_escribir",
                            "traza_llamar",
                        ],
                    },
                    "cases": [
                        {
                            "name": "diecisiete",
                            "inputs": ["17"],
                            "expected_output": "17\n18\n",
                            "kind": "normal",
                            "position": 1,
                        },
                        {
                            "name": "cero",
                            "inputs": ["0"],
                            "expected_output": "0\n1\n",
                            "kind": "boundary",
                            "position": 2,
                        },
                    ],
                    "hints": _hints(
                        (1, "El parámetro del procedimiento va por referencia."),
                        (
                            2,
                            "Dentro se suma 1 a ese parámetro. Afuera se lee, se llama y se escribe.",
                        ),
                        (
                            5,
                            "Esta es la solución explicada: Incrementar hace n <- n + 1 por "
                            "referencia. El algoritmo lee edad, llama Incrementar(edad) y escribe edad.",
                        ),
                    ),
                },
            ],
        },
    ],
}
