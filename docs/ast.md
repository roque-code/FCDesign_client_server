# Diseño del AST

Estado: implementado en `language_core`. Las figuras del diagrama no son nodos del AST; salen de este árbol en `flowchart.py` y el cliente les pone coordenadas. El laboratorio construye estos mismos nodos desde los bloques. El mapa del sistema está en [arquitectura.md](arquitectura.md).

Los nodos son dataclasses inmutables. Cada nodo guarda un `SourceSpan`. El intérprete y el generador de diagramas consumen estos nodos; no vuelven al texto salvo para mostrar un fragmento de diagnóstico.

Los nombres de las clases están en inglés, como el resto del código Python. El token de una palabra reservada guarda el lexema escrito y el canónico español, aunque el estudiante haya escrito `If` o `Algorithm`. Los mensajes de diagnóstico siguen en español.

## 1. Posición y programa

```python
@dataclass(frozen=True)
class SourceSpan:
    start_line: int  # 1..n
    start_col: int   # 1..n
    end_line: int
    end_col: int

@dataclass(frozen=True)
class Program:
    algorithm: Algorithm
    functions: tuple[FunctionDecl, ...]
    procedures: tuple[ProcedureDecl, ...]
    span: SourceSpan
```

El parser puede construir un árbol parcial con subrutinas aunque falte el algoritmo, y en ese caso devuelve diagnósticos y un árbol opcional. Las herramientas no ejecutan un árbol que llegó con errores.

## 2. Declaraciones

```python
@dataclass(frozen=True)
class Algorithm:
    name: str
    name_span: SourceSpan
    body: tuple[Stmt, ...]
    span: SourceSpan

@dataclass(frozen=True)
class Param:
    name: str
    mode: Literal["value", "reference"]
    span: SourceSpan

@dataclass(frozen=True)
class FunctionDecl:
    result_name: str
    name: str
    params: tuple[Param, ...]
    body: tuple[Stmt, ...]
    span: SourceSpan

@dataclass(frozen=True)
class ProcedureDecl:
    name: str
    params: tuple[Param, ...]
    body: tuple[Stmt, ...]
    span: SourceSpan
```

## 3. Sentencias

```python
@dataclass(frozen=True)
class DefineStmt:
    names: tuple[str, ...]
    name_spans: tuple[SourceSpan, ...]
    type_name: Literal["entero", "real", "logico", "caracter", "cadena"]
    span: SourceSpan

@dataclass(frozen=True)
class DimensionStmt:
    declarations: tuple[DimDecl, ...]
    span: SourceSpan

@dataclass(frozen=True)
class DimDecl:
    name: str
    lengths: tuple[Expr, ...]
    type_name: Literal["entero", "real", "logico", "caracter", "cadena"] | None
    span: SourceSpan

@dataclass(frozen=True)
class AssignStmt:
    target: LValue
    value: Expr
    span: SourceSpan

@dataclass(frozen=True)
class ReadStmt:
    targets: tuple[LValue, ...]
    span: SourceSpan

@dataclass(frozen=True)
class WriteStmt:
    values: tuple[Expr, ...]
    span: SourceSpan
    newline: bool = True

@dataclass(frozen=True)
class ClearStmt:
    span: SourceSpan

@dataclass(frozen=True)
class WaitStmt:
    seconds: Expr
    span: SourceSpan

@dataclass(frozen=True)
class CallStmt:
    call: CallExpr
    span: SourceSpan

@dataclass(frozen=True)
class IfStmt:
    condition: Expr
    then_body: tuple[Stmt, ...]
    else_body: tuple[Stmt, ...] | None
    span: SourceSpan

@dataclass(frozen=True)
class SwitchStmt:
    selector: Expr
    cases: tuple[SwitchCase, ...]
    default_body: tuple[Stmt, ...] | None
    span: SourceSpan

@dataclass(frozen=True)
class SwitchCase:
    labels: tuple[Expr, ...]
    body: tuple[Stmt, ...]
    span: SourceSpan

@dataclass(frozen=True)
class WhileStmt:
    condition: Expr
    body: tuple[Stmt, ...]
    span: SourceSpan

@dataclass(frozen=True)
class RepeatStmt:
    body: tuple[Stmt, ...]
    condition: Expr
    span: SourceSpan

@dataclass(frozen=True)
class ForStmt:
    variable: str
    variable_span: SourceSpan
    start: Expr
    end: Expr
    step: Expr | None
    body: tuple[Stmt, ...]
    span: SourceSpan
```

`else_body is None` significa que no había `Sino`. Una rama `Sino` vacía es una tupla vacía y se distingue de la ausencia.

## 4. Expresiones

```python
@dataclass(frozen=True)
class LValue:
    name: str
    indexes: tuple[Expr, ...]  # vacía si es escalar
    span: SourceSpan

@dataclass(frozen=True)
class LiteralExpr:
    kind: Literal["entero", "real", "logico", "caracter", "cadena"]
    value: int | Decimal | bool | str
    raw: str
    span: SourceSpan

@dataclass(frozen=True)
class NameExpr:
    name: str
    span: SourceSpan

@dataclass(frozen=True)
class UnaryExpr:
    operator: Literal["neg", "pos", "not"]
    operand: Expr
    span: SourceSpan

@dataclass(frozen=True)
class BinaryExpr:
    operator: Literal[
        "add", "sub", "mul", "div", "idiv", "mod", "pow",
        "eq", "neq", "lt", "lte", "gt", "gte",
        "and", "or",
    ]
    left: Expr
    right: Expr
    span: SourceSpan

@dataclass(frozen=True)
class CallExpr:
    name: str
    args: tuple[Expr, ...]
    span: SourceSpan

@dataclass(frozen=True)
class IndexExpr:
    name: str
    indexes: tuple[Expr, ...]
    span: SourceSpan
```

