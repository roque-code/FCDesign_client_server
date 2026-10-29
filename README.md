# Aulivana-FCDdesign

Aplicación web educativa para escribir, validar, ejecutar, depurar y visualizar algoritmos en pseudocódigo estructurado en español.

**Aulivana-FCDdesign** es el nombre del producto. La identidad visual, el código y el lenguaje son propios. No se reutiliza código ni material gráfico de otras herramientas de pseudocódigo.

## Estado

Están hechas las fases 1 a 6. Los servicios de desarrollo corren en contenedores: PostgreSQL, Redis, el runner aislado, Gunicorn, Vite, Nginx y el buzón Mailpit. En esa máquina `DEBUG` sigue en verdadero y se usa `config.settings.development`. El servidor público ya carga `config.settings.production` y se abre en `https://fcdesign.aulivana.com`. El procedimiento está en [docs/instalacion-aws.md](docs/instalacion-aws.md). Las comunidades de docentes ya están; las actividades y las entregas del aula, no.

El núcleo ejecuta el pseudocódigo completo del encargo: secuencia, `Si`, `Segun`, `Mientras`, `Repetir`, `Para`, arreglos, funciones, procedimientos, recursión y la biblioteca estándar. El perfil estricto es el predeterminado. `<-` y `=` asignan, y `==` compara. Cada algoritmo puede, además, elegir si el punto y coma es obligatorio y si los índices de los arreglos empiezan en 1 o en 0. Esas dos opciones viven en el algoritmo y afectan a validar, ejecutar, depurar y al diagrama.

El diagrama sale del árbol de sintaxis. React Flow lo dibuja y el cliente calcula las posiciones en `frontend/src/diagram/layout.ts`. Las figuras siguen el uso del aula: óvalo de inicio y fin, rectángulo de proceso, paralelogramo verde de `Escribir`, paralelogramo rosa de `Leer`, rombo de `Si`, hexágono de ciclo y triángulo ancho de `Segun` con una barra de casos. La rama falsa sale por la izquierda y la verdadera por la derecha. Cada llegada a otra figura entra por el centro del lado superior. Se puede descargar en SVG, PNG y PDF, e imprimir.

El mismo intérprete se recorre paso a paso, con entrar, salir, continuar, pausar, detener, reiniciar y puntos de interrupción. En los contenedores de desarrollo los eventos salen por SSE: Gunicorn los reenvía y el runner aislado los publica en Redis. En la máquina, sin Docker, el proceso de Django sigue ejecutando en proceso. La consola muestra, en orden, lo que escribe `Escribir` y cada dato que un `Leer` acepta. Un dato rechazado no se pinta.

