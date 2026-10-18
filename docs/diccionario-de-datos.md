# Diccionario de datos

Fecha de referencia: 2026-10-17. Sirve para armar consultas sobre la base del compose. La traducción y la ventana de escritorio no agregan columnas: el código generado no se guarda. Los niveles viven en `billing_plan` y `billing_subscription`. El relato del modelo está en [modelo-de-datos.md](modelo-de-datos.md).

La base se llama `traza` y, con los contenedores levantados, escucha en `127.0.0.1:5434`. El usuario de desarrollo es `traza`. No es la base del contenedor anterior `traza-pg` del puerto `5433`.

```sql
SET search_path TO public;
```

## 1. Cómo leer una fila

| Tipo en PostgreSQL | Qué cabe | Notas para la consulta |
| --- | --- | --- |
| `bigint` | entero de 64 bits | Clave de `accounts_user` y de las tablas cuya clave no es UUID. Las claves foráneas hacia el usuario son `bigint` |
| `integer` | entero de 32 bits, de 0 a 2 147 483 647 | Enteros positivos del modelo: puntos, posición, número de versión, segundos |
| `smallint` | entero de 16 bits, de 0 a 32 767 | Dificultad, puntos de un reto, tamaño de fuente, nivel de pista o de dominio |
| `character varying(n)` | texto de hasta n caracteres | `n` es el tope de la columna |
| `text` | texto sin tope de columna | El fuente de un algoritmo lo limita la aplicación a 64 KiB antes de guardarlo |
| `uuid` | identificador de 16 bytes | Clave pública de proyectos, algoritmos, ejecuciones, comunidades y laboratorio |
| `boolean` | verdadero o falso | |
| `timestamp with time zone` | fecha y hora con zona | En el código se escribe `timestamptz` |
| `jsonb` | documento JSON | Preferencias, límites, lienzo, caché del diagrama |
| `inet` | dirección IPv4 o IPv6 | Solo la auditoría |

`Nulo = NO` obliga a un valor. `Nulo = SÍ` admite `NULL`. Una cadena vacía no es `NULL`: varios textos opcionales se guardan como `''`.

Tres tablas se borran en lógico. Una fila viva tiene `deleted_at IS NULL`. Si la consulta no filtra eso, mezcla la papelera con lo que el usuario ve.

| Tabla | Filtro de lo visible |
| --- | --- |
| `projects_project` | `deleted_at IS NULL` |
| `projects_folder` | `deleted_at IS NULL` |
| `projects_algorithm` | `deleted_at IS NULL` |

El laboratorio no usa esas tablas. Un intento no es una fila de `executions_execution`.

## 2. Relaciones

La columna foránea se llama `campo_id` y apunta a la clave de la otra tabla. `Al borrar` es lo que hace PostgreSQL si desaparece la fila padre.

