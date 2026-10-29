# Análisis de requerimientos

Fecha de referencia: 2026-10-29. Describe lo que Aulivana-FCDdesign ya exige para cumplir su propósito: enseñar programación estructurada en pseudocódigo. El detalle de pantallas está en [arquitectura funcional](vistas/arquitectura-funcional.md), el de tablas en [modelo de datos](modelo-de-datos.md) y el de columnas en [diccionario de datos](diccionario-de-datos.md).

El análisis cubre la aplicación (web, escritorio y núcleo del lenguaje) y la base de datos. No propone funciones que el código todavía no tiene.

## 1. Problema y alcance

El estudiante escribe un algoritmo en español, recibe el error en la línea, lo ejecuta, lo recorre paso a paso y ve el diagrama que sale del mismo árbol. El docente agrupa cuentas que ya existen, publica rutas y lee el avance. La cuenta, los proyectos y el laboratorio viven en el servidor. Validar, traducir, ejecutar y depurar pueden ocurrir en el servidor o en la máquina de la aplicación de escritorio.

Entran en este análisis:

- alta, sesión, perfil y niveles de suscripción;
- banco de trabajo, editor, consola, depurador y diagrama;
- traducción del algoritmo a otros lenguajes, sin ejecutarlo;
- laboratorio, banco de retos, rutas, notas y práctica libre;
- comunidades;
- aplicación de escritorio y el intérprete local;
- PostgreSQL como sistema de registro.

Quedan fuera, y el sistema no debe simular que existen:

- actividades y entregas del aula;
- orientación a objetos, archivos del pseudocódigo y concurrencia;
- cobro automático del nivel: el precio se guarda y el administrador asigna la vigencia;
- guardar el programa traducido.

## 2. Actores

| Actor | Necesidad |
| --- | --- |
| Estudiante | Practicar con diagnóstico, consola, diagrama y retos, dentro del cupo de su nivel |
| Docente | Formar un grupo, publicar una ruta, apagar traducción o pegado, y leer el trabajo y la nota |
| Administrador | Abrir o cerrar las altas, definir niveles y bloquear una cuenta. No se crea en el formulario público |
| Plataforma | Conservar la cuenta y el fuente, y ejecutar el programa fuera del proceso web cuando hay runner |

Una persona tiene un solo rol. Se elige al crear la cuenta y después no cambia. Si no se elige, queda estudiante. El administrador solo lo crea `manage.py create_admin`.

## 3. Requerimientos de la aplicación

Cada requerimiento dice qué debe poder hacerse y cuál es el resultado observable.

### 3.1 Acceso y cuenta

| Id | Requerimiento | Resultado |
| --- | --- | --- |
| RF-01 | La persona se identifica con el correo. Dos correos que solo cambian en las mayúsculas son el mismo. | El alta repetida responde que ya está registrado |
| RF-02 | En contenedores, la sesión no empieza hasta abrir el enlace de confirmación. El enlace sirve una vez. | Entrar antes responde que el correo no está confirmado |
| RF-03 | En la máquina sin buzón, el alta entra al momento. | La sesión queda abierta y llegan los ejemplos |
| RF-04 | Hay una sola sesión por cuenta. Otra ventana, otro equipo o la aplicación de escritorio tienen que esperar a que se cierre, o 30 minutos sin uso. | La sesión anterior deja de valer |
| RF-05 | Tres ingresos fallidos bloquean ese correo 15 minutos. | El ingreso siguiente se rechaza durante ese plazo |
| RF-06 | La persona restablece la contraseña con un enlace y, ya dentro, cambia nombre, foto y contraseña. | El tipo de cuenta no se puede cambiar desde la sesión |
| RF-07 | La foto es JPG o PNG, de hasta 120 KB. | Otro formato se rechaza |
| RF-08 | El administrador puede ocultar el alta de alumno, el de docente, o los dos. | El tipo apagado no aparece en Crear cuenta y el servidor lo rechaza |
| RF-09 | El administrador puede bloquear una cuenta. | Al entrar, la respuesta dice que está bloqueada |
| RF-10 | Cada cuenta nueva recibe los ejemplos 1 a 13. | Esos ejemplos no cuentan para el tope de proyectos ni de algoritmos del nivel |

### 3.2 Banco de trabajo

