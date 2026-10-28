# Pruebas y roadmap

Estado: fases 0 a 6 hechas en desarrollo. La configuración de producción no está activa: el compose usa `DEBUG` verdadero. Las comunidades de docentes ya están; las actividades y las entregas, no. Las pruebas del núcleo y del servidor se ejecutan; este documento ya no es un plan sin código.

## 1. Cómo se prueba

`language_core` se prueba con pytest, sin Django y sin base de datos. El servidor se prueba con pytest-django contra PostgreSQL, no contra SQLite, porque los índices parciales y las restricciones forman parte del diseño.

Herramientas: Ruff, Black, mypy y pytest-cov. En el cliente: `tsc` y Vitest. La interfaz se comprueba además en el navegador, recorriendo el flujo y no solo con una captura.

Metas, medidas al cerrar la fase correspondiente:

- 90 % de cobertura de líneas en `language_core`;
- 80 % de cobertura de líneas en el backend Django;
- cada código de error corregido gana una prueba de regresión que cita ese código.

No se dará por ejecutada una prueba sin mostrar el comando y el resumen real.

## 2. Núcleo

| Área | Qué fija la prueba |
| --- | --- |
| Lexer | palabras clave con distinto caso y acentos; la grafía inglesa (`Algorithm`, `If`, `True`) resuelve al canónico español; identificadores `año` y `ano`; cadenas y comentarios sin cerrar; columna correcta con carácter multibyte |
| Parser | cada producción válida y el cierre que falta (`FinSi`, `FinMientras`, `FinPara`, paréntesis, corchetes) |
| AST | volcado estable del ejemplo «mayor de edad» y de condicionales anidados |
| Precedencia | `-2^2`, `2^3^2`, `a O b Y c`, `NO a Y b`, rechazo de `a < b < c` |
| Semántica | no declarada, doble declaración, asignación incompatible, condición no lógica |
| Tipos | ensanche Entero a Real, rechazo de Real a Entero, cadena con `+` |
| Condicionales | ambas ramas, `Sino` vacío, anidación |
| Ciclos | cero vueltas de `Mientras`, una vuelta mínima de `Repetir`, paso positivo, paso negativo, paso omitido, paso cero |
| Arreglos | una, dos y tres dimensiones; base 0 y base 1; índice fuera de rango; arreglo por referencia y por valor |
| Funciones | retorno, retorno ausente, aridad, recursión dentro del límite y por encima del límite |
| Procedimientos | parámetro por valor no altera el original; por referencia sí |
| Entrada y salida | suspensión, texto inválido, reintento, formato de `Escribir`. El dato aceptado queda en la salida, en su línea y antes de lo que se escriba después. El rechazado no |
| Límites | instrucciones, profundidad, celdas, tamaño de salida, cancelación |
| Diagramas | grafo de secuencia, `Si`, `Para`, `Repetir`, `Segun` y llamada; el nodo apunta a la línea. Las etiquetas del grafo siguen siendo `Sí` y `No`. La figura de ciclo es `loop` y la de `Segun` es `switch`, con `kind` `decision` |
| Traducción | `language_core/tests/test_translate.py`. Python coincide con la salida del intérprete en los fixtures. C también, si el compilador está. `Segun` usa `match` o `switch`, y una cadena de `Si` cuando el tipo no cabe. Un error no genera código |
| Regresión | un archivo por código de error que se haya corregido |

Algoritmos completos que deben pasar como fixtures, en la fase que los haga ejecutables:

1. Hola mundo.
2. Área de un triángulo.
3. Número mayor.
4. Tabla de multiplicar.
5. Promedio de calificaciones.
6. Factorial.
7. Arreglo unidimensional.
8. Matriz.
9. Búsqueda lineal.
10. Ordenamiento básico.
11. Función con parámetros.
12. Procedimiento.
13. Recursividad, con el factorial recursivo además del iterativo.

## 3. Backend y API