| Desde | Columna | Hacia | Cardinalidad | Al borrar el padre |
| --- | --- | --- | --- | --- |
| `accounts_profile` | `user_id` | `accounts_user.id` | 1 a 1 | se borra el perfil |
| `billing_subscription` | `user_id` | `accounts_user.id` | 1 a 1 | se borra la suscripción |
| `billing_subscription` | `plan_id` | `billing_plan.id` | muchos cuentas, un nivel | se impide borrar el nivel |
| `editor_editorpreference` | `user_id` | `accounts_user.id` | 1 a 1 | se borra la preferencia |
| `projects_project` | `owner_id` | `accounts_user.id` | 1 usuario, muchos proyectos | se impide borrar al usuario |
| `projects_folder` | `project_id` | `projects_project.id` | 1 proyecto, muchas carpetas | se borran las carpetas |
| `projects_folder` | `parent_id` | `projects_folder.id` | una carpeta padre, o ninguna | se borran las hijas |
| `projects_algorithm` | `project_id` | `projects_project.id` | 1 proyecto, muchos algoritmos | se borran los algoritmos |
| `projects_algorithm` | `folder_id` | `projects_folder.id` | el algoritmo puede no tener carpeta | la carpeta queda en nulo |
| `projects_algorithm` | `owner_id` | `accounts_user.id` | el dueño coincide con el del proyecto | se impide borrar al usuario |
| `projects_algorithm` | `language_profile_id` | `language_languageprofile.id` | muchos algoritmos, un perfil | se impide borrar el perfil |
| `projects_algorithmversion` | `algorithm_id` | `projects_algorithm.id` | 1 algoritmo, muchas versiones | se borran las versiones |
| `projects_algorithmversion` | `created_by_id` | `accounts_user.id` | quién guardó la versión | se impide borrar al usuario |
| `projects_sharelink` | `algorithm_id` | `projects_algorithm.id` | uno de los dos destinos | se borra el enlace |
| `projects_sharelink` | `project_id` | `projects_project.id` | el otro destino, nunca los dos | se borra el enlace |
| `projects_sharelink` | `created_by_id` | `accounts_user.id` | quién creó el enlace | se impide borrar al usuario |
| `executions_execution` | `algorithm_id` | `projects_algorithm.id` | 1 algoritmo, muchas ejecuciones | se impide borrar el algoritmo |
| `executions_execution` | `user_id` | `accounts_user.id` | quién ejecutó | se impide borrar al usuario |
| `executions_executionevent` | `execution_id` | `executions_execution.id` | 1 ejecución, muchos eventos | se borran los eventos |
| `classroom_community` | `owner_id` | `accounts_user.id` | 1 docente, muchas comunidades | se borran sus comunidades |
| `classroom_membership` | `community_id` | `classroom_community.id` | 1 comunidad, muchos miembros | se borran las membresías |
| `classroom_membership` | `user_id` | `accounts_user.id` | 1 usuario, muchas membresías | se borran las membresías |
| `audit_auditevent` | `actor_id` | `accounts_user.id` | el actor puede desaparecer | el actor queda en nulo |
| `learning_learningpath` | `owner_id` | `accounts_user.id` | la ruta de sistema no tiene dueño | se borra la ruta del docente |
| `learning_learningunit` | `path_id` | `learning_learningpath.id` | 1 ruta, muchas unidades | se borran las unidades |
| `learning_learningunit` | `concept_id` | `learning_concept.key` | muchas unidades, un concepto | se impide borrar el concepto |
| `learning_learningunit` | `prerequisite_id` | `learning_learningunit.id` | una unidad previa, o ninguna | se impide borrar la previa |
| `learning_challenge` | `unit_id` | `learning_learningunit.id` | 1 unidad, muchos retos | se borran los retos |
| `learning_challengetestcase` | `challenge_id` | `learning_challenge.id` | 1 reto, muchos casos | se borran los casos |
| `learning_hint` | `challenge_id` | `learning_challenge.id` | 1 reto, muchas pistas | se borran las pistas |
| `learning_pathentry` | `path_id` | `learning_learningpath.id` | un reto colocado en una ruta | se borra la colocación |
| `learning_pathentry` | `challenge_id` | `learning_challenge.id` | el reto del catálogo | se borra la colocación |
| `learning_pathassignment` | `path_id` | `learning_learningpath.id` | la ruta asignada | se borra la asignación |
| `learning_pathassignment` | `community_id` | `classroom_community.id` | o la comunidad, o el alumno | se borra la asignación |
| `learning_pathassignment` | `student_id` | `accounts_user.id` | el otro destino, nunca los dos | se borra la asignación |
| `learning_challengeattempt` | `challenge_id` | `learning_challenge.id` | 1 reto, muchos intentos | se impide borrar el reto |
| `learning_challengeattempt` | `user_id` | `accounts_user.id` | 1 alumno, muchos intentos | se impide borrar al alumno |
| `learning_workspacesnapshot` | `attempt_id` | `learning_challengeattempt.id` | 1 intento, muchas fotos | se borran las fotos |
| `learning_hintusage` | `attempt_id` | `learning_challengeattempt.id` | pistas pedidas en el intento | se borra el uso |
| `learning_hintusage` | `hint_id` | `learning_hint.id` | la pista pedida | se impide borrar la pista |
| `learning_prediction` | `attempt_id` | `learning_challengeattempt.id` | 1 intento, muchas predicciones | se borran |
| `learning_reflection` | `attempt_id` | `learning_challengeattempt.id` | 1 a 1 | se borra la reflexión |
| `learning_conceptmastery` | `user_id` | `accounts_user.id` | un nivel por usuario y concepto | se borra el dominio |
| `learning_conceptmastery` | `concept_id` | `learning_concept.key` | | se impide borrar el concepto |
| `learning_practice` | `user_id` | `accounts_user.id` | prácticas libres de esa cuenta | se impide borrar al usuario |

`projects_sharelink` exige exactamente uno de `algorithm_id` o `project_id`. `learning_pathassignment` exige exactamente uno de `community_id` o `student_id`.

## 3. Cuentas

### `accounts_user`

La cuenta. El identificador para entrar es `email`, no hay columna `username`. La contraseña está solo en `password`, con el hasher de Django: no se consulta ni se muestra.

| Campo | Tipo | Nulo | Descripción |
| --- | --- | --- | --- |
| `id` | `bigint` | NO | Clave. La usan el perfil, los proyectos, las comunidades y los intentos |
| `password` | `varchar(128)` | NO | Hash. No es la contraseña en claro |
| `last_login` | `timestamptz` | SÍ | Última entrada. Nulo si nunca entró |
| `is_superuser` | `boolean` | NO | Acceso total al administrador de Django |
| `first_name` | `varchar(150)` | NO | Nombre de la ficha de Django. La pantalla usa `accounts_profile.display_name` |
| `last_name` | `varchar(150)` | NO | Apellido de la ficha de Django. Puede ir vacío |
| `is_staff` | `boolean` | NO | Puede abrir `/admin/` |
| `is_active` | `boolean` | NO | Cuenta activa para Django. La confirmación del correo es `email_confirmed`, no esta columna |
| `date_joined` | `timestamptz` | NO | Alta de la fila |
| `email` | `varchar(254)` | NO | Único. Correo normalizado, es el usuario |
| `email_confirmed` | `boolean` | NO | En los contenedores nace en falso hasta abrir el enlace. Las cuentas anteriores y las de la máquina nacen en verdadero |

