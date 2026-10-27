# Despliegue

El servidor público ya está en `https://fcdesign.aulivana.com`. Usa `compose.servidor.yaml`, `config.settings.production` y el certificado de Let's Encrypt. El procedimiento de esa instancia está en [instalacion-aws.md](instalacion-aws.md). El compose de esta máquina sigue siendo de desarrollo: el runner y Redis son los mismos, y el intérprete no cambia.

## 1. Lo que el compose de desarrollo no hace

- No apunta Gunicorn a `config.settings.production`.
- Deja `DEBUG` en verdadero.
- No activa HSTS ni cookies `Secure`: el origen de esta máquina es `http://127.0.0.1:18080`.
- No publica PostgreSQL ni Redis en una red abierta.
- No usa las contraseñas `traza`, `traza-web-dev` ni `traza-runner-dev` fuera de esta máquina.
- No publica Mailpit en el servidor público. Aquí solo guarda el correo de este entorno.

`config.settings.production` se niega a arrancar si `TRAZA_RUNNER` no es `redis`, si falta `REDIS_URL`, si falta `EMAIL_HOST`, si la clave es la de desarrollo o si `DJANGO_CSRF_ORIGINS` no es `https://`. El compose de desarrollo no importa ese módulo. El de `compose.servidor.yaml` sí.

## 2. Lo que el servidor público ya hace

1. La clave de Django y la de Gmail viven en el `.env`, fuera del repositorio. Las contraseñas de PostgreSQL y de Redis del compose siguen siendo las de desarrollo.
2. `DJANGO_SETTINGS_MODULE=config.settings.production`, `TRAZA_RUNNER=redis`, SMTP de Gmail, `TRAZA_EMAIL_CONFIRMATION=1` y `TRAZA_PUBLIC_ORIGIN=https://fcdesign.aulivana.com`.
3. Nginx termina TLS y sirve el resultado de `npm run build`. El compose de desarrollo sigue con Vite.
4. PostgreSQL, Redis, el runner y el contenedor de lenguajes no publican puertos. El runner no tiene credenciales de la base ni salida a internet. El de lenguajes tampoco tiene salida: Node, Java y .NET entran al construir la imagen.
5. El canal SSE conserva `proxy_buffering off`.
6. El servicio `web` sigue montando el árbol del repositorio. El de lenguajes no lo monta.

El arranque de esta máquina es el de [instalacion.md](instalacion.md). El de la instancia es el de [instalacion-aws.md](instalacion-aws.md).

## 3. La ventana de escritorio no sustituye ese servidor

El paquete de `desktop/` lleva la interfaz y el intérprete local. La cuenta, los proyectos y el laboratorio persistido siguen pidiendo una API. El origen de esa API es `TRAZA_API_ORIGIN`. Publicar el paquete no cambia el compose de desarrollo ni apaga Mailpit en esta máquina. El flujo de empaquetado, lanzado a mano, está en `.github/workflows/desktop.yml`.
