/** Funciones, clases y métodos que el editor de cada lenguaje sugiere. Solo los de uso escolar. */

import type { ForeignLanguage } from "./keywords"

export type EntryKind = "function" | "method" | "class" | "property" | "constant" | "namespace"

export type Entry = {
  name: string
  sig: string
  doc: string
  kind: EntryKind
  /** Tabla de miembros del valor que devuelve. Sirve para `a.b().` */
  returns?: string
}

export type Catalog = {
  globals: Entry[]
  members: Record<string, Entry[]>
  /** Expresión escrita antes del punto que ya tiene tabla, como `System.out` o `Math`. */
  receivers: Record<string, string>
  /** Nombre del tipo declarado a la tabla que lo describe. */
  aliases: Record<string, string>
}

function fn(name: string, sig: string, doc: string, returns?: string): Entry {
  return { name, sig, doc, kind: "function", returns }
}

function me(name: string, sig: string, doc: string, returns?: string): Entry {
  return { name, sig, doc, kind: "method", returns }
}

function cl(name: string, sig: string, doc: string, returns?: string): Entry {
  return { name, sig, doc, kind: "class", returns }
}

function pr(name: string, sig: string, doc: string, returns?: string): Entry {
  return { name, sig, doc, kind: "property", returns }
}

function co(name: string, sig: string, doc: string): Entry {
  return { name, sig, doc, kind: "constant" }
}

function ns(name: string, sig: string, doc: string): Entry {
  return { name, sig, doc, kind: "namespace" }
}