### `accounts_profile`

Datos visibles de esa cuenta. Una fila por usuario.

| Campo | Tipo | Nulo | Descripción |
| --- | --- | --- | --- |
| `id` | `bigint` | NO | Clave propia. Para unir con el usuario se usa `user_id` |
| `user_id` | `bigint` | NO | Único. Apunta a `accounts_user.id` |
| `display_name` | `varchar(80)` | NO | Nombre que se muestra. Si el alta no lo trae, se toma la parte del correo antes de `@` |
| `institution` | `varchar(120)` | NO | Escuela u organización. Vacío si no se indicó |
| `role` | `varchar(16)` | NO | `student`, `teacher` o `admin`. El alta pública solo escribe los dos primeros. `admin` lo crea el comando `create_admin` |
| `points` | `integer` | NO | Puntos acumulados. Suben una vez al terminar un reto. El puesto no es una columna: es 1 más la cantidad de perfiles con más puntos |
| `created_at` | `timestamptz` | NO | Alta del perfil |
| `updated_at` | `timestamptz` | NO | Último cambio del perfil |

### `billing_plan`

Un nivel de suscripción. Hay filas distintas para alumno y para docente. El alta usa la fila con `is_default`.

| Campo | Tipo | Nulo | Descripción |
| --- | --- | --- | --- |
| `id` | `uuid` | NO | Clave |
| `code` | `varchar(32)` | NO | Único junto con `audience`. `gratis` y `premium` son la semilla |
| `name` | `varchar(80)` | NO | Nombre que ve la cuenta |
| `audience` | `varchar(16)` | NO | `student` o `teacher` |
| `price_cents` | `integer` | NO | Precio en centavos. 15000 es 150.00 |
| `currency` | `varchar(3)` | NO | Moneda, por ejemplo `MXN` |
| `period_days` | `integer` | NO | Días de vigencia. 0 no vence |
| `browser_allowed` | `boolean` | NO | Si el navegador abre la aplicación. Falso en la semilla |
| `max_projects` | `integer` | SÍ | Tope de proyectos propios. Nulo es sin límite. El proyecto Ejemplos no cuenta |
| `max_algorithms` | `integer` | SÍ | Tope de algoritmos propios. Nulo es sin límite |
| `features` | `jsonb` | NO | Mapa de funciones encendidas. Las claves salen de `apps.billing.catalog` |
| `is_default` | `boolean` | NO | Una sola fila por tipo. Es el nivel del alta y el respaldo si otro vence |
| `is_active` | `boolean` | NO | Si se puede asignar. El nivel por defecto no se desactiva |
| `sort_order` | `smallint` | NO | Orden en la pantalla de administrador |
| `created_at`, `updated_at` | `timestamptz` | NO | |

### `billing_subscription`

El nivel asignado a una cuenta. El administrador no tiene fila.

| Campo | Tipo | Nulo | Descripción |
| --- | --- | --- | --- |
| `id` | `bigint` | NO | Clave |
| `user_id` | `bigint` | NO | Único. Apunta a `accounts_user.id` |
| `plan_id` | `uuid` | NO | Apunta a `billing_plan.id`. No se borra el nivel si alguien lo tiene |
| `paid_until` | `timestamptz` | SÍ | Fin de la vigencia. Nulo en un nivel que no vence |
| `browser_allowed` | `boolean` | SÍ | Nulo: sigue al nivel. Verdadero: esta cuenta abre la aplicación en el navegador aunque el nivel no lo permita |
| `updated_at` | `timestamptz` | NO | Última asignación |

### `editor_editorpreference`

Cómo abre el editor esa cuenta. Una fila por usuario.

| Campo | Tipo | Nulo | Descripción |
| --- | --- | --- | --- |
| `id` | `bigint` | NO | Clave |
| `user_id` | `bigint` | NO | Único. Apunta a `accounts_user.id` |
| `theme` | `varchar(16)` | NO | `light` o `dark`. Arranca en `light` |
| `font_size` | `smallint` | NO | Cuerpo del editor, entre 12 y 28. Arranca en 16 |
| `keymap` | `varchar(32)` | NO | Mapa de teclas. Arranca en `default` |
| `indent_size` | `smallint` | NO | Espacios de la indentación. Arranca en 4 |
| `autosave` | `boolean` | NO | Si el editor guarda solo. Arranca en verdadero |
| `locale` | `varchar(8)` | NO | `es` o `en`. Arranca en `es`. Idioma de la interfaz y grafía visible de las palabras reservadas. No reescribe el fuente guardado |
| `require_semicolons` | `boolean` | NO | Punto y coma que prefiere la cuenta. Arranca en verdadero |
| `index_base` | `smallint` | NO | Índice de arreglos que prefiere la cuenta: `0` o `1`. Arranca en `1` |

