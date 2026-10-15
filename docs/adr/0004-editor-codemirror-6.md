# ADR 0004: CodeMirror 6 como editor

## Estado

Aceptado.

## Contexto

El editor debe resaltar, numerar, completar, plegar, emparejar, marcar errores, atender atajos, cambiar de tema y de cuerpo, indentar y buscar. También debe poder usarse en una tableta.

## Decisión

CodeMirror 6. La gramática del resaltado consume la tabla de palabras que exporta `language_core`, no una lista copiada a mano en el cliente.

## Consecuencias

El paquete es más pequeño que Monaco y se comporta mejor con toque. El autocompletado y la búsqueda se arman con extensiones. Monaco queda descartado salvo que una prueba en tableta de la Fase 2 muestre un bloqueo concreto.
