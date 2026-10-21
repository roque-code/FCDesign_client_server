# Arquitectura de negocio

Fecha de referencia: 2026-10-21. Aulivana-FCDdesign enseña programación estructurada. El canónico del lenguaje es el español y la cuenta puede ver la interfaz y las palabras reservadas en inglés. El estudiante escribe pseudocódigo, lo valida, lo ejecuta, lo depura, ve el diagrama y puede pedir el mismo algoritmo en otro lenguaje de programación. El docente agrupa cuentas ya registradas y sigue el avance del laboratorio. La ventana de escritorio ofrece lo mismo: el intérprete corre en la máquina y la cuenta sigue en el servidor.

## Actores

| Actor | Objetivo |
| --- | --- |
| Estudiante | Practicar algoritmos con diagnóstico de línea y columna, consola y diagrama |
| Docente | Formar comunidades, publicar rutas, apagar traducción y pegado, ver el tablero, descargar notas y retos, y abrir el trabajo de un alumno, dentro de su nivel |
| Administrador | Definir niveles, precios y funciones, y asignar un nivel a una cuenta ya creada |
| Plataforma | Conservar la cuenta, el fuente y el intento, y ejecutar el programa fuera del proceso web |

Quedan fuera del negocio actual las actividades y las entregas del aula, la orientación a objetos, los archivos del pseudocódigo y la concurrencia.

## Capacidades

```mermaid
flowchart TB
    subgraph oferta [Lo que Aulivana-FCDdesign ofrece]
        cuenta[Cuenta por correo confirmado]
        editor[Banco de trabajo y traducción]
        lab[Laboratorio y puntos]
        aula[Comunidades]
        figura[Armar diagrama]
    end
    estudiante[Estudiante] --> cuenta
    estudiante --> editor
    estudiante --> lab
    estudiante --> figura
    docente[Docente] --> aula
    docente --> lab
    cuenta --> editor
```

## Reglas de negocio

- El identificador es el correo. En los contenedores la sesión no empieza hasta abrir el enlace. Hay una sola sesión por cuenta. Tres fallos bloquean el correo 15 minutos y 30 minutos sin uso cierran la sesión.
- Cada cuenta nueva recibe los ejemplos 1 a 13.
- El perfil es estudiante o docente. Si no se elige, queda estudiante. Se fija al crear la cuenta. El administrador puede cerrar uno de los dos altas.
- El administrador no se elige en el alta. Se crea con `manage.py create_admin`.
- Cada alumno o docente entra en el nivel gratis de su tipo. El nivel dice qué menús hay, cuántos proyectos y códigos se pueden crear, el precio y si el navegador abre la aplicación.
- Si el nivel no permite el navegador, ahí solo queda la cuenta: tipo, foto, contraseña y tiempo para pagar. Las funciones se usan en la aplicación de escritorio.
- Un docente no crea cuentas desde la comunidad: busca personas ya registradas.
- La comunidad puede apagar traducir o pegar. No puede dar una función que el nivel tiene apagada.
- Los puntos de un reto se suman una sola vez. El puesto sale de comparar `Profile.points`.
- El laboratorio y el editor comparten el lenguaje. Un intento no es un algoritmo del banco de trabajo.
- El idioma de la cuenta es español o inglés. Cambia la pantalla y la grafía de las palabras reservadas. No reescribe un fuente ya guardado.
- Armar diagrama produce texto. Al abrirlo en el editor, el núcleo pasa a ser la autoridad.

Volver al [índice](indice.md).
