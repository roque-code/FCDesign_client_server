# Diagrama de secuencia

Fecha de referencia: 2026-10-14. Dos secuencias del compose de desarrollo. En la máquina, Django ocupa el lugar del runner y el correo sale por la consola.

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
    Persona->>Web: POST /api/v1/auth/confirm-email/
    Web->>Web: Marca el correo y abre la sesión
    Web-->>Persona: Cuenta y ejemplos
```

Si entra antes de confirmar, `POST /api/v1/auth/login/` responde `email_unconfirmed` y no abre sesión.

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

El laboratorio repite la segunda secuencia con `POST /api/v1/learning/run/` y `GET /api/v1/learning/runs/{id}/events/`. No inserta `executions.Execution`.

Volver al [índice](indice.md).