## 4. Banco de trabajo

### `language_languageprofile`

Reglas del lenguaje. `strict` es el predeterminado. Un perfil con `is_system` verdadero no se borra.

| Campo | Tipo | Nulo | Descripción |
| --- | --- | --- | --- |
| `id` | `bigint` | NO | Clave. La guarda `projects_algorithm.language_profile_id` |
| `key` | `varchar(32)` | NO | Único. `strict`, `flexible`, u otro que se añada |
| `name` | `varchar(80)` | NO | Nombre visible |
| `config` | `jsonb` | NO | Banderas: base de índices, punto y coma, declaraciones, ensanche, globales, avisos y límites |
| `is_system` | `boolean` | NO | Verdadero en los perfiles de fábrica |

### `projects_project`

Carpeta de algoritmos de una cuenta.

| Campo | Tipo | Nulo | Descripción |
| --- | --- | --- | --- |
| `id` | `uuid` | NO | Clave pública |
| `owner_id` | `bigint` | NO | Dueño. Apunta a `accounts_user.id` |
| `name` | `varchar(120)` | NO | Único entre los proyectos vivos de ese dueño |
| `description` | `text` | NO | Texto libre. Vacío si no hay |
| `visibility` | `varchar(16)` | NO | `private` o `unlisted` |
| `created_at` | `timestamptz` | NO | Alta |
| `updated_at` | `timestamptz` | NO | Último cambio |
| `deleted_at` | `timestamptz` | SÍ | Nulo si está vivo. Con fecha, está en la papelera |

### `projects_folder`

Carpeta dentro de un proyecto. Puede anidar hasta 8 niveles; ese tope lo aplica la aplicación, no la columna.

| Campo | Tipo | Nulo | Descripción |
| --- | --- | --- | --- |
| `id` | `uuid` | NO | Clave |
| `project_id` | `uuid` | NO | Proyecto |
| `parent_id` | `uuid` | SÍ | Carpeta padre. Nulo si está en la raíz |
| `name` | `varchar(120)` | NO | Único entre hermanas vivas |
| `created_at` | `timestamptz` | NO | Alta |
| `deleted_at` | `timestamptz` | SÍ | Nulo si está viva |

### `projects_algorithm`

El fuente que se edita, valida, ejecuta y dibuja. El texto vivo está en `source`. El autoguardado lo actualiza y no abre una versión en cada pulsación.

| Campo | Tipo | Nulo | Descripción |
| --- | --- | --- | --- |
| `id` | `uuid` | NO | Clave pública |
| `project_id` | `uuid` | NO | Proyecto |
| `folder_id` | `uuid` | SÍ | Carpeta. Nulo si está en la raíz del proyecto |
| `owner_id` | `bigint` | NO | Dueño. Debe ser el mismo que `projects_project.owner_id` |
| `name` | `varchar(120)` | NO | Único entre los algoritmos vivos de la misma carpeta, o de la raíz si no hay carpeta |
| `source` | `text` | NO | Pseudocódigo actual. Tope de aplicación 64 KiB |
| `language_profile_id` | `bigint` | NO | Perfil de `language_languageprofile` |
| `language_options` | `jsonb` | NO | Vacío significa usar el perfil. Puede traer `require_semicolons` e `index_base` (`0` o `1`) |
| `profile_snapshot` | `jsonb` | NO | Copia de las banderas usadas en la última ejecución |
| `current_version` | `integer` | NO | Número de la última versión explícita. 0 si solo hubo autoguardado |
| `flowchart` | `jsonb` | SÍ | Caché `{source_hash, graph}`. Nulo si todavía no se calculó |
| `created_at` | `timestamptz` | NO | Alta |
| `updated_at` | `timestamptz` | NO | Último cambio del fuente o del nombre |
| `deleted_at` | `timestamptz` | SÍ | Nulo si está vivo |

### `projects_algorithmversion`

Historia. Se abre una fila al guardar de forma explícita, al restaurar y al ejecutar si el fuente cambió. Restaurar no reescribe números viejos: copia el texto y crea un número nuevo.

| Campo | Tipo | Nulo | Descripción |
| --- | --- | --- | --- |
| `id` | `bigint` | NO | Clave interna |
| `algorithm_id` | `uuid` | NO | Algoritmo |
| `number` | `integer` | NO | Único dentro del algoritmo. Empieza en 1 |
| `source` | `text` | NO | Fuente de esa versión |
| `message` | `varchar(200)` | NO | Nota. Vacía si no hay |
| `created_by_id` | `bigint` | NO | Quién la guardó |
| `created_at` | `timestamptz` | NO | Momento |

### `projects_sharelink`

