# Arquitectura física

Fecha de referencia: 2026-10-21. El compose de desarrollo corre en la máquina, dentro de Docker. `config.settings.production` no está activo. La ventana de escritorio es otro nodo: el intérprete queda en esa máquina y la API sale hacia `TRAZA_API_ORIGIN`.

```mermaid
flowchart TB
    subgraph anfitrion [Máquina de desarrollo]
        browser[Navegador]
        subgraph docker [Motor Docker]
            subgraph redweb [Red web]
                ngx[Nginx :18080]
                vite[Vite]
                web[Gunicorn]
                mail[Mailpit :8025]
                db[(PostgreSQL :5434)]
            end
            subgraph redisn [Redis en las dos redes]
                redis[(Redis)]
            end
            subgraph aislada [Red isolated, sin salida]
                run[runner]
            end
        end
        vol1[(volumen traza-db)]
        vol2[(volumen traza-redis)]
    end
    browser -->|18080| ngx
    browser -->|8025| mail
    ngx --> vite
    ngx --> web
    web --> db
    web --> redis
    web -->|SMTP 1025| mail
    redis --> run
    db --> vol1
    redis --> vol2
```

| Pieza física | Puerto en el anfitrión | Disco |
| --- | --- | --- |
| Nginx | `18080` | configuración de solo lectura |
| Mailpit | `8025`. El SMTP `1025` no se publica | mensajes en memoria, tope 500 |
| PostgreSQL 16 | `5434` | volumen `traza-db` |
| Redis 7 | ninguno | volumen `traza-redis` |
| Vite, Gunicorn, runner | ninguno | el código va montado en Vite y Gunicorn. El runner no monta el servidor |

El runner usa sistema de archivos de solo lectura, `/tmp` en memoria, sin capacidades añadidas y con tope de memoria, CPU y procesos. La red `isolated` no tiene salida a internet. Redis es el único nodo en las dos redes.

En la misma máquina puede seguir el contenedor anterior `traza-pg` en `5433`. El compose no lo usa.

La ventana Tauri no entra en este compose. Lleva la interfaz y `local_host` en `127.0.0.1`. En un paquete publicado, el proxy de `/api/` usa `TRAZA_API_ORIGIN` y, si falta, `http://3.17.151.210:18080`. Validar, traducir, ejecutar y depurar no salen de esa máquina.

Volver al [índice](indice.md).
