"""Banco compartido de 200 retos, de básico a avanzado.

No es una ruta del alumno. El docente los ve en el catálogo y elige cuáles
poner en una ruta. Cada programa de Construir y Predecir se comprueba con el
mismo lienzo que usa el laboratorio.
"""

from __future__ import annotations

import json
import random
import time
from typing import Any

from language_core.block_adapter import adapt_workspace
from language_core.block_import import workspace_from_source
from language_core.debugger import drive
from language_core.grammar import STRICT
from language_core.interpreter import Interpreter
from language_core.runtime import Cancellation, Limits

BANK_NAME = "Banco de retos"
BANK_DESCRIPTION = (
    "Doscientos retos de básico a avanzado. No se asignan solos: "
    "el docente elige cuáles colocar en una ruta."
)
ROUTE_NAME = "De básico a avanzado"
ROUTE_DESCRIPTION = (
    "Los 200 retos del banco, de variables a funciones, "
    "ordenados de básico a avanzado."
)
_SOLUTION = "Esta es la solución explicada"
_POINTS = {1: 10, 2: 15, 3: 20, 4: 30, 5: 40}
_SECOND = {
    "classify": "Compara cada frase con el nombre de la categoría.",
    "order": "Lo que se usa tiene que existir antes. Empieza por la declaración.",
    "predict": "Anota el valor después de cada asignación, antes del Escribir.",
    "build": "Cada Escribir cierra con un salto de línea. La salida debe coincidir.",
}


def algo(lines: list[str]) -> str:
    body = "\n".join(f"    {line}" for line in lines)
    return f"Algoritmo Laboratorio\n{body}\nFinAlgoritmo\n"


def programa(header: str, lines: list[str]) -> str:
    return f"{header}\n{algo(lines)}"


def build_bank() -> dict[str, Any]:
    """Arma las 11 unidades. Falla si un programa no corre en el laboratorio."""
    units = []
    for position, (concept, title, specs) in enumerate(_UNITS, start=1):
        challenges = [
            _materialize(spec, index, len(specs)) for index, spec in enumerate(specs, start=1)
        ]
        units.append(
            {
                "title": title,
                "concept": concept,
                "position": position,
                "challenges": challenges,
            }
        )
    titles = [item["title"] for unit in units for item in unit["challenges"]]
    if len(titles) != 200:
        raise ValueError(f"El banco tiene {len(titles)} retos, no 200.")
    if len(titles) != len(set(titles)):
        raise ValueError("Hay títulos repetidos en el banco.")
    return {"name": BANK_NAME, "description": BANK_DESCRIPTION, "units": units}


