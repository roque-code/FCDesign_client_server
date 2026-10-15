# Diagrama de procesos

Fecha de referencia: 2026-10-14. Son los procesos de negocio que el sistema sostiene, de punta a punta.

## Alta

```mermaid
flowchart TD
    inicio([Inicio]) --> datos[Escribe correo, contraseña y perfil]
    datos --> existe{El correo ya está confirmado?}
    existe -->|sí| rechazo[Avisa que ya está registrado]
    existe -->|no, pendiente| reenvia[Actualiza la contraseña y reenvía el enlace]
    existe -->|no existe| crea[Crea la cuenta y envía el enlace]
    crea --> buzon[La persona abre Mailpit]
    reenvia --> buzon
    buzon --> enlace{El enlace sigue vigente?}
    enlace -->|sí| activa[Marca el correo y abre la sesión]
    enlace -->|ya confirmado| entrar[Pide entrar con la contraseña]
    activa --> ejemplos[Quedan los ejemplos 1 a 13]
    ejemplos --> fin([Puede usar el editor])
```

En la máquina, sin `TRAZA_EMAIL_CONFIRMATION`, el alta entra al momento y el correo se imprime en la consola.

## Escribir y ejecutar

```mermaid
flowchart TD
    abrir([Algoritmo abierto]) --> texto[Edita el fuente]
    texto --> guarda[Autoguardado del texto vivo]
    texto --> val[Validar]
    val --> err{Hay error?}
    err -->|sí| texto
    err -->|no| modo{Ejecutar o depurar?}
    modo -->|ejecutar| run[Recorrido del AST]
    modo -->|depurar| paso[Pausa en paso, corte o Leer]
    paso --> orden[Entrada, continuar o detener]
    orden --> run
    run --> consola[Consola y eventos]
    consola --> figura[Diagrama sincronizado con la línea]
```

El editor muestra las palabras reservadas en el idioma de la cuenta. El texto que se guarda conserva la grafía que ya tenía.

## Laboratorio

```mermaid
flowchart TD
    lab([Entra al laboratorio]) --> tipo{Qué abre?}
    tipo -->|ruta| reto[Reto en orden]
    tipo -->|práctica| libre[Lienzo libre]
    tipo -->|docente| roster[Avance de sus comunidades]
    reto --> etapas[Comprender, razonar, construir, comprobar, explicar]
    etapas --> bloques[Bloques a AST]
    libre --> bloques
    bloques --> mismo[El mismo intérprete del editor]
    mismo --> puntos[Al terminar, suma los puntos una vez]
```

Volver al [índice](indice.md).
