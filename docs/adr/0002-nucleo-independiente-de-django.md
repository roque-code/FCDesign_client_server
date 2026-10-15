# ADR 0002: El núcleo del lenguaje no es una aplicación Django

## Estado

Aceptado.

## Contexto

El encargo pide módulos `parser`, `semantic`, `interpreter` y `debugger`, y a la vez un paquete Python que se pruebe sin levantar el servidor.

## Decisión

Esos módulos viven en `language_core` e importan solo la biblioteca estándar. Django expone fachadas delgadas en `apps.language`, `apps.executions`, `apps.flowcharts` y `apps.learning`. El laboratorio construye los mismos nodos; no tiene otro intérprete.

## Consecuencias

Las pruebas del lenguaje no necesitan PostgreSQL. Un defecto del intérprete se puede reproducir con un script. Hace falta disciplina para no «ayudarse» importando modelos desde el núcleo: la revisión de la Fase 1 debe mirar los imports.