| Id | Requerimiento | Resultado |
| --- | --- | --- |
| RF-11 | La cuenta crea proyectos, carpetas y algoritmos, los renombra, los descarga y los envía a la papelera. | Un nombre vacío o con caracteres de control se rechaza. La papelera se puede restaurar |
| RF-12 | El editor autoguarda el fuente vivo. El guardado explícito, la restauración y una ejecución con fuente distinto abren una versión nueva. | El autoguardado no crea una versión por cada pulsación. Restaurar no reescribe la historia |
| RF-13 | Al escribir una instrucción, el editor ofrece su estructura. Enter o Tab la insertan y Tab salta de un hueco al siguiente. | En solo lectura no hay lista |
| RF-14 | Validar devuelve diagnósticos con código, línea, columna, fragmento y, cuando se puede, una sugerencia. | Validar no crea una ejecución ni descuenta el cupo del día |
| RF-15 | Traducir emite el mismo árbol en Python, JavaScript, TypeScript, Java, C, C++ y C#. | No ejecuta el programa generado ni lo guarda |
| RF-16 | El diagrama sale del árbol: inicio y fin, proceso, `Escribir`, `Leer`, `Si`, ciclo, `Segun` y `Dimension`. Se descarga en SVG, PNG y PDF, y se imprime. | La rama falsa sale por la izquierda y la verdadera por la derecha |
| RF-17 | Armar diagrama y Armar Nassi-Shneiderman convierten figuras en pseudocódigo. Al abrirlo en el editor, el núcleo pasa a ser la autoridad. | Un `Si` parte el bloque; los ciclos encierran el cuerpo; `Segun` abre una columna por caso |
| RF-18 | Se puede ocultar proyectos y diagrama, y arrastrar el ancho de proyectos, editor y diagrama. Actualizar vuelve a pedir los datos y suelta el borrador que aún no se guardó. | La barra muestra el estado de guardado y la línea del cursor |
| RF-19 | Un enlace de solo lectura muestra un algoritmo o un proyecto. El valor en claro se enseña una vez. | Se puede poner caducidad y se puede revocar |
| RF-20 | La cuenta elige tema, cuerpo, idioma, punto y coma e índice de arreglos. Un algoritmo nuevo copia esas dos últimas. Los que ya existen conservan las suyas. | Cambiar el idioma no reescribe un fuente guardado |

### 3.3 Lenguaje

| Id | Requerimiento | Resultado |
| --- | --- | --- |
| RF-21 | El lenguaje cubre secuencia, `Si`, `Segun`, `Mientras`, `Repetir`, `Para`, arreglos, funciones, procedimientos, recursión y la biblioteca estándar. | El perfil estricto es el predeterminado |
| RF-22 | `<-` y `=` asignan. `==` compara. Ningún signo de asignación va dentro de una expresión. | El perfil no cambia esa regla |
| RF-23 | Cada algoritmo elige si el punto y coma es obligatorio y si los índices empiezan en 0 o en 1. | Esa elección afecta validar, ejecutar, depurar y el diagrama |
| RF-24 | Las palabras reservadas se reconocen sin importar mayúsculas ni acentos, y también en inglés. El canónico interno sigue en español. | Los identificadores sí distinguen acentos. Los nombres de la biblioteca, las cadenas y los diagnósticos siguen en español |
| RF-25 | Un algoritmo nuevo, con el idioma de la cuenta en inglés, se guarda con las palabras en inglés. | El lexer acepta las dos grafías |
| RF-26 | El intérprete no abre archivos del sistema, ni red, ni variables de entorno del estudiante. No se usa `eval` ni `exec`. | Un ciclo se corta a 100 000 instrucciones o a 5 segundos. Detener lo corta antes |

### 3.4 Ejecución y depuración

