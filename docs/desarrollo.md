# Desarrollo

Hay dos formas de trabajar. Las dos usan `DEBUG` verdadero. Ninguna carga `config.settings.production`. El dibujo de contenedores, redes y correo está en [arquitectura.md](arquitectura.md).

## 1. Contenedores

Es el modo descrito en [instalacion.md](instalacion.md). `TRAZA_RUNNER=redis`. Gunicorn no interpreta el pseudocódigo: publica la orden en Redis y el proceso `runner` ejecuta `language_core`. El laboratorio visual usa el mismo bus, así una sesión no depende del worker de Gunicorn que atendió el alta.

El código del servidor y del cliente está montado desde el árbol. Un cambio de Python se ve al reiniciar `web` (`docker compose restart web`). Vite recarga el cliente solo. Si cambia una dependencia, hay que reconstruir la imagen.

Variables que el compose ya define:

- `DJANGO_SETTINGS_MODULE=config.settings.development`
- `TRAZA_RUNNER=redis`
- `REDIS_URL` con el usuario `web`
- `DJANGO_CSRF_ORIGINS` incluye `http://127.0.0.1:18080` y `http://localhost:18080`. En la máquina, sin compose, el ajuste de desarrollo también confía en el puerto `5174` de la ventana de escritorio
- `EMAIL_HOST=mail` y `TRAZA_EMAIL_CONFIRMATION=1`: el alta envía la confirmación por SMTP y no abre sesión hasta el enlace
- `TRAZA_PUBLIC_ORIGIN` arma ese enlace; `TRAZA_MAIL_UI` es la dirección del buzón que ve quien crea la cuenta

La clave y las contraseñas de Redis son de desarrollo. No sirven para un servidor.

## 2. Máquina, sin Docker de la aplicación

PostgreSQL puede ser el contenedor `traza-pg` en `127.0.0.1:5433`. Sin `TRAZA_RUNNER`, el ajuste de desarrollo deja el ejecutor en proceso. Sirve para las pruebas y para el editor en `http://127.0.0.1:5173`.

```bash
python3 -m pip install -e ".[dev,server]"
cd server && python3 manage.py migrate && python3 manage.py runserver 127.0.0.1:8002
cd frontend && npm install && npm run dev
```

Ese proceso sí importa el intérprete. Los límites lógicos siguen activos. No es el aislamiento del contenedor `runner`.

## 3. Pruebas

```bash
python3 -m pytest
python3 -m pytest runner/tests -o addopts= -p no:cov
cd server && python3 -m pytest -q --tb=line
cd frontend && npm test && npm run lint
```

Las pruebas del servidor siguen en el ejecutor en proceso, y además cubren el bus con un Redis de mentira. No hace falta levantar el compose para la suite.

## 4. OpenAPI

Con el servidor en marcha, `GET /api/schema/`.

## 5. Aplicación de escritorio

Hay una tercera forma de abrir la interfaz: la ventana de `desktop/`. En depuración, Tauri levanta Vite en `http://127.0.0.1:5174` y arranca `python3 -m local_host`. Ese proceso atiende validar, traducir, ejecutar, depurar y el laboratorio. La cuenta y los proyectos siguen saliendo de Django. En depuración el proxy de la API queda apagado, así que Vite tiene que alcanzar el mismo origen que el navegador.

```bash
cd desktop && npm install && npm run dev
```

En un paquete publicado, las llamadas que empiezan por `/api/` pasan por `server_fetch` hacia `TRAZA_API_ORIGIN`. Si esa variable no está, el origen es `http://18.118.112.206:18080`. `TRAZA_UPDATE_URL`, si existe, apunta a un manifiesto `version` y `url` para descargar un paquete más nuevo. El detalle del lanzador está en [arquitectura.md](arquitectura.md).
