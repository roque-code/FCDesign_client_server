# ADR 0008: Usuario propio, correo y sesión

## Estado

Aceptado.

## Contexto

La autenticación debe ser la de Django. El identificador del estudiante, en un aula, suele ser el correo. Sustituir el modelo de usuario después de migrar es una de las operaciones más frágiles de Django.

## Decisión

`accounts.User` hereda de `AbstractUser` y usa `email` como `USERNAME_FIELD`. La contraseña no se guarda aparte del hasher de Django. La API se autentica con la sesión y CSRF. Un objeto privado de otro usuario se responde con 404.

## Consecuencias

La primera migración de la Fase 2 ya incluye este usuario. El alta y el restablecimiento dependen de un backend de correo. En los contenedores el SMTP es Mailpit y la cuenta espera la confirmación del enlace. En la máquina, sin ese servicio, el correo sigue yendo a la consola y el alta entra al momento. No hay JWT que mantener.
