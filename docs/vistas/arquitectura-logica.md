# Arquitectura lógica

Fecha de referencia: 2026-10-14. Las capas no se saltan: el navegador no llama al runner, y el runner no llama a PostgreSQL.

```mermaid
flowchart TB
    subgraph presentacion [Presentación]
        react[React: cuenta, banco, laboratorio y armar diagrama]
    end
    subgraph aplicacion [Aplicación]
        django[Django y DRF]
        apps[accounts, projects, executions, learning, classroom, editor, language, flowcharts, audit]
    end
    subgraph dominio [Dominio del lenguaje]
        core[language_core]
    end
    subgraph ejecucion [Ejecución]
        runner[runner]
        redis[(Redis)]
    end
    subgraph estado [Estado durable]
        pg[(PostgreSQL)]
    end
    subgraph correo [Correo]
        mail[Mailpit en desarrollo]
    end

    react -->|HTTP y SSE| django
    django --> apps
    django --> pg
    django --> redis
    django -->|SMTP| mail
    redis --> runner
    runner --> core
    runner --> redis
    django -.->|solo en la máquina, sin compose| core
```

| Capa | Responsabilidad | No hace |
| --- | --- | --- |
| Presentación | Paneles, CodeMirror, React Flow, Blockly, el modelo de armar diagrama y la grafía visible del idioma | Ejecutar el pseudocódigo del editor. Traducir un fuente ya guardado al cambiar el idioma |
| Aplicación | Permisos, tamaño, límites de peticiones, persistencia y reenvío del SSE | Interpretar en los contenedores |
| Dominio | Léxico, sintaxis, semántica, intérprete, depurador, diagrama, grafías en inglés y adaptador de bloques | Importar Django o Redis |
| Ejecución | Consumir órdenes y publicar eventos | Abrir la base ni el buzón |
| Estado | Cuentas, algoritmos, intentos y auditoría | Guardar la pila viva del depurador |
| Correo | Entregar el enlace de confirmación y el de restablecimiento | Validar el programa |

En la máquina, sin compose, la aplicación llama al dominio en el mismo proceso. Esa flecha punteada no existe cuando `TRAZA_RUNNER=redis`.

Volver al [índice](indice.md).
