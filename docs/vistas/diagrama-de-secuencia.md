# Diagrama de secuencia

Fecha de referencia: 2026-10-21. Dos secuencias del compose de desarrollo, más la traducción. En la máquina, Django ocupa el lugar del runner y el correo sale por la consola. En la ventana de escritorio, `local_host` ocupa el lugar del runner y la traducción no abre canal.

## Confirmar el correo

```mermaid
sequenceDiagram
    actor Persona
    participant Web as Django
    participant Buzon as Mailpit

    Persona->>Web: POST /api/v1/auth/register/
    Web->>Web: Crea la cuenta con email_confirmed en falso
    Web->>Buzon: SMTP, enlace con uid y token
    Web-->>Persona: pending_confirmation
    Persona->>Buzon: Abre el mensaje en el puerto 8025
    Persona->>Web: GET /api/v1/auth/confirm-email/open/?confirmar&token
    Web->>Web: Marca el correo, también si el enlace se abre en otro equipo
    Web-->>Persona: Entra, o conserva la sesión que ya había
```

Si entra antes de confirmar, `POST /api/v1/auth/login/` responde `email_unconfirmed` y no abre sesión. El tercer fallo del mismo correo responde `login_locked` durante 15 minutos. Si la cuenta ya tiene sesión en otro equipo, el ingreso responde `session_open`. A los 30 minutos sin uso, la siguiente petición responde `session_idle` y cierra esa sesión.

## Ejecutar un algoritmo

```mermaid
sequenceDiagram
    actor Persona
    participant Nginx
    participant Web as Django
    participant Bus as Redis
    participant Run as runner
    participant Core as language_core

    Persona->>Nginx: POST execute
    Nginx->>Web: La orden
    Web->>Web: Sesión, tamaño y límite
    Web->>Bus: Orden con el fuente
    Bus->>Run: Entrega
    Run->>Core: Léxico, sintaxis, semántica y recorrido
    Core-->>Run: Eventos
    Run->>Bus: Publica
    Bus-->>Web: Suscripción
    Web-->>Nginx: SSE
    Nginx-->>Persona: Línea, salida o pausa de Leer
    Persona->>Web: POST input o control
    Web->>Bus: Reanudar
```

Validar recorre léxico, sintaxis y semántica y se detiene ahí. No publica una ejecución ni abre el canal SSE.

## Traducir un algoritmo

```mermaid
sequenceDiagram
    actor Persona
    participant Web as Django o local_host
    participant Core as language_core

    Persona->>Web: POST translate
    Web->>Core: El mismo árbol que Validar
    Core-->>Web: Diagnósticos y, sin errores, siete programas
    Web-->>Persona: Pestañas, sin ejecución
```

Si el docente o el nivel apagaron la traducción, la respuesta es 403 y no hay programas. El repaso de un alumno usa las mismas órdenes de validar y ejecutar, sin crear una versión.

Si el navegador no está permitido y la petición no trae `X-Aulivana-FCDdesign-Client: desktop`, entrar y cambiar la cuenta siguen abiertos. El resto de `/api/v1/` responde 403 antes de llegar a la vista.

El laboratorio repite la segunda secuencia con `POST /api/v1/learning/run/` y `GET /api/v1/learning/runs/{id}/events/`. No inserta `executions.Execution`.

Volver al [índice](indice.md).