| Id | Requerimiento | Resultado |
| --- | --- | --- |
| RF-27 | Ejecutar muestra, en orden, lo que escribe `Escribir` y cada dato que un `Leer` acepta. | Un dato rechazado no se pinta. El nivel descuenta una ejecución del día |
| RF-28 | El depurador permite entrar, salir, continuar, pausar, detener, reiniciar y puntos de interrupción. | En contenedores los eventos salen por SSE. El proceso web no interpreta el código del usuario |
| RF-29 | Si el cupo del día se agota, la pantalla lo dice. Vacío en el nivel significa sin límite. Un número no baja de 3. El tope de arranque es 3. | La barra muestra las que quedan, o infinito si no hay tope |
| RF-30 | Lenguajes aparece si el nivel lo incluye. En el navegador público corre en un contenedor aparte, sin salida a internet. En el escritorio corre en la máquina. | Si el contenedor no responde, la pantalla dice que Lenguajes no está disponible. No corren más de 6 a la vez |
| RF-31 | El historial de consola del editor web se puede volver a leer. | Cada paso del depurador no se guarda como fila |

### 3.5 Laboratorio

| Id | Requerimiento | Resultado |
| --- | --- | --- |
| RF-32 | El laboratorio ofrece retos de clasificar, ordenar, construir y predecir. Un intento no es un algoritmo del banco de trabajo. | La ruta Fundamentos y la práctica de concurso (cincuenta problemas) vienen sembradas |
| RF-33 | Un construir con casos no se cierra hasta coincidir en todos. Al terminar, el alumno ve su respuesta y el docente la ve aunque el intento siga abierto. | Sin casos, basta con que el programa esté bien escrito |
| RF-34 | El docente reparte la nota de 100 en cada reto de una ruta. La nota se guarda al avanzar. | El CSV de la ruta trae la nota y cada problema, solo de los alumnos de la comunidad elegida |
| RF-35 | El docente arma rutas con retos del banco, con horario de apertura y cierre, y puede repetir un reto. La copia nueva conserva los intentos anteriores. | Puede retirar una colocación sin borrar el reto |
| RF-36 | Un CSV agrega retos al banco del docente, hasta 250 filas y 1 MB. Descargar CSV entrega un tipo, el catálogo o el concurso. | La carga no escribe en el banco de concurso |
| RF-37 | La práctica libre se guarda, se abre, se descarga y se borra. Hay un tope de 40 por cuenta. El nombre es único entre las suyas. | No cuenta como algoritmo del banco de trabajo |
| RF-38 | Los puntos de un reto se suman una sola vez al perfil. El puesto es cuántos perfiles tienen más puntos, más uno. | Repetir el reto no vuelve a sumar esos puntos |
| RF-39 | La campana avisa de un reto nuevo o de uno que el docente volvió a habilitar. | El aviso es de la cuenta que está en sesión |

### 3.6 Comunidades y repaso

| Id | Requerimiento | Resultado |
| --- | --- | --- |
| RF-40 | El docente crea hasta 30 comunidades. Cada una tiene un código de 6 caracteres. El alumno lo escribe en Unirme. | El nombre es único entre las de ese docente. Hay un tope de 200 personas |
| RF-41 | El docente busca cuentas ya registradas, de alumnos o de otros docentes, y las agrega. No se registran personas desde la comunidad. | No puede agregarse a sí mismo. La búsqueda va por páginas de 15 |
| RF-42 | Traducción y pegado nacen habilitados en la comunidad. El docente puede apagarlos para la comunidad o para un alumno. | No puede encender una función que el nivel tiene apagada. Pegar apagado deja escribir y rechaza el texto pegado |
| RF-43 | En Repaso, el docente abre los proyectos de un alumno de sus comunidades en solo lectura. | No crea versiones ni modifica el fuente |

### 3.7 Niveles

| Id | Requerimiento | Resultado |
| --- | --- | --- |
| RF-44 | Cada alumno o docente entra en el nivel gratis de su tipo. El nivel dice el precio, la vigencia, los menús, los topes de proyectos y de algoritmos, las ejecuciones por día y si el navegador abre la aplicación. | Se pueden crear más niveles sin reescribir la pantalla |
| RF-45 | Si el navegador no está permitido, ahí solo se entra a la cuenta: tipo, foto, contraseña y días que faltan para pagar. | La aplicación de escritorio sigue usando las funciones del nivel |
| RF-46 | Si `paid_until` ya pasó, las funciones que aplican son las del nivel por defecto del mismo tipo. | La cuenta sigue mostrando el nivel asignado como vencido |
| RF-47 | Una excepción en la suscripción puede abrir o cerrar el navegador solo para esa cuenta. | Si el campo está vacío, manda el nivel |

