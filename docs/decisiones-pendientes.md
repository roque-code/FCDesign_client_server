# Decisiones

Las doce decisiones de este documento se aceptaron y están en el código. Las recomendaciones de abajo son el registro de por qué se eligieron. Al final están las decisiones tomadas después, también ya implementadas.

## Bloquean la Fase 1

### 1. Representación de Real

Recomendación: `decimal.Decimal` a partir del texto del literal.

- Ventaja: `9.5` se guarda exacto y la salida del estudiante coincide con lo que escribió.
- Desventaja: algunas cuentas binarias «típicas» de otros lenguajes no se reproducen. Hay que definir el redondeo de `Sen`, `Cos` y `Tan`.
- Impacto: `type_system.py`, literales, división y el formato de `Escribir`.

Alternativa: `float`. Más familiar para quien viene de C, y peor para calificaciones y dinero de juguete.

### 2. Escalar sin asignar

Recomendación: en el perfil estricto, leer un escalar antes de asignarlo es un error. Las celdas de un arreglo nacen con el valor inicial del tipo.

- Ventaja: el estudiante ve el olvido en el momento de la lectura.
- Desventaja: no se puede usar una variable como acumulador sin escribir antes `suma <- 0`.
- Impacto: analizador de caminos y runtime. El acumulador explícito es el hábito que se quiere enseñar.

### 3. Acentos en palabras clave

Recomendación: `Logico` y `Lógico` son la misma palabra clave. Los identificadores no pierden el acento.

- Ventaja: tolera lo que el estudiante teclea.
- Desventaja: hay que normalizar con cuidado los caracteres Unicode.
- Impacto: solo el lexer.

### 4. Signo de DIV y MOD

Recomendación: truncar hacia cero. `-7 DIV 2` vale `-3` y `-7 MOD 2` vale `-1`.

- Ventaja: coincide con la división entera que suelen enseñar los cursos introductorios en español, y cumple `a = (a DIV b) * b + (a MOD b)`.
- Desventaja: no coincide con `//` de Python, que redondea hacia menos infinito.
- Impacto: cuatro operaciones en el intérprete y sus pruebas.

### 5. Paso omitido en `Para`

Recomendación: si no se escribe `Con Paso`, el paso es `1` cuando el inicio es menor o igual que el fin, y `-1` cuando el inicio es mayor. `Para i <- 10 Hasta 1 Hacer` cuenta hacia abajo. El paso `0` sigue siendo error.

- Ventaja: el ciclo que el estudiante escribe «de 10 a 1» hace lo que parece.
- Desventaja: un paso explícito `1` con inicio mayor que el fin no entra al cuerpo. La omisión y el `1` escrito no se comportan igual.
- Impacto: el intérprete del `Para` en la Fase 1 y el diagrama de la Fase 5.

### 6. Punto y coma

Recomendación: el perfil estricto lo exige en sentencias simples y no lo exige tras `FinSi`, `FinMientras`, `FinPara`, `FinSegun`, `FinFuncion` ni `FinAlgoritmo`. El parser lo acepta siempre; el perfil informa si falta.

- Ventaja: los ejemplos del encargo ya llevan punto y coma, y un perfil flexible puede apagar la obligación sin otra gramática.
- Desventaja: un primer error del estudiante será a menudo el punto y coma, no la idea.
- Impacto: una regla semántica, no una segunda gramática.

## Conviene cerrarlas antes de la Fase 2

### 7. Nombre

Recomendación: **Aulivana-FCDdesign**.

- Ventaja: nombre propio del producto, distinto de otras herramientas de pseudocódigo.
- Desventaja: hace falta logotipo y dominio si se publican aparte.
- Impacto: títulos de la interfaz y del manual. No cambia los paquetes: el núcleo sigue llamándose `language_core`.

### 8. Cliente web

Recomendación: React, TypeScript y Vite, en el mismo origen que Django, con sesión y CSRF.

- Ventaja: paneles sincronizados, CodeMirror 6 y React Flow.
- Desventaja: hay un segundo empaquetado en CI y en la imagen.
- Impacto: toda la Fase 2 de interfaz. No cambia la Fase 1.

