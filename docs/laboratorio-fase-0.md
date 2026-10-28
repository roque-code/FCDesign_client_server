# Laboratorio visual — fase 0

Estado: fase 8 hecha, y después llegaron el banco, la autoría de rutas, los puntos, el idioma de la cuenta, la traducción del algoritmo y la ventana de escritorio. Fecha de referencia: 2026-10-27. Los menús del laboratorio dependen del nivel de la cuenta. La ruta Fundamentos publica treinta y cuatro retos. La ruta Práctica de concurso publica cincuenta problemas de creación de código. Un docente carga y descarga retos por CSV, ve el tablero de avance, descarga las notas y abre el trabajo de un reto. Al armar una ruta, elige el tipo y la lista solo muestra Clasificar, Ordenar, Construir o Predecir. En cada reto de esa ruta define la ponderación de la nota, y esas cifras no cambian el reto original. Un construir con casos pide además el código de un lenguaje y no se cierra si ese código no pasa todos los casos. Si el docente apaga la validación por casos, el alumno entrega el programa y el lenguaje sin comparar una salida, y esa comprobación no descuenta una ejecución. Un caso admite hasta 40 entradas. El mismo reto puede repetirse en la ruta: la copia nueva tiene su horario y los intentos de la anterior se conservan. Los paneles del enunciado, de los casos, de la ayuda y del editor se arrastran. La campana del alumno avisa de un reto nuevo o de uno que volvió a estar disponible. La nota del intento se guarda al avanzar, y el docente la ve aunque el reto no esté terminado. En el reto, esa nota queda junto a los nombres de las etapas. Comprobar el reto y arrancar la práctica cuentan como una ejecución del día. Un docente abre el avance eligiendo primero una comunidad y ve solo a sus alumnos. El CSV de una ruta, pedido desde ahí, trae solo a esa comunidad. Arma rutas y las asigna. La práctica libre y el reto se usan con teclado y, en pantalla chica, con pestañas. El intento no es una fila de `Execution`. El banco de trabajo sigue en su pantalla. El mapa del sistema está en [arquitectura.md](arquitectura.md).

Las secciones 1 a 11 conservan el diseño con el que se autorizó el módulo. Varias frases de ese tramo describen el hueco que había antes de construirlo. Lo que está en el código empieza en la sección 12.

## 1. Diagnóstico

Aulivana-FCDdesign ya es el editor: el estudiante escribe pseudocódigo, lo valida, lo ejecuta, lo depura y ve el diagrama. El núcleo recorre un AST. No usa `eval` ni `exec`. Traducir a Python u otro lenguaje es otra acción y no corre el algoritmo. Las fases 1 a 6 del producto están hechas en desarrollo. El laboratorio no depende de un servidor de producción. En los contenedores, la pasada del laboratorio usa el mismo runner. En la máquina, sin la ventana de escritorio, sigue en el proceso de Django. En esa ventana la pasada va a `local_host`, que importa el mismo núcleo.

El diseño nuevo pide otra cosa encima de ese motor: una secuencia pedagógica. El alumno comprende el problema, razona reglas y casos, construye con bloques, predice, ejecuta paso a paso y explica. Blockly es la entrada visual. El AST actual sigue siendo la representación canónica. El pseudocódigo, el diagrama, la validación y la ejecución salen de ese mismo árbol.

Hoy el camino es al revés para el editor: el texto es la entrada y el árbol es el resultado. El laboratorio añade el camino bloques → árbol → texto, sin reemplazar el primero.

Antes de la fase 1 no había rutas, retos, intentos, pistas, predicciones, dominio ni reflexión. `classroom` solo agrupaba cuentas. El laboratorio no rellenó las tablas de actividades y entregas, que siguen sin existir: usa las suyas. Hoy esas tablas de `learning` están migradas.

## 2. Stack que se reutiliza

| Pieza | Dónde está | Uso en el laboratorio |
| --- | --- | --- |
| AST, tipos, semántica, intérprete, depurador, límites | `language_core` | El mismo paquete. Sin copia. |
| Diagrama desde el árbol | `language_core/flowchart.py`, `frontend/src/diagram/` | Se puede mostrar cuando el árbol exista. No es el centro del primer corte. |
| Sesión, CSRF, alumno y docente | `accounts` | La misma cookie. El papel `student` o `teacher` ya vive en `Profile.role`. |
| API `/api/v1/`, errores, paginación, permisos | `server/config` y las apps actuales | Mismo sobre `{ "error": { "code", "message", "details" } }`. |
| Ejecución paso a paso | `executions`, SSE | El patrón se copia en un servicio del laboratorio. Las filas de `Execution` no se reutilizan: exigen un `Algorithm`. |
| Comunidades | `classroom` | Siguen siendo membresía. El avance docente llega después y no mezcla retos con comunidades en la fase 1. |
| Cliente React, TypeScript, Vite | `frontend` | Pantalla nueva al lado de `Workbench`. |

