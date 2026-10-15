"""Los cinco algoritmos de esta fase, creados con cada cuenta nueva."""

from apps.language.models import LanguageProfile
from apps.projects.models import Algorithm, Project

EXAMPLES: tuple[tuple[str, str], ...] = (
    (
        "Hola mundo",
        """Algoritmo HolaMundo
    Escribir "Hola mundo";
FinAlgoritmo
""",
    ),
    (
        "Área de un triángulo",
        """Algoritmo AreaTriangulo
    Definir base, altura, area Como Real;
    Escribir "Ingrese la base:";
    Leer base;
    Escribir "Ingrese la altura:";
    Leer altura;
    area <- (base * altura) / 2;
    Escribir "El area es ", area;
FinAlgoritmo
""",
    ),
    (
        "Número mayor",
        """Algoritmo Mayor
    Definir a, b Como Entero;
    Leer a;
    Leer b;
    Si a > b Entonces
        Escribir a;
    Sino
        Si a = b Entonces
            Escribir "iguales";
        Sino
            Escribir b;
        FinSi
    FinSi
FinAlgoritmo
""",
    ),
    (
        "Tabla de multiplicar",
        """Algoritmo Tabla
    Definir n, i, producto Como Entero;
    Leer n;
    Para i <- 1 Hasta 10 Hacer
        producto <- n * i;
        Escribir n, " x ", i, " = ", producto;
    FinPara
FinAlgoritmo
""",
    ),
    (
        "Promedio de calificaciones",
        """Algoritmo Promedio
    Definir nota, suma, promedio Como Real;
    Definir cantidad, i Como Entero;
    Leer cantidad;
    suma <- 0;
    Si cantidad > 0 Entonces
        Para i <- 1 Hasta cantidad Hacer
            Leer nota;
            suma <- suma + nota;
        FinPara
        promedio <- suma / cantidad;
        Escribir promedio;
    Sino
        Escribir "sin notas";
    FinSi
FinAlgoritmo
""",
    ),
    (
        "Factorial",
        """Algoritmo Factorial
    Definir n, i, resultado Como Entero;
    Leer n;
    resultado <- 1;
    Si n > 1 Entonces
        Para i <- 2 Hasta n Hacer
            resultado <- resultado * i;
        FinPara
    FinSi
    Escribir resultado;
FinAlgoritmo
""",
    ),
    (
        "Arreglo de números",
        """Algoritmo Arreglo
    Definir numeros, i, suma Como Entero;
    Dimension numeros[5] Como Entero;
    suma <- 0;
    Para i <- 1 Hasta 5 Hacer
        numeros[i] <- i * 10;
        suma <- suma + numeros[i];
    FinPara
    Escribir suma;
FinAlgoritmo
""",
    ),
    (
        "Matriz",
        """Algoritmo Matriz
    Definir tabla, fila, columna, suma Como Entero;
    Dimension tabla[2, 3] Como Entero;
    suma <- 0;
    Para fila <- 1 Hasta 2 Hacer
        Para columna <- 1 Hasta 3 Hacer
            tabla[fila, columna] <- fila * 10 + columna;
            suma <- suma + tabla[fila, columna];
        FinPara
    FinPara
    Escribir suma;
FinAlgoritmo
""",
    ),
    (
        "Búsqueda lineal",
        """Algoritmo Busqueda
    Definir datos, i, buscado, encontrado Como Entero;
    Dimension datos[4] Como Entero;
    datos[1] <- 4;
    datos[2] <- 7;
    datos[3] <- 9;
    datos[4] <- 2;
    Leer buscado;
    encontrado <- 0;
    Para i <- 1 Hasta 4 Hacer
        Si datos[i] = buscado Entonces
            encontrado <- i;
        FinSi
    FinPara
    Escribir encontrado;
FinAlgoritmo
""",
    ),
    (
        "Ordenamiento",
        """Algoritmo Ordenar
    Definir datos, i, j, temporal Como Entero;
    Dimension datos[4] Como Entero;
    datos[1] <- 4;
    datos[2] <- 1;
    datos[3] <- 3;
    datos[4] <- 2;
    Para i <- 1 Hasta 3 Hacer
        Para j <- 1 Hasta 4 - i Hacer
            Si datos[j] > datos[j + 1] Entonces
                temporal <- datos[j];
                datos[j] <- datos[j + 1];
                datos[j + 1] <- temporal;
            FinSi
        FinPara
    FinPara
    Para i <- 1 Hasta 4 Hacer
        Escribir datos[i];
    FinPara
FinAlgoritmo
""",
    ),
    (
        "Función doblar",
        """Funcion resultado <- Doblar(n)
    Definir resultado, n Como Entero;
    resultado <- n * 2;
FinFuncion
Algoritmo Doble
    Definir numero Como Entero;
    Leer numero;
    Escribir Doblar(numero);
FinAlgoritmo
""",
    ),
    (
        "Procedimiento incrementar",
        """SubProceso Incrementar(n Por Referencia)
    Definir n Como Entero;
    n <- n + 1;
FinSubProceso
Algoritmo Incremento
    Definir edad Como Entero;
    edad <- 17;
    Incrementar(edad);
    Escribir edad;
FinAlgoritmo
""",
    ),
    (
        "Factorial recursivo",
        """Funcion resultado <- Factorial(n)
    Definir resultado, n Como Entero;
    Si n <= 1 Entonces
        resultado <- 1;
    Sino
        resultado <- n * Factorial(n - 1);
    FinSi
FinFuncion
Algoritmo Recursivo
    Definir numero Como Entero;
    Leer numero;
    Escribir Factorial(numero);
FinAlgoritmo
""",
    ),
)


def seed_examples(user) -> Project:
    profile = LanguageProfile.objects.get(key="strict")
    project = Project.objects.create(
        owner=user,
        name="Ejemplos",
        description="Algoritmos de ejemplo",
        visibility="private",
    )
    for name, source in EXAMPLES:
        Algorithm.objects.create(
            project=project,
            owner=user,
            name=name,
            source=source,
            language_profile=profile,
        )
    return project