const PYTHON: Catalog = {
  globals: [
    fn("print", "print(*valores, sep=\" \", end=\"\\n\")", "Escribe los valores en la consola, separados por sep, y termina con end."),
    fn("input", "input(mensaje=\"\") -> str", "Lee una línea que escribe el usuario. Siempre devuelve texto.", "str"),
    fn("int", "int(valor) -> int", "Convierte texto o un real a entero. int(\"12\") da 12."),
    fn("float", "float(valor) -> float", "Convierte texto o un entero a real. float(\"3.5\") da 3.5."),
    fn("str", "str(valor) -> str", "Convierte cualquier valor a texto.", "str"),
    fn("bool", "bool(valor) -> bool", "Convierte a verdadero o falso. 0, \"\" y [] dan False."),
    fn("len", "len(secuencia) -> int", "Cantidad de elementos de un texto, lista, tupla o diccionario."),
    fn("range", "range(inicio, fin, paso)", "Números desde inicio hasta fin sin incluirlo. Se usa en for i in range(n)."),
    fn("list", "list(iterable) -> list", "Crea una lista. list(\"abc\") da ['a', 'b', 'c'].", "list"),
    fn("dict", "dict() -> dict", "Crea un diccionario de clave y valor.", "dict"),
    fn("set", "set(iterable) -> set", "Crea un conjunto sin elementos repetidos.", "set"),
    fn("tuple", "tuple(iterable) -> tuple", "Crea una tupla, una lista que no se puede cambiar."),
    fn("abs", "abs(x)", "Valor absoluto de x."),
    fn("round", "round(x, decimales=0)", "Redondea x a la cantidad de decimales indicada."),
    fn("min", "min(a, b, ...) | min(iterable)", "El menor de los valores."),
    fn("max", "max(a, b, ...) | max(iterable)", "El mayor de los valores."),
    fn("sum", "sum(iterable, inicio=0)", "Suma todos los elementos."),
    fn("sorted", "sorted(iterable, reverse=False) -> list", "Devuelve una lista nueva ordenada.", "list"),
    fn("reversed", "reversed(secuencia)", "Recorre la secuencia al revés."),
    fn("enumerate", "enumerate(iterable, inicio=0)", "Da pares (posición, elemento). for i, x in enumerate(lista)."),
    fn("zip", "zip(a, b, ...)", "Junta varias secuencias elemento por elemento."),
    fn("map", "map(funcion, iterable)", "Aplica la función a cada elemento."),
    fn("filter", "filter(funcion, iterable)", "Conserva los elementos para los que la función da True."),
    fn("type", "type(valor)", "Tipo del valor."),
    fn("isinstance", "isinstance(valor, tipo) -> bool", "True si el valor es de ese tipo."),
    fn("chr", "chr(codigo) -> str", "Carácter de un código Unicode. chr(65) da 'A'.", "str"),
    fn("ord", "ord(caracter) -> int", "Código Unicode de un carácter. ord('A') da 65."),
    fn("pow", "pow(base, exponente)", "Potencia. Igual que base ** exponente."),
    fn("divmod", "divmod(a, b)", "Cociente y residuo juntos: (a // b, a % b)."),
    fn("any", "any(iterable) -> bool", "True si al menos un elemento es verdadero."),
    fn("all", "all(iterable) -> bool", "True si todos los elementos son verdaderos."),
    ns("math", "import math", "Funciones matemáticas: sqrt, pi, floor, ceil…"),
    ns("random", "import random", "Números al azar: randint, choice, shuffle…"),
  ],
  members: {
    str: [
      me("upper", "upper() -> str", "Copia en mayúsculas.", "str"),
      me("lower", "lower() -> str", "Copia en minúsculas.", "str"),
      me("strip", "strip(caracteres=None) -> str", "Quita espacios al inicio y al final.", "str"),
      me("lstrip", "lstrip() -> str", "Quita espacios al inicio.", "str"),
      me("rstrip", "rstrip() -> str", "Quita espacios al final.", "str"),
      me("split", "split(separador=None) -> list", "Corta el texto en una lista. Sin separador corta en los espacios.", "list"),
      me("join", "join(iterable) -> str", "Une los textos de la lista usando este texto como separador.", "str"),
      me("replace", "replace(viejo, nuevo) -> str", "Cambia cada aparición de viejo por nuevo.", "str"),
      me("find", "find(sub) -> int", "Posición de sub, o -1 si no está."),
      me("count", "count(sub) -> int", "Cuántas veces aparece sub."),
      me("startswith", "startswith(prefijo) -> bool", "True si empieza con prefijo."),
      me("endswith", "endswith(sufijo) -> bool", "True si termina con sufijo."),
      me("isdigit", "isdigit() -> bool", "True si todos son dígitos."),
      me("isalpha", "isalpha() -> bool", "True si todos son letras."),
      me("isalnum", "isalnum() -> bool", "True si todos son letras o dígitos."),
      me("isspace", "isspace() -> bool", "True si todos son espacios."),
      me("title", "title() -> str", "Primera letra de cada palabra en mayúscula.", "str"),
      me("capitalize", "capitalize() -> str", "Primera letra en mayúscula.", "str"),
      me("center", "center(ancho, relleno=\" \") -> str", "Centra el texto en ese ancho.", "str"),
      me("zfill", "zfill(ancho) -> str", "Rellena con ceros a la izquierda.", "str"),
      me("format", "format(*valores) -> str", "Pone los valores en los {} del texto.", "str"),
    ],
    list: [
      me("append", "append(x)", "Agrega x al final."),
      me("extend", "extend(iterable)", "Agrega todos los elementos al final."),
      me("insert", "insert(posicion, x)", "Inserta x en esa posición."),
      me("pop", "pop(posicion=-1)", "Quita y devuelve el elemento. Sin posición, el último."),
      me("remove", "remove(x)", "Quita la primera aparición de x."),
      me("index", "index(x) -> int", "Posición de la primera aparición de x."),
      me("count", "count(x) -> int", "Cuántas veces aparece x."),
      me("sort", "sort(reverse=False)", "Ordena la lista en su lugar."),
      me("reverse", "reverse()", "Invierte la lista en su lugar."),
      me("clear", "clear()", "Deja la lista vacía."),
      me("copy", "copy() -> list", "Copia de la lista.", "list"),
    ],
    dict: [
      me("get", "get(clave, defecto=None)", "Valor de la clave, o defecto si no existe."),
      me("keys", "keys()", "Las claves."),
      me("values", "values()", "Los valores."),
      me("items", "items()", "Pares (clave, valor). for k, v in d.items()."),
      me("pop", "pop(clave)", "Quita la clave y devuelve su valor."),
      me("update", "update(otro)", "Copia las claves de otro diccionario."),
      me("setdefault", "setdefault(clave, defecto)", "Devuelve el valor; si no existe, lo crea con defecto."),
      me("clear", "clear()", "Deja el diccionario vacío."),
      me("copy", "copy() -> dict", "Copia del diccionario.", "dict"),
    ],
    set: [
      me("add", "add(x)", "Agrega x."),
      me("remove", "remove(x)", "Quita x. Da error si no está."),
      me("discard", "discard(x)", "Quita x si está."),
      me("union", "union(otro) -> set", "Elementos de los dos conjuntos.", "set"),
      me("intersection", "intersection(otro) -> set", "Elementos que están en ambos.", "set"),
      me("difference", "difference(otro) -> set", "Elementos que no están en otro.", "set"),
      me("pop", "pop()", "Quita y devuelve un elemento cualquiera."),
      me("clear", "clear()", "Deja el conjunto vacío."),
    ],
    math: [
      fn("sqrt", "math.sqrt(x) -> float", "Raíz cuadrada."),
      fn("pow", "math.pow(x, y) -> float", "x elevado a y."),
      fn("floor", "math.floor(x) -> int", "Redondea hacia abajo."),
      fn("ceil", "math.ceil(x) -> int", "Redondea hacia arriba."),
      fn("trunc", "math.trunc(x) -> int", "Quita los decimales."),
      fn("fabs", "math.fabs(x) -> float", "Valor absoluto como real."),
      fn("factorial", "math.factorial(n) -> int", "n! para un entero no negativo."),
      fn("gcd", "math.gcd(a, b) -> int", "Máximo común divisor."),
      fn("log", "math.log(x, base=e) -> float", "Logaritmo. Sin base, natural."),
      fn("log10", "math.log10(x) -> float", "Logaritmo base 10."),
      fn("sin", "math.sin(x) -> float", "Seno de x en radianes."),
      fn("cos", "math.cos(x) -> float", "Coseno de x en radianes."),
      fn("tan", "math.tan(x) -> float", "Tangente de x en radianes."),
      fn("hypot", "math.hypot(x, y) -> float", "Hipotenusa: raíz de x² + y²."),
      fn("radians", "math.radians(grados) -> float", "Grados a radianes."),
      fn("degrees", "math.degrees(radianes) -> float", "Radianes a grados."),
      fn("isclose", "math.isclose(a, b) -> bool", "True si dos reales son casi iguales."),
      co("pi", "math.pi", "3.141592…"),
      co("e", "math.e", "2.718281…"),
      co("inf", "math.inf", "Infinito."),
    ],
    random: [
      fn("randint", "random.randint(a, b) -> int", "Entero al azar entre a y b, ambos incluidos."),
      fn("random", "random.random() -> float", "Real al azar entre 0 y 1."),
      fn("uniform", "random.uniform(a, b) -> float", "Real al azar entre a y b."),
      fn("randrange", "random.randrange(inicio, fin, paso)", "Entero al azar del range indicado."),
      fn("choice", "random.choice(secuencia)", "Un elemento al azar."),
      fn("shuffle", "random.shuffle(lista)", "Revuelve la lista en su lugar."),
      fn("sample", "random.sample(secuencia, k) -> list", "k elementos distintos al azar.", "list"),
      fn("seed", "random.seed(valor)", "Fija la semilla para repetir los mismos números."),
    ],
  },
  receivers: { math: "math", random: "random" },
  aliases: {},
}

const JS_STRING: Entry[] = [
  pr("length", "length: number", "Cantidad de caracteres."),
  me("toUpperCase", "toUpperCase(): string", "Copia en mayúsculas.", "String"),
  me("toLowerCase", "toLowerCase(): string", "Copia en minúsculas.", "String"),
  me("trim", "trim(): string", "Quita espacios al inicio y al final.", "String"),
  me("split", "split(separador): string[]", "Corta el texto en un arreglo.", "Array"),
  me("includes", "includes(texto): boolean", "true si contiene el texto."),
  me("indexOf", "indexOf(texto): number", "Posición del texto, o -1."),
  me("startsWith", "startsWith(texto): boolean", "true si empieza con el texto."),
  me("endsWith", "endsWith(texto): boolean", "true si termina con el texto."),
  me("slice", "slice(inicio, fin?): string", "Parte del texto entre inicio y fin.", "String"),
  me("substring", "substring(inicio, fin?): string", "Parte del texto entre inicio y fin.", "String"),
  me("replace", "replace(buscar, nuevo): string", "Cambia la primera aparición.", "String"),
  me("replaceAll", "replaceAll(buscar, nuevo): string", "Cambia todas las apariciones.", "String"),
  me("charAt", "charAt(posicion): string", "Carácter en esa posición.", "String"),
  me("repeat", "repeat(veces): string", "Repite el texto.", "String"),
  me("padStart", "padStart(largo, relleno): string", "Rellena a la izquierda.", "String"),
  me("padEnd", "padEnd(largo, relleno): string", "Rellena a la derecha.", "String"),
]

