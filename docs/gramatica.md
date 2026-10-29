# Gramática del pseudolenguaje

Estado: implementada. El lexer, el parser, el análisis y el intérprete cubren esta gramática, incluidos arreglos, `Segun`, funciones, procedimientos y la biblioteca estándar. El lugar de este lenguaje en el sistema está en [arquitectura.md](arquitectura.md).

## 1. Convenciones léxicas

- Codificación UTF-8.
- Espacios, tabuladores y saltos de línea separan tokens y no son significativos, salvo dentro de literales y para numerar líneas.
- Las palabras clave se comparan con `casefold` y sin marcas diacríticas. `Algoritmo`, `ALGORITMO` y `Álgoritmo` son la misma palabra clave. El lexema original se guarda para mostrarlo.
- Cada palabra reservada tiene, además, una grafía en inglés. `Algorithm` es `Algoritmo` y `If` es `Si`. La tabla está en la sección 2. El canónico del token sigue siendo el español. El parser no ve la grafía inglesa.
- Los identificadores sí distinguen acentos y mayúsculas. `año` y `ano` son variables distintas.
- Un identificador no puede ser una palabra clave.
- Comentario de línea: `//` hasta el final de la línea.
- Comentario de bloque: `/*` … `*/`, sin anidación. Si falta el cierre, el error apunta al `/*`.
- No hay punto y coma implícito por salto de línea. El salto no termina una sentencia.

```ebnf
letra        = categoría Unicode L ;
digito       = categoría Unicode Nd ;
identificador = ( letra | "_" ) , { letra | digito | "_" } ;

entero       = digito , { digito } ;
real         = digito , { digito } , "." , digito , { digito } ;

cadena       = '"' , { carácter de cadena } , '"' ;
caracter     = "'" , un carácter , "'" ;

comentario   = "//" , { cualquier carácter salvo salto de línea }
             | "/*" , { cualquier carácter } , "*/" ;
```

Cadenas: `\\`, `\"`, `\n`, `\t`. Un salto de línea real dentro de la cadena es un error. El carácter usa comilla simple y representa un solo carácter Unicode. No hay literales crudos ni interpolación.

`Verdadero` y `Falso` son literales lógicos, no identificadores.

## 2. Palabras reservadas

Reconocidas sin distinguir mayúsculas ni acentos:

```text
Algoritmo  FinAlgoritmo
Funcion    FinFuncion
SubProceso FinSubProceso
Definir    Como       Dimension
Por        Valor      Referencia
Leer       Escribir
Si         Entonces   Sino       FinSi
Segun      Hacer      De         Otro       Modo       FinSegun
Mientras   FinMientras
Repetir    Hasta      Que
Para       Hasta      Con        Paso       FinPara
Entero     Real       Logico     Caracter   Cadena
Verdadero  Falso
Y          O          NO
DIV        MOD
```

`Hasta` se usa en `Para` y en `Repetir`. El contexto lo resuelve el parser, no el lexer: el lexer emite un identificador de palabra clave y el parser exige la secuencia.

El completado del editor muestra la forma del idioma de la cuenta y sigue listando la otra. Al escribir el comienzo de una instrucción, ofrece su estructura: la palabra reservada queda escrita y el hueco, marcado. Enter o Tab aceptan la fila. Tab pasa al hueco siguiente. La grafía del otro idioma abre la misma estructura a partir de la segunda letra. Si el punto y coma es opcional, la plantilla no lo agrega. En español llevan tilde `Función`, `FinFunción`, `Según` y `Lógico`. `Caracter` y `FinSegun` se muestran sin tilde. Escribirlas con o sin tilde las reconoce igual.

La grafía inglesa no es un alias del perfil: el lexer la acepta siempre, en estricto y en flexible. La tabla vive en `language_core/dialect.py` y se repite en `frontend/src/dialect.ts`. Un perfil puede añadir otros sinónimos (`Procedimiento` por `SubProceso`, `Entera` por `Entero`) mediante `keyword_aliases`, sin duplicar reglas.

