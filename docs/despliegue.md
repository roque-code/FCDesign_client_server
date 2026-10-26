# Despliegue

Este paso no está activo. El compose del repositorio es de desarrollo. Cuando haya un servidor, el cambio es de configuración y de borde, no de intérprete: el runner y Redis ya son los del desarrollo en contenedores.

## 1. Lo que hoy no hay que hacer

- No apuntar Gunicorn a `config.settings.production`.
- No poner `DEBUG` en falso.
- No activar HSTS ni cookies `Secure` mientras el origen sea `http://127.0.0.1:18080`.
- No publicar PostgreSQL ni Redis en una red abierta.
- No usar las contraseñas `traza`, `traza-web-dev` ni `traza-runner-dev` fuera de esta máquina.
- No publicar Mailpit: solo guarda el correo de este entorno. Un servidor necesita un SMTP de verdad y las mismas variables `EMAIL_HOST` y `TRAZA_EMAIL_CONFIRMATION`.

`config.settings.production` ya se niega a arrancar si `TRAZA_RUNNER` no es `redis`, si falta `REDIS_URL` o si falta `EMAIL_HOST`. Esa comprobación queda lista. El proceso que se usa ahora no importa ese módulo.

## 2. Cuando exista el servidor

1. Secreto de Django, contraseñas de PostgreSQL y usuarios ACL de Redis distintos, fuera del repositorio.
2. `DJANGO_SETTINGS_MODULE=config.settings.production`, `TRAZA_RUNNER=redis`, `EMAIL_HOST` de un SMTP real, `TRAZA_EMAIL_CONFIRMATION=1` y `TRAZA_PUBLIC_ORIGIN` con el origen HTTPS. Mailpit no sirve en ese puesto.
3. TLS delante de Nginx. `compose.servidor.yaml` ya sirve el resultado de `npm run build` y no levanta Vite. El compose de desarrollo sigue con Vite.
4. Dejar PostgreSQL, Redis y el runner sin puertos públicos. El runner sigue sin credenciales de la base y sin salida a internet.
5. Conservar `proxy_buffering off` en el canal SSE.
6. Sustituir el volumen de código fuente por la imagen construida, sin montar el árbol.

Hasta entonces, el arranque es el de [instalacion.md](instalacion.md).

## 3. La ventana de escritorio no sustituye ese servidor

El paquete de `desktop/` lleva la interfaz y el intérprete local. La cuenta, los proyectos y el laboratorio persistido siguen pidiendo una API. El origen de esa API es `TRAZA_API_ORIGIN`. Publicar el paquete no activa `config.settings.production` ni apaga Mailpit en la máquina de desarrollo. El flujo de empaquetado, lanzado a mano, está en `.github/workflows/desktop.yml`.
