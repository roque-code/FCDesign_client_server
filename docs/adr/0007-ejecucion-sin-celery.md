# ADR 0007: Redis sin Celery, eventos por SSE

## Estado

Aceptado.

## Contexto

Celery está permitido solo si aporta algo real. La ejecución se pausa para leer datos y para depurar, y debe poder cancelarse.

## Decisión

No se usa Celery. Un worker propio consume órdenes en Redis y publica eventos. Django los reenvía al navegador por Server-Sent Events. Las órdenes de entrada y de depuración son POST. La máquina puede llamar al intérprete en proceso. Ese modo no existe cuando la configuración es de producción. El compose de desarrollo ya usa el worker y Redis, con `DEBUG` verdadero.

## Consecuencias

Hay menos infraestructura y la sesión interactiva tiene un dueño claro. Hay que operar el latido del runner, el bloqueo de una ejecución activa y el cierre del canal cuando el cliente se va. El sobre de los eventos no depende del transporte, así que un cambio futuro a WebSocket no toca el intérprete.

El worker y Redis están en el compose de desarrollo. Mailpit también, en otra red: el runner no envía correo. `config.settings.production` rechaza el modo en proceso, exige Redis y `EMAIL_HOST`, y no es el módulo que arranca el compose.