- Crear usuario, entrar, salir y pedir restablecimiento con el backend de correo en memoria. Con la confirmación activa, el alta no abre sesión hasta el enlace.
- Un usuario no lee ni modifica el proyecto de otro: la respuesta es 404.
- El enlace revocado o caducado no entrega el fuente.
- Validar no crea una ejecución.
- Traducir no crea una ejecución y, con un fuente válido, devuelve los siete lenguajes. Si el docente o el nivel la apagaron, responde 403.
- El alta no crea un administrador. `create_admin` sí. El nivel gratis limita proyectos y códigos. Sin la cabecera de la aplicación, el navegador recibe 403 fuera de la cuenta.
- El administrador puede apagar el alta de alumno o de docente. El formulario oculta esa opción y el servidor la rechaza.
- Pegar se apaga por comunidad o por alumno. El docente sigue pudiendo pegar si su nivel lo incluye.
- Un docente lee y ejecuta el algoritmo de su alumno sin crear una versión. Otra persona recibe 404.
- El CSV de una ruta trae una fila por alumno y la nota. El docente descarga los retos de un tipo; un alumno recibe 403. La carga admite hasta 250 filas y 1 MB y, si una fila falla, no guarda ninguna.
- La ruta Práctica de concurso publica 50 retos. El primero está abierto y el segundo, cerrado.
- Un reto de construir no se cierra si falta un caso. Al cerrarlo, el alumno ve su respuesta. El docente la ve aunque el intento siga abierto.
- Ejecutar persiste salida y error, y no persiste cada línea del depurador.
- El autoguardado no multiplica versiones; ejecutar con fuente nuevo sí abre versión.
- Restaurar una versión no borra las posteriores.
- El tercer ingreso fallido del mismo correo responde 429 y bloquea ese correo 15 minutos. Una segunda sesión responde 409. Tras 30 minutos sin uso la API responde 401 y cierra la sesión. `execute` sigue con su límite de peticiones.
- El modo en proceso no está disponible con la configuración de producción. Esta prueba importa los ajustes y espera un error de arranque.

## 4. Interfaz crítica del MVP

El cliente ya existe. Estas comprobaciones se hacen en el navegador, recorriendo el flujo:

- registrarse y entrar;
- crear proyecto y algoritmo;
- escribir, ver el error de un `FinSi` ausente y saltar a la línea;
- ejecutar un programa con `Leer` y comprobar la salida;
- recargar y ver el mismo fuente;
- cambiar tema claro y oscuro;
- abrir el diagrama del condicional y comprobar que seleccionar el rombo marca la línea del `Si`.

Esas pruebas son de comportamiento. Una captura estática no las sustituye.

## 5. Roadmap

### Fase 0 — diseño

Hecha. Esta documentación, puesta al día con el código.

### Fase 1 — núcleo mínimo

Hecha. Paquete `language_core` y pruebas. Sin Django.

1. Tokens, lexer y diagnósticos léxicos.
2. Parser de sentencias del subconjunto y Pratt de expresiones.
3. AST y volcado.
4. Tipos, ámbitos y analizador semántico de escalares.
5. Intérprete de asignación, expresiones, `Leer`, `Escribir`, `Si`, `Mientras`, `Repetir` y `Para`.
6. Límites de instrucciones, tiempo y cancelación.
7. Fixture de los algoritmos 1 a 5.
8. Ruff, Black, mypy y cobertura del paquete.

Esos archivos están en el árbol, junto con `pyproject.toml` en la raíz.

### Fase 2 — editor web

Hecha. Django, usuario propio, proyectos, algoritmos, autoguardado, API de validar y ejecutar, React, CodeMirror, consola que responde a `input_requested`, temas y ejemplos. Los ejemplos precargados son los 1 a 13.

El ejecutor de esta fase es el de desarrollo, en proceso, con límites. La pantalla lo indica en la configuración de desarrollo.

### Fase 3 — lenguaje avanzado

Hecha. Arreglos, `Segun`, funciones, procedimientos, parámetros, recursión, biblioteca estándar, perfiles estricto y flexible, fixtures 6 a 13. Cada algoritmo puede exigir o no el punto y coma, y usar índices desde 1 o desde 0.

### Fase 4 — depurador

Hecha. Paso, entrar, salir, puntos de interrupción, paneles y SSE. Sigue el mismo intérprete. El SSE sale del proceso de desarrollo.

### Fase 5 — diagramas

Hecha. `flowchart.py`, API, React Flow, posiciones en el cliente, sincronización en ambos sentidos, SVG, PNG, PDF y vista de impresión. El detalle de figuras y de trazos está en [arquitectura.md](arquitectura.md).

### Después de la fase 5, ya en el editor