const JS_ARRAY: Entry[] = [
  pr("length", "length: number", "Cantidad de elementos."),
  me("push", "push(...elementos): number", "Agrega al final."),
  me("pop", "pop()", "Quita y devuelve el último."),
  me("shift", "shift()", "Quita y devuelve el primero."),
  me("unshift", "unshift(...elementos): number", "Agrega al inicio."),
  me("includes", "includes(valor): boolean", "true si contiene el valor."),
  me("indexOf", "indexOf(valor): number", "Posición del valor, o -1."),
  me("join", "join(separador): string", "Une los elementos en un texto.", "String"),
  me("slice", "slice(inicio, fin?)", "Copia una parte.", "Array"),
  me("splice", "splice(inicio, cuantos, ...nuevos)", "Quita o inserta elementos en su lugar.", "Array"),
  me("sort", "sort(comparar?)", "Ordena en su lugar. Para números: sort((a, b) => a - b).", "Array"),
  me("reverse", "reverse()", "Invierte en su lugar.", "Array"),
  me("map", "map(fn)", "Arreglo nuevo con fn aplicada a cada elemento.", "Array"),
  me("filter", "filter(fn)", "Arreglo con los elementos donde fn da true.", "Array"),
  me("reduce", "reduce(fn, inicial)", "Combina los elementos en un solo valor."),
  me("forEach", "forEach(fn)", "Ejecuta fn con cada elemento."),
  me("find", "find(fn)", "Primer elemento donde fn da true."),
  me("some", "some(fn): boolean", "true si algún elemento cumple fn."),
  me("every", "every(fn): boolean", "true si todos cumplen fn."),
  me("concat", "concat(...otros)", "Arreglo nuevo con los otros al final.", "Array"),
]

const JAVASCRIPT: Catalog = {
  globals: [
    ns("console", "console", "Escribe en la consola: console.log(…)."),
    ns("Math", "Math", "Funciones matemáticas: Math.sqrt, Math.round, Math.random…"),
    ns("JSON", "JSON", "Convierte entre texto JSON y objetos."),
    cl("Number", "Number(valor): number", "Convierte a número. Number(\"12\") da 12."),
    cl("String", "String(valor): string", "Convierte a texto.", "String"),
    cl("Array", "Array", "Arreglo de elementos.", "Array"),
    cl("Object", "Object", "Utilidades de objetos: keys, values, entries."),
    cl("Map", "new Map()", "Pares de clave y valor.", "Map"),
    cl("Set", "new Set()", "Conjunto sin repetidos.", "Set"),
    cl("Date", "new Date()", "Fecha y hora."),
    fn("parseInt", "parseInt(texto, base = 10): number", "Convierte texto a entero."),
    fn("parseFloat", "parseFloat(texto): number", "Convierte texto a real."),
    fn("isNaN", "isNaN(valor): boolean", "true si el valor no es un número."),
    fn("require", "require(modulo)", "Carga un módulo de Node, como \"readline\" o \"fs\"."),
    ns("process", "process", "Programa en marcha: process.stdin, process.stdout, process.argv."),
    fn("setTimeout", "setTimeout(fn, ms)", "Ejecuta fn después de ms milisegundos."),
  ],
  members: {
    console: [
      me("log", "console.log(...valores)", "Escribe los valores y salta de línea."),
      me("error", "console.error(...valores)", "Escribe en la salida de errores."),
      me("table", "console.table(datos)", "Muestra un arreglo u objeto como tabla."),
    ],
    Math: [
      fn("sqrt", "Math.sqrt(x): number", "Raíz cuadrada."),
      fn("pow", "Math.pow(x, y): number", "x elevado a y."),
      fn("abs", "Math.abs(x): number", "Valor absoluto."),
      fn("round", "Math.round(x): number", "Redondea al entero más cercano."),
      fn("floor", "Math.floor(x): number", "Redondea hacia abajo."),
      fn("ceil", "Math.ceil(x): number", "Redondea hacia arriba."),
      fn("trunc", "Math.trunc(x): number", "Quita los decimales."),
      fn("max", "Math.max(...valores): number", "El mayor."),
      fn("min", "Math.min(...valores): number", "El menor."),
      fn("random", "Math.random(): number", "Real al azar entre 0 y 1."),
      fn("sin", "Math.sin(x): number", "Seno en radianes."),
      fn("cos", "Math.cos(x): number", "Coseno en radianes."),
      co("PI", "Math.PI", "3.141592…"),
    ],
    JSON: [
      fn("stringify", "JSON.stringify(valor): string", "Objeto a texto JSON.", "String"),
      fn("parse", "JSON.parse(texto)", "Texto JSON a objeto."),
    ],
    Number: [
      fn("isInteger", "Number.isInteger(x): boolean", "true si x es entero."),
      fn("parseFloat", "Number.parseFloat(texto): number", "Texto a real."),
      fn("parseInt", "Number.parseInt(texto): number", "Texto a entero."),
    ],
    Object: [
      fn("keys", "Object.keys(objeto): string[]", "Las claves.", "Array"),
      fn("values", "Object.values(objeto)", "Los valores.", "Array"),
      fn("entries", "Object.entries(objeto)", "Pares [clave, valor].", "Array"),
    ],
    ArrayStatic: [
      fn("from", "Array.from(iterable)", "Crea un arreglo.", "Array"),
      fn("isArray", "Array.isArray(valor): boolean", "true si es un arreglo."),
    ],
    process: [
      pr("stdin", "process.stdin", "Entrada estándar."),
      pr("stdout", "process.stdout", "Salida estándar. process.stdout.write(texto) no salta de línea."),
      pr("argv", "process.argv", "Argumentos del programa.", "Array"),
      fn("exit", "process.exit(codigo)", "Termina el programa."),
    ],
    String: JS_STRING,
    Array: JS_ARRAY,
    Map: [
      me("set", "set(clave, valor)", "Guarda el valor en la clave.", "Map"),
      me("get", "get(clave)", "Valor de la clave."),
      me("has", "has(clave): boolean", "true si existe la clave."),
      me("delete", "delete(clave): boolean", "Quita la clave."),
      pr("size", "size: number", "Cantidad de pares."),
      me("keys", "keys()", "Las claves."),
      me("values", "values()", "Los valores."),
      me("clear", "clear()", "Deja el mapa vacío."),
    ],
    Set: [
      me("add", "add(valor)", "Agrega el valor.", "Set"),
      me("has", "has(valor): boolean", "true si contiene el valor."),
      me("delete", "delete(valor): boolean", "Quita el valor."),
      pr("size", "size: number", "Cantidad de elementos."),
      me("clear", "clear()", "Deja el conjunto vacío."),
    ],
  },
  receivers: {
    console: "console",
    Math: "Math",
    JSON: "JSON",
    Number: "Number",
    Object: "Object",
    Array: "ArrayStatic",
    process: "process",
  },
  aliases: { string: "String", String: "String", Array: "Array", Map: "Map", Set: "Set" },
}