Las funciones que un nivel puede encender son: editor, ver diagrama, armar diagrama, validar, traducir, lenguajes, ejecutar, depurar, descargar, pegar, laboratorio, ruta y práctica libre. Comunidades, banco, rutas propias y avance son solo de docente.

### 3.8 Escritorio, idioma y ayuda

| Id | Requerimiento | Resultado |
| --- | --- | --- |
| RF-48 | La ventana de escritorio abre la misma interfaz. Validar, traducir, ejecutar y depurar no salen de la máquina. La cuenta, los proyectos y el laboratorio siguen en la API. | El cupo del día sí se descuenta en el servidor |
| RF-49 | En un paquete publicado, las llamadas a la API pasan por un proxy local. El proxy solo acepta rutas que empiezan por `/api/`. | Si no hay origen configurado, el destino es `https://fcdesign.aulivana.com` |
| RF-50 | El idioma es español o inglés. Cambia los textos, las etiquetas de los bloques, las figuras y la grafía de las palabras reservadas. | El alumno ve el manual del lenguaje y el del alumno. El docente ve también el suyo. El PDF se ve en la aplicación y se puede guardar |
| RF-51 | Operadores muestra cada símbolo y el orden en que se ligan. Funciones lista la biblioteca estándar. | La ayuda no ejecuta código |

## 4. Reglas que cruzan varias funciones

1. El objeto de otra cuenta responde como si no existiera.
2. El fuente de un algoritmo no pasa de 64 KiB. Hay como máximo 50 proyectos vivos por cuenta y 200 algoritmos vivos por proyecto, salvo que el nivel fije un tope menor. El proyecto de ejemplos no entra en esa cuenta.
3. Las carpetas no pasan de 8 niveles y no se puede elegir como padre a un descendiente.
4. La comunidad no amplía el nivel: solo puede apagar traducción o pegado dentro de lo que el nivel ya permite.
5. El laboratorio y el editor comparten el lenguaje. Un intento no es una fila de ejecución del banco de trabajo.
6. En producción el proceso web no interpreta código de usuarios. Si la configuración lo intenta, no arranca.

## 5. Requerimientos no funcionales

| Id | Tema | Exigencia |
| --- | --- | --- |
| RNF-01 | Aislamiento | El runner no tiene credenciales de PostgreSQL, no monta Django y no alcanza el correo. Redis es el único puente y su credencial solo lee y escribe claves `traza:*` |
| RNF-02 | Recursos | El runner corre sin capacidades de más, con disco de solo lectura, `/tmp` en memoria, y topes de memoria, CPU y procesos |
| RNF-03 | Sesión | Cookie de sesión y CSRF en los cambios de estado. Sin JWT. La contraseña solo se guarda con el hasher de Django |
| RNF-04 | Auditoría | Se registra la acción, el actor, el objeto y la dirección. No se guarda el fuente completo ni un secreto |
| RNF-05 | Idioma de datos | El canónico del lenguaje es el español. La interfaz admite español e inglés sin duplicar el fuente |
| RNF-06 | Disponibilidad del ejecutor | Si el runner no responde, Lenguajes se declara no disponible. El resto de la cuenta sigue abriendo |
| RNF-07 | Correo | En desarrollo el buzón no entrega a internet. En el servidor público la confirmación sale por SMTP real |
| RNF-08 | Un origen | El navegador habla con Nginx. `/api` no usa buffer, para no cortar el canal de eventos |
| RNF-09 | Escritorio | El anfitrión local solo acepta el token de arranque y marca las peticiones como cliente de escritorio |
| RNF-10 | Privacidad del repaso | El docente solo lee algoritmos de alumnos de sus comunidades, y solo en lectura |

## 6. Requerimientos de la base de datos

Motor: PostgreSQL. Redis no es el sistema de registro: guarda órdenes, eventos en tránsito, el latido del runner y la caché de límites. La ventana de escritorio lee y escribe las mismas tablas a través de la API.

### 6.1 Qué debe recordar el sistema