Lo que no se trae del diseño, porque el proyecto ya decidió otra cosa:

- Celery. [ADR 0007](adr/0007-ejecucion-sin-celery.md): la ejecución se pausa en `Leer` y en el depurador.
- WebSocket o Django Channels. El canal vigente es SSE. El sobre de eventos no depende del transporte.
- Un segundo intérprete, ni generar JavaScript o Python desde los bloques.

## 3. Riesgos

| Riesgo | Efecto | Cómo se contiene |
| --- | --- | --- |
| Otro árbol distinto del de `ast_nodes.py` | El diagrama y el intérprete del editor dejan de coincidir con el laboratorio | El adaptador construye los nodos que ya existen |
| Líneas de pseudocódigo inestables | El paso a paso no cae en el bloque | La impresora numera al emitir y guarda `block_id` → línea |
| Eventos nuevos dentro del intérprete | El depurador del editor cambia de comportamiento | El primer corte no añade tipos de evento. Traduce los que ya hay |
| Guardar bloques en `Algorithm.source` | Un intento pisa un algoritmo del banco de trabajo | Tablas propias. Un intento no escribe proyectos |
| Blockly genera código ejecutable | Dos semánticas | Blockly solo serializa JSON. Ejecuta el AST |
| Acoplar el laboratorio al runner | Se frena la pantalla si Redis no responde | En la máquina, el mismo proceso y los mismos `Limits`. En los contenedores, la pasada viaja por Redis. La configuración de producción sigue sin cargarse |
| Retos escritos en el cliente | No se pueden añadir sin cambiar la pantalla | El reto es un registro. La pantalla lee la API |

## 4. Mapa de archivos

Crear, cuando se autorice cada fase:

```text
language_core/block_adapter.py      JSON de Blockly → nodos actuales
language_core/pseudocode.py         AST → texto del perfil estricto
language_core/tests/test_block_adapter.py
language_core/tests/test_pseudocode.py
server/apps/learning/               modelos, API, servicios, pruebas
frontend/src/learning/              pantalla, etapas, mentor, traza, bloques
```

Enganchar, con el menor diff posible:

| Archivo | Cambio |
| --- | --- |
| `frontend/src/App.tsx` | Tras entrar, elige banco de trabajo o laboratorio. Al volver, el banco sigue siendo el de siempre |
| Barra del banco de trabajo | Un control «Laboratorio». No se mueve el editor, el diagrama ni las comunidades |
| `server/config/urls.py` | `include` de `apps.learning.urls` |
| `server/config/settings/base.py` | la app en `INSTALLED_APPS` |
| `frontend/package.json` | dependencia Blockly |

No se modifican el interior de `Workbench`, `CodeEditor`, el cliente del depurador, los modelos de proyectos, ejecuciones, cuentas y comunidades, ni el parser, el intérprete y el generador de diagramas.

## 5. Contrato del AST

El contrato ya está en [ast.md](ast.md) y en `language_core/ast_nodes.py`. El laboratorio no define otro. Los nodos son dataclasses inmutables con `SourceSpan`. Los nombres de clase están en inglés. El adaptador sigue emitiendo el canónico español. Si la cuenta está en inglés, los bloques y el pseudocódigo que se muestra usan la grafía inglesa; el intérprete recibe el canónico.

Programa mínimo que el adaptador debe poder construir en el primer corte:

```text
Program
  Algorithm
    DefineStmt          Definir … Como Entero|Real|Cadena|Caracter|Lógico
    AssignStmt          destino <- expresión
    ReadStmt            Leer
    WriteStmt           Escribir
    IfStmt              Si / Entonces / Sino / FinSi
    WhileStmt           Mientras / Hacer / FinMientras
  functions = ()
  procedures = ()
```

