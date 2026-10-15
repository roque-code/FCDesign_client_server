# ADR 0003: Cliente React y TypeScript junto a la API Django

## Estado

Aceptado.

## Contexto

Hay que elegir entre plantillas de Django con JavaScript, o Django como API y un cliente separado. La autenticación pedida es por sesión, no por token.

## Decisión

El banco de trabajo es una aplicación React con TypeScript, construida con Vite y servida en el mismo origen. Django conserva la sesión, el CSRF y la API REST. La cuenta, el laboratorio y armar diagrama también quedaron en ese cliente.

## Consecuencias

Ventaja: el estado de editor, consola, depurador y diagrama tiene un lugar natural, y React Flow encaja. Desventaja: CI y la imagen de producción compilan Node. La cookie de sesión solo es válida porque el origen es el mismo; un dominio separado para el cliente quedaría fuera de esta decisión.
