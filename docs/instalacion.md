# Instalación en desarrollo

Estado: los servicios corren en contenedores con `DEBUG` en verdadero. No es el despliegue de un servidor. El mapa de esos servicios está en [arquitectura.md](arquitectura.md).

## 1. Qué levanta el compose

| Servicio | Papel | Puerto en el anfitrión |
| --- | --- | --- |
| `nginx` | Origen único. Sirve Vite y proxifica `/api` con `proxy_buffering off` | `18080` |
| `frontend` | Vite en caliente | solo red interna |
| `web` | Gunicorn y Django, configuración `config.settings.development` | solo red interna |
| `runner` | Intérprete aislado. Sin PostgreSQL, sin código de Django, sistema de archivos de solo lectura | solo red interna, sin salida a internet |
| `redis` | Bus de órdenes y eventos, y caché de Django | solo red interna |
| `db` | PostgreSQL 16 | `5434` |
| `mail` | Mailpit. Recibe el SMTP de Django y muestra los mensajes | `8025` |

La aplicación se abre en `http://127.0.0.1:18080`. El buzón, en `http://127.0.0.1:8025`.

Al crear una cuenta, Django envía un enlace de confirmación al contenedor `mail`. La sesión no empieza hasta abrir ese enlace. El alta en la máquina, sin estas variables, sigue entrando al momento: el correo va a la consola y no hay buzón.

El contenedor anterior `traza-pg` puede seguir en el puerto `5433`. El compose no lo usa y no lo detiene.

## 2. Arranque

Desde la raíz del repositorio:

```bash
docker compose up --build
```

La primera vez construye las imágenes e instala dependencias. Django aplica las migraciones al arrancar. El runner publica un latido en Redis. `/api/health/` responde `200` cuando la base y ese latido están bien. Nginx espera a los dos.

Para parar:

```bash
docker compose down
```

Los volúmenes `traza-db` y `traza-redis` conservan los datos. `docker compose down -v` los borra.

## 3. Comprobaciones

- `GET http://127.0.0.1:18080/api/health/` devuelve `{"status":"ok",...}`.
- `GET http://127.0.0.1:18080/api/schema/` publica el esquema OpenAPI de la API.
- Un alta en la pantalla crea la cuenta en la base del compose, no en la de `traza-pg`, y deja el mensaje de confirmación en Mailpit.

Para volcar el esquema a un archivo, con el entorno del servidor y la base accesible:

```bash
cd server && python3 manage.py spectacular --file ../docs/openapi.yaml
```

Ese archivo no se versiona: la referencia viva es `/api/schema/`.

## 4. Aislamiento del runner

La imagen solo lleva Python, `language_core` y el paquete `runner`. El usuario no es root. El contenedor descarta capacidades, no gana privilegios, limita memoria, CPU y procesos, y monta `/tmp` en memoria. La credencial de Redis solo alcanza las claves `traza:*`. El fuente viaja en el mensaje, no en un archivo del proceso web.

## 5. Integración continua

`.github/workflows/ci.yml` ejecuta Ruff, Black, mypy, las pruebas del núcleo, las del runner y las del servidor contra PostgreSQL, y el lint y las pruebas del cliente.