`MOD` y `%` comparten el operador `mod`. `<>` y `!=` comparten `neq`. El lexema original no hace falta para ejecutar; el span permite mostrarlo.

No hay nodo `AssignExpr`. La asignación no es una expresión, así que no puede aparecer dentro de `Escribir` ni de una condición.

## 5. Análisis semántico

El analizador no modifica el AST. Devuelve el mismo árbol, una tabla de símbolos y una lista de diagnósticos.

```python
@dataclass(frozen=True)
class Symbol:
    name: str
    kind: Literal["scalar", "array", "function", "procedure", "parameter"]
    type_name: Literal["entero", "real", "logico", "caracter", "cadena"] | None
    dimensions: int | None
    mode: Literal["value", "reference"] | None
    declared_at: SourceSpan

@dataclass
class Scope:
    kind: Literal["algorithm", "function", "procedure"]
    name: str
    symbols: dict[str, Symbol]
```

Recorrido:

1. Registrar firmas de funciones y procedimientos. Un nombre duplicado es `E0302`.
2. Recorrer cada cuerpo. `Definir` y `Dimension` añaden símbolos. Una asignación o una lectura consultan el ámbito actual, no el del algoritmo padre.
3. Comprobar tipos de expresiones de abajo hacia arriba. El tipo de una expresión se calcula y se descarta salvo para el diagnóstico; no se anota todavía en el nodo. Si más adelante el intérprete repite trabajo de tipos de forma medible, se añadirá una estructura paralela `TypedTree`. No se anota el AST inmutable en la primera versión.
4. Comprobar aridad y modo de las llamadas contra la firma o contra la biblioteca.
5. Asignación definida de escalares y de la variable de retorno, por un análisis sencillo de caminos: secuencia, ambas ramas de `Si`, cuerpo de ciclos tratado como «puede no ejecutarse» en `Mientras` y `Para`, y «se ejecuta al menos una vez» en `Repetir`.

Los nombres de la biblioteca se registran en un ámbito raíz de solo lectura, anterior al archivo.

## 6. Valores en ejecución

Estos tipos no son nodos del AST. Viven en el runtime.

```python
Scalar = int | Decimal | bool | str

@dataclass
class ArrayValue:
    type_name: Literal["entero", "real", "logico", "caracter", "cadena"]
    lengths: tuple[int, ...]
    base: int
    cells: list[object]

@dataclass
class Cell:
    type_name: str
    value: object | Unassigned
    dimensions: int | None

@dataclass
class Frame:
    scope_name: str
    cells: dict[str, Cell]
    call_line: int | None
```

Una celda `Por Referencia` apunta a la celda del llamador. No se copia el contenedor de Python del usuario hacia fuera del intérprete.

El arreglo se guarda en orden por filas. La comprobación de cada índice es independiente: `base <= índice < base + longitud`.

## 7. Del AST al diagrama

`flowchart.build(program) -> FlowGraph` recorre el mismo AST.

```python
@dataclass(frozen=True)
class FlowNode:
    id: str
    kind: Literal["terminal", "process", "io", "decision", "subprocess", "join"]
    text: str
    span: SourceSpan | None
    figure: str = ""

@dataclass(frozen=True)
class FlowEdge:
    source: str
    target: str
    label: str | None

@dataclass(frozen=True)
class FlowGraph:
    nodes: tuple[FlowNode, ...]
    edges: tuple[FlowEdge, ...]
    entry: str
```

`kind` es la clase semántica. `figure` es la forma que pinta el cliente. El grafo no guarda coordenadas.

| Nodo AST | `kind` | `figure` |
| --- | --- | --- |
| inicio y fin del algoritmo o subrutina | `terminal` | `terminal` |
| `Definir`, `Dimension`, asignación, paso del `Para` | `process` | `process` |
| `Escribir` | `io` | `output` |
| `Leer` | `io` | `input` |
| condición de `Si` | `decision` | `decision` |
| condición de `Mientras`, `Repetir` y `Para` | `decision` | `loop` |
| selector de `Segun` | `decision` | `switch` |
| `CallStmt` o expresión de llamada usada como sentencia | `subprocess` | `subprocess` |

Los `join` son nodos técnicos. El cliente los colapsa antes de colocar las figuras y conserva el enlace entre formas visibles.

El `Para` se dibuja como proceso de inicio, hexágono de continuación, cuerpo, proceso de incremento y arista de vuelta. El `Repetir` coloca el hexágono después del cuerpo. Las etiquetas de arista en el grafo son `Sí` y `No`; el dibujo las muestra como V y F. El recorrido de las líneas está en [arquitectura.md](arquitectura.md).

## 8. Impresión y pruebas

Cada nodo implementa una forma estable de volcado, de una línea por nodo, con sangría. Las pruebas de parser comparan ese volcado, no la identidad de los objetos. Así un cambio de posición no rompe una prueba de estructura, y una prueba de spans comprueba las posiciones por separado.