| Canónico | Se muestra en español | Se muestra en inglés |
| --- | --- | --- |
| algoritmo | Algoritmo | Algorithm |
| finalgoritmo | FinAlgoritmo | EndAlgorithm |
| funcion | Función | Function |
| finfuncion | FinFunción | EndFunction |
| subproceso | SubProceso | SubProcedure |
| finsubproceso | FinSubProceso | EndSubProcedure |
| definir | Definir | Declare |
| como | Como | As |
| dimension | Dimension | Dimension |
| por | Por | By |
| valor | Valor | Value |
| referencia | Referencia | Reference |
| leer | Leer | Read |
| escribir | Escribir | Write |
| sin | Sin | Without |
| saltar | Saltar | Newline |
| borrar | Borrar | Clear |
| pantalla | Pantalla | Screen |
| esperar | Esperar | Wait |
| segundos | Segundos | Seconds |
| si | Si | If |
| entonces | Entonces | Then |
| sino | Sino | Else |
| finsi | FinSi | EndIf |
| segun | Según | Switch |
| hacer | Hacer | Do |
| de | De | In |
| otro | Otro | Other |
| modo | Modo | Case |
| finsegun | FinSegun | EndSwitch |
| mientras | Mientras | While |
| finmientras | FinMientras | EndWhile |
| repetir | Repetir | Repeat |
| hasta | Hasta | Until |
| que | Que | That |
| para | Para | For |
| con | Con | With |
| paso | Paso | Step |
| finpara | FinPara | EndFor |
| entero | Entero | Integer |
| real | Real | Real |
| logico | Lógico | Boolean |
| caracter | Caracter | Character |
| cadena | Cadena | String |
| verdadero | Verdadero | True |
| falso | Falso | False |
| y | Y | And |
| o | O | Or |
| no | NO | Not |
| div | DIV | Div |
| mod | MOD | Mod |

`Dimension` y `Real` se escriben igual en las dos grafías, así que no cuentan como alias. `De Otro Modo` se lee `In Other Case` porque cada palabra se traduce sola. `Hasta Que` se lee `Until That`. `Sin Saltar` se lee `Without Newline`. `Borrar Pantalla` se lee `Clear Screen`. `Por Referencia` se lee `By Reference`.

Cambiar el idioma de la cuenta no recorre ni reescribe el fuente guardado. El editor lo muestra en la grafía elegida. Si el texto guardado está en la otra, al guardar devuelve las palabras a esa grafía y conserva las letras de las que no se editaron. Si el texto ya coincide con el idioma, o el algoritmo es nuevo, se guarda lo escrito. Un algoritmo nuevo en inglés empieza con `Algorithm` y `EndAlgorithm`. La EBNF de este documento usa el canónico español. Un fuente en inglés es el mismo programa.

Los nombres de la biblioteca no están en esta tabla. El idioma de la cuenta no los cambia: `Raíz` y `Longitud` siguen en español. Los identificadores, las cadenas y los comentarios tampoco cambian con el idioma. Los mensajes de diagnóstico siguen en español. `Escribir` de un lógico imprime `Verdadero` o `Falso`. `Leer` de un lógico acepta las dos grafías. Otra cosa es el botón **Traducir**: ese emite el algoritmo en otro lenguaje de programación y sí escribe la biblioteca en la forma de ese lenguaje. La sección 12 lo detalla.

## 3. Gramática