Enlace de solo lectura. El token en claro se muestra una vez. En la base queda `token_hash`.

| Campo | Tipo | Nulo | Descripción |
| --- | --- | --- | --- |
| `id` | `uuid` | NO | Clave |
| `algorithm_id` | `uuid` | SÍ | Destino, si el enlace es de un algoritmo |
| `project_id` | `uuid` | SÍ | Destino, si el enlace es de un proyecto. No pueden ir los dos, ni ninguno |
| `token_hash` | `varchar(64)` | NO | Único. No es el token que ve quien abre el enlace |
| `created_by_id` | `bigint` | NO | Autor del enlace |
| `expires_at` | `timestamptz` | SÍ | Caducidad. Nulo si no caduca |
| `revoked_at` | `timestamptz` | SÍ | Revocación. Nulo si sigue vigente |
| `created_at` | `timestamptz` | NO | Alta |

Un enlace sirve si `revoked_at` es nulo y `expires_at` es nulo o posterior a ahora.

## 5. Ejecución del editor

### `executions_execution`

Una corrida de un algoritmo del banco de trabajo. La pila viva del depurador no está aquí: viaja por Redis. Cada línea del paso a paso tampoco se guarda.

| Campo | Tipo | Nulo | Descripción |
| --- | --- | --- | --- |
| `id` | `uuid` | NO | Clave. Es la que usa el canal SSE |
| `algorithm_id` | `uuid` | NO | Algoritmo |
| `version_number` | `integer` | SÍ | Versión ejecutada. Nulo si era un autoguardado sin versión |
| `user_id` | `bigint` | NO | Quién la lanzó |
| `status` | `varchar(32)` | NO | `queued`, `running`, `waiting_input`, `paused`, `completed`, `error`, `cancelled` o `timeout` |
| `source` | `text` | NO | Fuente con el que corrió, copia del momento |
| `profile_config` | `jsonb` | NO | Banderas aplicadas |
| `limits` | `jsonb` | NO | Topes de instrucciones, tiempo, profundidad, celdas y salida |
| `pending_input` | `jsonb` | SÍ | Lo que un `Leer` está esperando. Nulo si no espera |
| `instruction_count` | `integer` | NO | Instrucciones ya ejecutadas |
| `started_at` | `timestamptz` | NO | Inicio |
| `finished_at` | `timestamptz` | SÍ | Cierre. Nulo mientras sigue abierta |

Índices útiles: `(user_id, started_at desc)`, `(algorithm_id, started_at desc)`, `(status)`.

### `executions_executionevent`

Salida, entradas aceptadas y error de la ejecución. No hay una fila por cada línea recorrida. Cada vez que la corrida avanza, la aplicación borra los eventos de esa ejecución y los vuelve a escribir: la tabla muestra el estado más reciente, no un historial de cada paso.

| Campo | Tipo | Nulo | Descripción |
| --- | --- | --- | --- |
| `id` | `bigint` | NO | Clave interna |
| `execution_id` | `uuid` | NO | Ejecución |
| `sequence` | `integer` | NO | Orden dentro de la ejecución. Único junto con `execution_id` |
| `kind` | `varchar(16)` | NO | `output`, `input`, `error` o `status` |
| `text` | `text` | NO | Texto de la consola, del dato aceptado o del mensaje |
| `line` | `integer` | SÍ | Línea del fuente. Nula si no aplica |
| `column` | `integer` | SÍ | Columna. Nula si no aplica |
| `code` | `varchar(16)` | NO | Código de diagnóstico, por ejemplo `E0406`. Vacío en una salida normal |
| `suggestion` | `text` | NO | Sugerencia del error. Vacía si no hay |

La consola va en una sola fila `kind = 'output'`, con todo el texto junto. Cada `Leer` aceptado suma otra fila `kind = 'input'`. Un dato rechazado no se guarda. El error, si lo hubo, va en `kind = 'error'`.

## 6. Comunidades

No hay actividades ni entregas. Una comunidad solo agrupa cuentas que ya existen.

### `classroom_community`

| Campo | Tipo | Nulo | Descripción |
| --- | --- | --- | --- |
| `id` | `uuid` | NO | Clave |
| `owner_id` | `bigint` | NO | Docente dueño. El nombre es único entre las suyas |
| `name` | `varchar(80)` | NO | Nombre visible |
| `translation_enabled` | `boolean` | NO | Si los alumnos heredan la traducción de código. Nace en verdadero |
| `created_at` | `timestamptz` | NO | Alta |
| `updated_at` | `timestamptz` | NO | Último cambio |

Tope de aplicación: 30 comunidades por docente y 200 personas por comunidad.

### `classroom_membership`

| Campo | Tipo | Nulo | Descripción |
| --- | --- | --- | --- |
| `id` | `bigint` | NO | Clave |
| `community_id` | `uuid` | NO | Comunidad |
| `user_id` | `bigint` | NO | Miembro. Único dentro de la comunidad. No es el dueño: el dueño no se agrega a sí mismo |
| `translation_enabled` | `boolean` | SÍ | Ajuste del alumno. Nulo significa heredar el de la comunidad |
| `created_at` | `timestamptz` | NO | Momento en que se agregó |