const TYPESCRIPT: Catalog = {
  ...JAVASCRIPT,
  globals: [
    ...JAVASCRIPT.globals,
    cl("Record", "Record<Clave, Valor>", "Tipo de objeto con claves y valores de un tipo."),
    cl("Partial", "Partial<Tipo>", "El mismo tipo con todos sus campos opcionales."),
  ],
}

const JAVA_STRING: Entry[] = [
  me("length", "int length()", "Cantidad de caracteres."),
  me("charAt", "char charAt(int indice)", "Carácter en esa posición."),
  me("substring", "String substring(int inicio, int fin)", "Parte del texto entre inicio y fin, sin incluir fin.", "String"),
  me("indexOf", "int indexOf(String texto)", "Posición del texto, o -1."),
  me("contains", "boolean contains(CharSequence texto)", "true si contiene el texto."),
  me("equals", "boolean equals(Object otro)", "Compara el contenido. Usa equals, no ==, para textos."),
  me("equalsIgnoreCase", "boolean equalsIgnoreCase(String otro)", "Compara sin distinguir mayúsculas."),
  me("compareTo", "int compareTo(String otro)", "Negativo, cero o positivo según el orden alfabético."),
  me("toUpperCase", "String toUpperCase()", "Copia en mayúsculas.", "String"),
  me("toLowerCase", "String toLowerCase()", "Copia en minúsculas.", "String"),
  me("trim", "String trim()", "Quita espacios al inicio y al final.", "String"),
  me("split", "String[] split(String regex)", "Corta el texto en un arreglo.", "array"),
  me("replace", "String replace(CharSequence viejo, CharSequence nuevo)", "Cambia cada aparición.", "String"),
  me("startsWith", "boolean startsWith(String prefijo)", "true si empieza con prefijo."),
  me("endsWith", "boolean endsWith(String sufijo)", "true si termina con sufijo."),
  me("isEmpty", "boolean isEmpty()", "true si no tiene caracteres."),
  me("toCharArray", "char[] toCharArray()", "Los caracteres en un arreglo.", "array"),
]

const JAVA_LIST: Entry[] = [
  me("add", "boolean add(E elemento)", "Agrega al final."),
  me("get", "E get(int indice)", "Elemento en esa posición."),
  me("set", "E set(int indice, E elemento)", "Cambia el elemento de esa posición."),
  me("remove", "E remove(int indice)", "Quita el elemento de esa posición."),
  me("size", "int size()", "Cantidad de elementos."),
  me("isEmpty", "boolean isEmpty()", "true si no tiene elementos."),
  me("contains", "boolean contains(Object o)", "true si contiene el elemento."),
  me("indexOf", "int indexOf(Object o)", "Posición del elemento, o -1."),
  me("clear", "void clear()", "Deja la lista vacía."),
  me("sort", "void sort(Comparator c)", "Ordena. list.sort(null) usa el orden natural."),
]