Expresiones del primer corte: `LiteralExpr`, `NameExpr`, `UnaryExpr` (`neg`, `not`), `BinaryExpr` aritmético, relacional y lógico (`add`, `sub`, `mul`, `div`, `mod`, `eq`, `neq`, `lt`, `lte`, `gt`, `gte`, `and`, `or`).

Quedan para fases posteriores del laboratorio, aunque el editor ya los ejecuta: `SwitchStmt`, `RepeatStmt`, `ForStmt`, `DimensionStmt`, `IndexExpr`, `CallExpr`, `FunctionDecl`, `ProcedureDecl`.

Los nodos no llevan `block_id`. No se les añade un campo: el depurador y el diagrama leen `SourceSpan`. El adaptador devuelve, junto al `Program`, un índice aparte:

```text
BlockBinding
  block_id: str
  line: int          # start_line del nodo, 1..n
  column: int
```

Ese índice vive en la foto del workspace, no en el árbol. Si mañana cambian los bloques, el AST no migra.

Perfil del laboratorio: estricto, punto y coma obligatorio, índices desde 1, declaración obligatoria, `<-` asigna y `=` compara. Esas banderas ya existen. El laboratorio no ofrece el menú de punto y coma ni de base de índices del editor.

## 6. Estrategia de transformación

```text
JSON de Blockly
  → block_adapter
  → Program + BlockBinding
  → semantic_analyzer (el de hoy)
  → si no hay error:
       pseudocode.py  → texto
       flowchart.py   → grafo
       interpreter    → eventos ya existentes
  → la pantalla une block_id, línea y variables
```

Reglas:

1. No se ejecuta el texto generado. El texto es una vista. Si se quiere comprobar que la vista es fiel, una prueba puede volver a parsear ese texto y comparar el volcado de `dump()` con el del árbol original.
2. La impresora usa la grafía de `KEYWORD_DISPLAY`: `Definir`, `Como`, `Leer`, `Escribir`, `Si`, `Entonces`, `Sino`, `FinSi`, `Mientras`, `Hacer`, `FinMientras`, `Algoritmo`, `FinAlgoritmo`.
3. Cada sentencia ocupa líneas estables. El cuerpo anidado se indenta con cuatro espacios, como los ejemplos de `apps/projects/examples.py`.
4. El evento `line` ya trae línea, columna, ámbito y `payload.variables`. La pantalla resalta el bloque cuyo `BlockBinding.line` coincide, la línea del pseudocódigo y los valores.
5. Correspondencia con los nombres del diseño, sin cambiar `EventKind`:

| Evento actual | Lo que muestra el laboratorio |
| --- | --- |
| primer `line` | ejecución iniciada |
| `line` | sentencia activa, variables |
| `output` | salida |
| `input_requested` | espera de `Leer` |
| `input_rejected` | dato no aceptado; no se pinta como salida |
| `call` / `return` | el depurador ya los emite; la práctica libre muestra el ámbito |
| `error` | fallo, con el código de diagnóstico ya existente |
| `finished` | fin |
| `cancelled` | detención |

`expression_evaluated`, `condition_evaluated` y `variable_changed` no se añaden al intérprete en el primer corte. El resaltado de la sentencia y la foto de variables cubren comprobar. Esos eventos finos solo se valorarían en una fase posterior, y el depurador del editor tendría que ignorarlos.

Órdenes de la pantalla: ejecutar, pausar, continuar, un paso, detener, reiniciar. Son las que el depurador ya entiende. En desarrollo las atiende el proceso de Django, con `Limits`. Sin acceso a archivos, red ni entorno.

## 7. Modelos propuestos

Aplicación `server/apps/learning`, con los modelos en carpetas aparte del editor. Convenciones iguales a las de hoy: UUID público, `timestamptz`, JSON para lo que cambia de forma con la versión de los bloques. El catálogo de conceptos se carga en la migración `0002_seed_concepts`. Los diez retos de Fundamentos llegan en `0003_seed_path`.

El reto es un dato. La primera ruta carga diez. Se pueden definir más sin cambiar la pantalla, mientras el tipo de actividad y los bloques pedidos ya estén implementados. Una ruta o una unidad nueva es otro registro, no otro módulo.