| Necesidad | Dato que hay que conservar | Qué no hace falta guardar |
| --- | --- | --- |
| Saber quién es | Correo único sin distinguir mayúsculas, confirmación, clave de la sesión abierta, nombre, institución, rol, puntos y foto | La contraseña en claro |
| Saber qué puede hacer | Nivel, precio, vigencia, topes, mapa de funciones y, si existe, la excepción de navegador de esa cuenta | Un cobro ni un comprobante |
| Saber qué escribió | Fuente vivo, opciones de lenguaje, versiones y papelera | Cada pulsación del autoguardado como versión |
| Saber qué pasó al correr | Estado, límites, conteo, salida, entradas aceptadas y errores | Cada línea recorrida por el depurador |
| Saber a quién enseña | Comunidad, código de ingreso, miembros, y si traducción y pegado están habilitados | Cuentas creadas desde el grupo |
| Saber qué practicó | Ruta, reto, caso, pista, intento, nota, foto del lienzo, predicción, reflexión y práctica libre | Una fila de ejecución del editor |
| Saber qué se hizo | Actor, acción, objeto, metadatos y dirección | El fuente completo |

Hay dos grupos que no se mezclan. El banco de trabajo cuelga del algoritmo. El laboratorio cuelga del reto y de la práctica libre.

### 6.2 Grupos y reglas de integridad

**Cuenta.** Un usuario tiene un perfil y, si no es administrador, una suscripción. El rol es `student`, `teacher` o `admin`. Existe una sola fila de altas abiertas. El correo es único aunque cambien las mayúsculas.

**Nivel.** El código del nivel es único dentro del tipo (alumno o docente). Un solo nivel por tipo es el de alta. No se borra un nivel que todavía tenga suscripciones. El cupo del día es una fila por cuenta y por fecha.

**Proyectos.** La clave pública es UUID. El nombre de un proyecto vivo es único para su dueño. El nombre de una carpeta viva es único entre hermanas. El nombre de un algoritmo vivo es único en su carpeta, o en el proyecto si no tiene carpeta. El dueño del algoritmo coincide con el dueño del proyecto. Borrar al dueño está prohibido mientras existan esas filas. El perfil de lenguaje de sistema no se borra.

**Versiones.** El par algoritmo y número es único. El número nuevo se agrega; no se reescribe uno anterior.

**Ejecución.** El estado es uno de: en cola, corriendo, esperando entrada, en pausa, terminada, con error, cancelada o por tiempo. Los eventos de una ejecución llevan una secuencia única. El tipo de evento es salida, entrada, error o estado.

**Comunidad.** El nombre es único para ese docente. El código de ingreso es único en toda la base. Una persona entra una sola vez a la misma comunidad. Traducción y pegado en la membresía vacíos significan «heredar la comunidad».

**Laboratorio.** El tipo de reto es clasificar, ordenar, construir o predecir. La dificultad va de 1 a 5. Los puntos del reto van de 1 a 500. La nota del intento es nula o de 0 a 100. El tiempo límite, si existe, va de 1 segundo a 24 horas. Una pista tiene nivel de 1 a 5. Una ruta se asigna a una comunidad o a un alumno, nunca a los dos a la vez, y no se asigna dos veces al mismo destino. El dominio de un concepto por alumno es único y va de 0 a 5. El nombre de una práctica libre es único para esa cuenta.

**Enlace.** El enlace apunta a un algoritmo o a un proyecto, exactamente a uno. Se guarda el hash del token, no el token en claro.

**Preferencias.** Una fila por cuenta. El idioma es `es` o `en`. El índice de arreglos de la cuenta es el valor inicial de un algoritmo nuevo.

### 6.3 Borrado y conservación

| Hecho | Qué debe pasar en la base |
| --- | --- |
| Enviar un proyecto, una carpeta o un algoritmo a la papelera | Se marca `deleted_at`. Deja de listarse. Los índices de nombre solo miran filas vivas, así se puede reutilizar el nombre |
| Restaurar | Se quita `deleted_at` si el nombre vivo no choca |
| Vaciar la papelera | Borrado físico del algoritmo, sus versiones, sus eventos de ejecución y sus enlaces |
| Borrar una comunidad | Se van sus membresías y las asignaciones de ruta que la tenían como destino |
| Borrar un reto que ya tiene intentos | Se impide. El intento conserva el reto |
| Borrar un usuario con proyectos vivos | Se rechaza. Primero debe vaciarlos. La auditoría puede quedar con el actor vacío |
| Cerrar un intento | Se guardan la nota, el resumen, los segundos y la hora de fin. El intento abierto sigue siendo legible para el docente |