const JAVA: Catalog = {
  globals: [
    cl("System", "java.lang.System", "System.out.println, System.in, System.exit."),
    cl("Math", "java.lang.Math", "Funciones matemáticas: Math.sqrt, Math.pow, Math.random…"),
    cl("String", "java.lang.String", "Texto."),
    cl("Integer", "java.lang.Integer", "Entero como objeto. Integer.parseInt convierte texto."),
    cl("Double", "java.lang.Double", "Real como objeto. Double.parseDouble convierte texto."),
    cl("Character", "java.lang.Character", "Utilidades de caracteres: isDigit, isLetter…"),
    cl("Scanner", "java.util.Scanner", "Lee datos. Scanner sc = new Scanner(System.in); requiere import java.util.Scanner;"),
    cl("StringBuilder", "java.lang.StringBuilder", "Texto que se arma por partes."),
    cl("ArrayList", "java.util.ArrayList<E>", "Lista que crece. Requiere import java.util.ArrayList;"),
    cl("HashMap", "java.util.HashMap<K, V>", "Pares de clave y valor. Requiere import java.util.HashMap;"),
    cl("HashSet", "java.util.HashSet<E>", "Conjunto sin repetidos. Requiere import java.util.HashSet;"),
    cl("Arrays", "java.util.Arrays", "Utilidades de arreglos: sort, toString, fill."),
    cl("Collections", "java.util.Collections", "Utilidades de listas: sort, reverse, max, min."),
    cl("Random", "java.util.Random", "Números al azar. Random r = new Random();"),
  ],
  members: {
    System: [
      pr("out", "PrintStream System.out", "Salida estándar.", "PrintStream"),
      pr("err", "PrintStream System.err", "Salida de errores.", "PrintStream"),
      pr("in", "InputStream System.in", "Entrada estándar. Se usa con new Scanner(System.in)."),
      fn("currentTimeMillis", "long System.currentTimeMillis()", "Milisegundos desde 1970."),
      fn("exit", "void System.exit(int codigo)", "Termina el programa."),
    ],
    PrintStream: [
      me("println", "void println(x)", "Escribe x y salta de línea."),
      me("print", "void print(x)", "Escribe x sin saltar de línea."),
      me("printf", "PrintStream printf(String formato, Object... valores)", "Escribe con formato: printf(\"%.2f%n\", x)."),
    ],
    Math: [
      fn("sqrt", "double Math.sqrt(double x)", "Raíz cuadrada."),
      fn("pow", "double Math.pow(double base, double exp)", "Potencia."),
      fn("abs", "Math.abs(x)", "Valor absoluto."),
      fn("max", "Math.max(a, b)", "El mayor de dos."),
      fn("min", "Math.min(a, b)", "El menor de dos."),
      fn("round", "long Math.round(double x)", "Redondea al entero más cercano."),
      fn("floor", "double Math.floor(double x)", "Redondea hacia abajo."),
      fn("ceil", "double Math.ceil(double x)", "Redondea hacia arriba."),
      fn("random", "double Math.random()", "Real al azar entre 0 y 1."),
      fn("sin", "double Math.sin(double rad)", "Seno."),
      fn("cos", "double Math.cos(double rad)", "Coseno."),
      co("PI", "double Math.PI", "3.141592…"),
    ],
    StringStatic: [
      fn("valueOf", "String String.valueOf(x)", "Convierte a texto.", "String"),
      fn("format", "String String.format(String formato, Object... valores)", "Texto con formato.", "String"),
      fn("join", "String String.join(CharSequence sep, elementos)", "Une con separador.", "String"),
    ],
    Integer: [
      fn("parseInt", "int Integer.parseInt(String texto)", "Convierte texto a int."),
      fn("valueOf", "Integer Integer.valueOf(String texto)", "Convierte texto a Integer."),
      fn("toString", "String Integer.toString(int n)", "Convierte a texto.", "String"),
      co("MAX_VALUE", "int Integer.MAX_VALUE", "El int más grande."),
      co("MIN_VALUE", "int Integer.MIN_VALUE", "El int más pequeño."),
    ],
    Double: [
      fn("parseDouble", "double Double.parseDouble(String texto)", "Convierte texto a double."),
      fn("valueOf", "Double Double.valueOf(String texto)", "Convierte texto a Double."),
      fn("toString", "String Double.toString(double x)", "Convierte a texto.", "String"),
    ],
    Character: [
      fn("isDigit", "boolean Character.isDigit(char c)", "true si es dígito."),
      fn("isLetter", "boolean Character.isLetter(char c)", "true si es letra."),
      fn("isUpperCase", "boolean Character.isUpperCase(char c)", "true si es mayúscula."),
      fn("toUpperCase", "char Character.toUpperCase(char c)", "En mayúscula."),
      fn("toLowerCase", "char Character.toLowerCase(char c)", "En minúscula."),
    ],
    Arrays: [
      fn("sort", "void Arrays.sort(arreglo)", "Ordena el arreglo."),
      fn("toString", "String Arrays.toString(arreglo)", "Texto como [1, 2, 3].", "String"),
      fn("fill", "void Arrays.fill(arreglo, valor)", "Pone el mismo valor en todo el arreglo."),
      fn("asList", "List Arrays.asList(elementos...)", "Lista con esos elementos.", "ArrayList"),
    ],
    Collections: [
      fn("sort", "void Collections.sort(lista)", "Ordena la lista."),
      fn("reverse", "void Collections.reverse(lista)", "Invierte la lista."),
      fn("max", "Collections.max(coleccion)", "El mayor."),
      fn("min", "Collections.min(coleccion)", "El menor."),
      fn("shuffle", "void Collections.shuffle(lista)", "Revuelve la lista."),
    ],
    Scanner: [
      me("nextLine", "String nextLine()", "Lee la línea completa.", "String"),
      me("nextInt", "int nextInt()", "Lee un entero. Después usa nextLine() para limpiar el salto."),
      me("nextDouble", "double nextDouble()", "Lee un real."),
      me("next", "String next()", "Lee la siguiente palabra.", "String"),
      me("nextBoolean", "boolean nextBoolean()", "Lee true o false."),
      me("hasNextLine", "boolean hasNextLine()", "true si queda otra línea."),
      me("hasNextInt", "boolean hasNextInt()", "true si lo siguiente es un entero."),
      me("close", "void close()", "Cierra el Scanner."),
    ],
    String: JAVA_STRING,
    StringBuilder: [
      me("append", "StringBuilder append(x)", "Agrega x al final.", "StringBuilder"),
      me("insert", "StringBuilder insert(int pos, x)", "Inserta x en la posición.", "StringBuilder"),
      me("reverse", "StringBuilder reverse()", "Invierte el texto.", "StringBuilder"),
      me("length", "int length()", "Cantidad de caracteres."),
      me("toString", "String toString()", "El texto armado.", "String"),
      me("deleteCharAt", "StringBuilder deleteCharAt(int pos)", "Quita el carácter de la posición.", "StringBuilder"),
    ],
    ArrayList: JAVA_LIST,
    HashMap: [
      me("put", "V put(K clave, V valor)", "Guarda el valor en la clave."),
      me("get", "V get(Object clave)", "Valor de la clave, o null."),
      me("getOrDefault", "V getOrDefault(Object clave, V defecto)", "Valor de la clave o defecto."),
      me("containsKey", "boolean containsKey(Object clave)", "true si existe la clave."),
      me("remove", "V remove(Object clave)", "Quita la clave."),
      me("keySet", "Set<K> keySet()", "Las claves.", "HashSet"),
      me("values", "Collection<V> values()", "Los valores."),
      me("size", "int size()", "Cantidad de pares."),
      me("isEmpty", "boolean isEmpty()", "true si no tiene pares."),
    ],
    HashSet: [
      me("add", "boolean add(E e)", "Agrega el elemento."),
      me("contains", "boolean contains(Object o)", "true si contiene el elemento."),
      me("remove", "boolean remove(Object o)", "Quita el elemento."),
      me("size", "int size()", "Cantidad de elementos."),
      me("isEmpty", "boolean isEmpty()", "true si no tiene elementos."),
    ],
    Random: [
      me("nextInt", "int nextInt(int limite)", "Entero al azar de 0 a limite - 1."),
      me("nextDouble", "double nextDouble()", "Real al azar entre 0 y 1."),
      me("nextBoolean", "boolean nextBoolean()", "true o false al azar."),
    ],
    array: [pr("length", "int length", "Cantidad de elementos del arreglo. Sin paréntesis.")],
  },
  receivers: {
    System: "System",
    "System.out": "PrintStream",
    "System.err": "PrintStream",
    Math: "Math",
    String: "StringStatic",
    Integer: "Integer",
    Double: "Double",
    Character: "Character",
    Arrays: "Arrays",
    Collections: "Collections",
  },
  aliases: {
    String: "String",
    Scanner: "Scanner",
    StringBuilder: "StringBuilder",
    ArrayList: "ArrayList",
    List: "ArrayList",
    LinkedList: "ArrayList",
    HashMap: "HashMap",
    Map: "HashMap",
    TreeMap: "HashMap",
    HashSet: "HashSet",
    Set: "HashSet",
    TreeSet: "HashSet",
    Random: "Random",
    PrintStream: "PrintStream",
  },
}