| Modelo | Campos principales | Notas |
| --- | --- | --- |
| `LearningPath` | id, name, description, position, is_published | Contenido de sistema. Más rutas caben aquí |
| `LearningUnit` | id, path, title, concept_key, position, prerequisite | Orden dentro de la ruta |
| `Challenge` | id, unit, title, prompt, activity_type, difficulty, allowed_blocks, restrictions, position, is_published | `activity_type`: `classify`, `order`, `build`, `predict`. Otros tipos esperan su fase |
| `ChallengeTestCase` | id, challenge, name, inputs, expected_output, kind | `kind`: `normal`, `boundary`, `invalid` |
| `ChallengeAttempt` | id, challenge, user, status, score, started_at, finished_at | Un alumno, un reto, varios intentos. No es `Execution` |
| `WorkspaceSnapshot` | id, attempt, schema_version, blockly_json, ast_dump, pseudocode, bindings, created_at | Foto al guardar y al cerrar. El JSON de Blockly es el de su serialización actual |
| `Hint` | id, challenge, level, body, position | Niveles 1 a 5: orientación, pregunta, señalamiento, demostración parcial, solución explicada |
| `HintUsage` | id, attempt, hint, created_at | Qué ayuda se pidió y cuándo |
| `Prediction` | id, attempt, prompt_key, expected, answer, is_correct, created_at | Valor o rama anticipada |
| `Reflection` | id, attempt, body, created_at | Texto del alumno al explicar. Una por intento cerrado |
| `Concept` | key, name | Catálogo corto: `variable`, `assignment`, `io`, `operator`, `if`, `while`, … |
| `ConceptMastery` | id, user, concept, level, evidence, updated_at | Único `(user, concept)` |

`ExecutionTrace` no es tabla. La traza viva va por SSE. Al cerrar se guardan estado, puntuación, salida resumida y la foto. Igual que hoy no se persiste cada `line`.

Ponderación del diseño, aplicada al cerrar un intento de construcción, no en la fase 1: comprensión 20, diseño 25, corrección 30, explicación 15, autonomía 10. Los pesos viven en el servicio, no repartidos por filas.

Permisos: el alumno lee retos publicados y solo sus intentos. Un docente, en la fase 8, lee el avance de las cuentas que ya puede ver. Un reto ajeno o un intento ajeno responde 404, como un algoritmo privado.

No hay pantalla de autoría en el primer corte. Quien define más retos lo hace como datos de carga. Una alta docente usaría estos mismos modelos más adelante.

## 8. Pantalla

Nombre visible: **Laboratorio**. Se abre desde la barra del banco de trabajo y se cierra volviendo a él. `App` conserva la cuenta. El estado del editor no se mezcla con el del intento.

Regiones, de arriba abajo y de izquierda a derecha en escritorio:

| Región | Contenido | Regla |
| --- | --- | --- |
| Barra | Reto, avance de etapas, ejecutar, pausar, paso, reiniciar | Solo las acciones de la etapa actual |
| Etapas | Comprender, Razonar, Construir, Comprobar, Explicar | Si el reto lo exige, Construir sigue cerrado hasta terminar el análisis |
| Izquierda | Caja de bloques por categoría | El reto declara `allowed_blocks`. Lo demás no se muestra |
| Centro | Lienzo Blockly | Conexión inválida: no enchufa, o advierte con texto |
| Derecha | Mentor | Preguntas del reto y pistas en orden. No muestra la solución en el primer clic |
| Abajo | Pseudocódigo y traza | La línea y el bloque activos coinciden. La predicción, cuando el reto la pide, ocurre antes de avanzar |

Escritorio: tres columnas y la franja inferior. Tableta: el mentor pasa debajo del lienzo. Teléfono: pestañas Problema, Construcción, Pseudocódigo y Ejecución. Teclado para las acciones de la barra, foco visible, etiquetas en los controles. El color de una rama o de un error va acompañado de texto.

Actividades del primer corte, todas sobre los mismos modelos:

| Tipo | Qué hace el alumno | Qué no abre todavía |
| --- | --- | --- |
| `classify` | Marca entradas, procesos, salidas y restricciones | El lienzo |
| `order` | Ordena instrucciones ya dadas | La caja libre |
| `build` | Arma el algoritmo con los bloques permitidos | — |
| `predict` | Anticipa un valor o una rama y después ejecuta | — |

Completar huecos, elegir condición, cazar errores, comparar soluciones y el editor textual del laboratorio quedan fuera de este corte. El editor textual del banco de trabajo sigue disponible en su pantalla.

## 9. Plan de pruebas

Se suman a la suite actual. No se da por ejecutada una prueba sin el comando y el resumen.