```ebnf
fuente = { subrutina | algoritmo } ;

(* Validación posterior: exactamente un Algoritmo.
   Las subrutinas pueden precederlo o seguirlo. No se anidan. *)

algoritmo = "Algoritmo" , identificador , bloque , "FinAlgoritmo" ;

subrutina = funcion | procedimiento ;

funcion = "Funcion" , identificador , ( "<-" | "=" ) , identificador ,
          "(" , [ parametros ] , ")" , bloque , "FinFuncion" ;

procedimiento = "SubProceso" , identificador ,
                "(" , [ parametros ] , ")" , bloque , "FinSubProceso" ;

parametros = parametro , { "," , parametro } ;
parametro  = identificador , [ "Por" , ( "Valor" | "Referencia" ) ] ;

bloque = { sentencia } ;

sentencia = sentencia_simple , [ ";" ]
          | sentencia_compuesta ;

sentencia_simple = definir
                 | dimension
                 | asignacion
                 | leer
                 | escribir
                 | borrar_pantalla
                 | esperar
                 | llamada ;

sentencia_compuesta = si | segun | mientras | repetir | para ;

definir   = "Definir" , lista_ids , "Como" , tipo ;
lista_ids = identificador , { "," , identificador } ;
tipo      = "Entero" | "Real" | "Logico" | "Caracter" | "Cadena" ;

dimension = "Dimension" , decl_dim , { "," , decl_dim } ;
decl_dim  = identificador , "[" , expresion , { "," , expresion } , "]" ,
            [ "Como" , tipo ] ;

asignacion = destino , ( "<-" | "=" ) , expresion ;
destino    = identificador , [ "[" , expresion , { "," , expresion } , "]" ] ;

leer     = "Leer" , destino , { "," , destino } ;
escribir = "Escribir" , expresion , { "," , expresion } , [ "Sin" , "Saltar" ] ;
borrar_pantalla = "Borrar" , "Pantalla" ;
esperar = "Esperar" , expresion , "Segundos" ;
llamada  = identificador , "(" , [ argumentos ] , ")" ;
argumentos = expresion , { "," , expresion } ;

si = "Si" , expresion , "Entonces" , bloque ,
     [ "Sino" , bloque ] , "FinSi" ;

segun = "Segun" , expresion , "Hacer" , { caso } ,
        [ "De" , "Otro" , "Modo" , ":" , bloque ] ,
        "FinSegun" ;
caso  = expresion , { "," , expresion } , ":" , bloque ;

mientras = "Mientras" , expresion , "Hacer" , bloque , "FinMientras" ;
repetir  = "Repetir" , bloque , "Hasta" , "Que" , expresion ;
para     = "Para" , identificador , ( "<-" | "=" ) , expresion , "Hasta" , expresion ,
           [ "Con" , "Paso" , expresion ] , "Hacer" , bloque , "FinPara" ;

expresion  = disyuncion ;
disyuncion = conjuncion , { "O" , conjuncion } ;
conjuncion = negacion , { "Y" , negacion } ;
negacion   = { "NO" } , comparacion ;
comparacion = suma , [ relacional , suma ] ;
relacional = "==" | "<>" | "!=" | "<" | "<=" | ">" | ">=" ;
suma       = termino , { ( "+" | "-" ) , termino } ;
termino    = unario_o_potencia , { ( "*" | "/" | "DIV" | "MOD" | "%" ) , unario_o_potencia } ;
primario   = literal | destino | llamada | "(" , expresion , ")" ;
literal    = entero | real | cadena | caracter | "Verdadero" | "Falso" ;
```

La potencia y el menos unario no quedan bien expresados en EBNF pura porque la potencia liga más que el signo. La tabla de precedencia de la sección 5 es la norma. El parser de expresiones es Pratt e implementa esa tabla. `unario_o_potencia` en la EBNF indica el lugar; no se implementa como gramática ingenua de descenso que invertiría `-2^2`.

Un `Sino` seguido de `Si` es un condicional anidado. No hay palabra clave `SinoSi`.

## 4. Decisiones sintácticas

