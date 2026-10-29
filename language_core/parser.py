"""Analizador sintáctico por descenso recursivo y Pratt para expresiones."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from language_core.ast_nodes import (
    Algorithm,
    AssignStmt,
    BinaryExpr,
    CallExpr,
    CallStmt,
    ClearStmt,
    DefineStmt,
    DimDecl,
    DimensionStmt,
    Expr,
    ForStmt,
    FunctionDecl,
    IfStmt,
    IndexExpr,
    LiteralExpr,
    LValue,
    NameExpr,
    Param,
    ProcedureDecl,
    Program,
    ReadStmt,
    RepeatStmt,
    SourceSpan,
    Stmt,
    SwitchCase,
    SwitchStmt,
    TypeName,
    UnaryExpr,
    WaitStmt,
    WhileStmt,
    WriteStmt,
    merge_spans,
)
from language_core.diagnostics import Diagnostic, make_diagnostic
from language_core.grammar import (
    BP_ADD,
    BP_AND,
    BP_MUL,
    BP_NOT,
    BP_OR,
    BP_POW,
    BP_REL,
    BP_UNARY,
    TYPE_KEYWORDS,
    LanguageProfile,
)
from language_core.tokens import Token, TokenKind

_CLOSERS = frozenset(
    {
        "finsi",
        "sino",
        "finmientras",
        "finpara",
        "finsegun",
        "finalgoritmo",
        "finfuncion",
        "finsubproceso",
        "hasta",
    }
)
_STMT_KEYWORDS = frozenset(
    {
        "definir",
        "dimension",
        "leer",
        "escribir",
        "borrar",
        "esperar",
        "si",
        "segun",
        "mientras",
        "repetir",
        "para",
    }
)
_REL_OPS = frozenset({"eq", "neq", "lt", "lte", "gt", "gte"})
_BinOp = Literal[
    "add",
    "sub",
    "mul",
    "div",
    "idiv",
    "mod",
    "pow",
    "eq",
    "neq",
    "lt",
    "lte",
    "gt",
    "gte",
    "and",
    "or",
]


class Parser:
    """Construye el AST y acumula diagnósticos de sintaxis."""

    def __init__(self, tokens: tuple[Token, ...], source: str, profile: LanguageProfile) -> None:
        self.tokens = tokens
        self.source = source
        self.profile = profile
        self.index = 0
        self.previous = tokens[0]
        self.diagnostics: list[Diagnostic] = []
        self._case_depth = 0

    def parse(self) -> Program | None:
        functions: list[FunctionDecl] = []
        procedures: list[ProcedureDecl] = []
        algorithm: Algorithm | None = None
        while not self._check(TokenKind.EOF):
            if self._check(TokenKind.SEMICOLON):
                tok = self._advance()
                self._error(
                    "E0211",
                    "Hay un punto y coma de más.",
                    tok.span,
                    "Elimina el punto y coma que no sigue a una sentencia.",
                )
                continue
            if self._check_kw("algoritmo"):
                parsed = self._parse_algorithm()
                if algorithm is not None:
                    self._error(
                        "E0311",
                        "El archivo solo puede contener un algoritmo.",
                        parsed.span,
                        "Deja un solo bloque Algoritmo y mueve las subrutinas fuera.",
                    )
                else:
                    algorithm = parsed
                continue
            if self._check_kw("funcion"):
                functions.append(self._parse_function())
                continue
            if self._check_kw("subproceso"):
                procedures.append(self._parse_procedure())
                continue
            self._unexpected("Se esperaba Algoritmo, Funcion o SubProceso.")
        if algorithm is None:
            self._error(
                "E0205",
                "El archivo no tiene un algoritmo.",
                self._peek().span,
                "Empieza con Algoritmo, un nombre y termina con FinAlgoritmo.",
            )
            return None
        end = self.previous.span
        if functions or procedures:
            end = self._peek().span
        return Program(
            algorithm, tuple(functions), tuple(procedures), merge_spans(algorithm.span, end)
        )

    def _parse_algorithm(self) -> Algorithm:
        start = self._advance()
        name, name_span = self._expect_name("Se esperaba el nombre del algoritmo.")
        body = self._parse_block()
        end = self._expect_kw(
            "finalgoritmo",
            "E0202",
            "Falta FinAlgoritmo.",
            "Cierra el algoritmo con FinAlgoritmo.",
            start,
        )
        span = merge_spans(start.span, end.span if end is not None else self.previous.span)
        return Algorithm(name or "?", name_span or start.span, body, span)

    def _parse_function(self) -> FunctionDecl:
        start = self._advance()
        result, _ = self._expect_name("Se esperaba el nombre del resultado.")
        self._expect_assign()
        name, _ = self._expect_name("Se esperaba el nombre de la función.")
        params = self._parse_params()
        body = self._parse_block()
        end = self._expect_kw(
            "finfuncion",
            "E0202",
            "Falta FinFuncion.",
            "Cierra la función con FinFuncion.",
            start,
        )
        span = merge_spans(start.span, end.span if end is not None else self.previous.span)
        return FunctionDecl(result or "?", name or "?", params, body, span)

    def _parse_procedure(self) -> ProcedureDecl:
        start = self._advance()
        name, _ = self._expect_name("Se esperaba el nombre del procedimiento.")
        params = self._parse_params()
        body = self._parse_block()
        end = self._expect_kw(
            "finsubproceso",
            "E0202",
            "Falta FinSubProceso.",
            "Cierra el procedimiento con FinSubProceso.",
            start,
        )
        span = merge_spans(start.span, end.span if end is not None else self.previous.span)
        return ProcedureDecl(name or "?", params, body, span)

    def _parse_params(self) -> tuple[Param, ...]:
        if not self._match(TokenKind.LPAREN):
            self._error(
                "E0212",
                "Falta el paréntesis de los parámetros.",
                self._peek().span,
                "Escribe el nombre seguido de ( y ).",
            )
            return ()
        params: list[Param] = []
        if not self._check(TokenKind.RPAREN):
            while True:
                name_tok = self._peek()
                name, name_span = self._expect_name("Se esperaba el nombre del parámetro.")
                mode: str = "value"
                explicit = False
                if self._check_kw("por"):
                    explicit = True
                    self._advance()
                    if self._check_kw("referencia"):
                        self._advance()
                        mode = "reference"
                    elif self._check_kw("valor"):
                        self._advance()
                    else:
                        self._error(
                            "E0201",
                            "Después de Por se espera Valor o Referencia.",
                            self._peek().span,
                            "Escribe Por Valor o Por Referencia.",
                        )
                if name is not None and name_span is not None:
                    params.append(Param(name, mode, name_span, explicit))  # type: ignore[arg-type]
                else:
                    params.append(Param("?", "value", name_tok.span))
                if not self._match(TokenKind.COMMA):
                    break
        if not self._match(TokenKind.RPAREN):
            self._error(
                "E0212",
                "Falta el paréntesis que cierra los parámetros.",
                self._peek().span,
                "Agrega ) después de la lista de parámetros.",
            )
        return tuple(params)

    def _parse_block(self) -> tuple[Stmt, ...]:
        statements: list[Stmt] = []
        while not self._block_ends():
            before = self.index
            if self._starts_statement():
                statement = self._parse_statement()
                if statement is not None:
                    statements.append(statement)
            else:
                self._unexpected("Esta línea no es una sentencia válida.")
            if self.index == before:
                self._advance()
        return tuple(statements)

    def _parse_case_body(self) -> tuple[Stmt, ...]:
        statements: list[Stmt] = []
        while not self._block_ends() and self._starts_statement():
            before = self.index
            statement = self._parse_statement()
            if statement is not None:
                statements.append(statement)
            if self.index == before:
                break
        return tuple(statements)

    def _parse_statement(self) -> Stmt | None:
        if self._check(TokenKind.SEMICOLON):
            tok = self._advance()
            self._error(
                "E0211",
                "Hay un punto y coma de más.",
                tok.span,
                "Elimina el punto y coma sobrante.",
            )
            return None
        if self._check_kw("definir"):
            return self._finish_simple(self._parse_define())
        if self._check_kw("dimension"):
            return self._finish_simple(self._parse_dimension())
        if self._check_kw("leer"):
            return self._finish_simple(self._parse_read())
        if self._check_kw("escribir"):
            return self._finish_simple(self._parse_write())
        if self._check_kw("borrar"):
            return self._finish_simple(self._parse_clear())
        if self._check_kw("esperar"):
            return self._finish_simple(self._parse_wait())
        if self._check_kw("si"):
            return self._parse_if()
        if self._check_kw("segun"):
            return self._parse_switch()
        if self._check_kw("mientras"):
            return self._parse_while()
        if self._check_kw("repetir"):
            return self._parse_repeat()
        if self._check_kw("para"):
            return self._parse_for()
        if self._check_kw("funcion"):
            self._error(
                "E0201",
                "Una función se escribe fuera del algoritmo.",
                self._peek().span,
                "Colócala antes de Algoritmo o después de FinAlgoritmo.",
            )
            self._parse_function()
            return None
        if self._check_kw("subproceso"):
            self._error(
                "E0201",
                "Un procedimiento se escribe fuera del algoritmo.",
                self._peek().span,
                "Colócalo antes de Algoritmo o después de FinAlgoritmo.",
            )
            self._parse_procedure()
            return None
        if self._check(TokenKind.IDENT):
            return self._finish_simple(self._parse_assign_or_call())
        self._unexpected("Esta línea no es una sentencia válida.")
        return None

    def _finish_simple(self, statement: Stmt | None) -> Stmt | None:
        if statement is None:
            return None
        if self._match(TokenKind.SEMICOLON):
            return statement
        if self.profile.require_semicolons:
            self._error(
                "E0210",
                "Falta el punto y coma al final de la sentencia.",
                statement.span,
                "Agrega ; al final de esta sentencia.",
            )
        return statement

    def _parse_define(self) -> DefineStmt | None:
        start = self._advance()
        names: list[str] = []
        spans: list[SourceSpan] = []
        if not self._check(TokenKind.IDENT):
            self._error(
                "E0201",
                "Se esperaba el nombre de la variable.",
                self._peek().span,
                "Escribe el nombre después de Definir.",
            )
            return None
        while True:
            token = self._advance()
            names.append(token.lexeme)
            spans.append(token.span)
            if not self._match(TokenKind.COMMA):
                break
            if not self._check(TokenKind.IDENT):
                self._error(
                    "E0201",
                    "Se esperaba otro nombre después de la coma.",
                    self._peek().span,
                    "Quita la coma o escribe el siguiente nombre.",
                )
                break
        if not self._check_kw("como"):
            self._error(
                "E0201",
                "Falta Como y el tipo de la variable.",
                self.previous.span,
                "Por ejemplo: Definir edad Como Entero;",
            )
            return None
        self._advance()
        type_name = self._parse_type()
        if type_name is None:
            return None
        return DefineStmt(
            tuple(names), tuple(spans), type_name, merge_spans(start.span, self.previous.span)
        )

    def _parse_type(self) -> TypeName | None:
        token = self._peek()
        mapped = TYPE_KEYWORDS.get(token.canonical) if token.kind is TokenKind.KEYWORD else None
        if mapped is None:
            self._error(
                "E0201",
                "Se esperaba un tipo: Entero, Real, Logico, Caracter o Cadena.",
                token.span,
                "Escríbelo después de Como.",
            )
            return None
        self._advance()
        return mapped  # type: ignore[return-value]

    def _parse_dimension(self) -> DimensionStmt | None:
        start = self._advance()
        declarations: list[DimDecl] = []
        while True:
            declaration = self._parse_dim_decl()
            if declaration is not None:
                declarations.append(declaration)
            if not self._match(TokenKind.COMMA):
                break
        if not declarations:
            return None
        return DimensionStmt(tuple(declarations), merge_spans(start.span, self.previous.span))

    def _parse_dim_decl(self) -> DimDecl | None:
        name, name_span = self._expect_name("Se esperaba el nombre del arreglo.")
        if name is None or name_span is None:
            return None
        if not self._match(TokenKind.LBRACK):
            self._error(
                "E0213",
                "Falta el corchete con el tamaño del arreglo.",
                self._peek().span,
                "Escribe el tamaño entre corchetes, por ejemplo numeros[10].",
            )
            return None
        lengths = [self._expression()]
        while self._match(TokenKind.COMMA):
            lengths.append(self._expression())
        if not self._match(TokenKind.RBRACK):
            self._error(
                "E0213",
                "Falta el corchete que cierra el tamaño.",
                self._peek().span,
                "Agrega ] después de las dimensiones.",
            )
        type_name = None
        if self._check_kw("como"):
            self._advance()
            type_name = self._parse_type()
        return DimDecl(name, tuple(lengths), type_name, merge_spans(name_span, self.previous.span))

    def _parse_read(self) -> ReadStmt | None:
        start = self._advance()
        targets = [self._parse_lvalue()]
        while self._match(TokenKind.COMMA):
            targets.append(self._parse_lvalue())
        ready = tuple(target for target in targets if target is not None)
        if not ready:
            return None
        return ReadStmt(ready, merge_spans(start.span, self.previous.span))

    def _parse_write(self) -> WriteStmt | None:
        start = self._advance()
        values = [self._expression()]
        while self._match(TokenKind.COMMA):
            values.append(self._expression())
        newline = True
        if self._check_kw("sin"):
            marker = self._advance()
            found = self._expect_kw(
                "saltar",
                "E0201",
                "Falta Saltar después de Sin.",
                "Escribe Sin Saltar para no bajar de línea.",
                marker,
            )
            if found is not None:
                newline = False
        return WriteStmt(
            tuple(values), merge_spans(start.span, self.previous.span), newline=newline
        )

    def _parse_clear(self) -> ClearStmt | None:
        start = self._advance()
        found = self._expect_kw(
            "pantalla",
            "E0201",
            "Falta Pantalla después de Borrar.",
            "Escribe Borrar Pantalla;",
            start,
        )
        if found is None:
            return None
        return ClearStmt(merge_spans(start.span, found.span))

    def _parse_wait(self) -> WaitStmt | None:
        start = self._advance()
        seconds = self._expression()
        found = self._expect_kw(
            "segundos",
            "E0201",
            "Falta Segundos después del tiempo.",
            "Escribe Esperar 2 Segundos;",
            self.previous,
        )
        if found is None:
            return None
        return WaitStmt(seconds, merge_spans(start.span, found.span))

    def _parse_assign_or_call(self) -> Stmt | None:
        name = self._advance()
        if self._match(TokenKind.LPAREN):
            call = self._finish_call(name)
            return CallStmt(call, call.span)
        target = self._finish_lvalue(name)
        if self._check(TokenKind.EQ):
            self._error(
                "E0203",
                "El signo == compara. Para asignar se usa <- o =.",
                self._peek().span,
                "Cambia == por <- o =.",
            )
            self._advance()
            self._expression()
            return None
        if not self._match(TokenKind.ASSIGN):
            self._error(
                "E0201",
                "Se esperaba <- o = para asignar, o ( para llamar.",
                self._peek().span,
                "Una asignación se escribe edad <- 18; o edad = 18;",
            )
            return None
        value = self._expression()
        return AssignStmt(target, value, merge_spans(name.span, value.span))

    def _parse_if(self) -> IfStmt:
        start = self._advance()
        condition = self._expression()
        self._expect_kw(
            "entonces",
            "E0201",
            "Falta Entonces después de la condición.",
            "Escribe Si condicion Entonces.",
            start,
        )
        then_body = self._parse_block()
        else_body: tuple[Stmt, ...] | None = None
        if self._check_kw("sino"):
            self._advance()
            else_body = self._parse_block()
        end = self._expect_kw(
            "finsi",
            "E0202",
            "Falta FinSi para cerrar este Si.",
            "Agrega FinSi después de las instrucciones del condicional.",
            start,
        )
        span = merge_spans(start.span, end.span if end is not None else self.previous.span)
        return IfStmt(condition, then_body, else_body, span)

    def _parse_switch(self) -> SwitchStmt:
        start = self._advance()
        selector = self._expression()
        self._expect_kw(
            "hacer",
            "E0201",
            "Falta Hacer después de Segun.",
            "Escribe Segun opcion Hacer.",
            start,
        )
        cases: list[SwitchCase] = []
        self._case_depth += 1
        try:
            default_body = self._parse_switch_arms(start, cases)
        finally:
            self._case_depth -= 1
        end = self._expect_kw(
            "finsegun",
            "E0202",
            "Falta FinSegun.",
            "Cierra la selección con FinSegun.",
            start,
        )
        span = merge_spans(start.span, end.span if end is not None else self.previous.span)
        return SwitchStmt(selector, tuple(cases), default_body, span)

    def _parse_switch_arms(self, start: Token, cases: list[SwitchCase]) -> tuple[Stmt, ...] | None:
        default_body: tuple[Stmt, ...] | None = None
        while (
            not self._check(TokenKind.EOF)
            and not self._check_kw("finsegun")
            and not self._check_kw("finalgoritmo")
        ):
            if self._is_default_arm():
                self._advance()
                self._expect_kw(
                    "otro", "E0201", "Se esperaba Otro.", "Escribe De Otro Modo:", start
                )
                self._expect_kw(
                    "modo", "E0201", "Se esperaba Modo.", "Escribe De Otro Modo:", start
                )
                if not self._match(TokenKind.COLON):
                    self._error(
                        "E0201", "Falta : después de De Otro Modo.", self._peek().span, "Agrega :."
                    )
                default_body = self._parse_block()
                break
            labels = [self._expression()]
            while self._match(TokenKind.COMMA):
                labels.append(self._expression())
            if not self._match(TokenKind.COLON):
                self._error(
                    "E0201",
                    "Falta : después de la etiqueta de Segun.",
                    self._peek().span,
                    "Cada caso termina con dos puntos, por ejemplo 1:.",
                )
                if self._check(TokenKind.EOF) or self._block_ends():
                    break
                self._advance()
            body = self._parse_case_body()
            cases.append(
                SwitchCase(tuple(labels), body, merge_spans(labels[0].span, self.previous.span))
            )
        return default_body

    def _parse_while(self) -> WhileStmt:
        start = self._advance()
        condition = self._expression()
        self._expect_kw(
            "hacer",
            "E0201",
            "Falta Hacer después de la condición.",
            "Escribe Mientras condicion Hacer.",
            start,
        )
        body = self._parse_block()
        end = self._expect_kw(
            "finmientras",
            "E0202",
            "Falta FinMientras para cerrar este ciclo.",
            "Agrega FinMientras después del cuerpo del ciclo.",
            start,
        )
        span = merge_spans(start.span, end.span if end is not None else self.previous.span)
        return WhileStmt(condition, body, span)

    def _parse_repeat(self) -> RepeatStmt:
        start = self._advance()
        body = self._parse_block()
        hasta = self._expect_kw(
            "hasta",
            "E0202",
            "Falta Hasta Que para cerrar este Repetir.",
            "Después del cuerpo escribe Hasta Que y la condición.",
            start,
        )
        self._expect_kw(
            "que",
            "E0201",
            "Falta Que después de Hasta.",
            "La forma completa es Hasta Que condicion.",
            hasta or start,
        )
        condition = self._expression()
        return RepeatStmt(body, condition, merge_spans(start.span, condition.span))

    def _parse_for(self) -> ForStmt:
        start = self._advance()
        name_tok = self._peek()
        variable, variable_span = self._expect_name("Se esperaba la variable del ciclo Para.")
        self._expect_assign()
        start_expr = self._expression()
        self._expect_kw(
            "hasta",
            "E0201",
            "Falta Hasta en el ciclo Para.",
            "Escribe Para i <- 1 Hasta 10 Hacer.",
            start,
        )
        end_expr = self._expression()
        step: Expr | None = None
        if self._check_kw("con"):
            self._advance()
            self._expect_kw(
                "paso",
                "E0201",
                "Falta Paso después de Con.",
                "Escribe Con Paso 1, o un paso negativo.",
                start,
            )
            step = self._expression()
        self._expect_kw(
            "hacer",
            "E0201",
            "Falta Hacer en el ciclo Para.",
            "Escribe Hacer antes de las instrucciones del ciclo.",
            start,
        )
        body = self._parse_block()
        end = self._expect_kw(
            "finpara",
            "E0202",
            "Falta FinPara para cerrar este ciclo.",
            "Agrega FinPara después del cuerpo del ciclo.",
            start,
        )
        span = merge_spans(start.span, end.span if end is not None else self.previous.span)
        return ForStmt(
            variable or "?", variable_span or name_tok.span, start_expr, end_expr, step, body, span
        )

    def _expression(self, min_bp: int = 0) -> Expr:
        left = self._nud()
        if left is None:
            return self._missing_expr(self._peek().span)
        while True:
            if self._check(TokenKind.ASSIGN):
                arrow = self._peek().lexeme == "<-"
                self._error(
                    "E0203",
                    "El signo <- asigna y no va dentro de una expresión."
                    if arrow
                    else "El signo = asigna. Para comparar se usa ==.",
                    self._peek().span,
                    "Saca la asignación de la condición." if arrow else "Cambia = por ==.",
                )
                mark = self._advance()
                right = self._expression(BP_REL)
                left = BinaryExpr(
                    "eq", left, right, merge_spans(left.span, right.span or mark.span)
                )
                break
            infix = self._infix()
            if infix is None:
                break
            operator, binding, assoc = infix
            if binding <= min_bp:
                break
            if operator in _REL_OPS and isinstance(left, BinaryExpr) and left.operator in _REL_OPS:
                self._error(
                    "E0204",
                    "No se pueden encadenar comparaciones.",
                    self._peek().span,
                    "Une las comparaciones con Y. Por ejemplo: a < b Y b < c.",
                )
                self._advance()
                self._expression(BP_REL)
                break
            self._advance()
            right_min = binding - 1 if assoc == "right" else binding
            right = self._expression(right_min)
            left = BinaryExpr(operator, left, right, merge_spans(left.span, right.span))
        return left

    def _nud(self) -> Expr | None:
        token = self._peek()
        if token.kind is TokenKind.INT and isinstance(token.value, int):
            self._advance()
            return LiteralExpr("entero", token.value, token.lexeme, token.span)
        if token.kind is TokenKind.REAL and isinstance(token.value, Decimal):
            self._advance()
            return LiteralExpr("real", token.value, token.lexeme, token.span)
        if token.kind is TokenKind.STRING and isinstance(token.value, str):
            self._advance()
            return LiteralExpr("cadena", token.value, token.lexeme, token.span)
        if token.kind is TokenKind.CHAR and isinstance(token.value, str):
            self._advance()
            return LiteralExpr("caracter", token.value, token.lexeme, token.span)
        if token.is_kw("verdadero") or token.is_kw("falso"):
            self._advance()
            return LiteralExpr("logico", token.value is True, token.lexeme, token.span)
        if token.is_kw("no"):
            self._advance()
            operand = self._expression(BP_NOT)
            return UnaryExpr("not", operand, merge_spans(token.span, operand.span))
        if token.kind in (TokenKind.PLUS, TokenKind.MINUS):
            self._advance()
            operand = self._expression(BP_UNARY)
            operator: Literal["pos", "neg"] = "pos" if token.kind is TokenKind.PLUS else "neg"
            return UnaryExpr(operator, operand, merge_spans(token.span, operand.span))
        if token.kind is TokenKind.IDENT:
            return self._primary_name()
        if token.kind is TokenKind.LPAREN:
            self._advance()
            inner = self._expression()
            if not self._match(TokenKind.RPAREN):
                self._error(
                    "E0212",
                    "Falta el paréntesis de cierre.",
                    self._peek().span,
                    "Agrega ) para cerrar la expresión.",
                )
            return inner
        if self._block_ends() or token.kind is TokenKind.EOF:
            self._error(
                "E0201",
                "Se esperaba una expresión.",
                token.span,
                "Completa la expresión antes de seguir.",
            )
            return None
        self._error(
            "E0201",
            f"Se esperaba una expresión y apareció {token.lexeme!r}.",
            token.span,
            "Revisa paréntesis, comas o una palabra clave fuera de lugar.",
        )
        self._advance()
        return None

    def _primary_name(self) -> Expr:
        name = self._advance()
        if self._match(TokenKind.LPAREN):
            return self._finish_call(name)
        if self._match(TokenKind.LBRACK):
            indexes = [self._expression()]
            while self._match(TokenKind.COMMA):
                indexes.append(self._expression())
            if not self._match(TokenKind.RBRACK):
                self._error(
                    "E0213",
                    "Falta el corchete de cierre.",
                    self._peek().span,
                    "Agrega ] después del índice.",
                )
            return IndexExpr(
                name.lexeme, tuple(indexes), merge_spans(name.span, self.previous.span)
            )
        return NameExpr(name.lexeme, name.span)

    def _finish_call(self, name: Token) -> CallExpr:
        args: list[Expr] = []
        if not self._check(TokenKind.RPAREN) and not self._check(TokenKind.EOF):
            args.append(self._expression())
            while self._match(TokenKind.COMMA):
                args.append(self._expression())
        if not self._match(TokenKind.RPAREN):
            self._error(
                "E0212",
                "Falta el paréntesis que cierra la llamada.",
                self._peek().span,
                "Agrega ) después de los argumentos.",
            )
        return CallExpr(name.lexeme, tuple(args), merge_spans(name.span, self.previous.span))

    def _parse_lvalue(self) -> LValue | None:
        if not self._check(TokenKind.IDENT):
            self._error(
                "E0201",
                "Se esperaba una variable.",
                self._peek().span,
                "Leer y la asignación necesitan el nombre de una variable.",
            )
            return None
        return self._finish_lvalue(self._advance())

    def _finish_lvalue(self, name: Token) -> LValue:
        indexes: list[Expr] = []
        if self._match(TokenKind.LBRACK):
            indexes.append(self._expression())
            while self._match(TokenKind.COMMA):
                indexes.append(self._expression())
            if not self._match(TokenKind.RBRACK):
                self._error(
                    "E0213",
                    "Falta el corchete de cierre.",
                    self._peek().span,
                    "Agrega ] después del índice.",
                )
        return LValue(name.lexeme, tuple(indexes), merge_spans(name.span, self.previous.span))

    def _infix(self) -> tuple[_BinOp, int, str] | None:
        token = self._peek()
        if token.kind is TokenKind.MINUS and self._starts_case_label():
            return None
        if token.kind is TokenKind.PLUS:
            return ("add", BP_ADD, "left")
        if token.kind is TokenKind.MINUS:
            return ("sub", BP_ADD, "left")
        if token.kind is TokenKind.STAR:
            return ("mul", BP_MUL, "left")
        if token.kind is TokenKind.SLASH:
            return ("div", BP_MUL, "left")
        if token.kind is TokenKind.PERCENT or token.is_kw("mod"):
            return ("mod", BP_MUL, "left")
        if token.is_kw("div"):
            return ("idiv", BP_MUL, "left")
        if token.kind is TokenKind.CARET:
            return ("pow", BP_POW, "right")
        if token.is_kw("y"):
            return ("and", BP_AND, "left")
        if token.is_kw("o"):
            return ("or", BP_OR, "left")
        if token.kind is TokenKind.EQ:
            return ("eq", BP_REL, "none")
        if token.kind is TokenKind.NEQ:
            return ("neq", BP_REL, "none")
        if token.kind is TokenKind.LT:
            return ("lt", BP_REL, "none")
        if token.kind is TokenKind.LTE:
            return ("lte", BP_REL, "none")
        if token.kind is TokenKind.GT:
            return ("gt", BP_REL, "none")
        if token.kind is TokenKind.GTE:
            return ("gte", BP_REL, "none")
        return None

    def _missing_expr(self, span: SourceSpan) -> LiteralExpr:
        return LiteralExpr("logico", False, "?", span)

    def _expect_assign(self) -> None:
        if self._match(TokenKind.ASSIGN):
            return
        if self._check(TokenKind.EQ):
            self._error(
                "E0203",
                "El signo == compara. Para asignar se usa <- o =.",
                self._peek().span,
                "Cambia == por <- o =.",
            )
            self._advance()
            return
        if not self._match(TokenKind.ASSIGN):
            self._error(
                "E0201",
                "Se esperaba <- o =.",
                self._peek().span,
                "La asignación se escribe con <- o =.",
            )

    def _expect_name(self, message: str) -> tuple[str | None, SourceSpan | None]:
        token = self._peek()
        if token.kind is not TokenKind.IDENT:
            self._error(
                "E0201", message, token.span, "Usa un nombre que no sea una palabra del lenguaje."
            )
            return None, None
        self._advance()
        return token.lexeme, token.span

    def _expect_kw(
        self,
        name: str,
        code: str,
        message: str,
        suggestion: str,
        anchor: Token,
    ) -> Token | None:
        if self._check_kw(name):
            return self._advance()
        self._error(code, message, anchor.span, suggestion)
        return None

    def _starts_case_label(self) -> bool:
        """Un - al inicio de la línea, seguido de un número y : o coma, es una etiqueta."""
        if self._case_depth <= 0:
            return False
        token = self._peek()
        if token.span.start_line <= self.previous.span.end_line:
            return False
        number = self._peek_at(1)
        if number.kind not in (TokenKind.INT, TokenKind.REAL):
            return False
        if number.span.start_line != token.span.start_line:
            return False
        return self._peek_at(2).kind in (TokenKind.COMMA, TokenKind.COLON)

    def _starts_statement(self) -> bool:
        token = self._peek()
        if token.kind is TokenKind.SEMICOLON:
            return True
        if token.kind is TokenKind.KEYWORD and token.canonical in _STMT_KEYWORDS:
            return True
        if token.kind is TokenKind.KEYWORD and token.canonical in ("funcion", "subproceso"):
            return True
        if token.kind is TokenKind.IDENT and self._peek_at(1).kind is not TokenKind.COLON:
            return True
        return False

    def _block_ends(self) -> bool:
        token = self._peek()
        if token.kind is TokenKind.EOF:
            return True
        if token.kind is TokenKind.KEYWORD and token.canonical in _CLOSERS:
            return True
        return self._is_default_arm()

    def _is_default_arm(self) -> bool:
        return self._check_kw("de") and self._peek_at(1).is_kw("otro")

    def _unexpected(self, message: str) -> None:
        token = self._peek()
        if token.kind is TokenKind.EOF:
            self._error("E0201", message, token.span, None)
            return
        self._error(
            "E0201",
            f"{message} Apareció {token.lexeme!r}.",
            token.span,
            None,
        )
        self._advance()

    def _error(self, code: str, message: str, span: SourceSpan, suggestion: str | None) -> None:
        self.diagnostics.append(
            make_diagnostic(self.source, "error", code, message, span, suggestion)
        )

    def _check(self, kind: TokenKind) -> bool:
        return self._peek().kind is kind

    def _check_kw(self, name: str) -> bool:
        return self._peek().is_kw(name)

    def _match(self, kind: TokenKind) -> bool:
        if self._check(kind):
            self._advance()
            return True
        return False

    def _peek(self) -> Token:
        return self.tokens[self.index]

    def _peek_at(self, offset: int) -> Token:
        index = min(self.index + offset, len(self.tokens) - 1)
        return self.tokens[index]

    def _advance(self) -> Token:
        token = self.tokens[self.index]
        if token.kind is not TokenKind.EOF:
            self.index += 1
        self.previous = token
        return token


def parse(
    tokens: tuple[Token, ...], source: str, profile: LanguageProfile
) -> tuple[Program | None, tuple[Diagnostic, ...]]:
    """Analiza la lista de tokens según el perfil."""
    parser = Parser(tokens, source, profile)
    program = parser.parse()
    return program, tuple(parser.diagnostics)