| Capa | Qué fija |
| --- | --- |
| Adaptador | Cada bloque del primer corte produce el nodo esperado. Un bloque desconocido o una conexión imposible devuelve diagnóstico y no un árbol ejecutable |
| Impresora | El texto usa las palabras del perfil estricto. Volver a parsear y comparar `dump()` con el árbol de origen |
| Semántica | El árbol adaptado pasa por el analizador actual: no declarada, tipo incompatible, condición no lógica |
| Intérprete | Un programa de bloques y el mismo programa de los ejemplos producen la misma salida y los mismos eventos `line` / `output` |
| Bindings | El `block_id` de una asignación cae en la línea que el evento `line` señala |
| Límites | Un `Mientras` que no termina corta por `E0410` o `E0411` |
| Modelos | Unicidad de ruta, orden de unidades, intento solo de su usuario |
| API | Lista publicada, inicio de intento, guardado, validación, pista, predicción, cierre. Ajeno → 404 |
| Cliente | Vitest del mapa línea → bloque y de las etapas que bloquean la construcción |
| Regresión del editor | `pytest` del núcleo y del servidor, y `npm test` del cliente, en verde al cerrar cada fase |

Tres retos de punta a punta, cuando existan la pantalla y los datos: uno de clasificar, uno de ordenar y uno de construir con `Si` y `Mientras`, incluyendo una predicción.

## 10. Plan incremental

Cada fase espera autorización. Al cerrarla se listan archivos, pruebas corridas y pendientes.

| Fase | Entrega | Criterio para seguir |
| --- | --- | --- |
| 0 | Este informe | Autorización explícita |
| 1 | App `learning`, modelos, migración, carga vacía o de catálogo mínimo, sin pantalla | Migración aplicada en desarrollo. El editor responde igual |
| 2 | Blockly con variables, asignación, lectura, escritura y operadores. Sin ejecutar | El banco de trabajo abre y cierra un algoritmo |
| 3 | Adaptador, validación e impresora | La prueba de ida y vuelta del volcado pasa |
| 4 | Paso a paso por el intérprete y SSE, con resaltado de bloque y línea | Los eventos del editor no cambian de forma |
| 5 | Una ruta, diez retos, mentor, intentos, pistas y predicción | Un alumno termina clasificar, ordenar, construir y predecir |
| 6 | `Si`/`Sino` y `Mientras` en los retos de esa ruta | Casos normales y de frontera |
| 7 | Arreglos y funciones en el laboratorio | El editor, que ya los tiene, sigue igual |
| 8 | Avance para el docente, teclado y tamaños de pantalla | Permisos por objeto y la suite completa |

Aceptación del módulo, cuando la fase 8 exista:

- El análisis previo bloquea la construcción cuando el reto lo pide.
- Una conexión incompatible no entra al árbol, o deja un aviso comprensible.
- Un solo AST produce pseudocódigo, diagrama, validación y ejecución.
- El paso resalta a la vez bloque, línea y variables.
- Hay predicción donde el reto la configura.
- El error nombra el concepto y la pista siguiente no es la solución.
- El intento guarda JSON, árbol, texto, entradas, resultado y ayudas.
- La pantalla se usa con teclado y en escritorio, tableta y teléfono.
- Hay pruebas de bloques, adaptación, tipos, intérprete, API y permisos.
- El editor, los proyectos y las comunidades se comportan como antes de la fase 1.

## 11. Decisiones de esta fase

Quedan así para la fase 1. Se pueden cambiar antes de autorizarla.

1. El acceso se llama Laboratorio y es otra vista. Volver restaura el banco de trabajo.
2. El primer corte de bloques es variables, asignación, lectura, escritura, operadores, `Si`/`Sino` y `Mientras`. Las actividades son clasificar, ordenar, construir y predecir.
3. La vista docente es la fase 8. La fase 1 no une retos con comunidades.
4. Los retos son contenido de sistema, los mismos para todos. Diez en la primera ruta. Se pueden cargar más en cualquier momento si su tipo y sus bloques ya existen. No hay pantalla de autoría en este corte.
5. La traza usa el SSE y los eventos actuales. No hay Celery ni WebSocket.
6. El perfil del laboratorio es el estricto, con punto y coma e índices desde 1.

## 12. Fase 1, hecha

Los archivos nuevos viven solo en `server/apps/learning/`:

```text
server/apps/learning/
├── apps.py
├── catalog.py
├── models/
│   ├── content.py      rutas, unidades, retos, casos y pistas
│   ├── attempts.py     intentos, fotos, ayudas, predicciones y reflexión
│   └── mastery.py      conceptos y dominio
├── migrations/
└── tests/
```

`INSTALLED_APPS` incluye `apps.learning`. No hay rutas de API.

## 13. Fase 2, hecha

El cliente nuevo vive en `frontend/src/learning/`:

```text
frontend/src/learning/
├── LearningLab.tsx       pantalla y vuelta al editor
├── BlockWorkspace.tsx    lienzo Blockly
├── blocks.ts             bloques y comprobación de conexiones
├── toolbox.ts            Variables, Entrada y salida, Operadores
├── names.ts              nombres de variable
├── types.ts              marcas de tipo
├── lab.css
└── connections.test.ts
```

Los iconos de Blockly están en `frontend/public/blockly-media/`. La barra del banco de trabajo tiene **Laboratorio**. Al volver, el algoritmo que estaba abierto sigue abierto.

## 14. Fase 3, hecha

El lienzo se traduce al AST de siempre y el texto es una vista. No se ejecuta.

```text
language_core/block_adapter.py
language_core/pseudocode.py
language_core/tests/test_block_adapter.py
language_core/tests/test_pseudocode.py
server/apps/learning/services.py
server/apps/learning/views.py
server/apps/learning/urls.py
```

`POST /api/v1/learning/preview/` recibe el JSON de Blockly y devuelve el pseudocódigo, los `BlockBinding` y los diagnósticos. No guarda nada y no crea una ejecución. Hace falta sesión.

Un bloque desconocido, un valor que falta o una comparación encadenada no produce programa. Un nombre sin `Definir`, o un tipo incompatible, sí deja el árbol y el aviso del analizador actual. «Unir» se imprime como `Concatenar`, porque en el perfil estricto `+` solo suma números.

La pantalla muestra ese texto al lado del lienzo.

## 15. Fase 4, hecha

Ejecutar abre una pasada en memoria. El depurador recorre el árbol que armó el adaptador: el texto no se vuelve a compilar. Si hay un error de estructura o del analizador, no hay pasada. Un aviso no la impide.

```text
language_core/debugger.py          open_program, sin eventos nuevos
server/apps/learning/live.py       pasadas del proceso, aparte del editor
server/apps/learning/runs.py
server/apps/learning/views.py
server/apps/learning/urls.py
frontend/src/learning/LearningLab.tsx
```

`POST /api/v1/learning/run/` devuelve el estado, el texto, los `BlockBinding` y los diagnósticos. Las órdenes son pausar, continuar, un paso, detener y reiniciar. `GET .../events/` es SSE con el mismo sobre que el editor: `paused`, `output`, `input_requested`, `input_rejected`, `finished`, `error`, `cancelled`. El campo `line` de `paused` elige el bloque y la línea. `input_rejected` no se suma a la salida.

La pasada no escribe `Execution`, `ChallengeAttempt` ni `WorkspaceSnapshot`. En la máquina corre en el proceso de Django, con `Limits`. En los contenedores usa el mismo runner que el editor. Un `Mientras` que no termina se corta por `E0410` o `E0411`. En este corte el lienzo todavía no tiene ese bloque; llega en la fase 6.

## 16. Fase 5, hecha

La ruta Fundamentos publica diez retos. El alumno los abre en orden. Clasificar y ordenar no muestran el lienzo. Construir lo mantiene cerrado hasta terminar comprender y razonar. Predecir ejecuta el programa del reto solo después de una respuesta correcta.

```text
server/apps/learning/path_data.py
server/apps/learning/progress.py
server/apps/learning/course_views.py
server/apps/learning/migrations/0003_seed_path.py
frontend/src/learning/LearningLab.tsx    ruta, práctica libre y vuelta al editor
frontend/src/learning/PathHome.tsx
frontend/src/learning/ChallengePlay.tsx
frontend/src/learning/PracticeLab.tsx
frontend/src/learning/trace.ts
```

`GET /api/v1/learning/path/` lista los diez con estado bloqueado, disponible o hecho. Abrir un reto crea el intento, o devuelve el que ya existe. Las etapas son comprender, razonar, construir, comprobar y explicar. El mentor entrega las pistas en orden: la primera no es la solución y la de nivel 5 empieza por «Esta es la solución explicada». La respuesta pública no incluye la solución, el programa inicial ni la salida esperada. Un error de construcción nombra el concepto. Cerrar el intento guarda la puntuación, el resumen y la reflexión. No escribe `Execution`. En un reto de construir, cerrar exige que coincidan todos los casos. Al terminar, la respuesta pública incluye cómo lo armó el alumno. El docente ve esa respuesta aunque el intento siga abierto.