- Hay exactamente un `Algoritmo`. Cero o más de uno es error semántico de programa, con el tramo del encabezado sobrante o del fin de archivo.
- Las subrutinas están al nivel del archivo, nunca dentro de `Algoritmo` ni de otra subrutina.
- El nombre que está a la izquierda de `<-` o de `=` en `Funcion resultado <- Sumar(a, b)` es la variable de retorno. `Sumar` es el nombre invocable. `Funcion resultado = Sumar(a, b)` es la misma cabecera.
- Si el modo del parámetro se omite, es `Por Valor`.
- `Segun` no hace caída de un caso al siguiente. `2, 3:` es un solo caso con dos etiquetas.
- `De Otro Modo` aparece como máximo una vez y al final.
- Las etiquetas de `Segun` deben ser literales. Un número con signo cuenta: `-1` y `-2.5` se comparan como esos valores. Una cuenta, como `1 + 0`, sigue siendo error. El parser acepta la expresión para poder decir «la etiqueta debe ser un literal».
- El punto y coma es opcional para el parser. En el perfil estricto, y en un algoritmo que no haya cambiado la opción, su ausencia en una sentencia simple es el error `E0210`. Un algoritmo puede guardar `require_semicolons` en falso: el punto y coma sigue siendo válido y deja de ser obligatorio.
- `;;` y una sentencia vacía son `E0211`.
- `<-` y `=` asignan. Valen en una sentencia, en `Para` y en la cabecera de `Funcion`. Dentro de una expresión son `E0203`: hay que comparar con `==`, o sacar la asignación de la condición.
- `==` compara. Si se escribe donde iría una asignación, el error `E0203` pide cambiarlo por `<-` o por `=`.
- El perfil no cambia estos signos. `allow_equals_assignment` sigue en el perfil guardado y el parser no lo consulta. `learning.0019` cambió por `==` cada `=` suelto de los algoritmos y retos ya guardados. Así la comparación anterior sigue comparando. No altera `<-`, `<=`, `>=`, `!=`, `<>` ni un `==` que ya estuviera escrito.

## 5. Precedencia y asociatividad

De mayor a menor ligadura:

| Nivel | Operadores | Asociación | Resultado |
| --- | --- | --- | --- |
| 1 | llamada, indexación, paréntesis | — | el del operando |
| 2 | `^` | derecha | ver reglas de tipos |
| 3 | `+` y `-` unarios | — | el del operando |
| 4 | `*`, `/`, `DIV`, `MOD`, `%` | izquierda | `/` es Real; `DIV` y `MOD` son Entero |
| 5 | `+`, `-` binarios | izquierda | numérico, o error en estricto si hay cadenas |
| 6 | `==`, `<>`, `!=`, `<`, `<=`, `>`, `>=` | no encadenan | Lógico |
| 7 | `NO` | — | Lógico |
| 8 | `Y` | izquierda | Lógico |
| 9 | `O` | izquierda | Lógico |

Consecuencias:

- `-2^2` se lee `-(2^2)` y vale `-4`.
- `2^3^2` se lee `2^(3^2)` y vale `512`.
- `a < b < c` es error de sintaxis. Hay que escribir `a < b Y b < c`.
- `NO a Y b` es `(NO a) Y b`.
- `a O b Y c` es `a O (b Y c)`.

`!=` es sinónimo de `<>`. `%` es sinónimo de `MOD`.

El botón **Operadores** del editor abre asignación, aritmética, comparación, lógica y paréntesis. En asignación lista `<-` y `=`. En comparación, la igualdad es `==`. El orden de una expresión sigue esta tabla: `^`, luego `* / DIV MOD`, luego `+` y `-`, luego las comparaciones, y al final `NO`, `Y` y `O`. `<-` y `=` no van dentro de una expresión. Con el idioma en inglés, el panel escribe `Div`, `Mod`, `Not`, `And` y `Or`. Los signos no cambian.

## 6. Tipos

| Tipo | Literal | Valor inicial de una celda de arreglo |
| --- | --- | --- |
| Entero | `20` | `0` |
| Real | `9.5` | `0.0` |
| Logico | `Verdadero`, `Falso` | `Falso` |
| Caracter | `'A'` | `' '` |
| Cadena | `"Ana"` | `""` |

El Real se representa con `decimal.Decimal`, construido desde el texto del literal. `9.5` es exactamente 9.5. La división `/` entre números produce Real. No hay tipo complejo.

En el perfil estricto, un escalar no tiene valor hasta que se asigna. Leerlo antes es error de ejecución `E0401`, aunque la celda de un arreglo sí nace con el valor de la tabla. Una celda `Caracter` nace con un espacio.

### Caracter

`Caracter` es un solo símbolo Unicode, no una cadena corta.