const C_FUNCTIONS: Entry[] = [
  fn("printf", "int printf(const char *formato, ...)  <stdio.h>", "Escribe con formato: %d entero, %f real, %c carácter, %s texto, \\n salto."),
  fn("scanf", "int scanf(const char *formato, ...)  <stdio.h>", "Lee con formato. Pasa la dirección: scanf(\"%d\", &n)."),
  fn("puts", "int puts(const char *texto)  <stdio.h>", "Escribe el texto y salta de línea."),
  fn("putchar", "int putchar(int c)  <stdio.h>", "Escribe un carácter."),
  fn("getchar", "int getchar(void)  <stdio.h>", "Lee un carácter."),
  fn("fgets", "char *fgets(char *destino, int largo, FILE *f)  <stdio.h>", "Lee una línea. fgets(texto, 100, stdin)."),
  fn("strlen", "size_t strlen(const char *s)  <string.h>", "Cantidad de caracteres sin contar el \\0."),
  fn("strcpy", "char *strcpy(char *destino, const char *origen)  <string.h>", "Copia el texto."),
  fn("strcat", "char *strcat(char *destino, const char *origen)  <string.h>", "Agrega origen al final de destino."),
  fn("strcmp", "int strcmp(const char *a, const char *b)  <string.h>", "0 si son iguales; negativo o positivo según el orden."),
  fn("strchr", "char *strchr(const char *s, int c)  <string.h>", "Primera aparición del carácter, o NULL."),
  fn("sqrt", "double sqrt(double x)  <math.h>", "Raíz cuadrada. Compila con -lm."),
  fn("pow", "double pow(double base, double exp)  <math.h>", "Potencia."),
  fn("fabs", "double fabs(double x)  <math.h>", "Valor absoluto de un real."),
  fn("floor", "double floor(double x)  <math.h>", "Redondea hacia abajo."),
  fn("ceil", "double ceil(double x)  <math.h>", "Redondea hacia arriba."),
  fn("round", "double round(double x)  <math.h>", "Redondea al más cercano."),
  fn("sin", "double sin(double rad)  <math.h>", "Seno."),
  fn("cos", "double cos(double rad)  <math.h>", "Coseno."),
  fn("abs", "int abs(int x)  <stdlib.h>", "Valor absoluto de un entero."),
  fn("rand", "int rand(void)  <stdlib.h>", "Entero al azar. rand() % n da de 0 a n - 1."),
  fn("srand", "void srand(unsigned semilla)  <stdlib.h>", "Fija la semilla. srand(time(NULL))."),
  fn("malloc", "void *malloc(size_t bytes)  <stdlib.h>", "Reserva memoria. Libérala con free."),
  fn("calloc", "void *calloc(size_t n, size_t tam)  <stdlib.h>", "Reserva memoria en ceros."),
  fn("free", "void free(void *p)  <stdlib.h>", "Libera la memoria reservada."),
  fn("atoi", "int atoi(const char *s)  <stdlib.h>", "Texto a entero."),
  fn("atof", "double atof(const char *s)  <stdlib.h>", "Texto a real."),
  fn("exit", "void exit(int codigo)  <stdlib.h>", "Termina el programa."),
  fn("isdigit", "int isdigit(int c)  <ctype.h>", "Distinto de 0 si es dígito."),
  fn("isalpha", "int isalpha(int c)  <ctype.h>", "Distinto de 0 si es letra."),
  fn("toupper", "int toupper(int c)  <ctype.h>", "El carácter en mayúscula."),
  fn("tolower", "int tolower(int c)  <ctype.h>", "El carácter en minúscula."),
  fn("time", "time_t time(time_t *t)  <time.h>", "Segundos desde 1970. time(NULL)."),
  co("NULL", "NULL", "Apuntador vacío."),
  co("EOF", "EOF  <stdio.h>", "Fin de la entrada."),
  co("stdin", "FILE *stdin  <stdio.h>", "Entrada estándar."),
]

const C: Catalog = { globals: C_FUNCTIONS, members: {}, receivers: {}, aliases: {} }

const CPP_STD: Entry[] = [
  pr("cout", "std::ostream std::cout  <iostream>", "Salida. std::cout << \"hola\" << std::endl;", "ostream"),
  pr("cin", "std::istream std::cin  <iostream>", "Entrada. std::cin >> n;", "istream"),
  co("endl", "std::endl", "Salta de línea y vacía la salida."),
  cl("string", "std::string  <string>", "Texto que crece.", "string"),
  cl("vector", "std::vector<T>  <vector>", "Arreglo que crece.", "vector"),
  cl("map", "std::map<K, V>  <map>", "Pares de clave y valor ordenados.", "map"),
  cl("set", "std::set<T>  <set>", "Conjunto ordenado sin repetidos.", "set"),
  fn("getline", "std::getline(std::cin, texto)  <string>", "Lee la línea completa en un std::string."),
  fn("to_string", "std::string std::to_string(numero)  <string>", "Número a texto.", "string"),
  fn("stoi", "int std::stoi(const std::string &s)  <string>", "Texto a entero."),
  fn("stod", "double std::stod(const std::string &s)  <string>", "Texto a real."),
  fn("sort", "std::sort(inicio, fin)  <algorithm>", "Ordena. std::sort(v.begin(), v.end())."),
  fn("reverse", "std::reverse(inicio, fin)  <algorithm>", "Invierte el rango."),
  fn("max", "std::max(a, b)  <algorithm>", "El mayor de dos."),
  fn("min", "std::min(a, b)  <algorithm>", "El menor de dos."),
  fn("swap", "std::swap(a, b)  <utility>", "Intercambia dos valores."),
  fn("setprecision", "std::setprecision(n)  <iomanip>", "Decimales al escribir. Úsalo con std::fixed."),
  co("fixed", "std::fixed  <iostream>", "Escribe los reales con decimales fijos."),
]