Alternativa: plantillas de Django y CodeMirror sin framework. Menos piezas, y un banco de trabajo más difícil de mantener cuando lleguen el depurador y el diagrama.

### 9. Editor

Recomendación: CodeMirror 6, no Monaco.

- Ventaja: mejor en tabletas y más fácil de alimentar con la tabla de palabras del núcleo.
- Desventaja: el autocompletado y la búsqueda hay que componerlos con las extensiones de CodeMirror; en Monaco vienen más cerrados.
- Impacto: el paquete del editor en `frontend`.

### 10. Índices de arreglos

Recomendación: base 1 en el perfil estricto. `Dimension a[10]` tiene los índices `1` a `10`.

- Ventaja: coincide con el ejemplo de la matriz del encargo.
- Desventaja: choca con quien viene de C o de Python. El perfil de base 0 existe para eso.
- Impacto: Fase 3, runtime de arreglos.

### 11. Paso de arreglos

Recomendación: escalares `Por Valor` por defecto; arreglos `Por Referencia` por defecto. Ambos se pueden invertir con `Por Valor` o `Por Referencia`.

- Ventaja: un procedimiento de ordenamiento modifica el arreglo del llamador, que es lo que el ejercicio pide.
- Desventaja: la regla no es la misma para todos los tipos y hay que decirlo en el manual y en la ayuda del editor.
- Impacto: Fase 3, llamadas.

### 12. Celery y canal de depuración

Recomendación: sin Celery. Redis como bus. El navegador recibe eventos por SSE y envía órdenes por POST.

- Ventaja: la pausa de `Leer` y del depurador encaja en una sesión con estado. Hay menos servicios.
- Desventaja: el worker del runner es código propio que hay que vigilar, con latido y bloqueo.
- Impacto: Fases 4 y 6. La Fase 1 no usa Redis.

## Lo que ya queda fijado si se acepta este paquete

- El núcleo no importa Django.
- No hay `eval` ni `exec`.
- `<-` asigna y `=` compara, en el perfil estricto.
- El ámbito es el de la subrutina, no el del bloque, y no hay globales.
- Hay un solo `Algoritmo` por archivo. Las subrutinas van fuera, antes o después.
- El proceso web de producción no interpreta código de usuarios. En los contenedores de desarrollo tampoco: lo hace el runner. En la máquina, sin compose, el editor sí ejecuta dentro de Django, con límites, y la pantalla lo dice. `config.settings.production` sigue sin cargarse.

## Decisiones posteriores, ya en el código

### Opciones por algoritmo

El perfil estricto sigue exigiendo punto y coma e índices desde 1. Cada algoritmo puede guardar otra elección: punto y coma obligatorio u opcional, e índice inicial `1` o `0`. Un objeto vacío usa el perfil. Afectan a validar, ejecutar, depurar y al diagrama.

### Posiciones del diagrama

El grafo sigue saliendo de Python, sin coordenadas. El cliente las calcula en `frontend/src/diagram/layout.ts`. `elkjs` sigue declarado en el paquete del cliente y no interviene en el dibujo. Las formas, el lado de las ramas y la llegada por el centro superior están descritos en [arquitectura.md](arquitectura.md).

### Eco de `Leer`

Un dato aceptado se escribe en la consola, en su propia línea, en el momento en que se guardó. Un dato rechazado no se escribe.

### `Caracter`

Es un símbolo Unicode, no una cadena. El editor muestra la palabra `Caracter`, sin tilde. `' '` es un carácter válido.

### Confirmación de correo