- Ocultar y mostrar proyectos y diagrama. El diagrama oculto deja el rótulo arriba, con el control para abrirlo.
- Separadores para el ancho de proyectos, editor y diagrama.
- Barra de estado con el guardado y la línea del cursor.
- Renombrar proyecto y algoritmo. Descargar el fuente y eliminar un algoritmo.
- Tabulador para indentar. Selección visible en una sola línea.
- Al escribir una instrucción, el editor ofrece su estructura. Tab recorre los huecos. La prueba está en `frontend/src/editor/snippets.test.ts`.
- Lenguajes aparece si el nivel lo incluye. En el navegador corre en el servidor; en la aplicación de escritorio, en la máquina. Si falta el runtime, se descarga del manifiesto y se escribe en disco. Un construir con casos no se cierra hasta que ese código pasa todos los casos. Repetir el alta con un correo existente responde que ya está registrado.
- Cada nivel tiene un tope de ejecuciones al día, 3 como mínimo, o vacío si no hay tope. Ejecutar, depurar, la práctica, comprobar un reto y arrancar un lenguaje descuentan una. El pseudocódigo se corta a 100 000 instrucciones o a 5 segundos, y Detener lo corta antes. La identidad muestra las que quedan.
- En el servidor público los lenguajes del navegador corren en un contenedor aparte. Si no responde, la API dice que Lenguajes no está disponible. El avance del docente empieza por la comunidad y el CSV de la ruta solo incluye a sus alumnos. El administrador puede bloquear una cuenta.
- Un construir puede guardarse sin casos. Probar no compara una salida ni descuenta una ejecución. Un caso admite hasta 40 entradas. El mismo reto puede estar dos veces en una ruta. La campana del alumno avisa de uno nuevo o de uno habilitado. Armar Nassi-Shneiderman dibuja el mismo algoritmo en columnas.
- Menú **Configuración** y menú **Funciones**. El idioma de la cuenta cambia los textos y la grafía de las palabras reservadas, y no reescribe el fuente guardado.
- **Traducir** muestra el algoritmo en los siete lenguajes sin ejecutarlo. **Actualizar** vuelve a cargar la cuenta y suelta el borrador local.
- La consola hace eco del dato aceptado y se desplaza hasta el final.
- `Caracter` es un solo símbolo. La palabra del editor es `Caracter`.

### Fase 6 — contenedores de desarrollo

Hecha en la máquina de desarrollo. `compose.yaml` levanta PostgreSQL, Redis, el runner aislado, Gunicorn, Vite, Nginx y Mailpit, con volúmenes y healthchecks. El runner no importa Django. Redis es el bus de órdenes y de eventos. Nginx publica el canal SSE con el buffer apagado. El alta de los contenedores envía la confirmación por SMTP y no abre sesión hasta el enlace. La integración continua está en `.github/workflows/ci.yml`. Los manuales son [instalacion.md](instalacion.md), [desarrollo.md](desarrollo.md), [despliegue.md](despliegue.md) y [arquitectura.md](arquitectura.md).

El servidor público ya carga `config.settings.production`. Rechaza el ejecutor en proceso, exige Redis y `EMAIL_HOST`, y exige orígenes `https://`. El procedimiento está en [instalacion-aws.md](instalacion-aws.md).

La aplicación de escritorio ya se empaqueta, a mano, con `.github/workflows/desktop.yml`. El intérprete de esa ventana es `local_host`. La API de cuentas sigue siendo la de Django. No es el nodo de producción descrito en [despliegue.md](despliegue.md).

En la máquina, sin el compose, el editor puede seguir con el ejecutor en proceso. Las pruebas cubren los dos caminos.

Las actividades y las entregas siguen sin implementarse. Las comunidades de un docente, sobre cuentas ya registradas, sí están.

## 6. Criterios del MVP

Un estudiante ya puede hacer lo siguiente desde un navegador de escritorio actual:

1. Registrarse e iniciar sesión. En los contenedores, abrir el enlace de Mailpit antes de entrar.
2. Crear un proyecto.
3. Crear y editar un algoritmo.
4. Declarar variables.
5. Leer y escribir.
6. Usar expresiones y operadores.
7. Ejecutar condicionales.
8. Ejecutar `Para`, `Mientras` y `Repetir`.
9. Validar antes de ejecutar.
10. Ver errores con línea, columna y sugerencia.
11. Ejecutar en una consola interactiva.
12. Guardar y volver a abrir.
13. Ver un diagrama básico generado desde el AST.
14. Usar la aplicación en un navegador moderno, en español o en inglés, o en la ventana de escritorio.
15. Pedir la traducción del algoritmo a otro lenguaje sin ejecutarlo.
16. Ejecutar las pruebas automáticas.

Arreglos, subrutinas, depurador y diagrama están en el producto. El aislamiento del runner está en el compose de desarrollo y en el servidor público.

## 7. Definición de hecho de cada fase

- Las pruebas nuevas pasan y se muestra el comando.
- Ruff y Black no cambian el árbol, cuando el paquete ya existe.
- mypy no reporta errores en el paquete tocado, cuando ya está configurado.
- No se abre la fase siguiente sin autorización.
