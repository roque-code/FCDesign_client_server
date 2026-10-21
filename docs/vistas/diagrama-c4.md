# Diagrama C4

Fecha de referencia: 2026-10-21. Tres niveles. El cuarto, el código, está en el repositorio y no se dibuja aquí.

## Nivel 1. Contexto

Aulivana-FCDdesign es el único sistema. Mailpit forma parte del entorno de desarrollo, no de un proveedor de correo. La cuenta elige español o inglés; el canónico del lenguaje sigue en español.

```mermaid
flowchart LR
    est[Estudiante]
    doc[Docente]
    producto[Aulivana-FCDdesign]
    est -->|pseudocódigo, retos y consola| producto
    doc -->|comunidades, rutas y avance| producto
    producto -->|diagnóstico, diagrama, traducción, puntos y enlace de correo| est
    producto -->|listas y avance| doc
```

## Nivel 2. Contenedores

```mermaid
flowchart TB
    est[Estudiante y docente]
    desk[Ventana Tauri y local_host]
    subgraph producto [Aulivana-FCDdesign en contenedores]
        ngx[Nginx]
        spa[Aplicación React]
        api[API Django]
        run[Runner]
        pg[(PostgreSQL)]
        redis[(Redis)]
        mail[Mailpit]
    end
    est --> ngx
    est --> mail
    est --> desk
    desk -->|cuenta y proyectos| api
    ngx --> spa
    ngx --> api
    api --> pg
    api --> redis
    api --> mail
    redis --> run
```

| Contenedor | Tecnología | Rol |
| --- | --- | --- |
| Nginx | nginx 1.27 | Un origen y SSE sin buffer |
| Aplicación React | Vite, TypeScript | Tres pantallas |
| API Django | Django 5.2, Gunicorn | Sesión, reglas y persistencia |
| Runner | Python, `language_core` | Interpreta lejos de la API |
| PostgreSQL | 16 | Sistema de registro |
| Redis | 7 | Bus de órdenes y eventos |
| Mailpit | 1.27 | Buzón de desarrollo |
| Ventana de escritorio | Tauri 2 y `local_host` | Interfaz y núcleo en la máquina. La API sigue en Django |

## Nivel 3. Componentes de la API y del núcleo

```mermaid
flowchart TB
    subgraph api [API Django]
        accounts[accounts]
        projects[projects]
        executions[executions]
        learning[learning]
        classroom[classroom]
        billing[billing]
        charts[flowcharts]
    end
    subgraph nucleo [language_core]
        lex[Léxico y sintaxis]
        sem[Semántica]
        interp[Intérprete, depurador y traductor]
        flow[Diagrama y adaptador de bloques]
    end
    accounts --> projects
    projects --> executions
    executions --> interp
    learning --> flow
    learning --> interp
    charts --> flow
    classroom --> accounts
    lex --> sem --> interp
    sem --> flow
```

`accounts` no interpreta. `billing` no interpreta: guarda niveles y cierra la API cuando el navegador no está permitido. `executions` y `learning` piden el recorrido al runner, que es el único que importa el núcleo en los contenedores.

Volver al [índice](indice.md).