El papel de alumno o docente de esa fila sale de `accounts_profile.role`, no de esta tabla.

## 7. Laboratorio

El contenido de sistema (la ruta Fundamentos) tiene `owner_id` nulo. Una ruta de un docente tiene dueño. `is_bank` marca el banco de retos reutilizables.

### `learning_concept`

Catálogo de temas. La clave es el texto, no un número.

| Campo | Tipo | Nulo | Descripción |
| --- | --- | --- | --- |
| `key` | `varchar(32)` | NO | Clave. Ejemplos: `variable`, `assignment`, `io`, `operator`, `if`, `while` |
| `name` | `varchar(80)` | NO | Nombre visible |

### `learning_learningpath`

| Campo | Tipo | Nulo | Descripción |
| --- | --- | --- | --- |
| `id` | `uuid` | NO | Clave |
| `name` | `varchar(120)` | NO | Único en toda la tabla |
| `description` | `text` | NO | Texto. Vacío si no hay |
| `position` | `integer` | NO | Orden. Único en toda la tabla |
| `is_published` | `boolean` | NO | Si los alumnos pueden verla |
| `is_bank` | `boolean` | NO | Verdadero si es el banco, no una ruta que se recorre |
| `owner_id` | `bigint` | SÍ | Docente. Nulo en el contenido de sistema |
| `created_at` | `timestamptz` | NO | Alta |
| `updated_at` | `timestamptz` | NO | Último cambio |

### `learning_learningunit`

Unidad dentro de una ruta. El orden y el título son únicos dentro de la ruta.

| Campo | Tipo | Nulo | Descripción |
| --- | --- | --- | --- |
| `id` | `uuid` | NO | Clave |
| `path_id` | `uuid` | NO | Ruta |
| `title` | `varchar(120)` | NO | Título |
| `concept_id` | `varchar(32)` | NO | Apunta a `learning_concept.key` |
| `position` | `integer` | NO | Orden dentro de la ruta |
| `prerequisite_id` | `uuid` | SÍ | Otra unidad de la que depende. Nulo si es la primera |

### `learning_challenge`

Reto. El tipo, la dificultad, los puntos y el tiempo tienen tope en la base.

| Campo | Tipo | Nulo | Descripción |
| --- | --- | --- | --- |
| `id` | `uuid` | NO | Clave |
| `unit_id` | `uuid` | NO | Unidad |
| `title` | `varchar(120)` | NO | Único dentro de la unidad |
| `prompt` | `text` | NO | Enunciado que lee el alumno |
| `activity_type` | `varchar(16)` | NO | `classify`, `order`, `build` o `predict` |
| `difficulty` | `smallint` | NO | De 1 a 5 |
| `points` | `smallint` | NO | De 1 a 500. Si no se cambia, vale 10. Se suman una vez a `accounts_profile.points` |
| `time_limit_seconds` | `integer` | SÍ | Segundos. Nulo si no hay límite. Si hay, entre 1 y 86 400 |
| `allowed_blocks` | `jsonb` | NO | Lista de bloques que el lienzo puede mostrar |
| `restrictions` | `jsonb` | NO | Reglas extra del reto |
| `position` | `integer` | NO | Orden dentro de la unidad. Único junto con `unit_id` |
| `is_published` | `boolean` | NO | Si el alumno puede abrirlo |
| `created_at` | `timestamptz` | NO | Alta |
| `updated_at` | `timestamptz` | NO | Último cambio |

### `learning_challengetestcase`

Caso con el que se comprueba un reto de construcción o de predicción.

| Campo | Tipo | Nulo | Descripción |
| --- | --- | --- | --- |
| `id` | `uuid` | NO | Clave |
| `challenge_id` | `uuid` | NO | Reto |
| `name` | `varchar(80)` | NO | Único dentro del reto |
| `inputs` | `jsonb` | NO | Lista de datos de entrada |
| `expected_output` | `text` | NO | Salida esperada. Vacía si el caso no compara texto |
| `kind` | `varchar(16)` | NO | `normal`, `boundary` o `invalid` |
| `position` | `integer` | NO | Orden. Único dentro del reto |

### `learning_hint`

Pista. El nivel 1 orienta. El nivel 5 es la solución explicada.

| Campo | Tipo | Nulo | Descripción |
| --- | --- | --- | --- |
| `id` | `uuid` | NO | Clave |
| `challenge_id` | `uuid` | NO | Reto |
| `level` | `smallint` | NO | De 1 a 5 |
| `body` | `text` | NO | Texto de la pista |
| `position` | `integer` | NO | Orden dentro del mismo nivel. Único junto con reto y nivel |

### `learning_pathentry`

Un reto del catálogo puesto dentro de una ruta de docente, con ventana de fechas.