def _materialize(spec: dict[str, Any], index: int, total: int) -> dict[str, Any]:
    kind = spec["kind"]
    difficulty = 1 + ((index - 1) * 5 // total)
    challenge: dict[str, Any] = {
        "title": spec["title"],
        "prompt": spec["prompt"],
        "activity_type": kind,
        "difficulty": difficulty,
        "points": _POINTS[difficulty],
        "position": index,
        "allowed_blocks": [],
        "time_limit_seconds": None,
        "cases": [],
    }
    if kind == "classify":
        categories = list(spec["categories"])
        items = [
            {"id": f"e{number}", "text": text, "category": category}
            for number, (text, category) in enumerate(spec["items"], start=1)
        ]
        if any(item["category"] not in categories for item in items):
            raise ValueError(f"{spec['title']}: categoría desconocida.")
        challenge["restrictions"] = {"categories": categories, "items": items}
        solve = spec["solve"]
    elif kind == "order":
        steps = list(spec["steps"])
        if len(steps) != len(set(steps)):
            raise ValueError(f"{spec['title']}: instrucciones repetidas.")
        shown = steps[1:] + steps[:1]
        items = [{"id": f"e{number}", "text": text} for number, text in enumerate(shown, start=1)]
        by_text = {item["text"]: item["id"] for item in items}
        challenge["restrictions"] = {
            "items": items,
            "solution": [by_text[text] for text in steps],
        }
        solve = spec["solve"]
    elif kind == "predict":
        output, workspace, source = _prove(spec["source"], [], spec["title"])
        lines = output.splitlines()
        if not lines:
            raise ValueError(f"{spec['title']}: no escribe nada.")
        question = (
            "¿Qué se escribe?"
            if len(lines) == 1
            else "¿Qué se escribe en la última línea?"
        )
        challenge["restrictions"] = {
            "question": question,
            "accepted": [lines[-1]],
            "source": source,
            "starter": workspace,
        }
        solve = f"se escribe {lines[-1]}."
    else:
        output, _workspace, _source = _prove(spec["source"], list(spec["inputs"]), spec["title"])
        challenge["restrictions"] = {
            "question": spec["question"],
            "accepted": list(spec["accepted"]),
        }
        challenge["cases"] = [
            {
                "name": "esperado",
                "inputs": list(spec["inputs"]),
                "expected_output": output,
                "kind": "normal",
                "position": 1,
            }
        ]
        solve = spec["solve"]
    challenge["hints"] = _hints(kind, spec["hint"], solve)
    _check_lengths(challenge)
    return challenge


def _hints(kind: str, hint: str, solve: str) -> list[dict[str, Any]]:
    body = f"{_SOLUTION}: {solve}"
    if len(body) > 500:
        body = body[:497] + "..."
    return [
        {"level": 1, "position": 1, "body": hint},
        {"level": 2, "position": 1, "body": _SECOND[kind]},
        {"level": 5, "position": 1, "body": body},
    ]


def _check_lengths(challenge: dict[str, Any]) -> None:
    if len(challenge["title"]) > 120 or len(challenge["prompt"]) > 4000:
        raise ValueError(f"{challenge['title']}: texto demasiado largo.")
    for hint in challenge["hints"]:
        if len(hint["body"]) > 500:
            raise ValueError(f"{challenge['title']}: pista demasiado larga.")


def _prove(source: str, inputs: list[str], title: str) -> tuple[str, dict[str, Any], str]:
    imported = workspace_from_source(source)
    errors = [item for item in imported.diagnostics if item.severity == "error"]
    if imported.workspace is None or errors:
        detail = errors[0].message if errors else "sin lienzo"
        raise ValueError(f"{title}: {detail}")
    adapted = adapt_workspace(imported.workspace)
    errors = [item for item in adapted.diagnostics if item.severity == "error"]
    if adapted.program is None or errors:
        detail = errors[0].message if errors else "sin programa"
        raise ValueError(f"{title}: {detail}")
    result = _run(adapted.program, adapted.source, inputs)
    if result.status != "completed" or not result.output.endswith("\n"):
        raise ValueError(f"{title}: la ejecución quedó en {result.status}.")
    json.dumps(imported.workspace)
    return result.output, imported.workspace, adapted.source


def _run(program: object, source: str, inputs: list[str]):
    interpreter = Interpreter(
        program,
        source,
        STRICT,
        Limits.from_profile(STRICT),
        Cancellation(),
        time.monotonic,
        random.Random(0),
    )
    return drive(interpreter.run(), inputs, (), interpreter.cells)


def _c(title: str, prompt: str, categories: list[str], items: list[tuple[str, str]], hint: str, solve: str):
    return {
        "kind": "classify",
        "title": title,
        "prompt": prompt,
        "categories": categories,
        "items": items,
        "hint": hint,
        "solve": solve,
    }


def _o(title: str, prompt: str, steps: list[str], hint: str, solve: str):
    return {
        "kind": "order",
        "title": title,
        "prompt": prompt,
        "steps": steps,
        "hint": hint,
        "solve": solve,
    }


def _p(title: str, prompt: str, source: str, hint: str):
    return {"kind": "predict", "title": title, "prompt": prompt, "source": source, "hint": hint}


def _b(
    title: str,
    prompt: str,
    question: str,
    accepted: list[str],
    inputs: list[str],
    source: str,
    hint: str,
    solve: str,
):
    return {
        "kind": "build",
        "title": title,
        "prompt": prompt,
        "question": question,
        "accepted": accepted,
        "inputs": inputs,
        "source": source,
        "hint": hint,
        "solve": solve,
    }


_UNITS: tuple[tuple[str, str, list[dict[str, Any]]], ...] = (
    (
        "variable",
        "Variables",
        [
            _c(
                "Nombre, tipo y valor",
                "Una variable tiene nombre, tipo y un valor guardado. Clasifica cada frase.",
                ["nombre", "tipo", "valor"],
                [
                    ("La palabra edad en Definir edad", "nombre"),
                    ("Entero, escrito después de Como", "tipo"),
                    ("El 15 que quedó guardado en edad", "valor"),
                    ("La palabra precio, a la izquierda de la flecha", "nombre"),
                ],
                "El nombre identifica la caja. El tipo dice qué puede guardar. El valor es el contenido.",
                "edad y precio son nombres, Entero es el tipo y 15 es el valor.",
            ),
            _c(
                "Elige el tipo que corresponde",
                "Clasifica cada dato según el tipo con el que conviene declararlo.",
                ["Entero", "Real", "Cadena", "Lógico"],
                [
                    ("La cantidad de alumnos de un grupo", "Entero"),
                    ("La estatura en metros, con decimales", "Real"),
                    ("El mensaje de bienvenida", "Cadena"),
                    ("Si la tarea ya fue entregada", "Lógico"),
                ],
                "Entero no lleva decimales. Real sí. Cadena es texto. Lógico es Verdadero o Falso.",
                "alumnos es Entero, estatura es Real, el mensaje es Cadena y la entrega es Lógico.",
            ),
            _c(
                "Dato o instrucción",
                "Separa lo que es un dato de lo que es una instrucción del lenguaje.",
                ["dato", "instrucción"],
                [
                    ("edad", "dato"),
                    ("Definir", "instrucción"),
                    ("el texto hola", "dato"),
                    ("Escribir", "instrucción"),
                    ("3.5", "dato"),
                    ("Leer", "instrucción"),
                ],
                "Las instrucciones dicen qué hacer. Los datos son números, textos o nombres de variables.",
                "Definir, Escribir y Leer son instrucciones. edad, hola y 3.5 son datos.",
            ),
            _c(
                "Qué puede cambiar",
                "Clasifica qué parte de una variable puede cambiar durante el programa.",
                ["puede cambiar", "se queda fijo"],
                [
                    ("El número guardado en total", "puede cambiar"),
                    ("El nombre total", "se queda fijo"),
                    ("El tipo elegido al definirla", "se queda fijo"),
                    ("El resultado nuevo de una suma que se vuelve a guardar", "puede cambiar"),
                ],
                "El nombre y el tipo se eligen al declarar. El valor se reemplaza con cada asignación.",
                "cambian el número de total y el resultado nuevo. El nombre y el tipo se quedan fijos.",
            ),
            _c(
                "Variable o literal",
                "Clasifica cada pieza: o nombra una caja, o es un valor escrito tal cual.",
                ["variable", "literal"],
                [
                    ("n dentro de Escribir n", "variable"),
                    ("12 dentro de n <- 12", "literal"),
                    ("mensaje dentro de mensaje <- ok", "variable"),
                    ("el texto ok dentro de esa asignación", "literal"),
                ],
                "La variable tiene nombre y puede cambiar. El literal es el valor escrito en el programa.",
                "n y mensaje son variables. 12 y ok son literales.",
            ),
            _o(
                "Declarar antes de usar",
                "Ordena los pasos para crear la variable edad y mostrarla.",
                [
                    "Elegir el nombre edad",
                    "Elegir el tipo Entero",
                    "Escribir Definir edad Como Entero",
                    "Guardar un número en edad",
                    "Escribir edad",
                ],
                "Sin Definir, la variable todavía no existe.",
                "primero el nombre y el tipo, luego Definir, después guardar y al final Escribir.",
            ),
            _o(
                "Preparar un saludo",
                "Ordena los pasos para guardar un texto y mostrarlo.",
                [
                    "Definir saludo Como Cadena",
                    "Guardar hola en saludo",
                    "Escribir saludo",
                ],
                "La cadena se declara antes de guardar el texto.",
                "se define saludo, se guarda hola y se escribe.",
            ),
            _o(
                "Preparar un lógico",
                "Ordena los pasos para guardar Falso y mostrarlo.",
                [
                    "Definir listo Como Logico",
                    "Guardar Falso en listo",
                    "Escribir listo",
                ],
                "Verdadero y Falso solo caben en un Lógico.",
                "se define listo, se guarda Falso y se escribe.",
            ),
            _o(
                "Dejar lista una variable real",
                "Ordena los pasos para guardar una estatura con decimales.",
                [
                    "Definir estatura Como Real",
                    "Guardar 1.68 en estatura",
                    "Escribir estatura",
                ],
                "Los decimales piden el tipo Real.",
                "se define estatura como Real, se guarda 1.68 y se escribe.",
            ),
            _p(
                "La caja con siete",
                "Anticipa el número que se escribe.",
                algo(
                    [
                        "Definir n Como Entero;",
                        "n <- 7;",
                        "Escribir n;",
                    ]
                ),
                "n recibe 7 y ese es el valor que se muestra.",
            ),
            _p(
                "El texto guardado",
                "Anticipa el texto que se escribe.",
                algo(
                    [
                        "Definir mensaje Como Cadena;",
                        'mensaje <- "hola";',
                        "Escribir mensaje;",
                    ]
                ),
                "Escribir muestra el contenido, sin las comillas.",
            ),
            _p(
                "La bandera verdadera",
                "Anticipa lo que se escribe.",
                algo(
                    [
                        "Definir activo Como Logico;",
                        "activo <- Verdadero;",
                        "Escribir activo;",
                    ]
                ),
                "Un lógico se escribe como Verdadero o Falso.",
            ),
            _p(
                "La estatura guardada",
                "Anticipa el número que se escribe.",
                algo(
                    [
                        "Definir estatura Como Real;",
                        "estatura <- 1.68;",
                        "Escribir estatura;",
                    ]
                ),
                "El real conserva los decimales que se guardaron.",
            ),
            _p(
                "La inicial guardada",
                "Anticipa el carácter que se escribe.",
                algo(
                    [
                        "Definir inicial Como Caracter;",
                        "inicial <- 'A';",
                        "Escribir inicial;",
                    ]
                ),
                "Un carácter se escribe sin las comillas simples.",
            ),
            _b(
                "Publicar la edad",
                "Define una variable entera llamada edad, guárdale 21 y escríbela.",
                "¿Con qué palabra se declara una variable?",
                ["Definir"],
                [],
                algo(["Definir edad Como Entero;", "edad <- 21;", "Escribir edad;"]),
                "Hacen falta Definir, la flecha de asignación y Escribir.",
                "define edad como Entero, asígnale 21 y escríbela.",
            ),
            _b(
                "Publicar la bienvenida",
                "Define una cadena llamada saludo, guárdale bienvenida y escríbela.",
                "¿Qué tipo guarda un texto?",
                ["Cadena"],
                [],
                algo(
                    [
                        "Definir saludo Como Cadena;",
                        'saludo <- "bienvenida";',
                        "Escribir saludo;",
                    ]
                ),
                "El texto va entre comillas y la variable es Cadena.",
                "define saludo como Cadena, asígnale bienvenida y escríbela.",
            ),
            _b(
                "Publicar la bandera",
                "Define un lógico llamado listo, guárdale Falso y escríbelo.",
                "¿Qué dos valores puede guardar un lógico?",
                ["Verdadero y Falso", "Verdadero, Falso"],
                [],
                algo(
                    [
                        "Definir listo Como Logico;",
                        "listo <- Falso;",
                        "Escribir listo;",
                    ]
                ),
                "Falso no lleva comillas: es un valor lógico.",
                "define listo como Logico, asígnale Falso y escríbelo.",
            ),
            _b(
                "Publicar la altura",
                "Define un real llamado altura, guárdale 1.75 y escríbelo.",
                "¿Qué tipo admite decimales?",
                ["Real"],
                [],
                algo(["Definir altura Como Real;", "altura <- 1.75;", "Escribir altura;"]),
                "1.75 no cabe en un Entero.",
                "define altura como Real, asígnale 1.75 y escríbela.",
            ),
        ],
    ),
    (
        "assignment",
        "Asignación",
        [
            _c(
                "Asignar o comparar",
                "Clasifica cada expresión: o guarda un valor, o compara dos valores.",
                ["asignación", "comparación"],
                [
                    ("n <- 3", "asignación"),
                    ("n = 3", "comparación"),
                    ("total <- total + 1", "asignación"),
                    ("edad >= 18", "comparación"),
                ],
                "La flecha guarda. El igual y los signos >, < comparan.",
                "n <- 3 y total <- total + 1 asignan. n = 3 y edad >= 18 comparan.",
            ),
            _c(
                "Qué queda después de asignar",
                "Clasifica qué le pasa al valor anterior cuando se vuelve a asignar.",
                ["se conserva", "se reemplaza"],
                [
                    ("El valor que tenía la variable antes de la flecha", "se reemplaza"),
                    ("El valor de otra variable que no se tocó", "se conserva"),
                    ("El número escrito a la derecha de la flecha", "se conserva"),
                    ("La copia que se hizo antes de cambiar el original", "se conserva"),
                ],
                "La flecha sustituye el contenido de esa variable. Las demás siguen igual.",
                "se reemplaza el valor anterior de esa variable. Lo demás se conserva.",
            ),
            _c(
                "Lado izquierdo y lado derecho",
                "En una asignación, clasifica qué va a cada lado de la flecha.",
                ["izquierda", "derecha"],
                [
                    ("El nombre de la variable que recibe", "izquierda"),
                    ("El valor o la cuenta que se guarda", "derecha"),
                    ("precio, cuando se escribe precio <- 40", "izquierda"),
                    ("40, en esa misma línea", "derecha"),
                ],
                "A la izquierda va el nombre. A la derecha va lo que se calcula.",
                "el nombre va a la izquierda y el valor o la cuenta a la derecha.",
            ),
            _c(
                "Una copia no es un enlace",
                "Después de b <- a, clasifica qué ocurre si más tarde cambia a.",
                ["cambia", "no cambia"],
                [
                    ("El valor de a", "cambia"),
                    ("El valor que ya se copió en b", "no cambia"),
                    ("Una tercera variable que nadie asignó", "no cambia"),
                    ("El resultado de volver a leer a", "cambia"),
                ],
                "b guarda una copia del número. No sigue a a.",
                "a cambia y volver a leerla también. b y la tercera variable no cambian.",
            ),
            _c(
                "Actualizar o empezar de cero",
                "Clasifica si la asignación usa el valor que ya había o lo ignora.",
                ["usa el valor anterior", "ignora el valor anterior"],
                [
                    ("total <- total + precio", "usa el valor anterior"),
                    ("total <- 0", "ignora el valor anterior"),
                    ("n <- n * 2", "usa el valor anterior"),
                    ("n <- 5", "ignora el valor anterior"),
                ],
                "Si el nombre aparece a la derecha, el cálculo usa lo que ya había.",
                "total + precio y n * 2 usan el anterior. total <- 0 y n <- 5 lo ignoran.",
            ),
            _o(
                "Sumar uno al contador",
                "Ordena los pasos para que n pase de 4 a 5 y se muestre.",
                [
                    "Definir n Como Entero",
                    "Guardar 4 en n",
                    "Guardar n + 1 en n",
                    "Escribir n",
                ],
                "La segunda asignación tiene que ocurrir cuando n ya vale 4.",
                "se define n, se guarda 4, se le suma 1 y se escribe.",
            ),
            _o(
                "Copiar y después cambiar",
                "Ordena los pasos para copiar a en b y luego cambiar solo a.",
                [
                    "Definir a y b como enteros",
                    "Guardar 2 en a",
                    "Guardar a en b",
                    "Guardar 9 en a",
                    "Escribir b",
                ],
                "La copia se hace antes de cambiar el original.",
                "se definen, se guarda 2 en a, se copia a b, se cambia a y se escribe b.",
            ),
            _o(
                "Intercambiar dos cajas",
                "Ordena los pasos para intercambiar los valores de a y b.",
                [
                    "Definir a, b y aux como enteros",
                    "Guardar a en aux",
                    "Guardar b en a",
                    "Guardar aux en b",
                ],
                "Sin una caja auxiliar, el primer valor se pierde.",
                "se guardan en aux, luego b pasa a a y aux pasa a b.",
            ),
            _o(
                "Acumular un precio",
                "Ordena los pasos para sumar 30 a un total que empezó en 0.",
                [
                    "Definir total Como Entero",
                    "Guardar 0 en total",
                    "Guardar total + 30 en total",
                    "Escribir total",
                ],
                "El acumulador empieza en 0 antes de sumar.",
                "se define total, se pone en 0, se le suman 30 y se escribe.",
            ),
            _p(
                "Después de sumar uno",
                "n empieza en 4 y luego se le suma 1. Anticipa lo que se escribe.",
                algo(["Definir n Como Entero;", "n <- 4;", "n <- n + 1;", "Escribir n;"]),
                "La segunda asignación usa el 4 que n ya tenía.",
            ),
            _p(
                "Después de restar",
                "Anticipa el número que se escribe.",
                algo(["Definir n Como Entero;", "n <- 10;", "n <- n - 3;", "Escribir n;"]),
                "A 10 se le restan 3.",
            ),
            _p(
                "La copia que se quedó",
                "b copia a a y después a cambia. Anticipa lo que se escribe.",
                algo(
                    [
                        "Definir a, b Como Entero;",
                        "a <- 2;",
                        "b <- a;",
                        "a <- 9;",
                        "Escribir b;",
                    ]
                ),
                "b se copió cuando a todavía valía 2.",
            ),
            _p(
                "El original que cambió",
                "Mira el mismo programa, pero ahora se escribe a. Anticipa el número.",
                algo(
                    [
                        "Definir a, b Como Entero;",
                        "a <- 2;",
                        "b <- a;",
                        "a <- 9;",
                        "Escribir a;",
                    ]
                ),
                "La última asignación de a es 9.",
            ),
            _p(
                "Tres asignaciones seguidas",
                "Anticipa el número que queda en n.",
                algo(
                    [
                        "Definir n Como Entero;",
                        "n <- 1;",
                        "n <- n * 4;",
                        "n <- n + 1;",
                        "Escribir n;",
                    ]
                ),
                "Primero 1 por 4, y a ese resultado se le suma 1.",
            ),
            _b(
                "Dejar el contador en diez",
                "Define n como entero, guárdale 8 y luego suma 2. Escribe el resultado.",
                "¿Qué símbolo guarda un valor en una variable?",
                ["<-"],
                [],
                algo(["Definir n Como Entero;", "n <- 8;", "n <- n + 2;", "Escribir n;"]),
                "La segunda asignación debe usar el 8 que ya está en n.",
                "n pasa de 8 a 10 y se escribe 10.",
            ),
            _b(
                "Mostrar la copia",
                "a vale 3 y b copia a a. Después a pasa a 9. Escribe b.",
                "¿La copia sigue los cambios posteriores del original?",
                ["no"],
                [],
                algo(
                    [
                        "Definir a, b Como Entero;",
                        "a <- 3;",
                        "b <- a;",
                        "a <- 9;",
                        "Escribir b;",
                    ]
                ),
                "Copia a en b antes de cambiar a.",
                "b se queda en 3 y eso es lo que se escribe.",
            ),
            _b(
                "Intercambiar y mostrar",
                "a empieza en 3 y b en 8. Intercámbialos con una auxiliar y escribe primero a y luego b.",
                "¿Cómo se llama la variable que guarda el valor temporal?",
                ["auxiliar", "aux", "temporal"],
                [],
                algo(
                    [
                        "Definir a, b, aux Como Entero;",
                        "a <- 3;",
                        "b <- 8;",
                        "aux <- a;",
                        "a <- b;",
                        "b <- aux;",
                        "Escribir a;",
                        "Escribir b;",
                    ]
                ),
                "aux guarda el 3 antes de que a reciba el 8.",
                "al terminar, a vale 8 y b vale 3.",
            ),
            _b(
                "Acumular dos precios",
                "total empieza en 0. Súmale 20 y después 15. Escribe total.",
                "¿Qué variable conviene para ir sumando?",
                ["acumulador", "total"],
                [],
                algo(
                    [
                        "Definir total Como Entero;",
                        "total <- 0;",
                        "total <- total + 20;",
                        "total <- total + 15;",
                        "Escribir total;",
                    ]
                ),
                "Cada suma usa el total que ya llevabas.",
                "0 + 20 + 15 deja 35 en total.",
            ),
        ],
    ),
    (
        "io",
        "Entrada y salida",
        [
            _c(
                "Entrada, proceso o salida",
                "Una caja cobra un producto. Clasifica cada frase.",
                ["entrada", "proceso", "salida"],
                [
                    ("El precio que escribe la persona", "entrada"),
                    ("Multiplicar precio por cantidad", "proceso"),
                    ("El total que aparece en pantalla", "salida"),
                    ("El nombre que se lee del teclado", "entrada"),
                ],
                "Entrada es lo que llega. Proceso es el cálculo. Salida es lo que se muestra.",
                "precio y nombre son entrada, la multiplicación es proceso y el total es salida.",
            ),
            _c(
                "Leer o escribir",
                "Clasifica la instrucción según la dirección del dato.",
                ["hacia el programa", "hacia la pantalla"],
                [
                    ("Leer edad", "hacia el programa"),
                    ("Escribir total", "hacia la pantalla"),
                    ("Leer nombre", "hacia el programa"),
                    ("Escribir un mensaje fijo", "hacia la pantalla"),
                ],
                "Leer mete un dato. Escribir lo muestra.",
                "Leer va hacia el programa. Escribir va hacia la pantalla.",
            ),
            _c(
                "Qué hace falta para leer",
                "Clasifica cada requisito de un Leer.",
                ["hace falta", "no hace falta"],
                [
                    ("Una variable ya definida", "hace falta"),
                    ("Un valor escrito por la persona", "hace falta"),
                    ("Que la variable sea el resultado de una división", "no hace falta"),
                    ("Comillas alrededor del nombre de la variable", "no hace falta"),
                ],
                "Leer guarda en una variable. El nombre no lleva comillas.",
                "hacen falta la variable y el valor tecleado. No hacen falta la división ni las comillas.",
            ),
            _c(
                "Texto fijo o valor de variable",
                "Clasifica lo que Escribir va a mostrar.",
                ["texto fijo", "valor de variable"],
                [
                    ('Escribir "hola"', "texto fijo"),
                    ("Escribir total", "valor de variable"),
                    ('Escribir "El area es "', "texto fijo"),
                    ("Escribir precio", "valor de variable"),
                ],
                "Las comillas marcan un texto fijo. Sin comillas, se muestra la variable.",
                "hola y El area es son textos fijos. total y precio son variables.",
            ),
            _c(
                "Restricción o dato",
                "Clasifica cada frase de un formulario.",
                ["dato", "restricción"],
                [
                    ("La cantidad que se lee", "dato"),
                    ("La cantidad no puede ser negativa", "restricción"),
                    ("El nombre del alumno", "dato"),
                    ("El nombre no puede quedar vacío", "restricción"),
                ],
                "Una restricción dice qué no está permitido. No es un valor que se lea.",
                "cantidad y nombre son datos. Lo negativo y el vacío son restricciones.",
            ),
            _o(
                "Preguntar el nombre",
                "Ordena los pasos para leer un nombre y mostrarlo.",
                [
                    "Definir nombre Como Cadena",
                    "Leer nombre",
                    "Escribir nombre",
                ],
                "No se puede leer una variable que todavía no existe.",
                "se define nombre, se lee y se escribe.",
            ),
            _o(
                "Preguntar dos números",
                "Ordena los pasos para leer dos enteros y escribir su suma.",
                [
                    "Definir a, b y suma como enteros",
                    "Leer a",
                    "Leer b",
                    "Guardar a + b en suma",
                    "Escribir suma",
                ],
                "La suma se calcula cuando los dos números ya se leyeron.",
                "se definen, se leen a y b, se guarda la suma y se escribe.",
            ),
            _o(
                "Saludar con el nombre",
                "Ordena los pasos para leer un nombre y escribir Hola junto a ese nombre.",
                [
                    "Definir nombre y saludo como cadenas",
                    "Leer nombre",
                    "Armar el saludo con el nombre",
                    "Escribir saludo",
                ],
                "Concatenar une textos. El nombre tiene que estar leído antes.",
                "se definen, se lee el nombre, se arma el saludo y se escribe.",
            ),
            _o(
                "Mostrar un aviso y luego el dato",
                "Ordena los pasos para avisar y después mostrar el número leído.",
                [
                    "Definir n Como Entero",
                    "Escribir el aviso Ingresa un numero",
                    "Leer n",
                    "Escribir n",
                ],
                "El aviso es un Escribir de texto. El dato se lee después.",
                "se define n, se escribe el aviso, se lee n y se escribe n.",
            ),
            _p(
                "Dos líneas en pantalla",
                "Anticipa la última línea que se escribe.",
                algo(['Escribir "hola";', 'Escribir "mundo";']),
                "Cada Escribir ocupa su propia línea. La pregunta pide la última.",
            ),
            _p(
                "Texto y número pegados",
                "Anticipa lo que se escribe. Escribir junta las partes sin agregar espacios.",
                algo(
                    [
                        "Definir n Como Entero;",
                        "n <- 5;",
                        'Escribir "total:", n;',
                    ]
                ),
                "Si quieres un espacio, tiene que ir dentro del texto.",
            ),
            _p(
                "El aviso no cambia el dato",
                "Anticipa el número que se escribe al final.",
                algo(
                    [
                        "Definir n Como Entero;",
                        "n <- 8;",
                        'Escribir "listo";',
                        "Escribir n;",
                    ]
                ),
                "El texto listo no modifica n.",
            ),
            _p(
                "Unir dos palabras",
                "Anticipa el texto que se escribe.",
                algo(['Escribir Concatenar("buenos", "dias");']),
                "Concatenar no agrega un espacio por su cuenta.",
            ),
            _p(
                "La longitud del mensaje",
                "Anticipa el número que se escribe.",
                algo(['Escribir Longitud("hola");']),
                "Longitud cuenta los caracteres. hola tiene cuatro.",
            ),
            _b(
                "Devolver el entero leído",
                "Lee un entero llamado n y escríbelo tal cual.",
                "¿Qué instrucción guarda lo que escribe la persona?",
                ["Leer"],
                ["15"],
                algo(["Definir n Como Entero;", "Leer n;", "Escribir n;"]),
                "La entrada de prueba es 15.",
                "define n, léelo y escríbelo. Con 15 se escribe 15.",
            ),
            _b(
                "Suma de dos lecturas",
                "Lee dos enteros y escribe su suma.",
                "¿Cuántos Leer hacen falta para dos números?",
                ["2", "dos"],
                ["4", "6"],
                algo(
                    [
                        "Definir a, b, suma Como Entero;",
                        "Leer a;",
                        "Leer b;",
                        "suma <- a + b;",
                        "Escribir suma;",
                    ]
                ),
                "Las entradas llegan en orden: primero 4 y después 6.",
                "4 + 6 se escribe como 10.",
            ),
            _b(
                "Saludo con nombre",
                "Lee una cadena llamada nombre y escribe Hola seguido de un espacio y el nombre.",
                "¿Qué función une dos textos?",
                ["Concatenar"],
                ["Ana"],
                algo(
                    [
                        "Definir nombre Como Cadena;",
                        "Leer nombre;",
                        'Escribir Concatenar("Hola ", nombre);',
                    ]
                ),
                "El espacio va dentro del texto Hola.",
                "con Ana se escribe Hola Ana.",
            ),
            _b(
                "Eco de un real",
                "Lee un real llamado medida y escríbelo.",
                "¿Qué tipo admite el decimal 2.5?",
                ["Real"],
                ["2.5"],
                algo(["Definir medida Como Real;", "Leer medida;", "Escribir medida;"]),
                "2.5 no es un Entero.",
                "define medida como Real, léela y escríbela.",
            ),
        ],
    ),
    (
        "operator",
        "Operadores",
        [
            _c(
                "Aritmético, relacional o lógico",
                "Clasifica cada operador.",
                ["aritmético", "relacional", "lógico"],
                [
                    ("+", "aritmético"),
                    (">", "relacional"),
                    ("Y", "lógico"),
                    ("MOD", "aritmético"),
                    ("=", "relacional"),
                    ("NO", "lógico"),
                ],
                "Aritmético calcula. Relacional compara. Lógico une condiciones.",
                "+ y MOD son aritméticos, > y = son relacionales, Y y NO son lógicos.",
            ),
            _c(
                "Enteros o decimales",
                "Clasifica qué operadores exigen enteros y cuáles admiten decimales.",
                ["solo enteros", "admite decimales"],
                [
                    ("MOD", "solo enteros"),
                    ("DIV", "solo enteros"),
                    ("/", "admite decimales"),
                    ("+", "admite decimales"),
                ],
                "MOD y DIV no aceptan reales. La barra / sí.",
                "MOD y DIV son solo enteros. / y + admiten decimales.",
            ),
            _c(
                "Resultado de la operación",
                "Clasifica el tipo del resultado.",
                ["número", "lógico"],
                [
                    ("3 + 4", "número"),
                    ("3 > 4", "lógico"),
                    ("Verdadero Y Falso", "lógico"),
                    ("10 MOD 3", "número"),
                ],
                "Comparar o unir con Y produce Verdadero o Falso. Sumar produce un número.",
                "la suma y el módulo son números. La comparación y el Y son lógicos.",
            ),
            _c(
                "Qué se evalúa primero",
                "Clasifica qué parte se resuelve primero en 2 + 3 * 4.",
                ["primero", "después"],
                [
                    ("La multiplicación 3 * 4", "primero"),
                    ("La suma con el 2", "después"),
                    ("El paréntesis, si lo hubiera", "primero"),
                    ("Leer el resultado de izquierda a derecha sin mirar el operador", "después"),
                ],
                "La multiplicación gana a la suma. Los paréntesis ganan a las dos.",
                "primero van la multiplicación y los paréntesis. La suma y el recorrido ciego van después.",
            ),
            _c(
                "Cociente o residuo",
                "Clasifica qué devuelve cada división entera.",
                ["cociente", "residuo"],
                [
                    ("10 DIV 3", "cociente"),
                    ("10 MOD 3", "residuo"),
                    ("La parte entera de la división", "cociente"),
                    ("Lo que sobra al repartir", "residuo"),
                ],
                "DIV se queda con el cociente. MOD se queda con lo que sobra.",
                "DIV y la parte entera son el cociente. MOD y lo que sobra son el residuo.",
            ),
            _o(
                "Calcular un total con impuesto",
                "Ordena el cálculo de un precio de 100 más el 16 por ciento, en enteros.",
                [
                    "Definir precio e impuesto como enteros",
                    "Guardar 100 en precio",
                    "Guardar precio * 16 / 100 en impuesto",
                    "Escribir precio + impuesto",
                ],
                "El impuesto se calcula antes de sumarlo al precio.",
                "se define, se guarda 100, se calcula el impuesto y se escribe la suma.",
            ),
            _o(
                "Saber si es par",
                "Ordena los pasos para escribir el residuo de n entre 2.",
                [
                    "Definir n Como Entero",
                    "Guardar 8 en n",
                    "Calcular n MOD 2",
                    "Escribir ese residuo",
                ],
                "Un par deja residuo 0.",
                "se define n, se guarda 8, se calcula el módulo y se escribe.",
            ),
            _o(
                "Comparar antes de decidir",
                "Ordena los pasos para saber si edad llega a 18.",
                [
                    "Definir edad Como Entero",
                    "Guardar 18 en edad",
                    "Comparar edad >= 18",
                    "Escribir el lógico resultante",
                ],
                "La comparación produce Verdadero o Falso.",
                "se define edad, se guarda 18, se compara y se escribe el lógico.",
            ),
            _o(
                "Negar una bandera",
                "Ordena los pasos para escribir lo contrario de activo.",
                [
                    "Definir activo Como Logico",
                    "Guardar Falso en activo",
                    "Calcular NO activo",
                    "Escribir el resultado",
                ],
                "NO cambia Verdadero por Falso y al revés.",
                "se define activo, se guarda Falso, se niega y se escribe.",
            ),
            _o(
                "Forzar el orden con paréntesis",
                "Ordena los pasos para sumar primero y multiplicar después.",
                [
                    "Definir total Como Entero",
                    "Sumar 2 + 3",
                    "Multiplicar ese resultado por 4",
                    "Guardar el producto en total",
                    "Escribir total",
                ],
                "Sin paréntesis, la multiplicación ocurriría antes.",
                "se define total, se suma, se multiplica, se guarda y se escribe.",
            ),
            _p(
                "La multiplicación gana",
                "Anticipa el resultado de 2 + 3 * 4.",
                algo(["Escribir 2 + 3 * 4;"]),
                "Primero se multiplica 3 * 4.",
            ),
            _p(
                "Los paréntesis ganan",
                "Anticipa el resultado de (2 + 3) * 4.",
                algo(["Escribir (2 + 3) * 4;"]),
                "El paréntesis obliga a sumar antes de multiplicar.",
            ),
            _p(
                "Cociente entero",
                "Anticipa lo que devuelve 10 DIV 3.",
                algo(["Escribir 10 DIV 3;"]),
                "DIV no conserva el decimal.",
            ),
            _p(
                "Residuo de la repartición",
                "Anticipa lo que devuelve 10 MOD 3.",
                algo(["Escribir 10 MOD 3;"]),
                "10 = 3 * 3 + 1. El residuo es 1.",
            ),
            _p(
                "Una comparación",
                "Anticipa el lógico que se escribe.",
                algo(["Escribir 5 > 3;"]),
                "5 es mayor que 3, así que la comparación es verdadera.",
            ),
            _b(
                "El doble de lo leído",
                "Lee un entero n y escribe su doble.",
                "¿Qué símbolo multiplica dos valores?",
                ["*"],
                ["6"],
                algo(
                    [
                        "Definir n Como Entero;",
                        "Leer n;",
                        "Escribir n * 2;",
                    ]
                ),
                "El doble es el número por 2.",
                "con la entrada 6 se escribe 12.",
            ),
            _b(
                "El residuo",
                "Lee un entero n y escribe n MOD 2.",
                "¿Qué operador devuelve lo que sobra de una división entera?",
                ["MOD", "%"],
                ["9"],
                algo(["Definir n Como Entero;", "Leer n;", "Escribir n MOD 2;"]),
                "MOD solo acepta enteros.",
                "9 MOD 2 deja 1.",
            ),
            _b(
                "Promedio de dos reales",
                "Lee dos reales y escribe su promedio.",
                "¿Qué operador divide conservando decimales?",
                ["/", "barra"],
                ["8", "10"],
                algo(
                    [
                        "Definir a, b, promedio Como Real;",
                        "Leer a;",
                        "Leer b;",
                        "promedio <- (a + b) / 2;",
                        "Escribir promedio;",
                    ]
                ),
                "Suma primero, entre paréntesis, y divide entre 2.",
                "8 y 10 promedian 9.",
            ),
            _b(
                "¿Llega a la mayoría?",
                "Lee una edad entera y escribe el lógico de edad >= 18.",
                "¿Qué operador pregunta si el primero es mayor o igual?",
                [">=", "mayor o igual"],
                ["17"],
                algo(["Definir edad Como Entero;", "Leer edad;", "Escribir edad >= 18;"]),
                "El resultado es Verdadero o Falso, no un número.",
                "17 no llega a 18, así que se escribe Falso.",
            ),
            _b(
                "Residuo con decimales",
                "Lee dos reales positivos y escribe el residuo de num1 entre num2. MOD no sirve con reales.",
                "¿Qué función quita los decimales hacia cero?",
                ["Trunc"],
                ["7.5", "2"],
                algo(
                    [
                        "Definir num1, num2, total Como Real;",
                        "Leer num1;",
                        "Leer num2;",
                        "total <- num1 - Trunc(num1 / num2) * num2;",
                        "Escribir total;",
                    ]
                ),
                "El residuo es el número menos las veces enteras que cabe el divisor.",
                "7.5 entre 2 deja 1.5.",
            ),
        ],
    ),
    (
        "if",
        "Decisiones",
        [
            _c(
                "Condición y ramas",
                "Clasifica cada pieza de un Si.",
                ["condición", "rama entonces", "rama sino"],
                [
                    ("edad >= 18", "condición"),
                    ("Escribir mayor", "rama entonces"),
                    ("Escribir menor", "rama sino"),
                    ("n = 0", "condición"),
                ],
                "La condición es un lógico. Cada rama es lo que se hace si corresponde.",
                "las comparaciones son la condición. mayor va en entonces y menor en sino.",
            ),
            _c(
                "Qué rama corre",
                "La condición resultó Falso. Clasifica qué ocurre.",
                ["se ejecuta", "no se ejecuta"],
                [
                    ("El bloque de Entonces", "no se ejecuta"),
                    ("El bloque de Sino", "se ejecuta"),
                    ("Un Escribir que está después de FinSi", "se ejecuta"),
                    ("La otra rama, la que no corresponde", "no se ejecuta"),
                ],
                "Solo entra una rama. Lo que está fuera del Si se hace igual.",
                "con Falso no entra Entonces. Entran Sino y lo que va después de FinSi.",
            ),
            _c(
                "Una condición o dos",
                "Clasifica cómo se combinan las condiciones.",
                ["las dos", "al menos una", "lo contrario"],
                [
                    ("edad >= 18 Y entregado", "las dos"),
                    ("edad >= 18 O permiso", "al menos una"),
                    ("NO activo", "lo contrario"),
                    ("nota >= 6 Y asistencia", "las dos"),
                ],
                "Y pide las dos. O pide una. NO invierte.",
                "Y exige las dos. O exige al menos una. NO es lo contrario.",
            ),
            _c(
                "Si anidado",
                "Clasifica cada pregunta de un Si dentro de otro Si.",
                ["primera pregunta", "pregunta interior"],
                [
                    ("Si a > b", "primera pregunta"),
                    ("Si a = b, escrito dentro del Sino", "pregunta interior"),
                    ("La comparación más externa", "primera pregunta"),
                    ("La comparación que solo se mira si la de afuera falló", "pregunta interior"),
                ],
                "La pregunta interior solo se evalúa si el programa entra a esa rama.",
                "a > b y la comparación externa son la primera. La igualdad interior es la otra.",
            ),
            _c(
                "Dato que decide",
                "Clasifica qué se usa como condición y qué es solo un mensaje.",
                ["condición", "mensaje"],
                [
                    ("nota >= 60", "condición"),
                    ("el texto aprobado", "mensaje"),
                    ("saldo > 0", "condición"),
                    ("el texto sin fondos", "mensaje"),
                ],
                "La condición se evalúa. El mensaje se escribe en una rama.",
                "nota y saldo son condiciones. aprobado y sin fondos son mensajes.",
            ),
            _o(
                "Armar un Si completo",
                "Ordena las piezas de un Si con Sino.",
                [
                    "Escribir la condición",
                    "Abrir Entonces",
                    "Escribir la rama verdadera",
                    "Abrir Sino",
                    "Escribir la rama falsa",
                    "Cerrar con FinSi",
                ],
                "FinSi cierra las dos ramas.",
                "condición, Entonces, rama verdadera, Sino, rama falsa y FinSi.",
            ),
            _o(
                "Decidir el mayor",
                "Ordena los pasos para escribir el mayor de a y b.",
                [
                    "Leer a y leer b",
                    "Preguntar si a > b",
                    "Si se cumple, escribir a",
                    "Si no, preguntar si a = b",
                    "Escribir iguales o escribir b",
                ],
                "La igualdad se pregunta solo cuando a no es mayor.",
                "se leen, se compara a > b, se escribe a o se distingue iguales de b.",
            ),
            _o(
                "Aprobar con dos requisitos",
                "Ordena los pasos para exigir nota y asistencia.",
                [
                    "Leer nota y asistencia",
                    "Preguntar nota >= 60 Y asistencia",
                    "Si se cumple, escribir aprobado",
                    "Si no, escribir reprobado",
                ],
                "Y exige que las dos partes sean verdaderas.",
                "se leen los datos, se unen con Y y se escribe la rama que corresponda.",
            ),
            _o(
                "Un Si sin Sino",
                "Ordena un aviso que solo aparece cuando el saldo es negativo.",
                [
                    "Leer saldo",
                    "Preguntar si saldo < 0",
                    "Si se cumple, escribir advertencia",
                    "Cerrar con FinSi",
                    "Escribir fin, ya fuera del Si",
                ],
                "Sin Sino, la condición falsa no escribe la advertencia.",
                "se lee, se pregunta, se escribe la advertencia solo si entra y luego fin.",
            ),
            _o(
                "Tres caminos para un número",
                "Ordena cómo distinguir positivo, negativo y cero.",
                [
                    "Leer n",
                    "Preguntar si n > 0",
                    "Si se cumple, escribir positivo",
                    "Si no, preguntar si n < 0",
                    "Escribir negativo o escribir cero",
                ],
                "Cero es el caso que no es mayor ni menor.",
                "se lee n, se prueba > 0 y, si no, se prueba < 0 o se escribe cero.",
            ),
            _p(
                "Entra por el cero",
                "n vale 0. Anticipa la palabra que se escribe.",
                algo(
                    [
                        "Definir n Como Entero;",
                        "n <- 0;",
                        "Si n = 0 Entonces",
                        '    Escribir "cero";',
                        "Sino",
                        '    Escribir "otro";',
                        "FinSi",
                    ]
                ),
                "La condición n = 0 se cumple, así que entra Entonces.",
            ),
            _p(
                "La rama falsa",
                "n vale 4 y el umbral es 10. Anticipa la palabra.",
                algo(
                    [
                        "Definir n Como Entero;",
                        "n <- 4;",
                        "Si n > 10 Entonces",
                        '    Escribir "alto";',
                        "Sino",
                        '    Escribir "bajo";',
                        "FinSi",
                    ]
                ),
                "4 no es mayor que 10.",
            ),
            _p(
                "Sin rama falsa",
                "n vale 5 y no hay Sino. Anticipa lo que se escribe.",
                algo(
                    [
                        "Definir n Como Entero;",
                        "n <- 5;",
                        "Si n > 0 Entonces",
                        '    Escribir "positivo";',
                        "FinSi",
                    ]
                ),
                "La condición se cumple, así que el Escribir sí corre.",
            ),
            _p(
                "El mayor de dos",
                "a vale 3 y b vale 8. Anticipa el número que se escribe.",
                algo(
                    [
                        "Definir a, b Como Entero;",
                        "a <- 3;",
                        "b <- 8;",
                        "Si a > b Entonces",
                        "    Escribir a;",
                        "Sino",
                        "    Escribir b;",
                        "FinSi",
                    ]
                ),
                "3 no es mayor que 8, así que se escribe b.",
            ),
            _p(
                "Las dos condiciones",
                "edad vale 20 y entregado es Falso. Anticipa la palabra.",
                algo(
                    [
                        "Definir edad Como Entero;",
                        "Definir entregado Como Logico;",
                        "edad <- 20;",
                        "entregado <- Falso;",
                        "Si edad >= 18 Y entregado Entonces",
                        '    Escribir "listo";',
                        "Sino",
                        '    Escribir "falta";',
                        "FinSi",
                    ]
                ),
                "Y exige las dos. La edad sí, la entrega no.",
            ),
            _b(
                "Escribir si o no",
                "Lee una edad. Si es mayor o igual que 18 escribe si. Si no, escribe no.",
                "¿Qué palabra abre la rama cuando la condición es falsa?",
                ["Sino"],
                ["18"],
                algo(
                    [
                        "Definir edad Como Entero;",
                        "Leer edad;",
                        "Si edad >= 18 Entonces",
                        '    Escribir "si";',
                        "Sino",
                        '    Escribir "no";',
                        "FinSi",
                    ]
                ),
                "La comparación es edad >= 18.",
                "con 18 se escribe si.",
            ),
            _b(
                "Signo del número",
                "Lee un entero. Escribe positivo, negativo o cero, según corresponda.",
                "¿Qué valor no es ni mayor ni menor que cero?",
                ["cero", "0"],
                ["-2"],
                algo(
                    [
                        "Definir n Como Entero;",
                        "Leer n;",
                        "Si n > 0 Entonces",
                        '    Escribir "positivo";',
                        "Sino",
                        "    Si n < 0 Entonces",
                        '        Escribir "negativo";',
                        "    Sino",
                        '        Escribir "cero";',
                        "    FinSi",
                        "FinSi",
                    ]
                ),
                "Primero pregunta si es mayor que 0. En el Sino distingue negativo y cero.",
                "con -2 se escribe negativo.",
            ),
            _b(
                "Aprobado o reprobado",
                "Lee una nota entera. Con 60 o más escribe aprobado. Si no, escribe reprobado.",
                "¿Qué operador incluye el 60 en los aprobados?",
                [">=", "mayor o igual"],
                ["59"],
                algo(
                    [
                        "Definir nota Como Entero;",
                        "Leer nota;",
                        "Si nota >= 60 Entonces",
                        '    Escribir "aprobado";',
                        "Sino",
                        '    Escribir "reprobado";',
                        "FinSi",
                    ]
                ),
                "59 está justo debajo del umbral.",
                "con 59 se escribe reprobado.",
            ),
            _b(
                "El mayor de tres",
                "Lee tres enteros y escribe el mayor. Si hay empate, cualquiera de los máximos sirve: escribe uno solo.",
                "¿Cuántas comparaciones hacen falta, como mínimo, para tres números?",
                ["2", "dos"],
                ["4", "9", "6"],
                algo(
                    [
                        "Definir a, b, c, mayor Como Entero;",
                        "Leer a;",
                        "Leer b;",
                        "Leer c;",
                        "mayor <- a;",
                        "Si b > mayor Entonces",
                        "    mayor <- b;",
                        "FinSi",
                        "Si c > mayor Entonces",
                        "    mayor <- c;",
                        "FinSi",
                        "Escribir mayor;",
                    ]
                ),
                "Guarda el primero y reemplázalo solo cuando encuentres uno más grande.",
                "entre 4, 9 y 6 se escribe 9.",
            ),
            _b(
                "Acceso con dos llaves",
                "Lee un lógico clave y un entero nivel. Escribe entra solo si clave es Verdadero y nivel es mayor que 0. Si no, escribe fuera.",
                "¿Qué operador exige que las dos condiciones se cumplan?",
                ["Y"],
                ["Verdadero", "0"],
                algo(
                    [
                        "Definir clave Como Logico;",
                        "Definir nivel Como Entero;",
                        "Leer clave;",
                        "Leer nivel;",
                        "Si clave Y nivel > 0 Entonces",
                        '    Escribir "entra";',
                        "Sino",
                        '    Escribir "fuera";',
                        "FinSi",
                    ]
                ),
                "El nivel 0 no basta, aunque la clave sea verdadera.",
                "con Verdadero y 0 se escribe fuera.",
            ),
        ],
    ),
    (
        "while",
        "Ciclo mientras",
        [
            _c(
                "Cuándo empieza el mientras",
                "Clasifica cada situación de un Mientras.",
                ["entra", "no entra", "puede repetir"],
                [
                    ("La condición es Verdadero al llegar al Mientras", "entra"),
                    ("La condición ya es Falso antes de empezar", "no entra"),
                    ("El cuerpo cambia la condición hacia Falso", "puede repetir"),
                    ("Nadie modifica la condición y sigue siendo Verdadero", "puede repetir"),
                ],
                "Si la condición empieza en Falso, el cuerpo no se ejecuta ni una vez.",
                "entra si es Verdadero. No entra si ya es Falso. Repite según cómo cambie la condición.",
            ),
            _c(
                "Piezas del mientras",
                "Clasifica cada pieza.",
                ["condición", "cuerpo", "cierre"],
                [
                    ("n < 3", "condición"),
                    ("n <- n + 1", "cuerpo"),
                    ("FinMientras", "cierre"),
                    ("Escribir n dentro del ciclo", "cuerpo"),
                ],
                "La condición se revisa antes de cada vuelta. FinMientras cierra el cuerpo.",
                "n < 3 es la condición, las instrucciones son el cuerpo y FinMientras cierra.",
            ),
            _c(
                "Contador bien o mal",
                "Clasifica si el contador permite que el ciclo termine.",
                ["termina", "no termina"],
                [
                    ("n empieza en 0 y en el cuerpo se le suma 1 hasta llegar a 3", "termina"),
                    ("La condición es n < 3 y el cuerpo no toca n", "no termina"),
                    ("Cada vuelta resta 1 a un n que debe bajar de 10 a 0", "termina"),
                    ("La condición usa una variable que nadie asigna dentro", "no termina"),
                ],
                "Si la condición no puede volverse Falso, el ciclo no acaba.",
                "sumar hasta 3 y restar hasta 0 terminan. No tocar la variable no termina.",
            ),
            _c(
                "Antes o dentro",
                "Clasifica dónde va cada instrucción de un conteo.",
                ["antes del ciclo", "dentro del ciclo"],
                [
                    ("Poner el contador en 0", "antes del ciclo"),
                    ("Sumar 1 al contador", "dentro del ciclo"),
                    ("Preparar la suma en 0", "antes del ciclo"),
                    ("Agregar el dato recién leído a la suma", "dentro del ciclo"),
                ],
                "Lo que se hace una sola vez va antes. Lo que se repite va dentro.",
                "iniciar contador y suma va antes. Incrementar y acumular va dentro.",
            ),
            _c(
                "Una vuelta o ninguna",
                "Clasifica cuántas veces corre el cuerpo.",
                ["ninguna", "varias"],
                [
                    ("Mientras 5 < 3", "ninguna"),
                    ("Mientras n < 3, con n en 0 y sumando 1", "varias"),
                    ("Mientras Falso", "ninguna"),
                    ("Mientras n <= 4, con n en 1 y sumando 1", "varias"),
                ],
                "Mientras revisa la condición antes de entrar.",
                "5 < 3 y Falso no entran. Los contadores que avanzan dan varias vueltas.",
            ),
            _o(
                "Contar hasta tres",
                "Ordena un ciclo que deja n en 3.",
                [
                    "Definir n Como Entero",
                    "Guardar 0 en n",
                    "Mientras n < 3, sumar 1 a n",
                    "Cerrar con FinMientras",
                    "Escribir n",
                ],
                "El Escribir va fuera, cuando el ciclo ya terminó.",
                "se define n, se pone en 0, se incrementa mientras sea menor que 3 y se escribe.",
            ),
            _o(
                "Sumar del uno al cuatro",
                "Ordena el acumulador de 1 a 4.",
                [
                    "Poner suma en 0 e i en 1",
                    "Mientras i <= 4, sumar i a suma",
                    "Sumar 1 a i",
                    "Cerrar el ciclo",
                    "Escribir suma",
                ],
                "i tiene que avanzar en cada vuelta, o el ciclo no acaba.",
                "se inicializa, se acumula i, se avanza i, se cierra y se escribe la suma.",
            ),
            _o(
                "Leer hasta el cero",
                "Ordena un ciclo que cuenta cuántos positivos llegan antes de un 0.",
                [
                    "Poner el conteo en 0",
                    "Leer el primer número",
                    "Mientras el número no sea 0, sumar 1 al conteo",
                    "Leer el siguiente número",
                    "Al salir, escribir el conteo",
                ],
                "Hay que leer de nuevo dentro del ciclo. Si no, el 0 nunca llega.",
                "se pone el conteo en 0, se lee, se cuenta mientras no sea 0 y se escribe.",
            ),
            _o(
                "El ciclo que no debe entrar",
                "Ordena un mientras que no entra porque n ya vale 5.",
                [
                    "Definir n Como Entero",
                    "Guardar 5 en n",
                    "Plantear Mientras n < 3",
                    "Dentro, sumar 1 a n",
                    "Después del ciclo, escribir n",
                ],
                "La condición se mira antes del cuerpo.",
                "n queda en 5 porque 5 < 3 es falso y el cuerpo no corre.",
            ),
            _p(
                "Tres vueltas",
                "n empieza en 0 y sube mientras sea menor que 3. Anticipa lo que se escribe.",
                algo(
                    [
                        "Definir n Como Entero;",
                        "n <- 0;",
                        "Mientras n < 3 Hacer",
                        "    n <- n + 1;",
                        "FinMientras",
                        "Escribir n;",
                    ]
                ),
                "Entra con 0, 1 y 2. Al llegar a 3 ya no entra.",
            ),
            _p(
                "Mientras que se salta",
                "n empieza en 5 y el ciclo pide n < 3. Anticipa lo que se escribe.",
                algo(
                    [
                        "Definir n Como Entero;",
                        "n <- 5;",
                        "Mientras n < 3 Hacer",
                        "    n <- n + 1;",
                        "FinMientras",
                        "Escribir n;",
                    ]
                ),
                "5 < 3 es falso desde el principio.",
            ),
            _p(
                "La suma del uno al cuatro",
                "Anticipa la suma que se escribe.",
                algo(
                    [
                        "Definir suma, i Como Entero;",
                        "suma <- 0;",
                        "i <- 1;",
                        "Mientras i <= 4 Hacer",
                        "    suma <- suma + i;",
                        "    i <- i + 1;",
                        "FinMientras",
                        "Escribir suma;",
                    ]
                ),
                "1 + 2 + 3 + 4.",
            ),
            _p(
                "Doble de vueltas",
                "Anticipa cuántas veces se sumó 1.",
                algo(
                    [
                        "Definir vueltas, n Como Entero;",
                        "vueltas <- 0;",
                        "n <- 1;",
                        "Mientras n <= 5 Hacer",
                        "    vueltas <- vueltas + 1;",
                        "    n <- n + 2;",
                        "FinMientras",
                        "Escribir vueltas;",
                    ]
                ),
                "n recorre 1, 3 y 5. Son tres vueltas.",
            ),
            _p(
                "Bajar hasta cero",
                "Anticipa el valor final de n.",
                algo(
                    [
                        "Definir n Como Entero;",
                        "n <- 4;",
                        "Mientras n > 0 Hacer",
                        "    n <- n - 1;",
                        "FinMientras",
                        "Escribir n;",
                    ]
                ),
                "Resta hasta que n ya no es mayor que 0.",
            ),
            _b(
                "Sumar del 1 al n",
                "Lee un entero n mayor que 0. Escribe la suma 1 + 2 + ... + n.",
                "¿Dónde se inicializa el acumulador?",
                ["antes del ciclo", "antes"],
                ["4"],
                algo(
                    [
                        "Definir n, i, suma Como Entero;",
                        "Leer n;",
                        "suma <- 0;",
                        "i <- 1;",
                        "Mientras i <= n Hacer",
                        "    suma <- suma + i;",
                        "    i <- i + 1;",
                        "FinMientras",
                        "Escribir suma;",
                    ]
                ),
                "i avanza en 1 y suma acumula i.",
                "con 4 se escribe 10.",
            ),
            _b(
                "Cuántos positivos",
                "Lee enteros hasta recibir un 0. El 0 no cuenta. Escribe cuántos positivos llegaron. Los datos de prueba no traen negativos.",
                "¿Qué valor indica que ya no hay más números?",
                ["0", "cero"],
                ["2", "5", "0"],
                algo(
                    [
                        "Definir n, conteo Como Entero;",
                        "conteo <- 0;",
                        "Leer n;",
                        "Mientras n <> 0 Hacer",
                        "    conteo <- conteo + 1;",
                        "    Leer n;",
                        "FinMientras",
                        "Escribir conteo;",
                    ]
                ),
                "Vuelve a leer dentro del ciclo. Si no, nunca llega el 0.",
                "llegan 2 y 5, así que se escribe 2.",
            ),
            _b(
                "Potencia por multiplicación",
                "Lee una base y un exponente, ambos enteros, con exponente mayor o igual que 0. Escribe la potencia multiplicando. No uses el operador ^.",
                "¿En qué valor empieza una potencia que se arma multiplicando?",
                ["1", "uno"],
                ["2", "5"],
                algo(
                    [
                        "Definir base, exponente, i, resultado Como Entero;",
                        "Leer base;",
                        "Leer exponente;",
                        "resultado <- 1;",
                        "i <- 1;",
                        "Mientras i <= exponente Hacer",
                        "    resultado <- resultado * base;",
                        "    i <- i + 1;",
                        "FinMientras",
                        "Escribir resultado;",
                    ]
                ),
                "Empieza en 1 y multiplica por la base, una vez por cada unidad del exponente.",
                "2 elevado a 5 es 32.",
            ),
            _b(
                "Dígitos de un entero",
                "Lee un entero mayor que 0 y escribe cuántos dígitos tiene. 100 tiene 3.",
                "¿Qué operación quita el último dígito de un entero?",
                ["DIV", "div"],
                ["100"],
                algo(
                    [
                        "Definir n, digitos Como Entero;",
                        "Leer n;",
                        "digitos <- 0;",
                        "Mientras n > 0 Hacer",
                        "    digitos <- digitos + 1;",
                        "    n <- n DIV 10;",
                        "FinMientras",
                        "Escribir digitos;",
                    ]
                ),
                "Cada DIV 10 recorta un dígito y el conteo sube en 1.",
                "100 tiene 3 dígitos.",
            ),
        ],
    ),
    (
        "switch",
        "Opción múltiple",
        [
            _c(
                "Partes de un Según",
                "Clasifica cada pieza de un Según.",
                ["selector", "caso", "alternativa"],
                [
                    ("La variable opcion", "selector"),
                    ("La etiqueta 1:", "caso"),
                    ("De Otro Modo", "alternativa"),
                    ("La etiqueta 2, 3:", "caso"),
                ],
                "El selector es el valor que se compara. De Otro Modo cubre lo que no coincidió.",
                "opcion es el selector, las etiquetas son casos y De Otro Modo es la alternativa.",
            ),
            _c(
                "Cae o no cae",
                "Clasifica cómo se comporta un caso cuando coincide.",
                ["se ejecuta", "no se ejecuta"],
                [
                    ("El caso cuya etiqueta es igual al selector", "se ejecuta"),
                    ("El caso siguiente, si no se volvió a pedir", "no se ejecuta"),
                    ("De Otro Modo, cuando ya hubo un caso igual", "no se ejecuta"),
                    ("De Otro Modo, cuando ninguna etiqueta coincidió", "se ejecuta"),
                ],
                "Un caso no cae al siguiente. Solo corre el que coincide.",
                "corre el caso igual y De Otro Modo solo si nadie coincidió. El siguiente no corre solo.",
            ),
            _c(
                "Etiqueta válida",
                "Clasifica qué puede ser etiqueta de un caso.",
                ["sirve", "no sirve"],
                [
                    ("El número 1", "sirve"),
                    ("Una cuenta como 1 + 0", "no sirve"),
                    ("Dos números escritos 2, 3", "sirve"),
                    ("Una variable", "no sirve"),
                ],
                "La etiqueta es un literal. No es una expresión ni una variable.",
                "1 y 2, 3 sirven. Una suma y una variable no sirven.",
            ),
            _c(
                "Menú de operaciones",
                "Clasifica cada opción de una calculadora.",
                ["suma", "resta", "otra"],
                [
                    ("La opción 1", "suma"),
                    ("La opción 2", "resta"),
                    ("La opción 9", "otra"),
                    ("De Otro Modo", "otra"),
                ],
                "Lo que no es 1 ni 2 cae en la alternativa.",
                "1 suma, 2 resta y tanto 9 como De Otro Modo son la otra salida.",
            ),
            _o(
                "Armar el Según",
                "Ordena las piezas de un menú con dos casos y una alternativa.",
                [
                    "Elegir el selector",
                    "Abrir Segun",
                    "Escribir el caso 1",
                    "Escribir el caso 2",
                    "Escribir De Otro Modo",
                    "Cerrar con FinSegun",
                ],
                "De Otro Modo va después de los casos numerados.",
                "selector, Segun, caso 1, caso 2, De Otro Modo y FinSegun.",
            ),
            _o(
                "Leer la opción y despachar",
                "Ordena un menú que lee un entero y escribe una palabra.",
                [
                    "Definir opcion Como Entero",
                    "Leer opcion",
                    "Abrir Segun opcion",
                    "Escribir la palabra del caso que coincida",
                    "Cerrar con FinSegun",
                ],
                "El Según usa el valor que ya se leyó.",
                "se define, se lee, se abre el Según, se escribe el caso y se cierra.",
            ),
            _o(
                "Días abreviados",
                "Ordena un Según que agrupa 1 y 2 en el mismo mensaje.",
                [
                    "Guardar 2 en dia",
                    "Abrir Segun dia",
                    "Poner la etiqueta 1, 2",
                    "Escribir inicio",
                    "Poner De Otro Modo y escribir resto",
                ],
                "Varias etiquetas del mismo caso se separan con coma.",
                "se guarda 2, se abre el Según, se etiqueta 1, 2, se escribe inicio y el resto queda aparte.",
            ),
            _o(
                "Cerrar todas las ramas",
                "Ordena el cierre correcto de un Según.",
                [
                    "Terminar el último caso",
                    "Escribir De Otro Modo si hace falta",
                    "Cerrar con FinSegun",
                    "Seguir con el Escribir que va fuera",
                ],
                "FinSegun va una sola vez, al final.",
                "se termina el caso, va De Otro Modo, se cierra y después sigue el programa.",
            ),
            _p(
                "El caso dos",
                "opcion vale 2. Anticipa la palabra.",
                algo(
                    [
                        "Definir opcion Como Entero;",
                        "opcion <- 2;",
                        "Segun opcion Hacer",
                        "    1:",
                        '        Escribir "uno";',
                        "    2:",
                        '        Escribir "dos";',
                        "    De Otro Modo:",
                        '        Escribir "otro";',
                        "FinSegun",
                    ]
                ),
                "La etiqueta 2 coincide. No sigue hacia De Otro Modo.",
            ),
            _p(
                "Ningún caso coincide",
                "opcion vale 9. Anticipa la palabra.",
                algo(
                    [
                        "Definir opcion Como Entero;",
                        "opcion <- 9;",
                        "Segun opcion Hacer",
                        "    1:",
                        '        Escribir "uno";',
                        "    2:",
                        '        Escribir "dos";',
                        "    De Otro Modo:",
                        '        Escribir "otro";',
                        "FinSegun",
                    ]
                ),
                "9 no es 1 ni 2.",
            ),
            _p(
                "Dos etiquetas, un caso",
                "dia vale 3. Anticipa la palabra.",
                algo(
                    [
                        "Definir dia Como Entero;",
                        "dia <- 3;",
                        "Segun dia Hacer",
                        "    1, 2:",
                        '        Escribir "inicio";',
                        "    3:",
                        '        Escribir "medio";',
                        "    De Otro Modo:",
                        '        Escribir "resto";',
                        "FinSegun",
                    ]
                ),
                "3 tiene su propio caso.",
            ),
            _p(
                "El caso compartido",
                "dia vale 2 y comparte caso con 1. Anticipa la palabra.",
                algo(
                    [
                        "Definir dia Como Entero;",
                        "dia <- 2;",
                        "Segun dia Hacer",
                        "    1, 2:",
                        '        Escribir "inicio";',
                        "    De Otro Modo:",
                        '        Escribir "resto";',
                        "FinSegun",
                    ]
                ),
                "2 está en la etiqueta 1, 2.",
            ),
            _b(
                "Menú sumar o restar",
                "Lee un entero. Si es 1 escribe sumar. Si es 2 escribe restar. En cualquier otro caso escribe otra.",
                "¿Qué frase cubre los valores que no tienen caso?",
                ["De Otro Modo", "de otro modo"],
                ["2"],
                algo(
                    [
                        "Definir opcion Como Entero;",
                        "Leer opcion;",
                        "Segun opcion Hacer",
                        "    1:",
                        '        Escribir "sumar";',
                        "    2:",
                        '        Escribir "restar";',
                        "    De Otro Modo:",
                        '        Escribir "otra";',
                        "FinSegun",
                    ]
                ),
                "Cada caso termina en su Escribir. No hace falta un corte extra.",
                "con 2 se escribe restar.",
            ),
            _b(
                "Semáforo",
                "Lee un entero. 1 escribe verde, 2 escribe amarillo, 3 escribe rojo y el resto escribe apagado.",
                "¿Cuántos casos numerados tiene este menú?",
                ["3", "tres"],
                ["3"],
                algo(
                    [
                        "Definir luz Como Entero;",
                        "Leer luz;",
                        "Segun luz Hacer",
                        "    1:",
                        '        Escribir "verde";',
                        "    2:",
                        '        Escribir "amarillo";',
                        "    3:",
                        '        Escribir "rojo";',
                        "    De Otro Modo:",
                        '        Escribir "apagado";',
                        "FinSegun",
                    ]
                ),
                "El 3 tiene su propio caso, no cae en De Otro Modo.",
                "con 3 se escribe rojo.",
            ),
            _b(
                "Calculadora de una tecla",
                "Lee la operación 1, 2 o 3 y dos enteros. 1 suma, 2 resta y 3 multiplica. Escribe el resultado. La prueba usa la suma.",
                "¿El Según elige la operación o los números?",
                ["la operacion", "la operación", "operacion"],
                ["1", "8", "5"],
                algo(
                    [
                        "Definir op, a, b, total Como Entero;",
                        "Leer op;",
                        "Leer a;",
                        "Leer b;",
                        "total <- 0;",
                        "Segun op Hacer",
                        "    1:",
                        "        total <- a + b;",
                        "    2:",
                        "        total <- a - b;",
                        "    3:",
                        "        total <- a * b;",
                        "    De Otro Modo:",
                        "        total <- 0;",
                        "FinSegun",
                        "Escribir total;",
                    ]
                ),
                "Primero se leen la operación y los dos números. El Según solo elige la cuenta.",
                "la opción 1 con 8 y 5 escribe 13.",
            ),
            _b(
                "Fin de semana",
                "Lee un día del 1 al 7. Si es 6 o 7 escribe descanso. Si no, escribe clase.",
                "¿Cómo se escriben dos etiquetas del mismo caso?",
                ["con coma", "coma", "1, 2"],
                ["6"],
                algo(
                    [
                        "Definir dia Como Entero;",
                        "Leer dia;",
                        "Segun dia Hacer",
                        "    6, 7:",
                        '        Escribir "descanso";',
                        "    De Otro Modo:",
                        '        Escribir "clase";',
                        "FinSegun",
                    ]
                ),
                "6 y 7 comparten el mismo caso.",
                "con 6 se escribe descanso.",
            ),
        ],
    ),
    (
        "for",
        "Ciclo para",
        [
            _c(
                "Piezas del Para",
                "Clasifica cada parte de un Para.",
                ["inicio", "tope", "paso", "cuerpo"],
                [
                    ("i <- 1", "inicio"),
                    ("Hasta 5", "tope"),
                    ("Con Paso 1", "paso"),
                    ("Escribir i", "cuerpo"),
                ],
                "Inicio, tope y paso dicen cómo avanza i. El cuerpo es lo que se repite.",
                "i <- 1 inicia, Hasta 5 es el tope, Con Paso 1 es el paso y Escribir i es el cuerpo.",
            ),
            _c(
                "Cuántas vueltas",
                "Clasifica cuántas veces corre el cuerpo.",
                ["tres", "ninguna", "cinco"],
                [
                    ("Para i <- 1 Hasta 3 Con Paso 1", "tres"),
                    ("Para i <- 1 Hasta 0 Con Paso 1", "ninguna"),
                    ("Para i <- 1 Hasta 5 Con Paso 1", "cinco"),
                    ("Para i <- 3 Hasta 1 Con Paso 1", "ninguna"),
                ],
                "Si el paso es positivo y el inicio ya pasó el tope, no entra.",
                "1 a 3 son tres vueltas, 1 a 5 son cinco, y los que van al revés con paso 1 no entran.",
            ),
            _c(
                "Para o mientras",
                "Clasifica qué ciclo conviene.",
                ["Para", "Mientras"],
                [
                    ("Recorrer i desde 1 hasta n de uno en uno", "Para"),
                    ("Leer números hasta que llegue un 0", "Mientras"),
                    ("Escribir la tabla del 2, del 1 al 10", "Para"),
                    ("Repetir mientras la clave sea incorrecta", "Mientras"),
                ],
                "Para sirve cuando el recorrido ya tiene inicio, tope y paso.",
                "los recorridos contados son Para. Esperar un 0 o una clave es Mientras.",
            ),
            _c(
                "El paso",
                "Clasifica el efecto del paso.",
                ["sube", "baja"],
                [
                    ("Con Paso 1", "sube"),
                    ("Con Paso -1", "baja"),
                    ("Con Paso 2, desde 1", "sube"),
                    ("Desde 5 hasta 1 con paso negativo", "baja"),
                ],
                "El signo del paso dice si i crece o disminuye.",
                "paso 1 y paso 2 suben. Paso -1 y el recorrido hacia 1 bajan.",
            ),
            _c(
                "Dentro o fuera",
                "Clasifica dónde se escribe cada resultado.",
                ["dentro del Para", "después del Para"],
                [
                    ("Escribir i en cada vuelta", "dentro del Para"),
                    ("Escribir la suma cuando ya se recorrió todo", "después del Para"),
                    ("Acumular i", "dentro del Para"),
                    ("Mostrar el promedio final", "después del Para"),
                ],
                "Lo que depende de la vuelta va dentro. El total va cuando el Para ya cerró.",
                "escribir i y acumular van dentro. La suma final y el promedio van después.",
            ),
            _o(
                "Armar un Para",
                "Ordena un ciclo que escribe i desde 1 hasta 3.",
                [
                    "Definir i Como Entero",
                    "Abrir Para i desde 1 hasta 3 con paso 1",
                    "Escribir i",
                    "Cerrar con FinPara",
                ],
                "i tiene que estar definido antes del Para.",
                "se define i, se abre el Para, se escribe i y se cierra.",
            ),
            _o(
                "Sumar con Para",
                "Ordena la suma de 1 hasta 4 usando Para.",
                [
                    "Poner suma en 0",
                    "Abrir Para i desde 1 hasta 4",
                    "Sumar i a suma",
                    "Cerrar el Para",
                    "Escribir suma",
                ],
                "El Escribir de la suma va fuera del ciclo.",
                "suma empieza en 0, el Para acumula i y al final se escribe.",
            ),
            _o(
                "Bajar el índice",
                "Ordena un Para que va de 3 a 1.",
                [
                    "Definir i Como Entero",
                    "Abrir Para i desde 3 hasta 1 con paso -1",
                    "Escribir i",
                    "Cerrar con FinPara",
                ],
                "Para bajar, el paso tiene que ser negativo.",
                "se define i, se recorre de 3 a 1 con paso -1 y se escribe i.",
            ),
            _o(
                "Tabla del dos",
                "Ordena la escritura de 2, 4 y 6.",
                [
                    "Definir i Como Entero",
                    "Abrir Para i desde 1 hasta 3",
                    "Escribir i * 2",
                    "Cerrar el Para",
                ],
                "El 2 multiplica al índice de cada vuelta.",
                "se define i, el Para llega hasta 3 y cada vuelta escribe i * 2.",
            ),
            _p(
                "Del cuatro al cuatro",
                "El Para va de 4 a 4. Anticipa lo que se escribe.",
                algo(
                    [
                        "Definir i Como Entero;",
                        "Para i <- 4 Hasta 4 Con Paso 1 Hacer",
                        "    Escribir i;",
                        "FinPara",
                    ]
                ),
                "Inicio y tope son iguales, así que hay una vuelta.",
            ),
            _p(
                "La suma con Para",
                "Anticipa la suma de 1 a 4.",
                algo(
                    [
                        "Definir suma, i Como Entero;",
                        "suma <- 0;",
                        "Para i <- 1 Hasta 4 Con Paso 1 Hacer",
                        "    suma <- suma + i;",
                        "FinPara",
                        "Escribir suma;",
                    ]
                ),
                "1 + 2 + 3 + 4.",
            ),
            _p(
                "De tres a uno",
                "El Para baja. Anticipa la última línea.",
                algo(
                    [
                        "Definir i Como Entero;",
                        "Para i <- 3 Hasta 1 Con Paso -1 Hacer",
                        "    Escribir i;",
                        "FinPara",
                    ]
                ),
                "Escribe 3, luego 2 y al final 1.",
            ),
            _p(
                "De dos en dos",
                "Anticipa la última línea. i va de 1 a 5 con paso 2.",
                algo(
                    [
                        "Definir i Como Entero;",
                        "Para i <- 1 Hasta 5 Con Paso 2 Hacer",
                        "    Escribir i;",
                        "FinPara",
                    ]
                ),
                "Los valores son 1, 3 y 5.",
            ),
            _p(
                "No entra",
                "El paso es positivo, pero el tope está antes del inicio. Anticipa qué se escribe después.",
                algo(
                    [
                        "Definir i, marca Como Entero;",
                        "marca <- 7;",
                        "Para i <- 3 Hasta 1 Con Paso 1 Hacer",
                        "    marca <- 0;",
                        "FinPara",
                        "Escribir marca;",
                    ]
                ),
                "El cuerpo no corre, así que marca sigue en 7.",
            ),
            _b(
                "Contar hasta n con Para",
                "Lee un entero n mayor que 0 y escribe la suma de 1 hasta n.",
                "¿Qué instrucción repite un índice desde un inicio hasta un tope?",
                ["Para"],
                ["5"],
                algo(
                    [
                        "Definir n, i, suma Como Entero;",
                        "Leer n;",
                        "suma <- 0;",
                        "Para i <- 1 Hasta n Con Paso 1 Hacer",
                        "    suma <- suma + i;",
                        "FinPara",
                        "Escribir suma;",
                    ]
                ),
                "El tope del Para es el n leído.",
                "con 5 se escribe 15.",
            ),
            _b(
                "Tabla de un número",
                "Lee un entero n y escribe n * 1, n * 2 y n * 3, en tres líneas.",
                "¿Hasta qué número llega i si quieres tres vueltas empezando en 1?",
                ["3", "tres"],
                ["4"],
                algo(
                    [
                        "Definir n, i Como Entero;",
                        "Leer n;",
                        "Para i <- 1 Hasta 3 Con Paso 1 Hacer",
                        "    Escribir n * i;",
                        "FinPara",
                    ]
                ),
                "Cada vuelta escribe el producto, no solo i.",
                "con 4 se escriben 4, 8 y 12.",
            ),
            _b(
                "Factorial con Para",
                "Lee un entero n mayor o igual que 1 y escribe su factorial.",
                "¿En qué valor empieza el factorial antes de multiplicar?",
                ["1", "uno"],
                ["5"],
                algo(
                    [
                        "Definir n, i, resultado Como Entero;",
                        "Leer n;",
                        "resultado <- 1;",
                        "Para i <- 2 Hasta n Con Paso 1 Hacer",
                        "    resultado <- resultado * i;",
                        "FinPara",
                        "Escribir resultado;",
                    ]
                ),
                "Multiplica 2 * 3 * ... * n sobre el 1 inicial.",
                "5! es 120.",
            ),
            _b(
                "Cuenta regresiva",
                "Lee un entero n mayor que 0. Escribe desde n hasta 1, un número por línea.",
                "¿Qué paso usa un Para que baja de uno en uno?",
                ["-1"],
                ["3"],
                algo(
                    [
                        "Definir n, i Como Entero;",
                        "Leer n;",
                        "Para i <- n Hasta 1 Con Paso -1 Hacer",
                        "    Escribir i;",
                        "FinPara",
                    ]
                ),
                "El inicio es n y el tope es 1.",
                "con 3 se escriben 3, 2 y 1.",
            ),
        ],
    ),
    (
        "repeat",
        "Ciclo repetir",
        [
            _c(
                "El cuerpo corre primero",
                "Clasifica el Repetir frente al Mientras.",
                ["al menos una vez", "puede no entrar", "la condición va al final"],
                [
                    ("Repetir", "al menos una vez"),
                    ("Mientras con condición falsa", "puede no entrar"),
                    ("Hasta Que", "la condición va al final"),
                    ("El cuerpo de un Repetir", "al menos una vez"),
                ],
                "Repetir ejecuta el cuerpo y después mira Hasta Que.",
                "Repetir y su cuerpo corren al menos una vez. Mientras puede no entrar. Hasta Que va al final.",
            ),
            _c(
                "Entra aunque esté cerca",
                "n ya vale 3 y el ciclo dice Repetir n <- n + 1 Hasta Que n > 3. Clasifica.",
                ["ocurre", "no ocurre"],
                [
                    ("El cuerpo se ejecuta una vez", "ocurre"),
                    ("n se queda en 3", "no ocurre"),
                    ("La condición se revisa antes del cuerpo", "no ocurre"),
                    ("n termina en 4", "ocurre"),
                ],
                "Aunque la meta ya estuviera cerca, el cuerpo corre antes de la pregunta.",
                "el cuerpo corre, n termina en 4 y la condición no se mira antes.",
            ),
            _c(
                "Para salir",
                "Clasifica qué hace que un Repetir termine.",
                ["lo termina", "lo deja vivo"],
                [
                    ("Hasta Que queda en Verdadero", "lo termina"),
                    ("Hasta Que queda en Falso", "lo deja vivo"),
                    ("El cuerpo no cambia la variable de la condición", "lo deja vivo"),
                    ("El cuerpo empuja la variable hasta cumplir Hasta Que", "lo termina"),
                ],
                "Sale cuando Hasta Que es verdadero. Si sigue en falso, repite.",
                "Hasta Que verdadero y avanzar la variable lo terminan. Lo contrario lo deja vivo.",
            ),
            _c(
                "Qué abre y qué cierra",
                "Clasifica cada pieza de un Repetir.",
                ["abre", "cierra"],
                [
                    ("La palabra Repetir", "abre"),
                    ("Hasta Que n = 4", "cierra"),
                    ("La primera instrucción del cuerpo", "abre"),
                    ("La condición de salida", "cierra"),
                ],
                "Repetir abre el cuerpo. Hasta Que lo cierra.",
                "Repetir y el cuerpo abren. Hasta Que y la condición cierran.",
            ),
            _o(
                "Repetir hasta tres",
                "Ordena un Repetir que deja n en 3.",
                [
                    "Poner n en 0",
                    "Abrir Repetir",
                    "Sumar 1 a n",
                    "Cerrar con Hasta Que n = 3",
                    "Escribir n",
                ],
                "Hasta Que va después del cuerpo.",
                "n empieza en 0, se incrementa y se detiene cuando llega a 3.",
            ),
            _o(
                "Pedir de nuevo",
                "Ordena una lectura que se repite hasta recibir un número positivo.",
                [
                    "Abrir Repetir",
                    "Leer n",
                    "Cerrar con Hasta Que n > 0",
                    "Escribir n",
                ],
                "La lectura va dentro, porque puede hacer falta más de un intento.",
                "se abre, se lee, se espera un positivo y se escribe n.",
            ),
            _o(
                "Contar las vueltas",
                "Ordena un Repetir que cuenta cuántas veces corrió hasta que n llegó a 4.",
                [
                    "Poner n y vueltas en 0",
                    "Abrir Repetir",
                    "Sumar 1 a n y 1 a vueltas",
                    "Cerrar con Hasta Que n = 4",
                    "Escribir vueltas",
                ],
                "vueltas y n avanzan juntos dentro del cuerpo.",
                "empiezan en 0, cada vuelta suma 1 y se escribe vueltas al salir.",
            ),
            _o(
                "No uses Mientras para este",
                "Ordena la estructura que obliga a entrar una vez.",
                [
                    "Preparar la variable",
                    "Escribir Repetir",
                    "Escribir el cuerpo",
                    "Escribir Hasta Que con la condición de salida",
                ],
                "Si la primera acción tiene que ocurrir sí o sí, Repetir lo garantiza.",
                "se prepara la variable, se abre Repetir, va el cuerpo y se cierra con Hasta Que.",
            ),
            _p(
                "Hasta tres",
                "n empieza en 0. Anticipa lo que se escribe.",
                algo(
                    [
                        "Definir n Como Entero;",
                        "n <- 0;",
                        "Repetir",
                        "    n <- n + 1;",
                        "Hasta Que n = 3",
                        "Escribir n;",
                    ]
                ),
                "Suma 1 hasta que n sea 3.",
            ),
            _p(
                "Aunque ya estaba",
                "n empieza en 3 y el cuerpo le suma 1. Anticipa el resultado.",
                algo(
                    [
                        "Definir n Como Entero;",
                        "n <- 3;",
                        "Repetir",
                        "    n <- n + 1;",
                        "Hasta Que n > 3",
                        "Escribir n;",
                    ]
                ),
                "El cuerpo corre antes de mirar Hasta Que.",
            ),
            _p(
                "Cuatro vueltas seguras",
                "Anticipa cuántas vueltas se contaron.",
                algo(
                    [
                        "Definir n, vueltas Como Entero;",
                        "n <- 0;",
                        "vueltas <- 0;",
                        "Repetir",
                        "    n <- n + 1;",
                        "    vueltas <- vueltas + 1;",
                        "Hasta Que n = 4",
                        "Escribir vueltas;",
                    ]
                ),
                "n llega a 4 en la cuarta vuelta.",
            ),
            _p(
                "La última lectura gana",
                "Se escriben dos valores, pero el ciclo se queda con el último que cumpla. Anticipa el número.",
                algo(
                    [
                        "Definir n, i Como Entero;",
                        "i <- 0;",
                        "n <- 0;",
                        "Repetir",
                        "    i <- i + 1;",
                        "    n <- i * 10;",
                        "Hasta Que i = 3",
                        "Escribir n;",
                    ]
                ),
                "En la tercera vuelta i vale 3 y n vale 30.",
            ),
            _b(
                "Subir hasta el tope leído",
                "Lee un entero tope mayor que 0. Con un Repetir, suma 1 desde 0 hasta llegar a tope y escribe ese valor.",
                "¿Qué frase cierra un Repetir?",
                ["Hasta Que", "hasta que"],
                ["4"],
                algo(
                    [
                        "Definir n, tope Como Entero;",
                        "Leer tope;",
                        "n <- 0;",
                        "Repetir",
                        "    n <- n + 1;",
                        "Hasta Que n = tope",
                        "Escribir n;",
                    ]
                ),
                "n sube de uno en uno y se detiene cuando iguala al tope.",
                "con 4 se escribe 4.",
            ),
            _b(
                "Primer positivo",
                "Lee enteros con un Repetir hasta recibir uno mayor que 0. Escribe ese número. La prueba manda primero un cero.",
                "¿El cuerpo de Repetir puede no ejecutarse?",
                ["no"],
                ["0", "6"],
                algo(
                    [
                        "Definir n Como Entero;",
                        "Repetir",
                        "    Leer n;",
                        "Hasta Que n > 0",
                        "Escribir n;",
                    ]
                ),
                "Hay que leer al menos una vez, por eso cabe Repetir.",
                "ignora el 0 y se queda con 6.",
            ),
            _b(
                "Sumar hasta pasar",
                "Lee un entero meta mayor que 0. Suma 1, 2, 3... con un Repetir hasta que la suma sea mayor o igual que meta. Escribe la suma.",
                "¿La condición se revisa antes o después del cuerpo?",
                ["despues", "después"],
                ["5"],
                algo(
                    [
                        "Definir meta, i, suma Como Entero;",
                        "Leer meta;",
                        "i <- 0;",
                        "suma <- 0;",
                        "Repetir",
                        "    i <- i + 1;",
                        "    suma <- suma + i;",
                        "Hasta Que suma >= meta",
                        "Escribir suma;",
                    ]
                ),
                "1 + 2 ya llega a 3, y 1 + 2 + 3 llega a 6.",
                "para la meta 5 hace falta 1 + 2 + 3, que es 6.",
            ),
            _b(
                "Confirmación",
                "Lee caracteres hasta recibir S. Escribe cuantos intentos hizo, contando el que acertó. La prueba manda N y luego S.",
                "¿Qué tipo guarda una letra suelta?",
                ["Caracter", "caracter"],
                ["N", "S"],
                algo(
                    [
                        "Definir tecla Como Caracter;",
                        "Definir intentos Como Entero;",
                        "intentos <- 0;",
                        "Repetir",
                        "    Leer tecla;",
                        "    intentos <- intentos + 1;",
                        "Hasta Que tecla = 'S'",
                        "Escribir intentos;",
                    ]
                ),
                "Cada lectura cuenta, también la S final.",
                "N y S son dos intentos.",
            ),
        ],
    ),
    (
        "array",
        "Arreglos",
        [
            _c(
                "Casilla, tamaño o valor",
                "Clasifica cada frase de un arreglo.",
                ["casilla", "tamaño", "valor"],
                [
                    ("El 1 de datos[1]", "casilla"),
                    ("El 5 de Dimension datos[5]", "tamaño"),
                    ("El 8 guardado en esa casilla", "valor"),
                    ("El índice de un Para que recorre el arreglo", "casilla"),
                ],
                "La primera casilla es la 1, no la 0.",
                "el 1 y el índice son casillas, el 5 es el tamaño y el 8 es el valor.",
            ),
            _c(
                "Índice válido",
                "El arreglo tiene 3 casillas, numeradas desde 1. Clasifica cada acceso.",
                ["válido", "fuera"],
                [
                    ("datos[1]", "válido"),
                    ("datos[3]", "válido"),
                    ("datos[0]", "fuera"),
                    ("datos[4]", "fuera"),
                ],
                "Las casillas van de 1 al tamaño. 0 y tamaño + 1 quedan fuera.",
                "1 y 3 son válidos. 0 y 4 quedan fuera.",
            ),
            _c(
                "Arreglo o variable suelta",
                "Clasifica qué estructura conviene.",
                ["arreglo", "variable"],
                [
                    ("Las cinco calificaciones de un alumno", "arreglo"),
                    ("El promedio de esas calificaciones", "variable"),
                    ("Los nombres de un grupo", "arreglo"),
                    ("La cantidad de nombres leídos", "variable"),
                ],
                "El arreglo guarda la lista. Una variable guarda un solo dato, como el promedio.",
                "las calificaciones y los nombres son arreglos. El promedio y la cantidad son variables.",
            ),
            _c(
                "Recorrer",
                "Clasifica cada paso de un recorrido.",
                ["antes", "en cada casilla", "al final"],
                [
                    ("Dimension datos[3] Como Entero", "antes"),
                    ("Sumar datos[i] al acumulador", "en cada casilla"),
                    ("Escribir la suma", "al final"),
                    ("Poner el acumulador en 0", "antes"),
                ],
                "Dimension y el acumulador en 0 van antes del Para.",
                "Dimension y el cero van antes, la suma de la casilla va en cada vuelta y el Escribir al final.",
            ),
            _c(
                "Una fila o una tabla",
                "Clasifica la forma del arreglo.",
                ["una dimensión", "dos dimensiones"],
                [
                    ("datos[i]", "una dimensión"),
                    ("tabla[fila, columna]", "dos dimensiones"),
                    ("Dimension notas[10]", "una dimensión"),
                    ("Dimension sala[2, 3]", "dos dimensiones"),
                ],
                "Una coma dentro de los corchetes separa fila y columna.",
                "datos[i] y notas[10] tienen una dimensión. tabla y sala tienen dos.",
            ),
            _o(
                "Guardar y mostrar la primera",
                "Ordena los pasos para dejar 8 en la casilla 1 y mostrarla.",
                [
                    "Definir datos Como Entero",
                    "Dimension datos[3] Como Entero",
                    "Guardar 8 en datos[1]",
                    "Escribir datos[1]",
                ],
                "Primero se reserva el arreglo y después se usa una casilla.",
                "se define, se dimensiona, se guarda 8 en la casilla 1 y se escribe.",
            ),
            _o(
                "Llenar con un Para",
                "Ordena un arreglo de 3 casillas que guarda 10, 20 y 30.",
                [
                    "Dimension datos[3] Como Entero",
                    "Abrir Para i desde 1 hasta 3",
                    "Guardar i * 10 en datos[i]",
                    "Cerrar el Para",
                ],
                "El índice del Para y el de la casilla pueden ser el mismo i.",
                "se dimensiona, el Para va de 1 a 3 y cada casilla guarda i * 10.",
            ),
            _o(
                "Sumar las casillas",
                "Ordena la suma de un arreglo ya lleno.",
                [
                    "Poner suma en 0",
                    "Recorrer i desde 1 hasta el tamaño",
                    "Sumar datos[i] a suma",
                    "Escribir suma",
                ],
                "No empieces el índice en 0.",
                "suma empieza en 0, se recorren las casillas y se escribe el total.",
            ),
            _o(
                "Escribir los dos extremos",
                "Ordena cómo escribir los extremos de un arreglo de 4 casillas.",
                [
                    "Dimension datos[4] Como Entero",
                    "Llenar las cuatro casillas",
                    "Escribir datos[1]",
                    "Escribir datos[4]",
                ],
                "La última casilla es el tamaño, no el tamaño menos uno.",
                "se dimensiona, se llena y se escriben la casilla 1 y la casilla 4.",
            ),
            _o(
                "Buscar el mayor",
                "Ordena la búsqueda del mayor en un arreglo.",
                [
                    "Guardar datos[1] en mayor",
                    "Recorrer desde la casilla 2",
                    "Si datos[i] es mayor, reemplazar mayor",
                    "Al terminar, escribir mayor",
                ],
                "El mayor provisional es la primera casilla.",
                "se parte de la casilla 1, se recorre el resto y se escribe el mayor.",
            ),
            _p(
                "Lo que hay en la uno",
                "Anticipa el número de la primera casilla.",
                algo(
                    [
                        "Definir datos Como Entero;",
                        "Dimension datos[3] Como Entero;",
                        "datos[1] <- 8;",
                        "datos[2] <- 5;",
                        "Escribir datos[1];",
                    ]
                ),
                "datos[2] no cambia lo que hay en datos[1].",
            ),
            _p(
                "La suma de dos casillas",
                "Anticipa lo que queda en la casilla 3.",
                algo(
                    [
                        "Definir datos Como Entero;",
                        "Dimension datos[3] Como Entero;",
                        "datos[1] <- 4;",
                        "datos[2] <- 7;",
                        "datos[3] <- datos[1] + datos[2];",
                        "Escribir datos[3];",
                    ]
                ),
                "4 + 7 se guarda en la tercera casilla.",
            ),
            _p(
                "Recorrido que acumula",
                "Cada casilla guarda i * 10. Anticipa la suma.",
                algo(
                    [
                        "Definir datos, i, suma Como Entero;",
                        "Dimension datos[3] Como Entero;",
                        "suma <- 0;",
                        "Para i <- 1 Hasta 3 Con Paso 1 Hacer",
                        "    datos[i] <- i * 10;",
                        "    suma <- suma + datos[i];",
                        "FinPara",
                        "Escribir suma;",
                    ]
                ),
                "10 + 20 + 30.",
            ),
            _p(
                "La última casilla",
                "Anticipa el valor de la última posición.",
                algo(
                    [
                        "Definir datos, i Como Entero;",
                        "Dimension datos[4] Como Entero;",
                        "Para i <- 1 Hasta 4 Con Paso 1 Hacer",
                        "    datos[i] <- i;",
                        "FinPara",
                        "Escribir datos[4];",
                    ]
                ),
                "La casilla 4 recibe el 4.",
            ),
            _p(
                "Una celda de la tabla",
                "Anticipa el valor guardado en la fila 2, columna 3.",
                algo(
                    [
                        "Definir tabla, fila, columna Como Entero;",
                        "Dimension tabla[2, 3] Como Entero;",
                        "Para fila <- 1 Hasta 2 Con Paso 1 Hacer",
                        "    Para columna <- 1 Hasta 3 Con Paso 1 Hacer",
                        "        tabla[fila, columna] <- fila * 10 + columna;",
                        "    FinPara",
                        "FinPara",
                        "Escribir tabla[2, 3];",
                    ]
                ),
                "fila 2 y columna 3 arman 2 * 10 + 3.",
            ),
            _b(
                "Extremos",
                "Reserva un arreglo de 3 enteros. Guarda 4, 9 y 1. Escribe la primera casilla y luego la última.",
                "¿Cuál es el índice de la primera casilla?",
                ["1", "uno"],
                [],
                algo(
                    [
                        "Definir datos Como Entero;",
                        "Dimension datos[3] Como Entero;",
                        "datos[1] <- 4;",
                        "datos[2] <- 9;",
                        "datos[3] <- 1;",
                        "Escribir datos[1];",
                        "Escribir datos[3];",
                    ]
                ),
                "Con tamaño 3, la última casilla es la 3.",
                "se escriben 4 y 1.",
            ),
            _b(
                "Suma de tres lecturas",
                "Lee tres enteros, guárdalos en un arreglo y escribe su suma.",
                "¿En qué número empieza el índice de un Para que recorre desde la primera casilla?",
                ["1", "uno"],
                ["2", "5", "8"],
                algo(
                    [
                        "Definir datos, i, suma Como Entero;",
                        "Dimension datos[3] Como Entero;",
                        "Para i <- 1 Hasta 3 Con Paso 1 Hacer",
                        "    Leer datos[i];",
                        "FinPara",
                        "suma <- 0;",
                        "Para i <- 1 Hasta 3 Con Paso 1 Hacer",
                        "    suma <- suma + datos[i];",
                        "FinPara",
                        "Escribir suma;",
                    ]
                ),
                "Se puede leer directo sobre datos[i].",
                "2 + 5 + 8 es 15.",
            ),
            _b(
                "El mayor del arreglo",
                "Lee cuatro enteros y escribe el mayor.",
                "¿Qué casilla sirve como mayor provisional?",
                ["la primera", "datos[1]", "1"],
                ["3", "9", "4", "7"],
                algo(
                    [
                        "Definir datos, i, mayor Como Entero;",
                        "Dimension datos[4] Como Entero;",
                        "Para i <- 1 Hasta 4 Con Paso 1 Hacer",
                        "    Leer datos[i];",
                        "FinPara",
                        "mayor <- datos[1];",
                        "Para i <- 2 Hasta 4 Con Paso 1 Hacer",
                        "    Si datos[i] > mayor Entonces",
                        "        mayor <- datos[i];",
                        "    FinSi",
                        "FinPara",
                        "Escribir mayor;",
                    ]
                ),
                "Compara desde la segunda casilla.",
                "el mayor de 3, 9, 4 y 7 es 9.",
            ),
            _b(
                "Invertir tres casillas",
                "Lee tres enteros. Escribe el tercero, luego el segundo y luego el primero.",
                "¿La última casilla de un arreglo de 3 es la 3 o la 2?",
                ["3", "la 3"],
                ["1", "2", "3"],
                algo(
                    [
                        "Definir datos, i Como Entero;",
                        "Dimension datos[3] Como Entero;",
                        "Para i <- 1 Hasta 3 Con Paso 1 Hacer",
                        "    Leer datos[i];",
                        "FinPara",
                        "Para i <- 3 Hasta 1 Con Paso -1 Hacer",
                        "    Escribir datos[i];",
                        "FinPara",
                    ]
                ),
                "El segundo Para baja con paso -1.",
                "1, 2 y 3 se escriben al revés: 3, 2 y 1.",
            ),
            _b(
                "Suma de la tabla",
                "Llena una tabla de 2 por 2 con los valores fila * 10 + columna y escribe la suma de las cuatro celdas.",
                "¿Cuántos índices tiene una celda de esa tabla?",
                ["2", "dos"],
                [],
                algo(
                    [
                        "Definir tabla, fila, columna, suma Como Entero;",
                        "Dimension tabla[2, 2] Como Entero;",
                        "suma <- 0;",
                        "Para fila <- 1 Hasta 2 Con Paso 1 Hacer",
                        "    Para columna <- 1 Hasta 2 Con Paso 1 Hacer",
                        "        tabla[fila, columna] <- fila * 10 + columna;",
                        "        suma <- suma + tabla[fila, columna];",
                        "    FinPara",
                        "FinPara",
                        "Escribir suma;",
                    ]
                ),
                "Las celdas son 11, 12, 21 y 22.",
                "11 + 12 + 21 + 22 es 66.",
            ),
        ],
    ),
    (
        "function",
        "Funciones",
        [
            _c(
                "Devuelve o solo actúa",
                "Clasifica cada subrutina.",
                ["función", "procedimiento"],
                [
                    ("Doblar devuelve el doble", "función"),
                    ("Saludar escribe un texto y no devuelve nada", "procedimiento"),
                    ("Promedio devuelve un real", "función"),
                    ("Incrementar cambia una variable y no devuelve un número", "procedimiento"),
                ],
                "La función devuelve un valor. El procedimiento hace un trabajo y no se usa como número.",
                "Doblar y Promedio son funciones. Saludar e Incrementar son procedimientos.",
            ),
            _c(
                "Parámetro o resultado",
                "Clasifica cada nombre de Funcion resultado <- Doblar(n).",
                ["parámetro", "resultado", "nombre"],
                [
                    ("n", "parámetro"),
                    ("resultado", "resultado"),
                    ("Doblar", "nombre"),
                    ("El 6 de Doblar(6)", "parámetro"),
                ],
                "n entra, resultado sale y Doblar es el nombre con el que se llama.",
                "n y el 6 son parámetros, resultado es el valor devuelto y Doblar es el nombre.",
            ),
            _c(
                "Por valor o por referencia",
                "Clasifica el modo del parámetro.",
                ["por valor", "por referencia"],
                [
                    ("Doblar(n), que no debe cambiar la variable original", "por valor"),
                    ("Incrementar(edad Por Referencia)", "por referencia"),
                    ("Una copia del número", "por valor"),
                    ("La misma caja del algoritmo", "por referencia"),
                ],
                "Por valor se trabaja con una copia. Por referencia se modifica la variable de afuera.",
                "Doblar y la copia son por valor. Incrementar y la misma caja son por referencia.",
            ),
            _c(
                "Dónde se escribe",
                "Clasifica dónde vive cada pieza.",
                ["fuera del algoritmo", "dentro del algoritmo"],
                [
                    ("Funcion resultado <- Doblar(n)", "fuera del algoritmo"),
                    ("Escribir Doblar(6)", "dentro del algoritmo"),
                    ("SubProceso Incrementar(n Por Referencia)", "fuera del algoritmo"),
                    ("La llamada Incrementar(edad)", "dentro del algoritmo"),
                ],
                "La declaración va aparte. La llamada va donde se usa.",
                "Funcion y SubProceso van fuera. Las llamadas van dentro del algoritmo.",
            ),
            _c(
                "Qué hay que definir adentro",
                "Dentro de la función, clasifica qué se declara.",
                ["se declara", "no se vuelve a declarar"],
                [
                    ("El resultado", "se declara"),
                    ("El parámetro n", "se declara"),
                    ("El nombre Doblar", "no se vuelve a declarar"),
                    ("Una variable local auxiliar", "se declara"),
                ],
                "El resultado, los parámetros y las locales se definen en el cuerpo.",
                "resultado, n y la auxiliar se declaran. El nombre Doblar no.",
            ),
            _o(
                "Definir y usar Doblar",
                "Ordena cómo queda lista una función y su llamada.",
                [
                    "Escribir la función fuera del algoritmo",
                    "Definir resultado y n como enteros",
                    "Guardar n * 2 en resultado",
                    "Cerrar con FinFuncion",
                    "Dentro del algoritmo, escribir Doblar(6)",
                ],
                "La llamada va después de que la función ya está escrita.",
                "se declara la función, se define, se asigna el doble, se cierra y luego se llama.",
            ),
            _o(
                "Llamar con un dato leído",
                "Ordena el uso de Doblar sobre un número leído.",
                [
                    "Definir numero Como Entero",
                    "Leer numero",
                    "Llamar Doblar(numero)",
                    "Escribir el valor devuelto",
                ],
                "La función recibe numero. No lee por su cuenta.",
                "se define numero, se lee, se llama Doblar y se escribe lo que devuelve.",
            ),
            _o(
                "Pasos para incrementar",
                "Ordena un procedimiento que modifica edad.",
                [
                    "Escribir el SubProceso con Por Referencia",
                    "Dentro, sumar 1 al parámetro",
                    "En el algoritmo, guardar 17 en edad",
                    "Llamar Incrementar(edad)",
                    "Escribir edad",
                ],
                "Por Referencia hace que el cambio se vea en edad.",
                "se declara el procedimiento, se suma 1, se guarda 17, se llama y se escribe edad.",
            ),
            _o(
                "Dos funciones",
                "Ordena un programa que dobla y después suma diez usando dos funciones.",
                [
                    "Escribir la función Doblar",
                    "Escribir la función SumarDiez",
                    "Llamar Doblar(3)",
                    "Pasar ese resultado a SumarDiez",
                    "Escribir el valor final",
                ],
                "Se puede pasar el resultado de una llamada como argumento de la otra.",
                "primero las dos funciones, luego Doblar(3), luego SumarDiez y al final el Escribir.",
            ),
            _p(
                "Doblar el tres",
                "Anticipa lo que devuelve la función.",
                programa(
                    "\n".join(
                        [
                            "Funcion resultado <- Doblar(n)",
                            "    Definir resultado, n Como Entero;",
                            "    resultado <- n * 2;",
                            "FinFuncion",
                        ]
                    ),
                    ["Escribir Doblar(3);"],
                ),
                "Doblar multiplica el argumento por 2.",
            ),
            _p(
                "El doble de seis",
                "Anticipa el número que se escribe.",
                programa(
                    "\n".join(
                        [
                            "Funcion resultado <- Doblar(n)",
                            "    Definir resultado, n Como Entero;",
                            "    resultado <- n * 2;",
                            "FinFuncion",
                        ]
                    ),
                    ["Escribir Doblar(6);"],
                ),
                "6 * 2.",
            ),
            _p(
                "Sumar desde una función",
                "Anticipa la suma que devuelve la función.",
                programa(
                    "\n".join(
                        [
                            "Funcion resultado <- Sumar(a, b)",
                            "    Definir resultado, a, b Como Entero;",
                            "    resultado <- a + b;",
                            "FinFuncion",
                        ]
                    ),
                    ["Escribir Sumar(4, 5);"],
                ),
                "Los dos argumentos se suman dentro de la función.",
            ),
            _p(
                "La referencia sí cambia",
                "edad empieza en 17. Anticipa lo que se escribe después de la llamada.",
                programa(
                    "\n".join(
                        [
                            "SubProceso Incrementar(n Por Referencia)",
                            "    Definir n Como Entero;",
                            "    n <- n + 1;",
                            "FinSubProceso",
                        ]
                    ),
                    [
                        "Definir edad Como Entero;",
                        "edad <- 17;",
                        "Incrementar(edad);",
                        "Escribir edad;",
                    ],
                ),
                "Por Referencia modifica la misma variable edad.",
            ),
            _p(
                "Factorial de cuatro",
                "Anticipa el factorial que se escribe.",
                programa(
                    "\n".join(
                        [
                            "Funcion resultado <- Factorial(n)",
                            "    Definir resultado, n Como Entero;",
                            "    Si n <= 1 Entonces",
                            "        resultado <- 1;",
                            "    Sino",
                            "        resultado <- n * Factorial(n - 1);",
                            "    FinSi",
                            "FinFuncion",
                        ]
                    ),
                    ["Escribir Factorial(4);"],
                ),
                "4 * 3 * 2 * 1.",
            ),
            _b(
                "Doblar el número leído",
                "Escribe una función Doblar que devuelva el doble de su parámetro. Lee un entero y escribe Doblar de ese entero.",
                "¿La función se escribe dentro o fuera del algoritmo?",
                ["fuera"],
                ["7"],
                programa(
                    "\n".join(
                        [
                            "Funcion resultado <- Doblar(n)",
                            "    Definir resultado, n Como Entero;",
                            "    resultado <- n * 2;",
                            "FinFuncion",
                        ]
                    ),
                    [
                        "Definir numero Como Entero;",
                        "Leer numero;",
                        "Escribir Doblar(numero);",
                    ],
                ),
                "La función va antes del algoritmo. El algoritmo solo lee y llama.",
                "con 7 se escribe 14.",
            ),
            _b(
                "Promedio en una función",
                "Escribe una función real Promedio(a, b) que devuelva (a + b) / 2. Lee dos reales y escribe el promedio.",
                "¿Qué tipo devuelve un promedio con decimales?",
                ["Real"],
                ["8", "9"],
                programa(
                    "\n".join(
                        [
                            "Funcion resultado <- Promedio(a, b)",
                            "    Definir resultado, a, b Como Real;",
                            "    resultado <- (a + b) / 2;",
                            "FinFuncion",
                        ]
                    ),
                    [
                        "Definir primero, segundo Como Real;",
                        "Leer primero;",
                        "Leer segundo;",
                        "Escribir Promedio(primero, segundo);",
                    ],
                ),
                "El resultado de la función también es Real.",
                "8 y 9 promedian 8.5.",
            ),
            _b(
                "Incrementar la edad leída",
                "Escribe un procedimiento Incrementar que sume 1 a su parámetro por referencia. edad empieza en el valor leído. Escribe edad después de la llamada.",
                "¿Qué modo deja ver el cambio fuera del procedimiento?",
                ["Por Referencia", "referencia"],
                ["17"],
                programa(
                    "\n".join(
                        [
                            "SubProceso Incrementar(n Por Referencia)",
                            "    Definir n Como Entero;",
                            "    n <- n + 1;",
                            "FinSubProceso",
                        ]
                    ),
                    [
                        "Definir edad Como Entero;",
                        "Leer edad;",
                        "Incrementar(edad);",
                        "Escribir edad;",
                    ],
                ),
                "Sin Por Referencia, edad se quedaría en 17.",
                "17 pasa a 18.",
            ),
            _b(
                "Máximo de dos",
                "Escribe una función Mayor(a, b) que devuelva el mayor de dos enteros. Lee dos números y escribe Mayor de esos dos.",
                "¿Qué instrucción elige entre los dos parámetros dentro de la función?",
                ["Si", "si"],
                ["3", "9"],
                programa(
                    "\n".join(
                        [
                            "Funcion resultado <- Mayor(a, b)",
                            "    Definir resultado, a, b Como Entero;",
                            "    Si a > b Entonces",
                            "        resultado <- a;",
                            "    Sino",
                            "        resultado <- b;",
                            "    FinSi",
                            "FinFuncion",
                        ]
                    ),
                    [
                        "Definir primero, segundo Como Entero;",
                        "Leer primero;",
                        "Leer segundo;",
                        "Escribir Mayor(primero, segundo);",
                    ],
                ),
                "La función devuelve a o b. No los escribe ella.",
                "el mayor de 3 y 9 es 9.",
            ),
        ],
    ),
)
