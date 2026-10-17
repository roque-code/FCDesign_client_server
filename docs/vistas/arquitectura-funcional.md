# Arquitectura funcional

Fecha de referencia: 2026-10-17. Las funciones están agrupadas por lo que la persona hace, no por el archivo que las implementa.

```mermaid
flowchart TB
    subgraph acceso [Acceso]
        alta[Crear cuenta]
        confirmar[Confirmar correo]
        entrar[Entrar y salir]
        clave[Restablecer contraseña]
    end
    subgraph trabajo [Banco de trabajo]
        proy[Proyectos y algoritmos]
        editar[Editar y autoguardar]
        validar[Validar]
        traducir[Traducir a otro lenguaje]
        correr[Ejecutar y depurar]
        diagrama[Ver y exportar diagrama]
        compartir[Enlace de solo lectura]
    end
    subgraph aprendizaje [Aprendizaje]
        ruta[Ruta Fundamentos]
        banco[Banco y rutas propias]
        practica[Práctica libre]
        avance[Avance del docente]
    end
    subgraph grupo [Grupo]
        comunidad[Comunidades y traducción]
        repaso[Repaso del alumno]
        notas[Tablero y CSV de notas]
    end
    alta --> confirmar --> entrar --> proy
    proy --> editar --> validar --> correr
    editar --> traducir
    editar --> diagrama
    entrar --> ruta
    entrar --> comunidad
```

| Función | Resultado visible |
| --- | --- |
| Crear cuenta | Cuenta pendiente y mensaje en el buzón, o sesión inmediata en la máquina sin buzón |
| Confirmar correo | Sesión abierta y ejemplos disponibles |
| Validar | Diagnósticos con línea, columna y sugerencia. No crea una ejecución |
| Traducir | El mismo árbol, emitido en Python, JavaScript, TypeScript, Java, C, C++ y C#. No crea una ejecución |
| Actualizar | Vuelve a pedir proyectos, algoritmos, comunidades o el laboratorio. En el editor suelta el borrador local |
| Ejecutar | Consola con `Escribir` y con cada `Leer` aceptado |
| Depurar | Paso, entrar, salir, continuar, pausa, detener, reiniciar y puntos de interrupción |
| Diagrama | Figuras desde el AST, descarga SVG, PNG y PDF, e impresión |
| Laboratorio | Retos de clasificar, ordenar, construir y predecir, con el mismo intérprete |
| Comunidades | Lista de alumnos y docentes ya registrados, tope de 30 comunidades y 200 personas. La traducción nace habilitada y se puede apagar |
| Repaso | El docente abre los proyectos del alumno en solo lectura. No crea versiones |
| Notas | Tablero por alumno y CSV de una ruta. La nota promedia puntuaciones de 0 a 100 |
| Idioma | Textos, bloques, figuras y palabras reservadas en español o en inglés. El fuente guardado no se reescribe |

El cliente tiene tres pantallas: banco de trabajo, laboratorio y armar diagrama. Las tres comparten la sesión.

Volver al [índice](indice.md).
