# ADR 0005: Lexer propio, descenso recursivo y Pratt

## Estado

Aceptado.

## Contexto

Hace falta una gramática formal y errores que digan «falta FinSi» en la línea del `Si`. También hace falta cambiar palabras clave según el perfil. Lark, ANTLR y PLY son alternativas razonables.

## Decisión

El lexer y el parser se escriben en Python. Las sentencias siguen la EBNF por descenso recursivo. Las expresiones usan Pratt según la tabla de precedencia de `docs/gramatica.md`. `grammar.py` guarda las palabras clave, los operadores y el texto normativo; no es un archivo generado por otra herramienta.

Se descarta ANTLR por el paso de generación y el estilo del código producido. Se descarta PLY por la calidad de los mensajes. Se descarta Lark como motor principal porque los errores de LALR hablan de tokens inesperados y los perfiles de sinónimos moverían la gramática fuera del lexer.

## Consecuencias

El control de los diagnósticos es directo. El riesgo es que el parser se aparte del EBNF: cada producción lleva pruebas positivas y negativas, y la precedencia tiene una tabla exhaustiva. Si una parte de la gramática se vuelve inestable, esa parte se puede sustituir más adelante sin cambiar los nodos del AST.
