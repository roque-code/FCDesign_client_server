# Cómo crear un reto

El lugar de estas pantallas en el sistema está en [arquitectura.md](arquitectura.md). Un reto se arma dentro de una ruta. Entra a **Laboratorio**, abre **Rutas**, entra a la ruta y pulsa **Nuevo reto**. Al guardar, el reto queda en esa ruta y también en el grupo **Tus retos**. Para cambiarlo después, pulsa **Editar** en esa fila. Los retos del catálogo compartido se agregan a la ruta, pero no se editan. Si la cuenta está en inglés, el fuente del reto se muestra con las palabras reservadas en inglés y se guarda en la grafía que ya tenía.

El alumno ve el reto cuando la ruta está publicada y asignada. Los puntos se otorgan una sola vez, la primera vez que lo termina.

## Campos de todos los tipos

| Campo | Qué va ahí |
| --- | --- |
| Título | Nombre corto del reto. Máximo 120 caracteres. No se puede repetir dentro del mismo concepto. |
| Enunciado | Lo que el alumno lee antes de responder. Máximo 4000 caracteres. |
| Concepto | El tema que practica: Variables, Asignación, Entrada y salida, Operadores, Decisiones, Ciclo mientras, Opción múltiple, Ciclo para, Ciclo repetir, Arreglos o Funciones. |
| Tipo | Clasificar, Ordenar, Construir o Predecir. |
| Dificultad | Del 1 al 5. |
| Puntos | Del 1 al 500. Si lo dejas en 10, el reto vale 10 puntos. |
| Minutos | Tiempo para resolverlo. Déjalo vacío si no hay límite. El máximo es 1440 minutos. |
| Pistas | Hasta cinco, en el orden en que el alumno las pide. Cada una admite 500 caracteres. Si las dejas vacías, el reto no ofrece ayuda. |

Cada pista que el alumno pide baja la autonomía de la puntuación: sin pistas vale 10, con una vale 6, con dos vale 3 y con tres o más vale 0. La quinta pista es el nivel de solución: si la pide, la autonomía queda en 0. Si el texto de una pista incluye «Esta es la solución explicada», el alumno la ve marcada como solución.

## Clasificar

El alumno lee frases y coloca cada una en una categoría. No ve de antemano cuál es la categoría correcta.

Hacen falta al menos dos categorías y dos frases. El máximo es doce de cada una. Cada frase se asigna a una categoría escrita exactamente igual que en la lista. Una frase admite 240 caracteres.

### Ejemplo

| Campo | Contenido |
| --- | --- |
| Título | Señales de un programa |
| Enunciado | Separa lo que entra al programa, lo que el programa calcula y lo que muestra en pantalla. |
| Concepto | Entrada y salida |
| Tipo | Clasificar |
| Dificultad | 1 |
| Puntos | 10 |
| Minutos | vacío |
| Categorías | entrada, proceso, salida |
| Frases | Leer el nombre → entrada; Multiplicar precio por cantidad → proceso; Mostrar el total → salida |
| Pista 1 | Fíjate en quién produce el dato: la persona, el cálculo o la pantalla. |

En el formulario, las categorías van una por línea:

```text
entrada
proceso
salida
```

## Ordenar

El alumno acomoda instrucciones con **Subir** y **Bajar**. Escribe las líneas de arriba hacia abajo en el orden correcto: la primera línea es el primer paso. Hacen falta al menos dos y caben hasta doce. Cada línea admite 240 caracteres.

### Ejemplo

| Campo | Contenido |
| --- | --- |
| Título | Orden para saludar |
| Enunciado | Ordena los pasos para guardar un saludo y mostrarlo. |
| Concepto | Asignación |
| Tipo | Ordenar |
| Dificultad | 1 |
| Puntos | 10 |
| Minutos | vacío |
| Instrucciones | Definir saludo como cadena; Guardar hola en saludo; Escribir saludo |
| Pista 1 | Primero se declara la variable, después se guarda el texto y al final se muestra. |

En el formulario, una instrucción por línea:

```text
Definir saludo como cadena
Guardar hola en saludo
Escribir saludo
```

## Construir

El alumno responde una pregunta corta y después arma el programa con bloques, con el diagrama o con código. La salida del programa tiene que coincidir con la salida esperada, carácter por carácter, en todos los casos. Si falta uno, el reto no se cierra. Cada `Escribir` termina en un salto de línea. Si la salida que escribes no termina en salto de línea, el sistema agrega uno. Al terminar, el alumno ve cómo lo armó. El docente ve esa respuesta aunque el intento siga abierto.