const CPP: Catalog = {
  globals: [
    ns("std", "namespace std", "Biblioteca estándar: std::cout, std::string, std::vector…"),
    ...C_FUNCTIONS.filter((item) => !["malloc", "calloc", "free", "scanf", "printf"].includes(item.name)),
    fn("printf", "int printf(const char *formato, ...)  <cstdio>", "Escribe con formato, igual que en C."),
  ],
  members: {
    std: CPP_STD,
    ostream: [
      me("precision", "std::streamsize precision(n)", "Cantidad de dígitos al escribir reales."),
      me("flush", "std::ostream &flush()", "Vacía la salida."),
    ],
    istream: [
      me("ignore", "std::istream &ignore(n, delim)", "Descarta caracteres. Antes de getline: std::cin.ignore()."),
      me("get", "int get()", "Lee un carácter."),
      me("fail", "bool fail()", "true si la última lectura falló."),
    ],
    string: [
      me("length", "size_t length()", "Cantidad de caracteres."),
      me("size", "size_t size()", "Cantidad de caracteres."),
      me("substr", "std::string substr(pos, n)", "Parte del texto desde pos con n caracteres.", "string"),
      me("find", "size_t find(const std::string &s)", "Posición de s, o std::string::npos."),
      me("append", "std::string &append(const std::string &s)", "Agrega s al final.", "string"),
      me("push_back", "void push_back(char c)", "Agrega un carácter al final."),
      me("empty", "bool empty()", "true si no tiene caracteres."),
      me("at", "char &at(size_t pos)", "Carácter en pos, con revisión de límites."),
      me("c_str", "const char *c_str()", "El texto como cadena de C."),
      me("clear", "void clear()", "Deja el texto vacío."),
    ],
    vector: [
      me("push_back", "void push_back(const T &x)", "Agrega al final."),
      me("pop_back", "void pop_back()", "Quita el último."),
      me("size", "size_t size()", "Cantidad de elementos."),
      me("empty", "bool empty()", "true si no tiene elementos."),
      me("at", "T &at(size_t pos)", "Elemento en pos, con revisión de límites."),
      me("front", "T &front()", "Primer elemento."),
      me("back", "T &back()", "Último elemento."),
      me("begin", "iterator begin()", "Inicio, para std::sort(v.begin(), v.end())."),
      me("end", "iterator end()", "Fin, una posición después del último."),
      me("clear", "void clear()", "Deja el vector vacío."),
      me("resize", "void resize(size_t n)", "Cambia la cantidad de elementos."),
    ],
    map: [
      me("insert", "insert({clave, valor})", "Agrega el par si la clave no existe."),
      me("count", "size_t count(const K &clave)", "1 si existe la clave, 0 si no."),
      me("find", "iterator find(const K &clave)", "Busca la clave. Compara con end()."),
      me("erase", "size_t erase(const K &clave)", "Quita la clave."),
      me("size", "size_t size()", "Cantidad de pares."),
      me("empty", "bool empty()", "true si no tiene pares."),
      me("begin", "iterator begin()", "Inicio del recorrido."),
      me("end", "iterator end()", "Fin del recorrido."),
    ],
    set: [
      me("insert", "insert(const T &x)", "Agrega el elemento."),
      me("count", "size_t count(const T &x)", "1 si está, 0 si no."),
      me("erase", "size_t erase(const T &x)", "Quita el elemento."),
      me("size", "size_t size()", "Cantidad de elementos."),
      me("empty", "bool empty()", "true si no tiene elementos."),
    ],
  },
  receivers: { std: "std", cout: "ostream", cin: "istream", "std::cout": "ostream", "std::cin": "istream" },
  aliases: { string: "string", vector: "vector", map: "map", unordered_map: "map", set: "set", unordered_set: "set" },
}

const CSHARP_STRING: Entry[] = [
  pr("Length", "int Length", "Cantidad de caracteres."),
  me("ToUpper", "string ToUpper()", "Copia en mayúsculas.", "String"),
  me("ToLower", "string ToLower()", "Copia en minúsculas.", "String"),
  me("Trim", "string Trim()", "Quita espacios al inicio y al final.", "String"),
  me("Split", "string[] Split(char separador)", "Corta el texto en un arreglo.", "array"),
  me("Substring", "string Substring(int inicio, int largo)", "Parte del texto.", "String"),
  me("Contains", "bool Contains(string texto)", "true si contiene el texto."),
  me("IndexOf", "int IndexOf(string texto)", "Posición del texto, o -1."),
  me("Replace", "string Replace(string viejo, string nuevo)", "Cambia cada aparición.", "String"),
  me("StartsWith", "bool StartsWith(string prefijo)", "true si empieza con prefijo."),
  me("EndsWith", "bool EndsWith(string sufijo)", "true si termina con sufijo."),
  me("Equals", "bool Equals(string otro)", "Compara el contenido."),
  me("PadLeft", "string PadLeft(int ancho)", "Rellena a la izquierda.", "String"),
  me("ToCharArray", "char[] ToCharArray()", "Los caracteres en un arreglo.", "array"),
]