Las marcas de tiempo llevan zona. Las claves internas de alto volumen (eventos, versiones, usuario) son enteras. Las claves que salen a la interfaz de proyecto, algoritmo, ejecución, comunidad y laboratorio son UUID versión 4.

### 6.4 Límites que la aplicación impone antes de escribir

Estos topes no son columnas, pero la base no debe recibir filas que los violen:

| Tope | Valor |
| --- | --- |
| Fuente de un algoritmo | 64 KiB |
| Proyectos vivos por cuenta | 50, o el tope del nivel si es menor. Los ejemplos no cuentan |
| Algoritmos vivos por proyecto | 200, o el tope del nivel si es menor |
| Profundidad de carpetas | 8 |
| Comunidades por docente | 30 |
| Personas por comunidad | 200 |
| Prácticas libres por cuenta | 40 |
| Filas de un CSV de retos | 250, y 1 MB |
| Ejecuciones del día | el número del nivel; vacío es sin límite; un número no baja de 3 |
| Instrucciones de un ciclo | 100 000, o 5 segundos |
| Programas de Lenguajes a la vez | 6 |
| Foto de perfil | 120 KB, JPG o PNG |

### 6.5 Lo que la base no modela

- El texto traducido a Python, JavaScript, TypeScript, Java, C, C++ o C#.
- La pila y las variables vivas del depurador.
- Cada evento `line_executed`. Viaja por SSE o por el proceso local y se descarta.
- Actividades, entregas y calificaciones de un aula distintas del laboratorio.
- Un pago, una factura o un medio de cobro. Solo están el precio del nivel y `paid_until`.
- El código generado en la máquina del escritorio.

## 7. Trazabilidad

| Requerimientos | Tablas que los sostienen |
| --- | --- |
| RF-01 a RF-10 | `accounts_user`, `accounts_profile`, `accounts_signuppolicy` |
| RF-11, RF-12, RF-18, RF-20 | `projects_project`, `projects_folder`, `projects_algorithm`, `projects_algorithmversion`, `editor_editorpreference`, `language_languageprofile` |
| RF-14, RF-15, RF-21 a RF-26 | El núcleo no tiene tablas. El perfil y las opciones del algoritmo sí: `language_languageprofile` y `projects_algorithm.language_options` |
| RF-16, RF-17 | `projects_algorithm.flowchart` guarda la caché del grafo. Las coordenadas las calcula el cliente |
| RF-19 | `projects_sharelink` |
| RF-27 a RF-31 | `executions_execution`, `executions_executionevent`, `billing_dailyexecution` |
| RF-32 a RF-39 | `learning_learningpath`, `learning_learningunit`, `learning_challenge`, `learning_challengetestcase`, `learning_hint`, `learning_pathentry`, `learning_pathassignment`, `learning_challengeattempt`, `learning_workspacesnapshot`, `learning_practice`, `accounts_profile.points` |
| RF-40 a RF-43 | `classroom_community`, `classroom_membership` |
| RF-44 a RF-47 | `billing_plan`, `billing_subscription` |
| RF-48, RF-49 | Las mismas tablas, a través de la API. El intérprete local no abre PostgreSQL |
| RNF-04 | `audit_auditevent` |

## 8. Criterio de cumplimiento

El análisis se considera cubierto cuando se puede comprobar, con una cuenta de cada rol, lo siguiente:

1. Un alumno confirma el correo, recibe los ejemplos, escribe, valida, ejecuta, depura, ve el diagrama y entra a una comunidad con el código.
2. Un construir con casos no cierra hasta pasarlos todos, y la nota queda visible para el docente de esa comunidad.
3. Un docente apaga el pegado de un alumno y ese alumno sigue pudiendo escribir.
4. Una segunda sesión de la misma cuenta no convive con la primera.
5. Con el cupo del día agotado, ejecutar se rechaza y validar sigue disponible.
6. Un nivel sin navegador deja la cuenta usable en el escritorio y, en el navegador, solo el perfil.
7. Vaciar la papelera borra versiones y eventos de ese algoritmo, y el nombre vuelve a estar libre.
8. El runner, cuando está levantado, no consulta PostgreSQL.

Volver al [índice de vistas](vistas/indice.md).