- El literal se escribe entre comillas simples: `'A'`. `' '` es un carácter válido, el espacio.
- `''` y `'AB'` son `E0106`. Una comilla simple sin cerrar también es `E0106`.
- `"Ana"` es `Cadena`. `" "` es una cadena de longitud 1 y se puede asignar a un `Caracter` por esa longitud.
- Un `Caracter` se puede asignar a una `Cadena`.
- Comparar un `Caracter` con una `Cadena` es `E0306`.
- `Leer` hacia un `Caracter` exige exactamente un símbolo y no recorta espacios. Un texto más largo o vacío es `E0406` y se vuelve a pedir.
- La palabra que muestra el editor en español es `Caracter`, sin tilde, para que el completado coincida al escribir `caracter`. En inglés es `Character`. Con tilde también se acepta, porque las palabras clave no distinguen acentos.

### Conversiones

| Origen | Destino | Estricto |
| --- | --- | --- |
| Entero | Real | Permitida al asignar y al operar |
| Real | Entero | Error. Sugerir `Trunc` o `Redon` |
| Cadena de longitud 1 | Caracter | Permitida |
| Caracter | Cadena | Permitida |
| Cualquier tipo | Cadena por `+` | Error. Usar `ConvertirATexto` o `Concatenar` |
| Número | Logico | Error. No hay verdad implícita |
| Cadena numérica | Número | Solo con `ConvertirANumero` |

### Operaciones

- Aritmética: Entero y Real. Si uno es Real, el otro se ensancha.
- `DIV` y `MOD`: ambos operandos Entero. El divisor cero es `E0402`.
- División `/` con divisor cero: `E0402`.
- `DIV` y `MOD` truncan hacia cero. `-7 DIV 2` es `-3`. `-7 MOD 2` es `-1`. Se cumple `a == (a DIV b) * b + (a MOD b)`.
- `^`: si la base y el exponente son Entero y el exponente es mayor o igual que cero, el resultado es Entero. Si el exponente es negativo, el resultado es Real. `0^0` es `E0403`. Una base negativa elevada a un Real no entero es `E0403`.
- Comparar números entre sí está permitido. Comparar cadenas es lexicográfico por punto de código. Comparar caracteres es por punto de código. Un Lógico solo admite `==` y `<>` frente a otro Lógico.
- Comparar Real con `==` emite la advertencia `W0501`: la igualdad decimal puede fallar tras una división. No se bloquea la ejecución.
- `Y`, `O` y `NO` exigen Lógico. Se evalúan en cortocircuito: el operando que no hace falta no se ejecuta ni puede fallar.

### Arreglos

```text
Dimension matriz[3, 3] Como Entero;
```

`[3, 3]` son las longitudes, no los índices máximos escritos a la manera de un rango. Con base 1, los índices válidos son `1..3` en cada dimensión. Con base 0, son `0..2`. La base es del perfil y, si el algoritmo la cambia, de `index_base` en sus opciones de lenguaje. No es de cada arreglo. El valor permitido es `1` o `0`. El predeterminado del perfil estricto es `1`.

También vale declarar antes el tipo:

```text
Definir matriz Como Entero;
Dimension matriz[3, 3];
```

En estricto, hace falta el tipo por una de las dos vías. El máximo de dimensiones es 4. El número de celdas se comprueba al crear el arreglo y cuenta para el límite de memoria lógica.

Un índice fuera de rango es `E0404` e indica el índice recibido y el intervalo válido.

Los escalares se pasan `Por Valor` si no se dice otra cosa. Los arreglos se pasan `Por Referencia` si no se dice otra cosa, porque el estudiante los modifica en procedimientos de recorrido. `Por Valor` en un arreglo copia las celdas y esa copia cuenta para el límite.

### Ciclo Para

```text
Para i <- inicio Hasta fin Con Paso paso Hacer
```

- `inicio`, `fin` y `paso` se evalúan una vez, al entrar.
- Si se omite el paso, vale `1` cuando `inicio <= fin`. Si `inicio > fin` y se omite el paso, el paso es `-1`. Así `Para i <- 10 Hasta 1 Hacer` recorre hacia abajo.
- Paso `0`, aunque sea resultado de una expresión, es `E0405`.
- Si el paso aleja `i` del límite, el cuerpo no se ejecuta y, con advertencias de principiante, se emite `W0502`.
- En estricto, `i` es Entero. Un Real como variable de control es `E0308`.
- El cuerpo puede asignar a `i`. El incremento del paso ocurre al cerrar cada iteración, después del cuerpo.