const CSHARP: Catalog = {
  globals: [
    cl("Console", "System.Console", "Entrada y salida: Console.WriteLine, Console.ReadLine."),
    cl("Math", "System.Math", "Funciones matemáticas: Math.Sqrt, Math.Pow, Math.Round…"),
    cl("Convert", "System.Convert", "Convierte entre tipos: Convert.ToInt32, Convert.ToDouble."),
    cl("String", "System.String", "Utilidades de texto: string.Join, string.IsNullOrEmpty."),
    cl("List", "List<T>", "Lista que crece. using System.Collections.Generic;", "List"),
    cl("Dictionary", "Dictionary<TKey, TValue>", "Pares de clave y valor.", "Dictionary"),
    cl("StringBuilder", "System.Text.StringBuilder", "Texto que se arma por partes.", "StringBuilder"),
    cl("Random", "System.Random", "Números al azar. var r = new Random();", "Random"),
    cl("Array", "System.Array", "Utilidades de arreglos: Array.Sort, Array.Reverse."),
  ],
  members: {
    Console: [
      fn("WriteLine", "void Console.WriteLine(valor)", "Escribe y salta de línea."),
      fn("Write", "void Console.Write(valor)", "Escribe sin saltar de línea."),
      fn("ReadLine", "string? Console.ReadLine()", "Lee una línea. int.Parse(Console.ReadLine()) para un número.", "String"),
      fn("ReadKey", "ConsoleKeyInfo Console.ReadKey()", "Espera una tecla."),
      fn("Clear", "void Console.Clear()", "Limpia la consola."),
    ],
    Math: [
      fn("Sqrt", "double Math.Sqrt(double x)", "Raíz cuadrada."),
      fn("Pow", "double Math.Pow(double x, double y)", "Potencia."),
      fn("Abs", "Math.Abs(x)", "Valor absoluto."),
      fn("Round", "double Math.Round(double x, int decimales)", "Redondea."),
      fn("Floor", "double Math.Floor(double x)", "Redondea hacia abajo."),
      fn("Ceiling", "double Math.Ceiling(double x)", "Redondea hacia arriba."),
      fn("Max", "Math.Max(a, b)", "El mayor de dos."),
      fn("Min", "Math.Min(a, b)", "El menor de dos."),
      co("PI", "double Math.PI", "3.141592…"),
    ],
    Convert: [
      fn("ToInt32", "int Convert.ToInt32(valor)", "Convierte a int."),
      fn("ToDouble", "double Convert.ToDouble(valor)", "Convierte a double."),
      fn("ToString", "string Convert.ToString(valor)", "Convierte a texto.", "String"),
      fn("ToBoolean", "bool Convert.ToBoolean(valor)", "Convierte a bool."),
    ],
    StringStatic: [
      fn("Join", "string string.Join(string sep, valores)", "Une con separador.", "String"),
      fn("IsNullOrEmpty", "bool string.IsNullOrEmpty(string? s)", "true si es null o vacío."),
      fn("Format", "string string.Format(string formato, params object[] valores)", "Texto con formato.", "String"),
    ],
    int: [
      fn("Parse", "int int.Parse(string s)", "Convierte texto a int. Da error si no es número."),
      fn("TryParse", "bool int.TryParse(string s, out int n)", "Convierte sin error; devuelve false si no es número."),
      co("MaxValue", "int int.MaxValue", "El int más grande."),
    ],
    double: [
      fn("Parse", "double double.Parse(string s)", "Convierte texto a double."),
      fn("TryParse", "bool double.TryParse(string s, out double x)", "Convierte sin error."),
    ],
    ArrayStatic: [
      fn("Sort", "void Array.Sort(arreglo)", "Ordena el arreglo."),
      fn("Reverse", "void Array.Reverse(arreglo)", "Invierte el arreglo."),
      fn("IndexOf", "int Array.IndexOf(arreglo, valor)", "Posición del valor, o -1."),
    ],
    String: CSHARP_STRING,
    List: [
      me("Add", "void Add(T elemento)", "Agrega al final."),
      me("Remove", "bool Remove(T elemento)", "Quita la primera aparición."),
      me("RemoveAt", "void RemoveAt(int indice)", "Quita el elemento de esa posición."),
      me("Insert", "void Insert(int indice, T elemento)", "Inserta en la posición."),
      me("Contains", "bool Contains(T elemento)", "true si contiene el elemento."),
      me("IndexOf", "int IndexOf(T elemento)", "Posición del elemento, o -1."),
      me("Sort", "void Sort()", "Ordena."),
      me("Reverse", "void Reverse()", "Invierte."),
      me("Clear", "void Clear()", "Deja la lista vacía."),
      pr("Count", "int Count", "Cantidad de elementos."),
    ],
    Dictionary: [
      me("Add", "void Add(TKey clave, TValue valor)", "Agrega el par. Da error si la clave existe."),
      me("ContainsKey", "bool ContainsKey(TKey clave)", "true si existe la clave."),
      me("TryGetValue", "bool TryGetValue(TKey clave, out TValue valor)", "Lee el valor sin error si no existe."),
      me("Remove", "bool Remove(TKey clave)", "Quita la clave."),
      pr("Count", "int Count", "Cantidad de pares."),
      pr("Keys", "KeyCollection Keys", "Las claves."),
      pr("Values", "ValueCollection Values", "Los valores."),
    ],
    StringBuilder: [
      me("Append", "StringBuilder Append(valor)", "Agrega al final.", "StringBuilder"),
      me("AppendLine", "StringBuilder AppendLine(valor)", "Agrega y salta de línea.", "StringBuilder"),
      me("Insert", "StringBuilder Insert(int pos, valor)", "Inserta en la posición.", "StringBuilder"),
      me("ToString", "string ToString()", "El texto armado.", "String"),
      pr("Length", "int Length", "Cantidad de caracteres."),
    ],
    Random: [
      me("Next", "int Next(int min, int max)", "Entero al azar de min a max - 1."),
      me("NextDouble", "double NextDouble()", "Real al azar entre 0 y 1."),
    ],
    array: [pr("Length", "int Length", "Cantidad de elementos del arreglo.")],
  },
  receivers: {
    Console: "Console",
    Math: "Math",
    Convert: "Convert",
    string: "StringStatic",
    String: "StringStatic",
    int: "int",
    double: "double",
    Array: "ArrayStatic",
  },
  aliases: {
    string: "String",
    String: "String",
    List: "List",
    Dictionary: "Dictionary",
    StringBuilder: "StringBuilder",
    Random: "Random",
  },
}

const CATALOGS: Record<ForeignLanguage, Catalog> = {
  python: PYTHON,
  javascript: JAVASCRIPT,
  typescript: TYPESCRIPT,
  java: JAVA,
  c: C,
  cpp: CPP,
  csharp: CSHARP,
}

export function catalogFor(language: ForeignLanguage): Catalog {
  return CATALOGS[language]
}
