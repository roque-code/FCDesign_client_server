# ADR 0009: Niveles de suscripción en la base

## Estado

Aceptado.

## Contexto

Alumno y docente tenían las mismas funciones. Hacía falta limitar proyectos, códigos y menús, poner un precio por nivel y poder agregar niveles sin reescribir la pantalla. El navegador y la aplicación de escritorio comparten la interfaz, y el uso completo debe poder quedar solo en la aplicación.

## Decisión

`billing.Plan` guarda el precio, la vigencia, el navegador, los topes y un mapa de funciones. `billing.Subscription` une la cuenta con un plan. Si `browser_allowed` de la suscripción no es nulo, esa cuenta manda sobre el nivel. El alta pública sigue en estudiante o docente y asigna el plan por defecto de ese tipo. El administrador se crea con `manage.py create_admin` y no tiene suscripción.

La cuenta (`GET /api/v1/auth/me/`) incluye el plan y las funciones. El cliente no hace otra petición para pintar los menús. El motor local conserva esa respuesta y aplica el mismo mapa al validar, traducir, ejecutar y depurar. Si el plan no permite el navegador, la API de la aplicación responde 403 salvo que la petición traiga `X-Aulivana-FCDdesign-Client: desktop`.

Una función nueva se declara en `apps/billing/catalog.py`. El valor de cada plan queda en la base.

## Consecuencias

El precio se guarda y no se cobra solo: el administrador asigna la fecha `paid_until`. Si esa fecha pasa, aplican las funciones del nivel por defecto del mismo tipo. Las pruebas usan `TRAZA_SIGNUP_PLAN=premium` para no cambiar el comportamiento que ya cubría la suite. El alta real usa `gratis`.