El banco de trabajo tiene proyectos y algoritmos por cuenta, autoguardado, validación, depurador y consola con desplazamiento. **Traducir** genera el algoritmo en Python, JavaScript, TypeScript, Java, C, C++ y C# a partir del mismo árbol que usa Validar. No ejecuta el programa ni reescribe el fuente. Se puede renombrar un proyecto o un algoritmo, descargar el fuente como archivo y eliminar un algoritmo. El tabulador indenta el editor. Al escribir una instrucción, el editor ofrece su estructura: Enter o Tab la insertan y Tab salta de un hueco al siguiente. La grafía del otro idioma abre la misma plantilla. En el repaso de un alumno no hay lista, porque el editor es de solo lectura. La barra entre el código y el depurador muestra el estado de guardado y la línea del cursor. Proyectos y diagrama se ocultan y se vuelven a mostrar, y el ancho de proyectos, editor y diagrama se arrastra con el ratón. **Actualizar** vuelve a pedir proyectos, algoritmos y comunidades al servidor y suelta el borrador que aún no se guardó. La misma cuenta solo tiene una sesión: otro equipo tiene que esperar a que se cierre, o 30 minutos sin uso. Tres ingresos fallidos bloquean ese correo 15 minutos. En la aplicación de escritorio, descargar abre el diálogo de guardar del sistema. En la barra superior están **Funciones** (el listado de la biblioteca), **Operadores** (cada símbolo y el orden en que se ligan), **Manuales** (el PDF se ve en la aplicación y se puede guardar) y **Configuración** (idioma, cuerpo, tema, punto y coma e índice de arreglos). El alumno ve el manual del lenguaje y el del alumno. El docente ve también el suyo. El idioma es español o inglés. Cambia los textos de la interfaz, las etiquetas de los bloques, las figuras del diagrama y la grafía de las palabras reservadas. Un docente puede apagar la traducción de código y el pegado para una comunidad o para un alumno, dentro de lo que el nivel ya permite. Pegar apagado deja escribir y rechaza el texto pegado. La cuenta cambia su nombre, su foto JPG o PNG y su contraseña desde la misma sesión. En **Repaso** abre los proyectos de ese alumno en solo lectura. En el laboratorio ve un tablero de avance, descarga las notas de una ruta en CSV y abre el trabajo de un reto. La ruta Práctica de concurso trae cincuenta problemas. Un CSV agrega retos al banco del docente, hasta 250 filas y 1 MB. **Descargar CSV** entrega los retos de un tipo, del catálogo o del concurso, para que otro docente los vuelva a cargar. El fuente ya guardado no se reescribe: el editor lo muestra en la grafía elegida y, al guardar, conserva la que ya tenía. El lexer acepta las dos. Los nombres de la biblioteca, los identificadores, las cadenas y los mensajes de diagnóstico siguen en español. Un algoritmo nuevo, con el idioma en inglés, se guarda con las palabras en inglés. El perfil es docente o estudiante y se elige al crear la cuenta; después no se cambia. El administrador no aparece en el alta: se crea con `python manage.py create_admin`. Desde su pantalla puede ocultar el alta de alumno o de docente. Un reto de construir no se cierra hasta coincidir en todos los casos; al terminar, el alumno ve su respuesta y el docente la ve aunque el intento siga abierto. **Lenguajes** aparece, entre Actualizar y Laboratorio, si el nivel lo incluye. En el navegador, Ejecutar corre en el servidor: en desarrollo, en un proceso de esa misma máquina; en el servidor público, en un contenedor aparte, sin salida a internet. Si ese contenedor no responde, la pantalla dice que Lenguajes no está disponible. En la aplicación de escritorio corre en la máquina. La barra muestra las ejecuciones que quedan hoy, o el signo de infinito si el nivel no tiene tope. **Comunidades** abre su propia pantalla. El docente comparte un código de 6 caracteres y el alumno lo escribe en **Unirme**. El avance del docente pide primero la comunidad y el CSV de una ruta trae solo a esos alumnos. El administrador puede bloquear una cuenta, y al entrar responde que está bloqueada. Si falta el compilador, se descarga del manifiesto publicado en `/runtimes/`. Repetir el alta con un correo que ya existe responde que ya está registrado. Ese código se puede pasar a un reto de construir, y el reto no termina hasta que pase todos los casos. Pegar ahí sigue el bloqueo del docente. En cada reto de una ruta el docente reparte la nota de 100. La nota se guarda al avanzar y el docente la ve aunque el intento siga abierto. Una cuenta nueva puede entrar por el navegador; el administrador puede quitarle ese acceso. El pie reserva los derechos a R&J Integra Soluciones Tecnológicas. **Armar diagrama** y **Armar Nassi-Shneiderman** usan el mismo plan. En el segundo, un `Si` parte el bloque en dos columnas, los ciclos encierran el cuerpo y `Según` abre una columna por caso. `Dimension` es una figura, con nombre y tamaño. En el reto, el alumno arrastra el borde del enunciado, de los casos, de la ayuda y del editor. La campana, junto al nombre del alumno, avisa de un reto nuevo o de uno que el docente volvió a habilitar. Un construir puede ir sin casos: entonces no se compara una salida. En una ruta, el mismo reto se puede agregar otra vez; la copia nueva tiene su horario y los intentos anteriores se conservan. En Armar diagrama, al elegir una figura de la lista o al arrastrarla, el espacio entre figuras se abre para soltarla; al soltar, se vuelven a juntar. `compose.servidor.yaml` envía la confirmación por Gmail y no levanta Mailpit. Cada cuenta de alumno o docente queda en el nivel gratis de su tipo. El nivel, guardado en la base, dice cuántos proyectos y códigos puede crear, cuántas ejecuciones permite al día, qué menús tiene y si el navegador puede abrir la aplicación. El tope diario nace en 3. Vacío es sin límite, y un número no baja de 3. Si se acaba, la pantalla dice que ya se usaron las ejecuciones de hoy. Si el navegador no está permitido, ahí solo se entra a la cuenta: tipo, foto, contraseña y días que faltan para pagar. La aplicación de escritorio usa las funciones del nivel. Un docente crea comunidades, lista a sus alumnos y busca cuentas ya registradas, de alumnos o de otros docentes, para agregarlas. Cada cuenta nueva recibe los ejemplos 1 a 13, y esos ejemplos no cuentan para el tope del nivel.

Un ciclo se corta a 100 000 instrucciones o a 5 segundos. Detener lo corta antes. En Lenguajes, Detener cierra el programa y no corren más de 6 a la vez. La pantalla avisa, cuando el ejecutor es el del mismo proceso, que la ejecución ocurre ahí y con límites lógicos. Los contenedores usan el runner aislado. `config.settings.production` no arranca con el ejecutor en proceso: al importarse lanza `ImproperlyConfigured`. El compose de desarrollo no lo carga. El de `compose.servidor.yaml` sí.

La aplicación de escritorio, en `desktop/`, abre la misma interfaz en una ventana de Tauri. El intérprete corre en la máquina, en `local_host`. La cuenta, los proyectos y el laboratorio siguen en la API. En un paquete publicado, esas llamadas pasan por un proxy local hacia `TRAZA_API_ORIGIN`. Si la variable no está definida, el origen es `https://fcdesign.aulivana.com`. Validar, traducir, ejecutar y depurar no salen de la máquina. El cupo de ejecuciones del día sí se descuenta en el servidor.