| Campo | Tipo | Nulo | Descripción |
| --- | --- | --- | --- |
| `id` | `uuid` | NO | Clave |
| `path_id` | `uuid` | NO | Ruta. El reto no se repite en la misma ruta |
| `challenge_id` | `uuid` | NO | Reto |
| `position` | `integer` | NO | Orden. Único dentro de la ruta |
| `opens_at` | `timestamptz` | SÍ | Desde cuándo se abre. Nulo si no hay inicio |
| `closes_at` | `timestamptz` | SÍ | Hasta cuándo. Nulo si no cierra |
| `withdrawn` | `boolean` | NO | Verdadero si el docente lo retiró |

### `learning_pathassignment`

A quién llega la ruta: una comunidad entera o un alumno. Nunca los dos en la misma fila.

| Campo | Tipo | Nulo | Descripción |
| --- | --- | --- | --- |
| `id` | `uuid` | NO | Clave |
| `path_id` | `uuid` | NO | Ruta |
| `community_id` | `uuid` | SÍ | Comunidad, si el destino es el grupo |
| `student_id` | `bigint` | SÍ | Alumno, si el destino es una persona |
| `created_at` | `timestamptz` | NO | Momento de la asignación |

### `learning_challengeattempt`

Intento de un alumno en un reto. No apunta a `projects_algorithm` ni a `executions_execution`.

| Campo | Tipo | Nulo | Descripción |
| --- | --- | --- | --- |
| `id` | `uuid` | NO | Clave |
| `challenge_id` | `uuid` | NO | Reto |
| `user_id` | `bigint` | NO | Alumno |
| `status` | `varchar(16)` | NO | `open`, `completed` o `abandoned` |
| `score` | `smallint` | SÍ | Nota de 0 a 100. Nula mientras sigue abierto |
| `summary` | `text` | NO | Resumen al cerrar. Vacío antes |
| `elapsed_seconds` | `integer` | SÍ | Segundos usados. Nulo si no se cerró |
| `started_at` | `timestamptz` | NO | Apertura |
| `finished_at` | `timestamptz` | SÍ | Cierre. Nulo si sigue abierto |

Índice: `(user_id, started_at desc)`.

### `learning_workspacesnapshot`

Foto del lienzo durante un intento.

| Campo | Tipo | Nulo | Descripción |
| --- | --- | --- | --- |
| `id` | `uuid` | NO | Clave |
| `attempt_id` | `uuid` | NO | Intento |
| `schema_version` | `integer` | NO | Versión del JSON de bloques. Arranca en 1 |
| `blockly_json` | `jsonb` | NO | Lienzo serializado |
| `ast_dump` | `text` | NO | Volcado del árbol. Vacío si todavía no hubo árbol |
| `pseudocode` | `text` | NO | Texto generado. Vacío si no hubo |
| `bindings` | `jsonb` | NO | Lista de `block_id` a línea |
| `created_at` | `timestamptz` | NO | Momento de la foto |

### `learning_hintusage`

| Campo | Tipo | Nulo | Descripción |
| --- | --- | --- | --- |
| `id` | `uuid` | NO | Clave |
| `attempt_id` | `uuid` | NO | Intento |
| `hint_id` | `uuid` | NO | Pista pedida |
| `created_at` | `timestamptz` | NO | Momento |

Cada pista pedida baja la autonomía de la nota: ninguna vale 10, una vale 6, dos valen 3 y tres o más valen 0. Esa cuenta no está en una columna: se obtiene contando filas de esta tabla.

### `learning_prediction`

| Campo | Tipo | Nulo | Descripción |
| --- | --- | --- | --- |
| `id` | `uuid` | NO | Clave |
| `attempt_id` | `uuid` | NO | Intento |
| `prompt_key` | `varchar(80)` | NO | Qué se le pidió anticipar |
| `expected` | `text` | NO | Respuesta correcta |
| `answer` | `text` | NO | Lo que escribió el alumno |
| `is_correct` | `boolean` | NO | Si coincidió |
| `created_at` | `timestamptz` | NO | Momento |

### `learning_reflection`

Una por intento cerrado.

| Campo | Tipo | Nulo | Descripción |
| --- | --- | --- | --- |
| `id` | `uuid` | NO | Clave |
| `attempt_id` | `uuid` | NO | Único. El intento |
| `body` | `text` | NO | Explicación del alumno |
| `created_at` | `timestamptz` | NO | Momento |

### `learning_conceptmastery`

Nivel de un alumno en un concepto. La pareja `(user_id, concept_id)` es única.

| Campo | Tipo | Nulo | Descripción |
| --- | --- | --- | --- |
| `id` | `uuid` | NO | Clave |
| `user_id` | `bigint` | NO | Alumno |
| `concept_id` | `varchar(32)` | NO | `learning_concept.key` |
| `level` | `smallint` | NO | De 0 a 5 |
| `evidence` | `jsonb` | NO | De dónde salió el nivel |
| `updated_at` | `timestamptz` | NO | Último cálculo |