La pregunta admite 240 caracteres. Hace falta al menos una respuesta aceptada y caben hasta doce. En esas respuestas no importan las mayúsculas ni los espacios. Las entradas son opcionales: una por cada `Leer`, en el orden en que el programa las pide, hasta doce. Si el programa no lee datos, deja las entradas vacías.

**Limitar la caja de herramientas** elige los bloques que el alumno ve y puede usar. Si lo dejas sin marcar, la caja trae todos. Si lo marcas, elige al menos uno: un bloque que no esté en la lista no aparece y, si el alumno lo usa, la comprobación lo rechaza. Incluye también los bloques de valor que el programa necesita. Para escribir un número hace falta **Número entero** o **Número real**, y para un texto hace falta **Texto**.

### Ejemplo

| Campo | Contenido |
| --- | --- |
| Título | El doble de un número |
| Enunciado | Lee un entero y escribe su doble. |
| Concepto | Operadores |
| Tipo | Construir |
| Dificultad | 2 |
| Puntos | 20 |
| Minutos | 15 |
| Pregunta | ¿Qué símbolo multiplica dos valores? |
| Respuestas aceptadas | * |
| Entradas | 6 |
| Salida esperada | 12 |
| Bloques | Definir, Variable, Leer, Escribir, Número entero, Operación |
| Pista 1 | El doble se obtiene multiplicando el número por dos. |
| Pista 2 | Esta es la solución explicada: define un entero, léelo, multiplícalo por 2 y escríbelo. |

Con la entrada `6`, un programa que hace `Escribir n * 2` produce:

```text
12
```

Esa línea ya incluye el salto de línea del `Escribir`. En el campo basta con escribir `12`.

## Predecir

El alumno lee el pseudocódigo, responde la pregunta y después puede ejecutarlo. La pregunta y las respuestas aceptadas funcionan igual que en Construir. El programa lo escribes tú. Tiene que compilar: el nombre del algoritmo es `Laboratorio`, cada instrucción lleva punto y coma y no uses `Leer`, porque esa ejecución no recibe entradas. El máximo del pseudocódigo es 8000 caracteres.

### Ejemplo

| Campo | Contenido |
| --- | --- |
| Título | Después de sumar uno |
| Enunciado | Anticipa el número que se escribe. Después podrás ejecutarlo. |
| Concepto | Asignación |
| Tipo | Predecir |
| Dificultad | 2 |
| Puntos | 20 |
| Minutos | vacío |
| Pregunta | ¿Qué número se escribe? |
| Respuestas aceptadas | 5 |
| Pseudocódigo | El programa de abajo |
| Pista 1 | Sigue el valor de n línea por línea. |
| Pista 2 | La segunda asignación usa el valor que n ya tenía. |

```text
Algoritmo Laboratorio
Definir n Como Entero;
n <- 4;
n <- n + 1;
Escribir n;
FinAlgoritmo
```

`n` empieza en 4 y luego suma 1, así que se escribe 5. La respuesta `5` y la respuesta ` 5 ` cuentan como la misma.

Al colocar un reto en una ruta, el docente elige el tipo. La lista se parte en Tus retos y Del catálogo, y solo muestra ese tipo. Todos deja los dos grupos completos.

## Archivo CSV

En **Laboratorio**, **Banco**, **Formato CSV** se ve el formato y se descarga una plantilla. **Descargar CSV** guarda los retos del tipo elegido en el estante abierto, para que otro docente los suba. Con el tipo en Todos, la pantalla pide elegir Clasificar, Ordenar, Construir o Predecir. El catálogo produce `retos-clasificar.csv`, `retos-ordenar.csv`, `retos-construir.csv` o `retos-predecir.csv`, con el banco del sistema y los retos de quien descarga. El concurso produce `retos-construir-concurso.csv`, con los cincuenta problemas de creación. Un alumno no puede descargar. **Subir CSV** agrega los retos al banco del docente, no al concurso. Un archivo admite hasta 250 retos y 1 MB. Si una fila falla, no se guarda ninguna.

La primera fila es el encabezado. El separador es la coma. Si el encabezado trae más punto y coma que comas, el separador pasa a ser el punto y coma. Un campo con coma, salto de línea o comillas va entre comillas dobles. Las listas internas se separan con `|`, así que no chocan con el punto y coma de una hoja en español.