### Mientras, Repetir y Si

- `Mientras` comprueba antes del cuerpo. Cero vueltas es válido.
- `Repetir` ejecuta el cuerpo y luego comprueba. Al menos una vuelta.
- La condición es Lógico. Un número no sirve como condición.
- No existe `Salir` ni `Continuar` en esta versión. Un ciclo se termina haciendo falsa su condición, o agotando el `Para`.

## 7. Ámbito

El ámbito es el del algoritmo o el de la subrutina, no el del bloque. Una variable definida dentro de un `Si` existe en toda la subrutina. Definirla dos veces en ese ámbito es `E0302`.

Las variables del `Algoritmo` no se ven dentro de una función o un procedimiento. No hay palabra `Global` en esta versión. Los datos entran y salen por parámetros y por el valor de retorno.

La variable de retorno de una función se declara con `Definir` y el tipo. Al llegar a `FinFuncion` tiene que haber recibido valor por todos los caminos; si no, `E0309`.

La recursión está permitida hasta el límite de profundidad del perfil.

## 8. Entrada y salida

`Escribir` convierte cada expresión a texto canónico y las concatena sin separador añadido. Después baja de línea, salvo que la sentencia termine en `Sin Saltar`. Los espacios van dentro de los literales:

```text
Escribir nombre, " es mayor de edad";
```

Entero sin separadores de miles. Real sin ceros de cola innecesarios y sin exponente. Lógico como `Verdadero` o `Falso`.

`Borrar Pantalla` vacía la salida que se ve. Lo escrito antes deja de mostrarse.

`Esperar` recibe un Entero o un Real y detiene la ejecución esa cantidad de segundos, entre 0 y 60. El tiempo de la espera no cuenta para el límite del ciclo.

`Leer` pide un valor por cada destino, en orden. Suspende el intérprete. El conductor muestra la petición, espera el texto y solo entonces reanuda.

| Destino | Texto aceptado |
| --- | --- |
| Entero | un entero en base 10, espacios alrededor permitidos |
| Real | un decimal con punto, sin coma de miles |
| Logico | `Verdadero` o `Falso`, y también `True` o `False`, sin distinguir mayúsculas ni acentos |
| Caracter | un solo carácter |
| Cadena | el resto de la línea, sin el salto final |

Un texto incompatible es `E0406`. No se asigna, no aparece en la consola y la petición se repite. El programa no aborta en el primer intento fallido; aborta si el conductor cancela.

Cuando el texto sí se acepta, la consola lo muestra en su propia línea, en el momento en que se guardó, junto con lo que escriba `Escribir`. Ese eco cuenta para el tope de caracteres de salida (`E0414`).

## 9. Biblioteca estándar

Cada función registrada tiene nombre canónico, firma, tipo de retorno, documentación, ejemplo y una implementación que solo usa valores del intérprete.

El editor y el menú **Funciones** muestran estos nombres, con tilde donde corresponde. El idioma de la cuenta traduce la explicación, no el nombre. Escribirlos sin tilde también vale, porque el nombre se compara como palabra clave.

Matemáticas: `Abs`, `Raíz`, `Potencia`, `Redon`, `Trunc`, `Sen`, `Cos`, `Tan`, `Ln`, `Exp`, `Aleatorio`.

Cadenas: `Longitud`, `Subcadena`, `Concatenar`, `Mayúsculas`, `Minúsculas`, `ConvertirANumero`, `ConvertirATexto`.

`Aleatorio` sin argumentos devuelve un Real en `[0, 1)`. Con dos enteros `a` y `b` devuelve un Entero en el intervalo cerrado. El generador es injectable para las pruebas. No usa el aleatorio global del proceso sin semilla controlada.

