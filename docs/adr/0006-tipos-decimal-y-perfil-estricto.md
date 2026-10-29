# ADR 0006: Real decimal y perfil estricto por defecto

## Estado

Aceptado.

## Contexto

El tipo Real y las reglas de asignación definen el comportamiento que verá el estudiante en el primer programa. Hay que fijarlas antes de escribir el intérprete.

## Decisión

`Real` se guarda como `decimal.Decimal` creado desde el texto del literal. El perfil `strict` es el predeterminado: declaración obligatoria, punto y coma en sentencias simples, índices desde 1, asignación solo con `<-`, ensanche implícito únicamente de Entero a Real, sin globales y con error al leer un escalar no asignado.

`DIV` y `MOD` truncan hacia cero.

## Consecuencias

La salida de los decimales es predecible. `Sen`, `Cos` y `Tan` existen y reciben el ángulo en radianes. Un perfil flexible puede relajar banderas sin otra gramática. Cada algoritmo puede, además, guardar si el punto y coma es obligatorio y si la base de los índices es 1 o 0. Después, `=` también asigna y la igualdad se escribe `==`, en todos los perfiles.