Estas columnas van en los cuatro tipos:

| Columna | Qué va ahí |
| --- | --- |
| tipo | `clasificar`, `ordenar`, `construir` o `predecir`. |
| titulo | Nombre del reto. Máximo 120 caracteres. |
| enunciado | Lo que lee el alumno. Máximo 4000 caracteres. |
| concepto | La clave o el nombre: `variable`, `assignment`, `io`, `operator`, `if`, `while`, `switch`, `for`, `repeat`, `array`, `function`. También vale el nombre en español, por ejemplo `Operadores`. |
| dificultad | Del 1 al 5. Vacío significa 1. |
| puntos | Del 1 al 500. Vacío significa 10. |
| minutos | Tiempo para resolverlo. Vacío significa sin límite. El máximo es 1440. |
| pista1 … pista5 | Opcionales. Cada una admite 500 caracteres. |

`\n` dentro de una salida o de un pseudocódigo es un salto de línea.

### Clasificar

Además: `categorias` y `frases`.

`categorias` separa los nombres con `|`. Hacen falta al menos dos y caben hasta doce.

`frases` usa `texto => categoria` y separa las frases con `|`. La categoría tiene que coincidir con un nombre de `categorias`.

```text
tipo,titulo,enunciado,concepto,dificultad,puntos,minutos,categorias,frases,pista1
clasificar,Señales del dato,Separa lo que entra y lo que se muestra.,io,1,10,,entrada|salida,Leer un nombre => entrada|Mostrar el total => salida,Fíjate quién produce el dato.
```

### Ordenar

Además: `instrucciones`. Van en el orden correcto, separadas con `|`. La primera es el primer paso. Hacen falta al menos dos y caben hasta doce.

```text
tipo,titulo,enunciado,concepto,dificultad,puntos,minutos,instrucciones,pista1
ordenar,Pasos del saludo,Ordena las instrucciones.,assignment,1,10,,Definir saludo como cadena|Guardar hola en saludo|Escribir saludo,Primero se declara.
```

### Construir

Además: `pregunta`, `respuestas` y los casos `caso1_entradas`, `caso1_salida`, … hasta `caso6_entradas`, `caso6_salida`.

`respuestas` separa las opciones con `|`. Hace falta al menos una.

Cada caso tiene su salida. Las entradas de un caso se separan con `|`; si el programa no lee, `caso1_entradas` queda vacío. Los casos empiezan en 1 y no dejan huecos. Hace falta al menos un caso y caben seis. El reto abre código, diagrama y bloques, con la caja de herramientas completa.

Cada `Leer` del laboratorio también muestra el dato en su propia línea. La salida esperada es el texto completo, con esas líneas y después lo que escribe el programa. Si no termina en salto de línea, el sistema agrega uno.

```text
tipo,titulo,enunciado,concepto,dificultad,puntos,minutos,pregunta,respuestas,caso1_entradas,caso1_salida,caso2_entradas,caso2_salida,pista1
construir,El doble leído,Lee un entero y escribe su doble.,operator,2,15,15,¿Qué operador multiplica?,*|por,6,6\n12,0,0\n0,Multiplica por dos.
```

Con la entrada `6`, `Leer` muestra `6` y `Escribir` muestra `12`. La salida calificada es:

```text
6
12
```

### Predecir

Además: `pregunta`, `respuestas` y `pseudocodigo`.

El programa tiene que compilar. El nombre del algoritmo es `Laboratorio`, cada instrucción lleva punto y coma y no usa `Leer`. El máximo es 8000 caracteres.

```text
tipo,titulo,enunciado,concepto,dificultad,puntos,minutos,pregunta,respuestas,pseudocodigo,pista1
predecir,Después de sumar uno,Anticipa el número.,assignment,2,15,,¿Qué número se escribe?,5,"Algoritmo Laboratorio\nDefinir n Como Entero;\nn <- 4;\nn <- n + 1;\nEscribir n;\nFinAlgoritmo",Sigue el valor de n.
```

## Práctica de concurso

La ruta **Práctica de concurso** trae 50 problemas de creación de código. Los enunciados son propios y siguen el estilo de la práctica inicial de un concurso como omegaUp: se lee, se calcula y la salida se compara con tres casos (ejemplo, normal y borde). Van de la entrada y salida a las funciones. El primero queda abierto; el siguiente se abre al terminar el anterior.