En los contenedores de desarrollo el alta no abre sesión. Django envía un enlace por SMTP a Mailpit y `email_confirmed` pasa a verdadero al abrirlo, también si el enlace se abre en otro equipo. `compose.servidor.yaml` envía ese mismo enlace por Gmail y no levanta Mailpit. El administrador puede ocultar el alta de alumno o de docente. Si ese navegador ya tiene otra sesión, no la sustituye. En la máquina, sin `TRAZA_EMAIL_CONFIRMATION`, el correo va a la consola y la cuenta entra al momento. Las cuentas anteriores a la columna quedan confirmadas. Una cuenta solo tiene una sesión: otro equipo recibe que ya está abierta, y 30 minutos sin uso la cierran. Tres ingresos fallidos del mismo correo lo bloquean 15 minutos. El detalle está en [arquitectura.md](arquitectura.md).

### Banco de trabajo

Proyectos y diagrama se ocultan. El ancho de los tres paneles se arrastra. Se renombra, se descarga y se elimina un algoritmo. El tabulador indenta. **Configuración**, **Funciones**, **Traducir** y **Actualizar** están en la barra superior. **Actualizar** vuelve a pedir los datos y suelta el borrador local que aún no se guardó. Otra máquina no puede tener la misma cuenta abierta.

### Idioma de la cuenta

La cuenta elige español o inglés en **Configuración**. El valor vive en `EditorPreference.locale` y también en el navegador, para la pantalla de entrada. Cambia los textos, los bloques, las figuras y la grafía de las palabras reservadas. No cambia los nombres de la biblioteca, los identificadores, las cadenas ni los diagnósticos. Un fuente ya guardado no se reescribe. El lexer acepta las dos grafías y el canónico del token sigue en español. La tabla está en [gramatica.md](gramatica.md).

### Traducción a otros lenguajes

El algoritmo se puede emitir en Python, JavaScript, TypeScript, Java, C, C++ y C#. El emisor es `language_core/translate.py`. Recorre el AST de Validar, conserva comentarios, base de índices, `DIV`, `MOD` y referencias, y no ejecuta el programa. Un error deja la lista de traducciones vacía. `Segun` usa `switch` o `match` cuando el tipo cabe; si no, una cadena de `Si`. `Para` incluye los dos extremos. `Repetir` niega la condición de `Hasta Que`.

### Cuenta y pegado

`PATCH /api/v1/auth/me/` cambia el nombre, una foto JPG o PNG de hasta 120 KB y la contraseña, si se envía la actual. El tipo de cuenta no cambia. Pegar sigue la misma regla que traducir: nace habilitado, el docente lo apaga por comunidad o por alumno, y el nivel puede tenerlo apagado de antemano. El editor deja escribir.

### Traducción por comunidad

La traducción nace habilitada. El docente la apaga para una comunidad o para un alumno. El ajuste del alumno, si no es nulo, manda. Si el alumno está en varias comunidades y en una está apagada, no traduce. Un docente siempre puede. El repaso de un alumno abre sus proyectos en solo lectura y no crea versiones.

### Práctica de concurso y CSV

La ruta **Práctica de concurso** trae cincuenta problemas de creación de código, con tres casos cada uno. El banco del sistema se llama **Banco de concurso**. Un CSV del docente agrega retos a su propio banco, no al de concurso. **Descargar CSV**, en Concurso y con el tipo Construir, entrega esos cincuenta problemas en `retos-construir-concurso.csv`. La carga sigue yendo al banco del docente y admite hasta 250 filas y 1 MB. El formato está en [ejemplos-de-retos.md](ejemplos-de-retos.md). El avance de una ruta se descarga como CSV de notas. Al agregar un reto a una ruta, el docente filtra por tipo para no ver clasificar, ordenar, construir y predecir en la misma lista, y reparte la ponderación de la nota. Un construir con casos no se cierra hasta que el código de un lenguaje pasa esos casos. Lenguajes ejecuta ese código en la máquina y, si falta el compilador, lo baja del manifiesto.

### Aplicación de escritorio

La ventana es Tauri. El intérprete corre en `local_host`, en la máquina, con el mismo núcleo. La cuenta y los proyectos siguen en la API. En un paquete publicado el proxy local reenvía solo `/api/`. El origen es `TRAZA_API_ORIGIN` y, si falta, `http://3.17.151.210:18080`. El empaquetado manual está en `.github/workflows/desktop.yml`.