Los ángulos de `Sen`, `Cos` y `Tan` están en radianes. `Raíz` de un negativo es `E0403`. `Ln` de un no positivo es `E0403`.

Los nombres quedan reservados para que una variable no se llame `Abs`. El menú **Funciones** lista cada una con su forma de llamada.

## 10. Diagnósticos previstos

Forma lógica de un diagnóstico:

- severidad: `error`, `warning` o `info`;
- código estable, por ejemplo `E0301`;
- mensaje en español, dirigido al estudiante;
- línea y columna de inicio y de fin;
- fragmento de la línea;
- sugerencia opcional.

Familias:

| Prefijo | Familia | Ejemplos |
| --- | --- | --- |
| E01 | Léxico | carácter extraño, cadena sin cerrar, comentario sin cerrar |
| E02 | Sintaxis | falta `FinSi`, falta `FinMientras`, paréntesis o corchete abierto, `==` usado para asignar, `=` o `<-` dentro de una expresión |
| E03 | Semántica | no declarada, declarada dos veces, tipo incompatible, función inexistente, aridad incorrecta, retorno ausente, código inalcanzable |
| E04 | Ejecución | escalar sin valor, división entre cero, potencia inválida, índice fuera de rango, paso cero, entrada incompatible, límite de instrucciones, límite de profundidad |
| W05 | Advertencias | igualdad de reales, `Para` que no entra, variable asignada y no usada |

El límite de instrucciones menciona el encabezado del ciclo más interno cuando el corte ocurre dentro de un ciclo, para que el mensaje de «posible ciclo infinito» tenga un lugar concreto. No se promete detectar todos los ciclos infinitos en estático.

## 11. Qué se ejecuta

Se lexica, parsea, analiza y ejecuta todo lo descrito arriba: el algoritmo, los cinco tipos, las expresiones y las llamadas, `Leer` y `Escribir`, `Si`, `Segun`, `Mientras`, `Repetir`, `Para`, `Dimension`, funciones y procedimientos. No hay un diagnóstico de «construcción todavía no ejecutable».

## 12. Traducción a otros lenguajes

Traducir no es una segunda gramática ni un segundo intérprete. `language_core/translate.py` recorre el mismo AST que Validar y emite un programa. No lo ejecuta y no modifica el fuente. Si hay diagnósticos de severidad `error`, el resultado trae esos diagnósticos y ninguna traducción. Las advertencias no lo impiden.

Los destinos son Python, JavaScript, TypeScript, Java, C, C++ y C#. En el navegador la orden es `POST /api/v1/algorithms/{id}/translate/`. En la aplicación de escritorio es `POST /local/v1/translate`, contra el mismo núcleo. El botón **Traducir** del banco de trabajo muestra una pestaña por lenguaje, permite ampliar el recuadro y copiar el texto. Un docente puede apagar esa acción para una comunidad o para un alumno. Si está apagada, el servidor responde 403 y no emite código. El nivel de la cuenta es el techo: si el plan no incluye traducir, la comunidad no lo enciende. Pegar es del editor, no de esta gramática: se puede escribir y, si el docente o el nivel lo apagaron, no se pega texto.

Se conservan los comentarios, la base de índices del algoritmo, `DIV` y `MOD` hacia cero, los parámetros por referencia y el resultado de la biblioteca.

`Segun` sale como `match` en Python. En los demás lenguajes sale como `switch` cuando el tipo del selector cabe en esa construcción: un real no cabe en Java, C, C++ ni C#; una cadena no cabe en C ni C++; un lógico no cabe en Java. En esos casos sale una cadena de `Si`. Cada caso termina para no continuar en el siguiente. `De Otro Modo` es el caso por defecto.

`Mientras` sale como `while`. `Repetir` sale como `do`/`while` con la condición negada, porque `Hasta Que` para cuando la condición se cumple. Python no tiene `do`/`while`: usa `while True` y un `break`. `Para` incluye los dos extremos. El paso, si se conoce, elige `<=` o `>=`. Si el paso no es constante, la prueba mira el signo en cada vuelta. En Python el extremo de `range` se desplaza para que el último valor entre.