La práctica libre conserva el paso a paso de la fase 4.

## 17. Fase 6, hecha

El lienzo tiene `Si`, `Si` con `Sino` y `Mientras`. La práctica libre los muestra. La ruta Fundamentos suma las unidades Decisiones y Ciclo mientras: clasificar, ordenar, predecir y construir. Los casos cubren la rama verdadera, la rama falsa, el ciclo que entra y el ciclo que no entra. Contar positivos pide los dos bloques. Un `Mientras` que no termina sigue cortándose por `E0410`.

La ruta de esta fase termina en Ciclo repetir. Arreglos y funciones llegan en la sección 21.

## 18. Segun, Para y Repetir

El lienzo agrega la opción múltiple y dos ciclos más. `Segun` empieza con dos casos y `De Otro Modo`; el botón + agrega casos hasta doce. `Para` recorre un entero con inicio, límite y paso. `Repetir` ejecuta el cuerpo y después evalúa `Hasta Que`, así que corre al menos una vez.

La ruta suma tres unidades: Opción múltiple, Ciclo para y Ciclo repetir. Los casos cubren un valor normal, la rama que no coincide y la vuelta única.

## 19. Prácticas guardadas

La práctica libre se puede guardar con un nombre, volver a abrir, descargar como archivo de texto y eliminar. Queda en la cuenta del alumno, en `learning.Practice`, y no aparece entre los algoritmos del editor.

## 20. Abrir un archivo

En la práctica libre, Abrir archivo lee un `.txt` de pseudocódigo y coloca en el lienzo los bloques de variables, operadores, `Si`, `Segun`, `Mientras`, `Para`, `Repetir`, arreglos, funciones y procedimientos. El texto se parsea con el mismo núcleo del editor. `Escribir` admite hasta ocho valores en la misma línea. La casilla «sin saltar» escribe `Sin Saltar` y no baja de línea. `Borrar pantalla` vacía la salida y `Esperar` detiene el algoritmo los segundos indicados. El operador `^`, o más de cuatro parámetros, argumentos o dimensiones, o más de ocho valores en un `Escribir`, no arma un lienzo a medias: se muestra el aviso y el lienzo actual se queda. Un `Para` sin `Con Paso` recibe el paso 1, o -1 si los límites enteros van hacia abajo.

## 21. Fase 7, hecha

El lienzo agrega arreglos y rutinas. `Dimension` reserva de una a cuatro dimensiones. El índice, la asignación a casilla y `Leer` de casilla usan ese mismo tope. Una función y un procedimiento son bloques sombrero: van aparte del algoritmo, con hasta cuatro parámetros, por valor o por referencia. La llamada de función cabe en una expresión. La llamada de procedimiento es una sentencia.

La ruta suma Arreglos y Funciones: treinta y cuatro retos. Los casos cubren la casilla, el doble de un entero leído y un procedimiento que suma uno por referencia. El editor, el parser y el intérprete no cambian. `call` y `return` ya existían en el depurador; la práctica libre muestra el ámbito cuando llega uno de esos eventos.

## 22. Fase 8, hecha

Un docente abre **Avance** en el laboratorio y ve a las personas de las comunidades que ya administra. El detalle muestra los puntos, el puesto, el estado de cada reto y la nota del intento terminado. No incluye el lienzo, la reflexión ni las pistas.

`GET /api/v1/learning/roster/` lista esas cuentas. `GET /api/v1/learning/roster/{id}/` devuelve el avance de una. Un alumno recibe 403. Una cuenta que el docente no tiene en sus comunidades responde 404.

En la práctica libre, Ctrl+Enter ejecuta, Ctrl+. avanza un paso y Esc detiene, salvo cuando el foco está en un campo. En pantalla estrecha, la práctica libre separa Construcción, Pseudocódigo, Ejecución y Prácticas; el reto separa Problema, Construcción y Ayuda. El escritorio conserva las columnas.

```text
server/apps/learning/roster.py
server/apps/learning/tests/test_roster.py
frontend/src/learning/TeacherRoster.tsx
```