El mapa del sistema que corre hoy está en [arquitectura](docs/arquitectura.md).

## Documentos

| Documento | Contenido |
| --- | --- |
| [Instalación](docs/instalacion.md) | Contenedores de desarrollo y comprobaciones |
| [Desarrollo](docs/desarrollo.md) | Máquina local, ejecutor en proceso y bus Redis |
| [Despliegue](docs/despliegue.md) | Lo que falta cuando haya un servidor. No está activo |
| [Servidor en AWS](docs/instalacion-aws.md) | Instancia cfdesign, grupo de seguridad y arranque con `compose.servidor.yaml`. El Word está en [Instalacion-servidor-AWS.docx](docs/Instalacion-servidor-AWS.docx) |
| [Bitácora AWS](docs/bitacora-instalacion-aws.md) | Cambios desde la primera EC2 hasta HTTPS, en el orden para replicar la instancia |
| [Arquitectura](docs/arquitectura.md) | Contenedores, correo, tres pantallas, API y fronteras |
| [Vistas](docs/vistas/indice.md) | Negocio, datos, física, C4, UML, secuencia y el Word |
| [Gramática](docs/gramatica.md) | EBNF, léxico, grafías en inglés, operadores, perfiles y traducción |
| [Manual del lenguaje](docs/Manual-del-lenguaje.docx) | Instrucciones, palabras reservadas, figuras, bloques, funciones y traducción, con ejemplos |
| [Manual del alumno](docs/manual-alumno/Manual-del-alumno.docx) | Cada menú del alumno, con captura y ejemplo |
| [Manual del docente](docs/manual-docente/Manual-del-docente.docx) | Comunidades, banco, rutas, avance, operadores y descarga de retos |
| [AST](docs/ast.md) | Nodos, ámbitos y diagnósticos |
| [Modelo de datos](docs/modelo-de-datos.md) | Entidades Django, índices y borrado |
| [Diccionario de datos](docs/diccionario-de-datos.md) | Tablas, campos, tipos y relaciones para armar consultas |
| [Ejecución](docs/ejecucion.md) | Intérprete, depurador y aislamiento |
| [Pruebas y roadmap](docs/pruebas-y-roadmap.md) | Cobertura, iteraciones y criterios del MVP |
| [Decisiones](docs/decisiones-pendientes.md) | Decisiones del lenguaje y del editor, ya en el código |
| [Laboratorio](docs/laboratorio-fase-0.md) | Aprendizaje visual. La ruta incluye Si, Mientras, Segun, Para, Repetir, arreglos y funciones. La práctica libre se guarda, se abre, se descarga, se borra y arma bloques desde un archivo |
| [Canal de YouTube](docs/canal-youtube.md) | Secuencia, guiones y planos del canal de la plataforma. El Word está en [Canal-de-YouTube.docx](docs/Canal-de-YouTube.docx) |
| [ADR](docs/adr/) | Decisiones de arquitectura |

## Uso del núcleo

```bash
python3 -m pip install -e ".[dev]"
python3 -m pytest
python3 -m ruff check language_core
python3 -m black --check language_core
python3 -m mypy language_core
```

```python
from language_core import execute_source

result = execute_source(open("algoritmo.traza", encoding="utf-8").read(), ["Ana", "18"])
print(result.output)
```

## Editor en contenedores

Un solo origen, `http://127.0.0.1:18080`. Nginx entrega Vite y proxifica `/api` con el buffer apagado en el canal de eventos. PostgreSQL del compose publica el puerto `5434` para no chocar con el contenedor `traza-pg` del puerto `5433`. Al crear la cuenta, Aulivana-FCDdesign envía un enlace de confirmación; el buzón de desarrollo está en `http://127.0.0.1:8025`. La cuenta no entra hasta abrir ese enlace.

```bash
docker compose up --build
```

El detalle está en [instalación](docs/instalacion.md). La máquina sin Docker sigue en la sección siguiente.

## Editor en la máquina

PostgreSQL local en `127.0.0.1:5433`, base `traza`. El cliente en `http://127.0.0.1:5173` proxifica `/api` hacia Django. En esta máquina el puerto 8000 lo usa otra aplicación, así que Aulivana-FCDdesign escucha en `127.0.0.1:8002` y el proxy de Vite apunta ahí. Ese modo usa el ejecutor en proceso.

```bash
python3 -m pip install -e ".[dev,server]"
python3 -m pytest
cd server && python3 manage.py migrate && python3 manage.py runserver 127.0.0.1:8002
cd frontend && npm install && npm run dev
cd frontend && npm run typecheck && npm run lint && npm test
cd server && python3 -m mypy --config-file mypy.ini apps config && python3 -m pytest -q --tb=line
```