### `learning_practice`

Práctica libre guardada. No aparece entre los algoritmos del editor. El nombre es único por usuario. Tope de aplicación: 40 por cuenta.

| Campo | Tipo | Nulo | Descripción |
| --- | --- | --- | --- |
| `id` | `uuid` | NO | Clave |
| `user_id` | `bigint` | NO | Dueño |
| `name` | `varchar(120)` | NO | Nombre |
| `workspace` | `jsonb` | NO | Lienzo |
| `source` | `text` | NO | Pseudocódigo. Vacío si aún no se generó |
| `created_at` | `timestamptz` | NO | Alta |
| `updated_at` | `timestamptz` | NO | Último guardado |

## 8. Auditoría

### `audit_auditevent`

Hechos de acceso y de cambio. No guarda el fuente completo ni secretos.

| Campo | Tipo | Nulo | Descripción |
| --- | --- | --- | --- |
| `id` | `bigint` | NO | Clave |
| `actor_id` | `bigint` | SÍ | Quién lo hizo. Nulo si esa cuenta ya no está |
| `action` | `varchar(64)` | NO | Por ejemplo `auth.register`, `auth.login`, `auth.email_confirm`, `auth.password_reset`, `algorithm.delete`, `share.create`, `execution.start` |
| `object_type` | `varchar(64)` | NO | Tipo del objeto, en texto |
| `object_id` | `varchar(64)` | NO | Identificador en texto. Un UUID cabe. No es una clave foránea |
| `metadata` | `jsonb` | NO | Datos extra, sin secreto |
| `ip_address` | `inet` | SÍ | Dirección de la petición. Nula si no se conoció |
| `created_at` | `timestamptz` | NO | Momento |

Índices: `(actor_id, created_at desc)` y `(object_type, object_id)`.

## 9. Tablas que no son del dominio

Django las crea y la aplicación casi no las consulta. No describen alumnos ni algoritmos.

| Tabla | Para qué existe |
| --- | --- |
| `accounts_user_groups` | Une `user_id` con `auth_group.id`. Traza no asigna grupos |
| `accounts_user_user_permissions` | Permisos sueltos de una cuenta. Traza no los usa para el editor |
| `auth_group`, `auth_group_permissions`, `auth_permission` | Permisos del administrador |
| `django_content_type` | Registro interno de modelos |
| `django_admin_log` | Historial de `/admin/` |
| `django_session` | Sesión del navegador. La clave no es el correo |
| `django_migrations` | Qué migraciones ya corrieron |

## 10. Consultas de partida

Alumnos ordenados por puntos. El puesto es la posición de esa orden.

```sql
SELECT u.email,
       p.display_name,
       p.role,
       p.points
FROM accounts_profile AS p
JOIN accounts_user AS u ON u.id = p.user_id
WHERE p.role = 'student'
  AND u.email_confirmed
ORDER BY p.points DESC, u.email;
```

Algoritmos vivos de un correo.

```sql
SELECT pr.name AS proyecto,
       a.name AS algoritmo,
       a.updated_at
FROM projects_algorithm AS a
JOIN projects_project AS pr ON pr.id = a.project_id
JOIN accounts_user AS u ON u.id = a.owner_id
WHERE u.email = 'ana@ejemplo.test'
  AND a.deleted_at IS NULL
  AND pr.deleted_at IS NULL
ORDER BY pr.name, a.name;
```

Miembros de las comunidades de un docente, con su papel actual.

```sql
SELECT c.name AS comunidad,
       u.email,
       p.display_name,
       p.role
FROM classroom_community AS c
JOIN classroom_membership AS m ON m.community_id = c.id
JOIN accounts_user AS u ON u.id = m.user_id
JOIN accounts_profile AS p ON p.user_id = u.id
JOIN accounts_user AS dueno ON dueno.id = c.owner_id
WHERE dueno.email = 'profe@ejemplo.test'
ORDER BY c.name, p.display_name;
```

Retos terminados y su nota.

```sql
SELECT u.email,
       ch.title,
       att.score,
       att.elapsed_seconds,
       att.finished_at
FROM learning_challengeattempt AS att
JOIN learning_challenge AS ch ON ch.id = att.challenge_id
JOIN accounts_user AS u ON u.id = att.user_id
WHERE att.status = 'completed'
ORDER BY att.finished_at DESC;
```

Últimas ejecuciones que terminaron en error, con el mensaje guardado.

```sql
SELECT u.email,
       a.name,
       e.started_at,
       ev.code,
       ev.line,
       ev.text
FROM executions_execution AS e
JOIN executions_executionevent AS ev
  ON ev.execution_id = e.id AND ev.kind = 'error'
JOIN projects_algorithm AS a ON a.id = e.algorithm_id
JOIN accounts_user AS u ON u.id = e.user_id
WHERE e.status = 'error'
ORDER BY e.started_at DESC
LIMIT 50;
```
