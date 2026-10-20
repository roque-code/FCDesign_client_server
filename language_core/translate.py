"""Traducción del AST a lenguajes de programación.

No ejecuta el algoritmo. Recorre el mismo árbol que el intérprete y emite
un programa que conserva la estructura, los comentarios y las reglas que
no existen igual en el destino: índice inicial, DIV, MOD, referencias y consola.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from language_core.ast_nodes import (
    Algorithm,
    AssignStmt,
    BinaryExpr,
    CallExpr,
    CallStmt,
    ClearStmt,
    DefineStmt,
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
    SwitchStmt,
    TypeName,
    UnaryExpr,
    WaitStmt,
    WhileStmt,
    WriteStmt,
)
from language_core.diagnostics import Diagnostic
from language_core.grammar import STRICT, LanguageProfile, canonicalize
from language_core.interpreter import compile_source
from language_core.lexer import SourceComment, lex
from language_core.pseudocode import expr_power, format_real, needs_paren, quote_text
from language_core.stdlib import std_arity, std_return_type
from language_core.type_system import const_int

PRIMARY = 100

TARGETS: tuple[tuple[str, str, str], ...] = (
    ("python", "Python", "py"),
    ("javascript", "JavaScript", "js"),
    ("typescript", "TypeScript", "ts"),
    ("java", "Java", "java"),
    ("c", "C", "c"),
    ("cpp", "C++", "cpp"),
    ("csharp", "C#", "cs"),
)

_KEYWORDS: dict[str, frozenset[str]] = {
    "python": frozenset(
        {
            "False",
            "None",
            "True",
            "and",
            "as",
            "assert",
            "async",
            "await",
            "break",
            "class",
            "continue",
            "def",
            "del",
            "elif",
            "else",
            "except",
            "finally",
            "for",
            "from",
            "global",
            "if",
            "import",
            "in",
            "is",
            "lambda",
            "nonlocal",
            "not",
            "or",
            "pass",
            "raise",
            "return",
            "try",
            "while",
            "with",
            "yield",
            "print",
            "input",
            "int",
            "str",
            "len",
            "list",
            "range",
            "abs",
        }
    ),
    "javascript": frozenset(
        {
            "break",
            "case",
            "catch",
            "class",
            "const",
            "continue",
            "debugger",
            "default",
            "delete",
            "do",
            "else",
            "export",
            "extends",
            "false",
            "finally",
            "for",
            "function",
            "if",
            "implements",
            "import",
            "in",
            "instanceof",
            "interface",
            "let",
            "new",
            "null",
            "package",
            "private",
            "protected",
            "public",
            "return",
            "static",
            "super",
            "switch",
            "this",
            "throw",
            "true",
            "try",
            "typeof",
            "var",
            "void",
            "while",
            "with",
            "yield",
            "enum",
            "await",
            "console",
            "Math",
            "Array",
            "String",
            "Number",
        }
    ),
    "java": frozenset(
        {
            "abstract",
            "assert",
            "boolean",
            "break",
            "byte",
            "case",
            "catch",
            "char",
            "class",
            "const",
            "continue",
            "default",
            "do",
            "double",
            "else",
            "enum",
            "extends",
            "final",
            "finally",
            "float",
            "for",
            "goto",
            "if",
            "implements",
            "import",
            "instanceof",
            "int",
            "interface",
            "long",
            "native",
            "new",
            "package",
            "private",
            "protected",
            "public",
            "return",
            "short",
            "static",
            "strictfp",
            "super",
            "switch",
            "synchronized",
            "this",
            "throw",
            "throws",
            "transient",
            "try",
            "void",
            "volatile",
            "while",
            "true",
            "false",
            "null",
            "var",
            "String",
            "System",
            "Math",
        }
    ),
    "cpp": frozenset(
        {
            "alignas",
            "alignof",
            "and",
            "and_eq",
            "asm",
            "auto",
            "bitand",
            "bitor",
            "bool",
            "break",
            "case",
            "catch",
            "char",
            "class",
            "compl",
            "const",
            "continue",
            "default",
            "delete",
            "do",
            "double",
            "else",
            "enum",
            "explicit",
            "export",
            "extern",
            "false",
            "float",
            "for",
            "friend",
            "goto",
            "if",
            "inline",
            "int",
            "long",
            "mutable",
            "namespace",
            "new",
            "not",
            "nullptr",
            "operator",
            "or",
            "private",
            "protected",
            "public",
            "return",
            "short",
            "signed",
            "sizeof",
            "static",
            "struct",
            "switch",
            "template",
            "this",
            "throw",
            "true",
            "try",
            "typedef",
            "typeid",
            "typename",
            "union",
            "unsigned",
            "using",
            "virtual",
            "void",
            "volatile",
            "while",
            "std",
            "string",
        }
    ),
    "csharp": frozenset(
        {
            "abstract",
            "as",
            "base",
            "bool",
            "break",
            "byte",
            "case",
            "catch",
            "char",
            "checked",
            "class",
            "const",
            "continue",
            "decimal",
            "default",
            "delegate",
            "do",
            "double",
            "else",
            "enum",
            "event",
            "explicit",
            "extern",
            "false",
            "finally",
            "fixed",
            "float",
            "for",
            "foreach",
            "goto",
            "if",
            "implicit",
            "in",
            "int",
            "interface",
            "internal",
            "is",
            "lock",
            "long",
            "namespace",
            "new",
            "null",
            "object",
            "operator",
            "out",
            "override",
            "params",
            "private",
            "protected",
            "public",
            "readonly",
            "ref",
            "return",
            "sbyte",
            "sealed",
            "short",
            "sizeof",
            "stackalloc",
            "static",
            "string",
            "struct",
            "switch",
            "this",
            "throw",
            "true",
            "try",
            "typeof",
            "uint",
            "ulong",
            "unchecked",
            "unsafe",
            "ushort",
            "using",
            "virtual",
            "void",
            "volatile",
            "while",
            "Console",
            "Math",
            "Convert",
        }
    ),
    "c": frozenset(
        {
            "auto",
            "break",
            "case",
            "char",
            "const",
            "continue",
            "default",
            "do",
            "double",
            "else",
            "enum",
            "extern",
            "float",
            "for",
            "goto",
            "if",
            "inline",
            "int",
            "long",
            "register",
            "restrict",
            "return",
            "short",
            "signed",
            "sizeof",
            "static",
            "struct",
            "switch",
            "typedef",
            "union",
            "unsigned",
            "void",
            "volatile",
            "while",
            "_Bool",
            "true",
            "false",
            "NULL",
        }
    ),
}
_KEYWORDS["typescript"] = _KEYWORDS["javascript"] | {"type", "unknown", "any", "never", "undefined"}

_SCALAR: dict[str, dict[str, str]] = {
    "python": {
        "entero": "int",
        "real": "float",
        "logico": "bool",
        "caracter": "str",
        "cadena": "str",
    },
    "typescript": {
        "entero": "number",
        "real": "number",
        "logico": "boolean",
        "caracter": "string",
        "cadena": "string",
    },
    "java": {
        "entero": "int",
        "real": "double",
        "logico": "boolean",
        "caracter": "char",
        "cadena": "String",
    },
    "c": {
        "entero": "int",
        "real": "double",
        "logico": "bool",
        "caracter": "char",
        "cadena": "char *",
    },
    "cpp": {
        "entero": "int",
        "real": "double",
        "logico": "bool",
        "caracter": "char",
        "cadena": "std::string",
    },
    "csharp": {
        "entero": "int",
        "real": "double",
        "logico": "bool",
        "caracter": "char",
        "cadena": "string",
    },
}

_BOX: dict[str, str] = {
    "entero": "_TrazaCajaInt",
    "real": "_TrazaCajaReal",
    "logico": "_TrazaCajaLogico",
    "caracter": "_TrazaCajaCaracter",
    "cadena": "_TrazaCajaCadena",
}

_FILL: dict[str, dict[str, str]] = {
    "python": {"entero": "0", "real": "0.0", "logico": "False", "caracter": '" "', "cadena": '""'},
    "javascript": {
        "entero": "0",
        "real": "0",
        "logico": "false",
        "caracter": '" "',
        "cadena": '""',
    },
    "java": {"entero": "0", "real": "0.0", "logico": "false", "caracter": "' '", "cadena": '""'},
    "cpp": {"entero": "0", "real": "0.0", "logico": "false", "caracter": "' '", "cadena": '""'},
    "csharp": {"entero": "0", "real": "0.0", "logico": "false", "caracter": "' '", "cadena": '""'},
    "c": {"entero": "0", "real": "0.0", "logico": "false", "caracter": "' '", "cadena": '""'},
}

_FILL["typescript"] = _FILL["javascript"]


@dataclass(frozen=True)
class Translation:
    """Un lenguaje y el programa generado."""

    language: str
    label: str
    extension: str
    code: str


@dataclass(frozen=True)
class TranslationResult:
    """Diagnósticos del fuente y, si no hay errores, una traducción por lenguaje."""

    diagnostics: tuple[Diagnostic, ...]
    translations: tuple[Translation, ...]


@dataclass(frozen=True)
class _Sig:
    kind: str
    name: str
    result_name: str | None
    result_type: TypeName | None
    params: tuple[Param, ...]
    types: dict[str, TypeName]
    ranks: dict[str, int]
    body: tuple[Stmt, ...]
    span: SourceSpan


@dataclass
class _Notes:
    """Comentarios de una rutina, en orden de aparición."""

    items: list[SourceComment]
    index: int = 0

    def leading(self, line: int) -> list[SourceComment]:
        found: list[SourceComment] = []
        while self.index < len(self.items) and self.items[self.index].span.end_line < line:
            found.append(self.items[self.index])
            self.index += 1
        return found

    def trailing(self, span: SourceSpan) -> list[SourceComment]:
        found: list[SourceComment] = []
        while (
            self.index < len(self.items)
            and self.items[self.index].span.start_line == span.end_line
            and self.items[self.index].span.start_col > span.end_col
        ):
            found.append(self.items[self.index])
            self.index += 1
        return found


def translate_source(source: str, profile: LanguageProfile | None = None) -> TranslationResult:
    """Traduce si el fuente no tiene errores. Las advertencias no lo impiden."""
    chosen = profile or STRICT
    compiled = compile_source(source, chosen)
    errors = [item for item in compiled.diagnostics if item.severity == "error"]
    if compiled.program is None or errors:
        return TranslationResult(compiled.diagnostics, ())
    comments = lex(source).comments
    translations = tuple(
        Translation(
            language,
            label,
            extension,
            _Emitter(language, compiled.program, comments, chosen).generate(),
        )
        for language, label, extension in TARGETS
    )
    return TranslationResult(compiled.diagnostics, translations)


def _is_ref(param: Param, rank: int) -> bool:
    if param.explicit:
        return param.mode == "reference"
    return rank > 0


def _collect(statements: tuple[Stmt, ...]) -> tuple[dict[str, TypeName], dict[str, int]]:
    types: dict[str, TypeName] = {}
    ranks: dict[str, int] = {}

    def visit(body: tuple[Stmt, ...]) -> None:
        for statement in body:
            if isinstance(statement, DefineStmt):
                for name in statement.names:
                    types.setdefault(name, statement.type_name)
            elif isinstance(statement, DimensionStmt):
                for decl in statement.declarations:
                    ranks.setdefault(decl.name, len(decl.lengths))
                    if decl.type_name is not None:
                        types.setdefault(decl.name, decl.type_name)
            elif isinstance(statement, IfStmt):
                visit(statement.then_body)
                if statement.else_body is not None:
                    visit(statement.else_body)
            elif isinstance(statement, (WhileStmt, RepeatStmt, ForStmt)):
                visit(statement.body)
            elif isinstance(statement, SwitchStmt):
                for case in statement.cases:
                    visit(case.body)
                if statement.default_body is not None:
                    visit(statement.default_body)

    visit(statements)
    return types, ranks


def _signature(
    kind: str,
    name: str,
    result: str | None,
    params: tuple[Param, ...],
    body: tuple[Stmt, ...],
    span: SourceSpan,
) -> _Sig:
    types, ranks = _collect(body)
    result_type = types.get(result) if result is not None else None
    return _Sig(kind, name, result, result_type, params, types, ranks, body, span)


def _calls(statements: tuple[Stmt, ...]) -> list[CallExpr]:
    found: list[CallExpr] = []

    def walk_expr(expr: Expr) -> None:
        if isinstance(expr, CallExpr):
            found.append(expr)
            for arg in expr.args:
                walk_expr(arg)
        elif isinstance(expr, UnaryExpr):
            walk_expr(expr.operand)
        elif isinstance(expr, BinaryExpr):
            walk_expr(expr.left)
            walk_expr(expr.right)
        elif isinstance(expr, IndexExpr):
            for index in expr.indexes:
                walk_expr(index)

    def walk(body: tuple[Stmt, ...]) -> None:
        for statement in body:
            if isinstance(statement, AssignStmt):
                walk_expr(statement.value)
                for index in statement.target.indexes:
                    walk_expr(index)
            elif isinstance(statement, WriteStmt):
                for value in statement.values:
                    walk_expr(value)
            elif isinstance(statement, ReadStmt):
                for target in statement.targets:
                    for index in target.indexes:
                        walk_expr(index)
            elif isinstance(statement, WaitStmt):
                walk_expr(statement.seconds)
            elif isinstance(statement, CallStmt):
                walk_expr(statement.call)
            elif isinstance(statement, IfStmt):
                walk_expr(statement.condition)
                walk(statement.then_body)
                if statement.else_body is not None:
                    walk(statement.else_body)
            elif isinstance(statement, WhileStmt):
                walk_expr(statement.condition)
                walk(statement.body)
            elif isinstance(statement, RepeatStmt):
                walk(statement.body)
                walk_expr(statement.condition)
            elif isinstance(statement, ForStmt):
                walk_expr(statement.start)
                walk_expr(statement.end)
                if statement.step is not None:
                    walk_expr(statement.step)
                walk(statement.body)
            elif isinstance(statement, SwitchStmt):
                walk_expr(statement.selector)
                for case in statement.cases:
                    for label in case.labels:
                        walk_expr(label)
                    walk(case.body)
                if statement.default_body is not None:
                    walk(statement.default_body)
            elif isinstance(statement, DimensionStmt):
                for decl in statement.declarations:
                    for length in decl.lengths:
                        walk_expr(length)

    walk(statements)
    return found


class _Emitter:
    """Un lenguaje. El recorrido de sentencias es el mismo para todos."""

    def __init__(
        self,
        language: str,
        program: Program,
        comments: tuple[SourceComment, ...],
        profile: LanguageProfile,
    ) -> None:
        self.lang = language
        self.program = program
        self.profile = profile
        self.base = profile.index_base
        self.lines: list[str] = []
        self.level = 0
        self.temp_id = 0
        self.need: set[str] = set()
        self.box_types: set[TypeName] = set()
        self.array_declared: set[str] = set()
        self.c_refs: set[str] = set()
        self.scope = _signature(
            "procedure",
            program.algorithm.name,
            None,
            (),
            program.algorithm.body,
            program.algorithm.span,
        )
        self.sigs = self._sigs()
        self.notes = _Notes([])
        self.comments = comments
        self.boxed: set[str] = set()

    def generate(self) -> str:
        units = self._units()
        leading, inner, trailing = self._split_comments(units)
        methods: list[str] = []
        main = ""
        for kind, node in units:
            span = node.span
            ahead = leading.get(id(span), [])
            inside = inner.get(id(span), [])

            def build(
                kind: str = kind,
                node: FunctionDecl | ProcedureDecl | Algorithm = node,
                ahead: list[SourceComment] = ahead,
                inside: list[SourceComment] = inside,
            ) -> None:
                self._routine(kind, node, ahead, inside)

            text = self._capture(build)
            if kind == "algorithm":
                main = text
            else:
                methods.append(text)

        def build_tail() -> None:
            self._comment_list(trailing)

        tail = self._capture(build_tail)
        return self._assemble(methods, main, tail)

    def _sigs(self) -> dict[str, _Sig]:
        found: dict[str, _Sig] = {}
        for function in self.program.functions:
            found[function.name] = _signature(
                "function",
                function.name,
                function.result_name,
                function.params,
                function.body,
                function.span,
            )
        for procedure in self.program.procedures:
            found[procedure.name] = _signature(
                "procedure", procedure.name, None, procedure.params, procedure.body, procedure.span
            )
        return found

    def _units(self) -> list[tuple[str, FunctionDecl | ProcedureDecl | Algorithm]]:
        rows: list[tuple[int, int, str, FunctionDecl | ProcedureDecl]] = []
        for function in self.program.functions:
            rows.append((function.span.start_line, function.span.start_col, "function", function))
        for procedure in self.program.procedures:
            rows.append(
                (procedure.span.start_line, procedure.span.start_col, "procedure", procedure)
            )
        rows.sort()
        ordered: list[tuple[str, FunctionDecl | ProcedureDecl | Algorithm]] = [
            (kind, node) for _, _, kind, node in rows
        ]
        ordered.append(("algorithm", self.program.algorithm))
        return ordered

    def _split_comments(
        self, units: Sequence[tuple[str, FunctionDecl | ProcedureDecl | Algorithm]]
    ) -> tuple[dict[int, list[SourceComment]], dict[int, list[SourceComment]], list[SourceComment]]:
        spans = []
        for _, node in units:
            span = getattr(node, "span", None)
            if isinstance(span, SourceSpan):
                spans.append(span)
        leading: dict[int, list[SourceComment]] = {id(span): [] for span in spans}
        inner: dict[int, list[SourceComment]] = {id(span): [] for span in spans}
        trailing: list[SourceComment] = []
        ordered = sorted(spans, key=lambda span: (span.start_line, span.start_col))
        for comment in sorted(
            self.comments, key=lambda item: (item.span.start_line, item.span.start_col)
        ):
            host = next(
                (
                    span
                    for span in ordered
                    if span.start_line <= comment.span.start_line <= span.end_line
                ),
                None,
            )
            if host is not None:
                inner[id(host)].append(comment)
                continue
            nxt = next((span for span in ordered if span.start_line > comment.span.end_line), None)
            if nxt is not None:
                leading[id(nxt)].append(comment)
            else:
                trailing.append(comment)
        return leading, inner, trailing

    def _capture(self, build: Callable[[], None]) -> str:
        previous = self.lines
        self.lines = []
        if callable(build):
            build()
        text = "\n".join(self.lines).strip("\n")
        self.lines = previous
        return text

    def _routine(
        self,
        kind: str,
        node: object,
        leading: list[SourceComment],
        inner: list[SourceComment],
    ) -> None:
        if isinstance(node, FunctionDecl):
            sig = self.sigs[node.name]
            body = node.body
            result = node.result_name
        elif isinstance(node, ProcedureDecl):
            sig = self.sigs[node.name]
            body = node.body
            result = None
        else:
            algorithm = self.program.algorithm
            sig = _signature("procedure", algorithm.name, None, (), algorithm.body, algorithm.span)
            body = algorithm.body
            result = None
        self.scope = sig
        self.notes = _Notes(inner)
        self.level = 0
        self.c_refs = set()
        self.array_declared = {
            param.name for param in sig.params if sig.ranks.get(param.name, 0) > 0
        }
        if self.lang == "c":
            for param in sig.params:
                rank = sig.ranks.get(param.name, 0)
                if rank == 0 and _is_ref(param, rank):
                    self.c_refs.add(param.name)
        self._comment_list(leading)
        self.boxed = self._boxed(sig) if self._uses_box() else set()
        self._open_routine(kind, sig, self.boxed)
        locals_declared = self._declare_locals(sig, self.boxed, result)
        self._emit_block(body, sig.span.end_line, allow_empty=locals_declared or kind == "function")
        if kind == "function" and result is not None:
            self.sentence(f"return {self._slot(result, self.boxed)}")
        self._close_routine(kind)

    def _boxed(self, sig: _Sig) -> set[str]:
        found: set[str] = set()
        for param in sig.params:
            rank = sig.ranks.get(param.name, 0)
            if rank == 0 and _is_ref(param, rank):
                found.add(param.name)
                kind = sig.types.get(param.name) or "entero"
                self.box_types.add(kind)
                self.need.add("caja")
        for call in _calls(sig.body):
            if std_arity(call.name) is not None:
                continue
            target = self.sigs.get(call.name)
            if target is None:
                continue
            for param, arg in zip(target.params, call.args, strict=False):
                rank = target.ranks.get(param.name, 0)
                if rank == 0 and _is_ref(param, rank) and isinstance(arg, NameExpr):
                    found.add(arg.name)
                    kind = sig.types.get(arg.name) or target.types.get(param.name) or "entero"
                    self.box_types.add(kind)
                    self.need.add("caja")
        return found

    def _open_routine(self, kind: str, sig: _Sig, boxed: set[str]) -> None:
        self.level = 1 if self.lang in ("java", "csharp") else 0
        header = self._signature_text(kind, sig, boxed)
        if self.lang == "python":
            self.line(f"{header}:")
        else:
            self.line(f"{header} {{")
        self.level += 1

    def _close_routine(self, kind: str) -> None:
        del kind
        if self.lang == "python":
            self.level -= 1
            return
        self.level -= 1
        self.line("}")

    def _signature_text(self, kind: str, sig: _Sig, boxed: set[str]) -> str:
        params = ", ".join(self._param(param, sig, boxed) for param in sig.params)
        name = (
            "_traza_main"
            if kind == "algorithm" and self.lang in ("python", "javascript", "typescript")
            else self._name(sig.name)
        )
        if kind == "algorithm" and self.lang == "java":
            return "public static void main(String[] args)"
        if kind == "algorithm" and self.lang == "c":
            return "int main(void)"
        if kind == "algorithm" and self.lang == "cpp":
            return "int main()"
        if kind == "algorithm" and self.lang == "csharp":
            return "static void Main()"
        result = "void"
        if kind == "function":
            result = self._scalar(sig.result_type or "entero")
        if self.lang == "python":
            arrow = f" -> {result}" if kind == "function" else " -> None"
            if kind == "algorithm":
                arrow = " -> None"
            return f"def {name}({params}){arrow}"
        if self.lang == "javascript":
            return f"function {name}({params})"
        if self.lang == "typescript":
            ret = result if kind == "function" else "void"
            return f"function {name}({params}): {ret}"
        if self.lang == "java":
            ret = result if kind == "function" else "void"
            return f"static {ret} {name}({params})"
        if self.lang == "csharp":
            ret = result if kind == "function" else "void"
            return f"static {ret} {name}({params})"
        ret = result if kind == "function" else "void"
        return f"{ret} {name}({params})"

    def _param(self, param: Param, sig: _Sig, boxed: set[str]) -> str:
        rank = sig.ranks.get(param.name, 0)
        kind = sig.types.get(param.name) or "entero"
        ref = _is_ref(param, rank)
        renamed = self._name(param.name)
        if self.lang in ("python", "javascript"):
            return renamed
        if self.lang == "typescript":
            shown = self._box_ts(kind) if param.name in boxed else self._type_name(kind, rank)
            return f"{renamed}: {shown}"
        if param.name in boxed and self.lang == "java":
            return f"{_BOX[kind]} {renamed}"
        if self.lang == "cpp" and rank == 0 and ref:
            return f"{self._scalar(kind)}& {renamed}"
        if self.lang == "cpp" and rank > 0:
            vector = self._cpp_vector(kind, rank)
            mark = "&" if ref else ""
            return f"{vector}{mark} {renamed}"
        if self.lang == "csharp" and ref:
            return f"ref {self._type_name(kind, rank)} {renamed}"
        if self.lang == "c" and rank > 0:
            return f"{self._scalar(kind)} {renamed}[]"
        if self.lang == "c" and rank == 0 and ref:
            return f"{self._scalar(kind)} *{renamed}"
        return f"{self._type_name(kind, rank)} {renamed}"

    def _declare_locals(self, sig: _Sig, boxed: set[str], result: str | None) -> bool:
        params = {param.name for param in sig.params}
        names = list(dict.fromkeys([*sig.types.keys(), *sig.ranks.keys()]))
        wrote = False
        for name in names:
            if name in params:
                continue
            kind = sig.types.get(name) or (
                "entero" if name == result or sig.ranks.get(name, 0) == 0 else "entero"
            )
            rank = sig.ranks.get(name, 0)
            if self._declare(name, kind, rank, name in boxed):
                wrote = True
        return wrote

    def _declare(self, name: str, kind: TypeName, rank: int, boxed: bool) -> bool:
        renamed = self._name(name)
        fill = self._fill(kind)
        if boxed:
            self.need.add("caja")
            self.box_types.add(kind)
            if self.lang == "python":
                self.line(f"{renamed} = _TrazaCaja({fill})")
            elif self.lang == "javascript":
                self.sentence(f"let {renamed} = new _TrazaCaja({fill})")
            elif self.lang == "typescript":
                self.sentence(
                    f"let {renamed}: _TrazaCaja<{self._scalar(kind)}> = new _TrazaCaja({fill})"
                )
            else:
                self.sentence(f"{_BOX[kind]} {renamed} = new {_BOX[kind]}({fill})")
            return True
        if rank > 0:
            return False
        if self.lang == "python":
            self.line(f"{renamed}: {self._scalar(kind)} = {fill}")
        elif self.lang == "javascript":
            self.sentence(f"let {renamed} = {fill}")
        elif self.lang == "typescript":
            self.sentence(f"let {renamed}: {self._scalar(kind)} = {fill}")
        else:
            self.sentence(f"{self._scalar(kind)} {renamed} = {fill}")
        return True

    def _emit_block(
        self, statements: tuple[Stmt, ...], end_line: int, *, allow_empty: bool
    ) -> None:
        start = len(self.lines)
        for statement in statements:
            self._statement(statement)
        for comment in self.notes.leading(end_line):
            self._comment(comment)
        if len(self.lines) == start and self.lang == "python" and not allow_empty:
            self.line("pass")

    def _statement(self, statement: Stmt) -> None:
        for comment in self.notes.leading(statement.span.start_line):
            self._comment(comment)
        before = len(self.lines)
        if isinstance(statement, DefineStmt):
            pass
        elif isinstance(statement, DimensionStmt):
            self._dimension(statement)
        elif isinstance(statement, AssignStmt):
            self._assign(statement)
        elif isinstance(statement, ReadStmt):
            self._read(statement)
        elif isinstance(statement, WriteStmt):
            self._write(statement)
        elif isinstance(statement, ClearStmt):
            self.need.add("borrar")
            self.sentence("_traza_borrar()")
        elif isinstance(statement, WaitStmt):
            self.need.add("esperar")
            self.sentence(f"_traza_esperar({self.expression(statement.seconds)})")
        elif isinstance(statement, CallStmt):
            self.sentence(self._call(statement.call))
        elif isinstance(statement, IfStmt):
            self._if(statement)
        elif isinstance(statement, WhileStmt):
            self._while(statement)
        elif isinstance(statement, RepeatStmt):
            self._repeat(statement)
        elif isinstance(statement, ForStmt):
            self._for(statement)
        elif isinstance(statement, SwitchStmt):
            self._switch(statement)
        trail = self.notes.trailing(statement.span)
        if not trail:
            return
        if len(self.lines) == before + 1 and all(item.kind == "line" for item in trail):
            extra = " ".join(self._comment_text(item) for item in trail)
            self.lines[-1] = f"{self.lines[-1]} {extra}"
            return
        for comment in trail:
            self._comment(comment)

    def _dimension(self, statement: DimensionStmt) -> None:
        for decl in statement.declarations:
            kind = decl.type_name or self.scope.types.get(decl.name) or "entero"
            lengths = [self.expression(length) for length in decl.lengths]
            renamed = self._name(decl.name)
            if decl.name in self.array_declared:
                self.sentence(self._array_assign(renamed, kind, lengths))
                continue
            self.sentence(self._array_declare(renamed, kind, lengths, decl.lengths))
            self.array_declared.add(decl.name)

    def _assign(self, statement: AssignStmt) -> None:
        value = self.expression(statement.value)
        target_type = self._lvalue_type(statement.target)
        if (
            target_type == "entero"
            and isinstance(statement.value, CallExpr)
            and canonicalize(statement.value.name) == "convertiranumero"
            and self.lang in ("java", "cpp", "csharp", "c")
        ):
            value = f"({self._scalar('entero')}) ({value})"
        self.sentence(f"{self._lvalue(statement.target)} = {value}")

    def _read(self, statement: ReadStmt) -> None:
        for target in statement.targets:
            kind = self._lvalue_type(target) or "cadena"
            if self.lang == "java":
                self.need.add("leer")
            slot = self._lvalue(target)
            for row in self._native_read(target, slot, kind):
                self.sentence(row)

    def _native_read(self, target: LValue, slot: str, kind: TypeName) -> list[str]:
        if self.lang == "python":
            if kind == "entero":
                return [f"{slot} = int(input())"]
            if kind == "real":
                return [f"{slot} = float(input())"]
            if kind == "logico":
                return [f'{slot} = input().strip().lower() in {{"verdadero", "true"}}']
            return [f"{slot} = input()"]
        if self.lang in ("javascript", "typescript"):
            if kind in ("entero", "real"):
                return [f"{slot} = Number(prompt())"]
            if kind == "logico":
                return [
                    f'{slot} = ["verdadero", "true"].includes(String(prompt() ?? "").trim().toLowerCase())'
                ]
            return [f'{slot} = prompt() ?? ""']
        if self.lang == "java":
            if kind == "entero":
                return [f"{slot} = Integer.parseInt(_traza_entrada.nextLine().trim())"]
            if kind == "real":
                return [f"{slot} = Double.parseDouble(_traza_entrada.nextLine().trim())"]
            if kind == "caracter":
                return [f"{slot} = _traza_entrada.nextLine().charAt(0)"]
            if kind == "logico":
                clave = self._fresh("clave")
                return [
                    f"String {clave} = _traza_entrada.nextLine().trim().toLowerCase()",
                    f'{slot} = {clave}.equals("verdadero") || {clave}.equals("true")',
                ]
            return [f"{slot} = _traza_entrada.nextLine()"]
        if self.lang == "cpp":
            if kind == "logico":
                clave = self._fresh("clave")
                return [
                    f"std::string {clave}",
                    f"std::cin >> {clave}",
                    f'{slot} = {clave} == "Verdadero" || {clave} == "verdadero" || {clave} == "true"',
                ]
            return [f"std::cin >> {slot}"]
        if self.lang == "c":
            return self._c_read(target, slot, kind)
        if kind == "entero":
            return [f"{slot} = int.Parse(Console.ReadLine())"]
        if kind == "real":
            return [
                f"{slot} = double.Parse(Console.ReadLine(), System.Globalization.CultureInfo.InvariantCulture)"
            ]
        if kind == "caracter":
            return [f"{slot} = Console.ReadLine()[0]"]
        if kind == "logico":
            return [
                f'{slot} = (Console.ReadLine() ?? "").Trim().ToLowerInvariant() is "verdadero" or "true"'
            ]
        return [f'{slot} = Console.ReadLine() ?? ""']

    def _c_read(self, target: LValue, slot: str, kind: TypeName) -> list[str]:
        if kind == "cadena":
            self.need.add("calloc")
            return [f"{slot} = calloc(1024, 1)", f'(void) scanf("%1023s", {slot})']
        if kind == "logico":
            clave = self._fresh("clave")
            return [
                f"char {clave}[32]",
                f'(void) scanf("%31s", {clave})',
                f'{slot} = strcmp({clave}, "Verdadero") == 0 || strcmp({clave}, "verdadero") == 0 || strcmp({clave}, "true") == 0',
            ]
        address = self._c_address(target)
        spec = {"entero": "%d", "real": "%lf", "caracter": " %c"}[kind]
        return [f'(void) scanf("{spec}", {address})']

    def _c_address(self, target: LValue) -> str:
        if (
            not target.indexes
            and target.name in self.c_refs
            and self.scope.ranks.get(target.name, 0) == 0
        ):
            return self._name(target.name)
        return f"&({self._lvalue(target)})"

    def _write(self, statement: WriteStmt) -> None:
        pieces = [self._out_piece(value) for value in statement.values]
        self._print(pieces, statement.newline)

    def _if(self, statement: IfStmt) -> None:
        boundary = statement.span.end_line
        if statement.else_body:
            boundary = statement.else_body[0].span.start_line
        self._open_cond("if", statement.condition)
        self._emit_block(statement.then_body, boundary, allow_empty=False)
        if statement.else_body is None:
            self._close_cond()
            return
        self._else()
        self._emit_block(statement.else_body, statement.span.end_line, allow_empty=False)
        self._close_cond()

    def _while(self, statement: WhileStmt) -> None:
        self._open_cond("while", statement.condition)
        self._emit_block(statement.body, statement.span.end_line, allow_empty=False)
        self._close_cond()

    def _repeat(self, statement: RepeatStmt) -> None:
        if self.lang == "python":
            self.line("while True:")
            self.level += 1
            self._emit_block(statement.body, statement.span.end_line, allow_empty=False)
            cond = self.expression(statement.condition)
            self.line(f"if {cond}:")
            self.level += 1
            self.line("break")
            self.level -= 2
            return
        self.line("do {")
        self.level += 1
        self._emit_block(statement.body, statement.span.end_line, allow_empty=True)
        self.level -= 1
        cond = self.expression(statement.condition)
        self.line(f"}} while (!({cond}));")

    def _for(self, statement: ForStmt) -> None:
        if self.lang == "python":
            self.line(f"for {self._name(statement.variable)} in {self._py_range(statement)}:")
            self.level += 1
            self._emit_block(statement.body, statement.span.end_line, allow_empty=False)
            self.level -= 1
            return
        slot = self._slot(statement.variable, self.boxed)
        init, test, update = self._for_header(statement, slot)
        self.line(f"for ({init}; {test}; {update}) {{")
        self.level += 1
        self._emit_block(statement.body, statement.span.end_line, allow_empty=False)
        self._close_cond()

    def _py_range(self, statement: ForStmt) -> str:
        start = self.expression(statement.start)
        end = self.expression(statement.end)
        if statement.step is None:
            low = const_int(statement.start)
            high = const_int(statement.end)
            if low is not None and high is not None and low > high:
                return f"range({start}, {self._shifted(statement.end, end, -1)}, -1)"
            if low is not None and high is not None:
                return f"range({start}, {self._shifted(statement.end, end, 1)})"
            return (
                f"range({start}, {end} + (1 if {start} <= {end} else -1), "
                f"1 if {start} <= {end} else -1)"
            )
        step = self.expression(statement.step)
        known = const_int(statement.step)
        if known == 1:
            return f"range({start}, {self._shifted(statement.end, end, 1)})"
        if known is not None and known > 0:
            return f"range({start}, {self._shifted(statement.end, end, 1)}, {step})"
        if known is not None and known < 0:
            return f"range({start}, {self._shifted(statement.end, end, -1)}, {step})"
        return f"range({start}, {end} + (1 if {step} > 0 else -1), {step})"

    def _shifted(self, expr: Expr, code: str, delta: int) -> str:
        known = const_int(expr)
        if known is not None:
            return str(known + delta)
        if delta > 0:
            return f"({code}) + 1"
        return f"({code}) - 1"

    def _for_header(self, statement: ForStmt, slot: str) -> tuple[str, str, str]:
        start = self.expression(statement.start)
        end = self.expression(statement.end)
        init = f"{slot} = {start}"
        if statement.step is None:
            low = const_int(statement.start)
            high = const_int(statement.end)
            if low is not None and high is not None and low > high:
                return init, f"{slot} >= {end}", f"{slot}--"
            if low is not None and high is not None:
                return init, f"{slot} <= {end}", f"{slot}++"
            test = f"({start} <= {end} ? {slot} <= {end} : {slot} >= {end})"
            update = f"{slot} = {slot} + ({start} <= {end} ? 1 : -1)"
            return init, test, update
        step = self.expression(statement.step)
        known = const_int(statement.step)
        if known == 1:
            return init, f"{slot} <= {end}", f"{slot}++"
        if known is not None and known > 0:
            return init, f"{slot} <= {end}", f"{slot} = {slot} + {step}"
        if known == -1:
            return init, f"{slot} >= {end}", f"{slot}--"
        if known is not None and known < 0:
            return init, f"{slot} >= {end}", f"{slot} = {slot} + {step}"
        test = f"({step} > 0 ? {slot} <= {end} : {slot} >= {end})"
        return init, test, f"{slot} = {slot} + {step}"

    def _switch(self, statement: SwitchStmt) -> None:
        if not statement.cases and not statement.default_body:
            return
        kind = self.expr_type(statement.selector) or "entero"
        temp = self._fresh("caso")
        self._bind_typed(temp, kind, self.expression(statement.selector))
        if self._can_switch(kind):
            if self.lang == "python":
                self._match(statement, temp)
            else:
                self._switch_stmt(statement, temp)
            return
        self._switch_ifs(statement, temp, kind)

    def _can_switch(self, kind: TypeName) -> bool:
        if kind == "real":
            return self.lang in ("python", "javascript", "typescript")
        if kind == "cadena":
            return self.lang not in ("c", "cpp")
        if kind == "logico":
            return self.lang != "java"
        return True

    def _match(self, statement: SwitchStmt, temp: str) -> None:
        self.line(f"match {temp}:")
        self.level += 1
        for index, case in enumerate(statement.cases):
            labels = " | ".join(self.expression(label) for label in case.labels)
            self.line(f"case {labels}:")
            self.level += 1
            self._emit_block(case.body, self._case_end(statement, index), allow_empty=False)
            self.level -= 1
        if statement.default_body is not None:
            self.line("case _:")
            self.level += 1
            self._emit_block(statement.default_body, statement.span.end_line, allow_empty=False)
            self.level -= 1
        self.level -= 1

    def _switch_stmt(self, statement: SwitchStmt, temp: str) -> None:
        self.line(f"switch ({temp}) {{")
        self.level += 1
        for index, case in enumerate(statement.cases):
            for label in case.labels:
                self.line(f"case {self.expression(label)}:")
            self.level += 1
            self._emit_block(case.body, self._case_end(statement, index), allow_empty=True)
            self.sentence("break")
            self.level -= 1
        if statement.default_body is not None:
            self.line("default:")
            self.level += 1
            self._emit_block(statement.default_body, statement.span.end_line, allow_empty=True)
            self.sentence("break")
            self.level -= 1
        self.level -= 1
        self.line("}")

    def _case_end(self, statement: SwitchStmt, index: int) -> int:
        cases = statement.cases
        if index + 1 < len(cases):
            return cases[index + 1].span.start_line
        if statement.default_body:
            return statement.default_body[0].span.start_line
        return statement.span.end_line

    def _switch_ifs(self, statement: SwitchStmt, temp: str, kind: TypeName) -> None:
        cases = list(statement.cases)
        for index, case in enumerate(cases):
            checks = [
                self._equals(temp, kind, self.expression(label), self.expr_type(label))
                for label in case.labels
            ]
            joined = " or ".join(checks) if self.lang == "python" else " || ".join(checks)
            word = "if" if index == 0 else "elif" if self.lang == "python" else "else if"
            if self.lang == "python":
                self.line(f"{word} {joined}:")
            else:
                self.line(f"{word} ({joined}) {{")
            self.level += 1
            self._emit_block(case.body, self._case_end(statement, index), allow_empty=False)
            if self.lang != "python":
                self.level -= 1
                self.line("}")
            else:
                self.level -= 1
        if statement.default_body is None:
            return
        if self.lang == "python":
            self.line("else:")
        else:
            self.line("else {")
        self.level += 1
        self._emit_block(statement.default_body, statement.span.end_line, allow_empty=False)
        self._close_cond()

    def _open_cond(self, word: str, condition: Expr) -> None:
        code = self.expression(condition)
        if self.lang == "python":
            self.line(f"{word} {code}:")
        else:
            self.line(f"{word} ({code}) {{")
        self.level += 1

    def _else(self) -> None:
        self.level -= 1
        if self.lang == "python":
            self.line("else:")
        else:
            self.line("} else {")
        self.level += 1

    def _close_cond(self) -> None:
        if self.lang == "python":
            self.level -= 1
            return
        self.level -= 1
        self.line("}")

    def _bind(self, name: str, code: str) -> None:
        self._bind_typed(name, "entero", code)

    def _bind_typed(self, name: str, kind: TypeName, code: str) -> None:
        if self.lang == "python":
            self.line(f"{name}: {self._scalar(kind)} = {code}")
        elif self.lang == "javascript":
            self.sentence(f"let {name} = {code}")
        elif self.lang == "typescript":
            self.sentence(f"let {name}: {self._scalar(kind)} = {code}")
        else:
            self.sentence(f"{self._scalar(kind)} {name} = {code}")

    def _current_boxed(self) -> set[str]:
        return self.boxed

    def _slot(self, name: str, boxed: set[str]) -> str:
        renamed = self._name(name)
        if name in boxed and self._uses_box():
            return f"{renamed}.valor"
        if self.lang == "c" and name in self.c_refs and self.scope.ranks.get(name, 0) == 0:
            return f"(*{renamed})"
        return renamed

    def _lvalue(self, target: LValue) -> str:
        if target.indexes:
            return self._indexed(target.name, [self._index(index) for index in target.indexes])
        return self._slot(target.name, self._current_boxed())

    def _indexed(self, name: str, indexes: list[str]) -> str:
        renamed = self._name(name)
        if self.lang == "csharp" and len(indexes) > 1:
            return f"{renamed}[{', '.join(indexes)}]"
        return renamed + "".join(f"[{index}]" for index in indexes)

    def _lvalue_type(self, target: LValue) -> TypeName | None:
        return self.scope.types.get(target.name)

    def _index(self, expr: Expr) -> str:
        code = self.expression(expr)
        if self.base == 0:
            return code
        return f"({code} - 1)"

    def _call(self, call: CallExpr) -> str:
        if std_arity(call.name) is not None:
            return self._stdlib(call)
        return f"{self._name(call.name)}({self._args(call)})"

    def _args(self, call: CallExpr) -> str:
        sig = self.sigs.get(call.name)
        if sig is None:
            return ", ".join(self.expression(arg) for arg in call.args)
        rendered: list[str] = []
        boxed = self._current_boxed()
        for param, arg in zip(sig.params, call.args, strict=False):
            rank = sig.ranks.get(param.name, 0)
            ref = _is_ref(param, rank)
            if rank == 0 and ref and self._uses_box() and isinstance(arg, NameExpr):
                rendered.append(self._name(arg.name))
                continue
            if rank == 0 and ref and self.lang == "csharp" and isinstance(arg, NameExpr):
                rendered.append(f"ref {self._name(arg.name)}")
                continue
            if self.lang == "c" and rank > 0:
                rendered.append(self.expression(arg))
                continue
            if self.lang == "c" and ref and isinstance(arg, NameExpr):
                renamed = self._name(arg.name)
                rendered.append(renamed if arg.name in self.c_refs else f"&{renamed}")
                continue
            if isinstance(arg, NameExpr) and arg.name in boxed and not (rank == 0 and ref):
                rendered.append(f"{self._name(arg.name)}.valor")
                continue
            rendered.append(self.expression(arg))
        return ", ".join(rendered)

    def expression(self, node: Expr, parent_bp: int = 0, side: str = "left") -> str:
        code, binding, assoc = self._bare(node)
        if needs_paren(binding, assoc, parent_bp, side):
            return f"({code})"
        return code

    def _bare(self, node: Expr) -> tuple[str, int, str]:
        if isinstance(node, LiteralExpr):
            return self._literal(node), PRIMARY, "primary"
        if isinstance(node, NameExpr):
            return self._slot(node.name, self._current_boxed()), PRIMARY, "primary"
        if isinstance(node, IndexExpr):
            code = self._indexed(node.name, [self._index(index) for index in node.indexes])
            return code, PRIMARY, "primary"
        if isinstance(node, CallExpr):
            return self._call(node), PRIMARY, "primary"
        if isinstance(node, UnaryExpr):
            return self._unary(node)
        if isinstance(node, BinaryExpr):
            return self._binary(node)
        raise TypeError(f"Expresión sin traducción: {type(node)!r}")

    def _unary(self, node: UnaryExpr) -> tuple[str, int, str]:
        binding, assoc = expr_power(node)
        child = self.expression(node.operand, binding, "right")
        if node.operator == "not":
            code = f"not {child}" if self.lang == "python" else f"!{child}"
            return code, binding, assoc
        sign = "-" if node.operator == "neg" else "+"
        power = isinstance(node.operand, BinaryExpr) and node.operand.operator == "pow"
        if self.lang in ("javascript", "typescript") and power:
            return f"{sign}({child})", binding, assoc
        return f"{sign}{child}", binding, assoc

    def _binary(self, node: BinaryExpr) -> tuple[str, int, str]:
        binding, assoc = expr_power(node)
        left = self.expression(node.left, binding, "left")
        right = self.expression(node.right, binding, "right")
        op = node.operator
        if op == "idiv":
            return self._idiv(left, right), PRIMARY, "primary"
        if op == "mod":
            return self._mod(left, right), PRIMARY, "primary"
        if op == "div":
            return self._div(left, right), PRIMARY if self.lang != "python" else binding, "left"
        if op == "pow":
            return (
                self._pow(left, right, node),
                PRIMARY if self.lang not in ("python", "javascript", "typescript") else binding,
                assoc,
            )
        if op in ("eq", "neq", "lt", "lte", "gt", "gte"):
            return (
                self._relation(
                    op, left, right, self.expr_type(node.left), self.expr_type(node.right)
                ),
                binding,
                assoc,
            )
        symbol = (
            self._logic(op) if op in ("and", "or") else {"add": "+", "sub": "-", "mul": "*"}[op]
        )
        return f"{left} {symbol} {right}", binding, assoc

    def _logic(self, op: str) -> str:
        if self.lang == "python":
            return "and" if op == "and" else "or"
        return "&&" if op == "and" else "||"

    def _relation(
        self,
        op: str,
        left: str,
        right: str,
        left_type: TypeName | None,
        right_type: TypeName | None,
    ) -> str:
        textual = left_type == "cadena" or right_type == "cadena"
        symbols = {"eq": "==", "neq": "!=", "lt": "<", "lte": "<=", "gt": ">", "gte": ">="}
        if self.lang in ("javascript", "typescript"):
            symbols["eq"] = "==="
            symbols["neq"] = "!=="
        if self.lang == "java" and textual:
            if op == "eq":
                return f"java.util.Objects.equals({left}, {right})"
            if op == "neq":
                return f"!java.util.Objects.equals({left}, {right})"
            cmp = {"lt": "< 0", "lte": "<= 0", "gt": "> 0", "gte": ">= 0"}[op]
            return f"String.valueOf({left}).compareTo(String.valueOf({right})) {cmp}"
        if self.lang == "csharp" and textual and op not in ("eq", "neq"):
            cmp = {"lt": "< 0", "lte": "<= 0", "gt": "> 0", "gte": ">= 0"}[op]
            return f"string.Compare({left}, {right}) {cmp}"
        if self.lang == "c" and textual:
            cmp = {
                "eq": "== 0",
                "neq": "!= 0",
                "lt": "< 0",
                "lte": "<= 0",
                "gt": "> 0",
                "gte": ">= 0",
            }[op]
            return f"strcmp({left}, {right}) {cmp}"
        return f"{left} {symbols[op]} {right}"

    def _idiv(self, left: str, right: str) -> str:
        if self.lang == "python":
            return f"int({left} / {right})"
        if self.lang in ("javascript", "typescript"):
            return f"Math.trunc({left} / {right})"
        return f"({left} / {right})"

    def _mod(self, left: str, right: str) -> str:
        if self.lang == "python":
            return f"({left} - int({left} / {right}) * {right})"
        if self.lang in ("javascript", "typescript"):
            return f"({left} - Math.trunc({left} / {right}) * {right})"
        return f"({left} % {right})"

    def _div(self, left: str, right: str) -> str:
        if self.lang in ("python", "javascript", "typescript"):
            return f"{left} / {right}"
        if self.lang == "java":
            return f"((double) ({left}) / (double) ({right}))"
        if self.lang == "cpp":
            return f"(static_cast<double>({left}) / static_cast<double>({right}))"
        return f"((double) ({left}) / (double) ({right}))"

    def _pow(self, left: str, right: str, node: BinaryExpr) -> str:
        if self.lang in ("python", "javascript", "typescript"):
            return f"{left} ** {right}"
        call = (
            f"Math.Pow({left}, {right})"
            if self.lang == "csharp"
            else (
                f"pow({left}, {right})"
                if self.lang == "c"
                else (
                    f"std::pow({left}, {right})"
                    if self.lang == "cpp"
                    else f"Math.pow({left}, {right})"
                )
            )
        )
        if self.expr_type(node) == "entero":
            return f"((int) ({call}))"
        return call

    def _stdlib(self, call: CallExpr) -> str:
        name = canonicalize(call.name)
        args = [self.expression(arg) for arg in call.args]
        one = args[0] if args else ""
        two = args[1] if len(args) > 1 else ""
        if name == "abs":
            if self.lang == "python":
                return f"abs({one})"
            if self.lang == "csharp":
                return f"Math.Abs({one})"
            if self.lang == "cpp":
                return f"std::abs({one})"
            if self.lang == "c":
                if self.expr_type(call.args[0]) == "real":
                    return f"fabs({one})"
                return f"abs({one})"
            return f"Math.abs({one})"
        if name == "raiz":
            return self._math("sqrt", one)
        if name == "sen":
            return self._math("sin", one)
        if name == "cos":
            return self._math("cos", one)
        if name == "tan":
            return self._math("tan", one)
        if name == "ln":
            return self._math("log", one)
        if name == "exp":
            return self._math("exp", one)
        if name == "trunc":
            if self.lang == "python":
                self.need.add("math")
                return f"math.trunc({one})"
            if self.lang in ("javascript", "typescript"):
                return f"Math.trunc({one})"
            return f"({self._scalar('entero')}) ({one})"
        if name == "redon":
            self.need.add("redon")
            return f"_traza_redon({one})"
        if name == "potencia":
            return self._pow(one, two, BinaryExpr("pow", call.args[0], call.args[1], call.span))
        if name == "longitud":
            if self.lang == "python":
                return f"len({one})"
            if self.lang in ("javascript", "typescript"):
                return f"{one}.length"
            if self.lang == "java":
                return f"{one}.length()"
            if self.lang == "cpp":
                return f"{one}.size()"
            if self.lang == "c":
                return f"(int) strlen({one})"
            return f"{one}.Length"
        if name == "mayusculas":
            return self._case(one, True)
        if name == "minusculas":
            return self._case(one, False)
        if name == "concatenar":
            texts = []
            for code, arg in zip(args, call.args, strict=False):
                kind = self.expr_type(arg)
                if kind == "cadena" or (kind == "caracter" and self.lang != "c"):
                    texts.append(code)
                else:
                    texts.append(self._to_text(code, kind))
            return self._join(texts)
        if name == "subcadena":
            self.need.add("subcadena")
            return f"_traza_subcadena({args[0]}, {args[1]}, {args[2]})"
        if name == "aleatorio":
            if len(args) == 2:
                self.need.add("aleatorio_rango" if self.lang == "c" else "aleatorio")
                if self.lang == "c":
                    return f"_traza_aleatorio_rango({args[0]}, {args[1]})"
                return f"_traza_aleatorio({args[0]}, {args[1]})"
            self.need.add("aleatorio")
            return "_traza_aleatorio()"
        if name == "convertiranumero":
            self.need.add("numero")
            return f"_traza_numero({one})"
        if name == "convertiratexto":
            return self._to_text(one, self.expr_type(call.args[0]))
        return f"{self._name(call.name)}({', '.join(args)})"

    def _math(self, name: str, arg: str) -> str:
        if self.lang == "python":
            self.need.add("math")
            return f"math.{name}({arg})"
        if self.lang == "cpp":
            return f"std::{name}({arg})"
        if self.lang == "c":
            return f"{name}({arg})"
        if self.lang == "csharp":
            method = {
                "sqrt": "Sqrt",
                "sin": "Sin",
                "cos": "Cos",
                "tan": "Tan",
                "log": "Log",
                "exp": "Exp",
            }[name]
            return f"Math.{method}({arg})"
        return f"Math.{name}({arg})"

    def _case(self, arg: str, upper: bool) -> str:
        if self.lang == "python":
            return f"{arg}.upper()" if upper else f"{arg}.lower()"
        if self.lang in ("javascript", "typescript"):
            return f"{arg}.toUpperCase()" if upper else f"{arg}.toLowerCase()"
        if self.lang == "java":
            return f"{arg}.toUpperCase()" if upper else f"{arg}.toLowerCase()"
        if self.lang == "csharp":
            return f"{arg}.ToUpper()" if upper else f"{arg}.ToLower()"
        self.need.add("mayusculas" if upper else "minusculas")
        return f"_traza_mayusculas({arg})" if upper else f"_traza_minusculas({arg})"

    def _join(self, args: list[str]) -> str:
        if self.lang == "python":
            inner = ", ".join(args)
            return f"''.join([{inner}])"
        if self.lang == "c":
            if not args:
                return '""'
            self.need.add("unir")
            joined = args[0]
            for extra in args[1:]:
                joined = f"_traza_unir({joined}, {extra})"
            return joined
        return " + ".join(args) if args else '""'

    def _literal(self, node: LiteralExpr) -> str:
        if node.kind == "logico":
            return self._bool(bool(node.value))
        if node.kind == "caracter" and isinstance(node.value, str):
            return self._char(node.value)
        if node.kind == "cadena" and isinstance(node.value, str):
            return quote_text(node.value, '"')
        if node.kind == "real":
            from decimal import Decimal

            number = node.value if isinstance(node.value, Decimal) else Decimal(str(node.value))
            return format_real(number)
        return str(node.value)

    def _bool(self, value: bool) -> str:
        if self.lang == "python":
            return "True" if value else "False"
        return "true" if value else "false"

    def _char(self, value: str) -> str:
        if self.lang in ("python", "javascript", "typescript"):
            return quote_text(value, '"')
        if self.lang == "c":
            if value == "'":
                return "'\\''"
            if value == "\\":
                return "'\\\\'"
            if len(value) == 1 and ord(value) < 128:
                return f"'{value}'"
            if len(value) == 1:
                return f"'\\x{ord(value):02x}'"
            return quote_text(value, '"')
        if len(value) == 1 and ord(value) < 128 and value not in "'\\":
            return f"'{value}'"
        if len(value) == 1:
            return f"'\\u{ord(value):04x}'"
        return quote_text(value, '"')

    def expr_type(self, expr: Expr) -> TypeName | None:
        if isinstance(expr, LiteralExpr):
            return expr.kind
        if isinstance(expr, NameExpr):
            if self.scope.ranks.get(expr.name, 0) > 0:
                return None
            return self.scope.types.get(expr.name)
        if isinstance(expr, IndexExpr):
            return self.scope.types.get(expr.name)
        if isinstance(expr, UnaryExpr):
            if expr.operator == "not":
                return "logico"
            return self.expr_type(expr.operand)
        if isinstance(expr, BinaryExpr):
            if expr.operator in ("and", "or", "eq", "neq", "lt", "lte", "gt", "gte"):
                return "logico"
            if expr.operator == "div":
                return "real"
            if expr.operator in ("idiv", "mod"):
                return "entero"
            if expr.operator == "pow":
                left = self.expr_type(expr.left)
                right = self.expr_type(expr.right)
                if left == "entero" and right == "entero":
                    exponent = const_int(expr.right)
                    if exponent is not None and exponent < 0:
                        return "real"
                    return "entero"
                return "real"
            left = self.expr_type(expr.left)
            right = self.expr_type(expr.right)
            if left == "entero" and right == "entero":
                return "entero"
            if left in ("entero", "real") and right in ("entero", "real"):
                return "real"
            return None
        if isinstance(expr, CallExpr):
            if std_arity(expr.name) is not None:
                return std_return_type(expr.name, [self.expr_type(arg) for arg in expr.args])
            sig = self.sigs.get(expr.name)
            return None if sig is None else sig.result_type
        return None

    def _out_piece(self, expr: Expr) -> tuple[str, str]:
        kind = self.expr_type(expr) or "cadena"
        code = self.expression(expr)
        if kind == "logico":
            return self._bool_word(code), "text"
        if kind == "real":
            return code, "real"
        if kind == "entero":
            return code, "entero"
        if kind == "caracter" and self.lang not in ("python", "javascript", "typescript"):
            return code, "caracter"
        if kind in ("cadena", "caracter"):
            return code, "text"
        return self._to_text(code, kind), "text"

    def _print(self, pieces: list[tuple[str, str]], newline: bool) -> None:
        if not pieces:
            return
        if self.lang == "python":
            args = ", ".join(code for code, _kind in pieces)
            if len(pieces) > 1 and not newline:
                self.line(f'print({args}, sep="", end="")')
            elif len(pieces) > 1:
                self.line(f'print({args}, sep="")')
            elif not newline:
                self.line(f'print({args}, end="")')
            else:
                self.line(f"print({args})")
            return
        if self.lang in ("javascript", "typescript"):
            if len(pieces) == 1 and newline:
                self.sentence(f"console.log({pieces[0][0]})")
                return
            joined = " + ".join(f"String({code})" for code, _kind in pieces)
            if newline:
                self.sentence(f"console.log({joined})")
            else:
                self.sentence(f"process.stdout.write({joined})")
            return
        if self.lang == "cpp":
            stream = " << ".join(code for code, _kind in pieces)
            end = ' << "\\n"' if newline else ""
            self.sentence(f"std::cout << {stream}{end}")
            return
        if self.lang == "c":
            specs = {"entero": "%d", "real": "%g", "caracter": "%c", "text": "%s"}
            for index, (code, kind) in enumerate(pieces):
                last = index + 1 == len(pieces)
                end = "\\n" if newline and last else ""
                spec = specs.get(kind, "%s")
                self.sentence(f'printf("{spec}{end}", ({code}))')
            return
        write = "System.out.print" if self.lang == "java" else "Console.Write"
        write_line = "System.out.println" if self.lang == "java" else "Console.WriteLine"
        for index, (code, _kind) in enumerate(pieces):
            last = index + 1 == len(pieces)
            method = write_line if newline and last else write
            self.sentence(f"{method}({code})")

    def _bool_word(self, code: str) -> str:
        if self.lang == "python":
            return f'("Verdadero" if {code} else "Falso")'
        return f'({code} ? "Verdadero" : "Falso")'

    def _to_text(self, code: str, kind: TypeName | None) -> str:
        if kind == "logico":
            return self._bool_word(code)
        if self.lang == "python":
            return f"str({code})"
        if self.lang in ("javascript", "typescript"):
            return f"String({code})"
        if self.lang == "java":
            return f"String.valueOf({code})"
        if self.lang == "cpp":
            if kind in ("cadena", "caracter"):
                return code
            return f"std::to_string({code})"
        if self.lang == "c":
            if kind == "cadena":
                return code
            if kind == "caracter":
                self.need.add("texto_caracter")
                return f"_traza_texto_caracter({code})"
            if kind == "real":
                self.need.add("texto_real")
                return f"_traza_texto_real({code})"
            self.need.add("texto_entero")
            return f"_traza_texto_entero({code})"
        return f"({code}).ToString()"

    def _equals(
        self, temp: str, temp_type: TypeName, label: str, label_type: TypeName | None
    ) -> str:
        return self._relation("eq", temp, label, temp_type, label_type)

    def _array_declare(
        self, renamed: str, kind: TypeName, lengths: list[str], exprs: tuple[Expr, ...]
    ) -> str:
        rank = len(lengths)
        if self.lang == "python":
            return f"{renamed} = {self._py_array(kind, lengths)}"
        if self.lang == "javascript":
            return f"let {renamed} = {self._js_array(kind, lengths)}"
        if self.lang == "typescript":
            shown = self._type_name(kind, rank)
            return f"let {renamed}: {shown} = {self._js_array(kind, lengths)}"
        if self.lang == "java":
            return f"{self._type_name(kind, rank)} {renamed} = {self._java_new(kind, lengths)}"
        if self.lang == "csharp":
            return f"{self._type_name(kind, rank)} {renamed} = {self._cs_new(kind, lengths)}"
        if self.lang == "cpp":
            return f"{self._cpp_vector(kind, rank)} {renamed} = {self._cpp_new(kind, lengths)}"
        return self._c_declare(renamed, kind, lengths, exprs)

    def _array_assign(self, renamed: str, kind: TypeName, lengths: list[str]) -> str:
        if self.lang == "python":
            return f"{renamed} = {self._py_array(kind, lengths)}"
        if self.lang in ("javascript", "typescript"):
            return f"{renamed} = {self._js_array(kind, lengths)}"
        if self.lang == "java":
            return f"{renamed} = {self._java_new(kind, lengths)}"
        if self.lang == "csharp":
            return f"{renamed} = {self._cs_new(kind, lengths)}"
        if self.lang == "cpp":
            return f"{renamed} = {self._cpp_new(kind, lengths)}"
        self.need.add("calloc")
        return f"{renamed} = calloc((size_t) ({lengths[0]}), sizeof(*{renamed}))"

    def _py_array(self, kind: TypeName, lengths: list[str]) -> str:
        fill = self._fill(kind)
        expr = f"[{fill}] * ({lengths[-1]})"
        for length in reversed(lengths[:-1]):
            expr = f"[{expr} for _ in range({length})]"
        return expr

    def _js_array(self, kind: TypeName, lengths: list[str]) -> str:
        fill = self._fill(kind)
        expr = f"Array({lengths[-1]}).fill({fill})"
        for length in reversed(lengths[:-1]):
            expr = f"Array.from({{length: {length}}}, () => {expr})"
        return expr

    def _java_new(self, kind: TypeName, lengths: list[str]) -> str:
        dims = "".join(f"[{length}]" for length in lengths)
        return f"new {self._scalar(kind)}{dims}"

    def _cs_new(self, kind: TypeName, lengths: list[str]) -> str:
        scalar = self._scalar(kind)
        if len(lengths) == 1:
            return f"new {scalar}[{lengths[0]}]"
        return f"new {scalar}[{', '.join(lengths)}]"

    def _cpp_new(self, kind: TypeName, lengths: list[str]) -> str:
        current = self._scalar(kind)
        expr = ""
        for length in reversed(lengths):
            if not expr:
                expr = f"std::vector<{current}>({length})"
            else:
                expr = f"std::vector<{current}>({length}, {expr})"
            current = f"std::vector<{current}>"
        return expr

    def _c_declare(
        self, renamed: str, kind: TypeName, lengths: list[str], exprs: tuple[Expr, ...]
    ) -> str:
        scalar = self._scalar(kind)
        dims = "".join(f"[{length}]" for length in lengths)
        gap = "" if scalar.endswith("*") else " "
        text = f"{scalar}{gap}{renamed}{dims}"
        if all(const_int(item) is not None for item in exprs):
            return f"{text} = {{0}}"
        return text

    def _type_name(self, kind: TypeName, rank: int) -> str:
        if rank <= 0:
            return self._scalar(kind)
        if self.lang in ("typescript", "java"):
            return self._scalar(kind) + "[]" * rank
        if self.lang == "cpp":
            return self._cpp_vector(kind, rank)
        if self.lang == "csharp":
            return f"{self._scalar(kind)}[{',' * (rank - 1)}]"
        return "list"

    def _cpp_vector(self, kind: TypeName, rank: int) -> str:
        text = self._scalar(kind)
        for _ in range(rank):
            text = f"std::vector<{text}>"
        return text

    def _box_ts(self, kind: TypeName) -> str:
        return f"_TrazaCaja<{self._scalar(kind)}>"

    def _scalar(self, kind: TypeName) -> str:
        if self.lang in ("javascript",):
            return "number"
        table = _SCALAR.get(self.lang, _SCALAR["python"])
        return table.get(kind, "int")

    def _fill(self, kind: TypeName) -> str:
        table = _FILL.get(self.lang, _FILL["python"])
        return table.get(kind, "0")

    def _uses_box(self) -> bool:
        return self.lang in ("python", "javascript", "typescript", "java")

    def _name(self, name: str) -> str:
        if name.startswith("_traza") or name in _KEYWORDS[self.lang]:
            return f"{name}_"
        return name

    def _fresh(self, stem: str) -> str:
        self.temp_id += 1
        return f"_traza_{stem}_{self.temp_id}"

    def _comment_list(self, comments: list[SourceComment]) -> None:
        for comment in comments:
            self._comment(comment)

    def _comment(self, comment: SourceComment) -> None:
        for row in self._comment_rows(comment):
            self.line(row)

    def _comment_text(self, comment: SourceComment) -> str:
        rows = self._comment_rows(comment)
        return rows[0] if rows else self._mark()

    def _comment_rows(self, comment: SourceComment) -> list[str]:
        mark = self._mark()
        if comment.kind == "line":
            text = comment.text
            if text.startswith(" "):
                return [f"{mark}{text}"]
            return [f"{mark} {text}"]
        body = comment.text.replace("*/", "* /")
        if self.lang == "python":
            rows = body.split("\n")
            return [f"# {row}" if row else "#" for row in rows] or ["#"]
        return [f"/* {body} */"]

    def _mark(self) -> str:
        return "#" if self.lang == "python" else "//"

    def line(self, text: str) -> None:
        pad = "    " * self.level
        self.lines.append(f"{pad}{text}" if text else "")

    def sentence(self, text: str) -> None:
        if self.lang == "python":
            self.line(text)
            return
        self.line(f"{text};")

    def _assemble(self, methods: list[str], main: str, trailing: str) -> str:
        header = [f"{self._mark()} {row}" for row in _HEADER]
        support = self._support()
        body = [chunk for chunk in [*methods, main, trailing] if chunk]
        if self.lang == "java":
            class_name = self._name(self.program.algorithm.name)
            rows = header + [f"public class {class_name} {{"]
            for chunk in [support, *body]:
                if chunk:
                    rows.extend(chunk.split("\n"))
            rows.append("}")
            return "\n".join(rows) + "\n"
        if self.lang == "csharp":
            class_name = self._name(self.program.algorithm.name)
            rows = ["using System;", *header, f"class {class_name} {{"]
            for chunk in [support, *body]:
                if chunk:
                    rows.extend(chunk.split("\n"))
            rows.append("}")
            return "\n".join(rows) + "\n"
        if self.lang == "cpp":
            rows = [*self._cpp_includes(), *header]
            if support:
                rows.extend(support.split("\n"))
            for method in methods:
                rows.extend(self._prototype(method))
            rows.extend(chunk for chunk in body for chunk in chunk.split("\n"))
            text = "\n".join(rows)
            if "int main()" in text and "return 0;" not in text.split("int main()", 1)[1]:
                text = _insert_before_last_brace(text, "    return 0;")
            return text if text.endswith("\n") else text + "\n"
        if self.lang == "c":
            rows = [*self._c_includes(), *header]
            if self.need & {
                "calloc",
                "unir",
                "texto_entero",
                "texto_caracter",
                "texto_real",
                "subcadena",
            }:
                rows.append("// La memoria reservada no se libera.")
            if support:
                rows.extend(support.split("\n"))
            for method in methods:
                rows.extend(self._prototype(method))
            rows.extend(chunk for chunk in body for chunk in chunk.split("\n"))
            text = "\n".join(rows)
            if "int main(void)" in text and "return 0;" not in text.split("int main(void)", 1)[1]:
                text = _insert_before_last_brace(text, "    return 0;")
            return text if text.endswith("\n") else text + "\n"
        rows = header
        if self.lang == "python" and "math" in self.need:
            rows.append("import math")
        if "aleatorio" in self.need and self.lang == "python":
            rows.append("import random")
        if "esperar" in self.need and self.lang == "python":
            rows.append("import time")
        if support:
            rows.extend(support.split("\n"))
        for chunk in body:
            rows.extend(chunk.split("\n"))
        if self.lang == "python":
            rows.extend(["", 'if __name__ == "__main__":', "    _traza_main()"])
        elif self.lang in ("javascript", "typescript"):
            rows.append("_traza_main();")
        return "\n".join(rows) + "\n"

    def _prototype(self, method: str) -> list[str]:
        for raw in method.split("\n"):
            first = raw.strip()
            if first.endswith("{") and not first.startswith(("//", "/*", "#")):
                return [f"{first[:-1].rstrip()};"]
        return []

    def _cpp_includes(self) -> list[str]:
        rows = [
            "#include <iostream>",
            "#include <string>",
            "#include <vector>",
            "#include <cmath>",
            "#include <stdexcept>",
        ]
        return rows

    def _c_includes(self) -> list[str]:
        rows = [
            "#include <stdio.h>",
            "#include <stdlib.h>",
            "#include <string.h>",
            "#include <stdbool.h>",
            "#include <math.h>",
        ]
        if "mayusculas" in self.need or "minusculas" in self.need:
            rows.append("#include <ctype.h>")
        if "esperar" in self.need:
            rows.append("#include <time.h>")
        return rows

    def _support(self) -> str:
        if self.lang == "python":
            return self._support_python()
        if self.lang in ("javascript", "typescript"):
            return self._support_js()
        if self.lang == "java":
            return self._support_java()
        if self.lang == "cpp":
            return self._support_cpp()
        if self.lang == "c":
            return self._support_c()
        return self._support_cs()

    def _support_c(self) -> str:
        rows: list[str] = []
        if "mayusculas" in self.need or "minusculas" in self.need:
            rows.extend(self._c_duplicar())
        if "mayusculas" in self.need:
            rows.extend(self._c_case(True))
        if "minusculas" in self.need:
            rows.extend(self._c_case(False))
        if "unir" in self.need:
            rows.extend(
                [
                    "static char *_traza_unir(const char *izquierda, const char *derecha) {",
                    "    size_t largo_izq = strlen(izquierda);",
                    "    size_t largo_der = strlen(derecha);",
                    "    char *copia = malloc(largo_izq + largo_der + 1);",
                    '    if (copia == NULL) return (char *) "";',
                    "    memcpy(copia, izquierda, largo_izq);",
                    "    memcpy(copia + largo_izq, derecha, largo_der + 1);",
                    "    return copia;",
                    "}",
                ]
            )
        if "texto_entero" in self.need:
            rows.extend(
                [
                    "static char *_traza_texto_entero(int numero) {",
                    "    char *texto = malloc(32);",
                    '    if (texto == NULL) return (char *) "";',
                    '    snprintf(texto, 32, "%d", numero);',
                    "    return texto;",
                    "}",
                ]
            )
        if "texto_caracter" in self.need:
            rows.extend(
                [
                    "static char *_traza_texto_caracter(char simbolo) {",
                    "    char *texto = malloc(2);",
                    '    if (texto == NULL) return (char *) "";',
                    "    texto[0] = simbolo;",
                    "    texto[1] = '\\0';",
                    "    return texto;",
                    "}",
                ]
            )
        if "texto_real" in self.need:
            rows.extend(
                [
                    "static char *_traza_texto_real(double numero) {",
                    "    char *texto = malloc(64);",
                    '    if (texto == NULL) return (char *) "";',
                    '    snprintf(texto, 64, "%.12f", numero);',
                    "    size_t largo = strlen(texto);",
                    "    while (largo > 0 && texto[largo - 1] == '0') texto[--largo] = '\\0';",
                    "    if (largo > 0 && texto[largo - 1] == '.') texto[--largo] = '\\0';",
                    '    if (texto[0] == \'\\0\' || strcmp(texto, "-") == 0 || strcmp(texto, "-0") == 0) {',
                    "        texto[0] = '0';",
                    "        texto[1] = '\\0';",
                    "    }",
                    "    return texto;",
                    "}",
                ]
            )
        if "subcadena" in self.need:
            rows.extend(
                [
                    "static char *_traza_subcadena(const char *texto, int inicio, int fin) {",
                    f"    int desde = inicio - {self.base};",
                    "    int cantidad = fin - inicio + 1;",
                    "    if (desde < 0) desde = 0;",
                    "    if (cantidad < 0) cantidad = 0;",
                    "    char *copia = malloc((size_t) cantidad + 1);",
                    '    if (copia == NULL) return (char *) "";',
                    "    memcpy(copia, texto + desde, (size_t) cantidad);",
                    "    copia[cantidad] = '\\0';",
                    "    return copia;",
                    "}",
                ]
            )
        if "redon" in self.need:
            rows.extend(
                [
                    "static int _traza_redon(double numero) {",
                    "    return (int) (numero >= 0 ? floor(numero + 0.5) : ceil(numero - 0.5));",
                    "}",
                ]
            )
        if "aleatorio" in self.need:
            rows.extend(
                [
                    "static double _traza_aleatorio(void) {",
                    "    return (double) rand() / ((double) RAND_MAX + 1.0);",
                    "}",
                ]
            )
        if "aleatorio_rango" in self.need:
            rows.extend(
                [
                    "static int _traza_aleatorio_rango(int inicio, int fin) {",
                    "    if (fin < inicio) return inicio;",
                    "    return inicio + rand() % (fin - inicio + 1);",
                    "}",
                ]
            )
        if "numero" in self.need:
            rows.extend(
                [
                    "static double _traza_numero(const char *texto) {",
                    "    return strtod(texto, NULL);",
                    "}",
                ]
            )
        if "borrar" in self.need:
            rows.extend(
                ["static void _traza_borrar(void) {", '    printf("\\033[2J\\033[H");', "}"]
            )
        if "esperar" in self.need:
            rows.extend(
                [
                    "static void _traza_esperar(double segundos) {",
                    "    struct timespec pausa;",
                    "    pausa.tv_sec = (time_t) segundos;",
                    "    pausa.tv_nsec = (long) ((segundos - (double) pausa.tv_sec) * 1000000000.0);",
                    "    nanosleep(&pausa, NULL);",
                    "}",
                ]
            )
        return "\n".join(rows).strip("\n")

    def _c_duplicar(self) -> list[str]:
        return [
            "static char *_traza_duplicar(const char *texto) {",
            "    size_t largo = strlen(texto);",
            "    char *copia = malloc(largo + 1);",
            '    if (copia == NULL) return (char *) "";',
            "    memcpy(copia, texto, largo + 1);",
            "    return copia;",
            "}",
        ]

    def _c_case(self, upper: bool) -> list[str]:
        name = "_traza_mayusculas" if upper else "_traza_minusculas"
        letter = "toupper" if upper else "tolower"
        return [
            f"static char *{name}(const char *texto) {{",
            "    char *copia = _traza_duplicar(texto);",
            "    for (char *cursor = copia; *cursor != '\\0'; cursor++) {",
            f"        *cursor = (char) {letter}((unsigned char) *cursor);",
            "    }",
            "    return copia;",
            "}",
        ]

    def _support_python(self) -> str:
        rows: list[str] = []
        if "caja" in self.need:
            rows.extend(
                [
                    "class _TrazaCaja:",
                    "    def __init__(self, valor):",
                    "        self.valor = valor",
                    "",
                ]
            )
        if "borrar" in self.need:
            rows.extend(["def _traza_borrar():", "    print('\\033[2J\\033[H', end='')", ""])
        if "esperar" in self.need:
            rows.extend(["def _traza_esperar(segundos):", "    time.sleep(float(segundos))", ""])
        if "redon" in self.need:
            rows.extend(
                [
                    "def _traza_redon(numero):",
                    "    if numero >= 0:",
                    "        return math.floor(numero + 0.5)",
                    "    return math.ceil(numero - 0.5)",
                    "",
                ]
            )
            self.need.add("math")
        if "subcadena" in self.need:
            rows.extend(
                [
                    "def _traza_subcadena(texto, inicio, fin):",
                    f"    base = {self.base}",
                    "    return texto[inicio - base : fin - base + 1]",
                    "",
                ]
            )
        if "aleatorio" in self.need:
            rows.extend(
                [
                    "def _traza_aleatorio(inicio=None, fin=None):",
                    "    if inicio is None:",
                    "        return random.random()",
                    "    return random.randint(int(inicio), int(fin))",
                    "",
                ]
            )
        if "numero" in self.need:
            rows.extend(
                [
                    "def _traza_numero(texto):",
                    "    limpio = str(texto).strip()",
                    "    if '.' in limpio:",
                    "        return float(limpio)",
                    "    return int(limpio)",
                    "",
                ]
            )
        return "\n".join(rows).strip("\n")

    def _support_js(self) -> str:
        rows: list[str] = []
        typed = self.lang == "typescript"
        if "caja" in self.need:
            if typed:
                rows.extend(
                    [
                        "class _TrazaCaja<T> {",
                        "    valor: T;",
                        "    constructor(valor: T) { this.valor = valor; }",
                        "}",
                        "",
                    ]
                )
            else:
                rows.extend(
                    [
                        "class _TrazaCaja {",
                        "    constructor(valor) { this.valor = valor; }",
                        "}",
                        "",
                    ]
                )
        if "borrar" in self.need:
            head = "function _traza_borrar(): void {" if typed else "function _traza_borrar() {"
            rows.extend([head, "    process.stdout.write('\\x1b[2J\\x1b[H');", "}", ""])
        if "esperar" in self.need:
            head = (
                "function _traza_esperar(segundos: number): void {"
                if typed
                else "function _traza_esperar(segundos) {"
            )
            rows.extend(
                [
                    head,
                    "    const fin = Date.now() + Number(segundos) * 1000;",
                    "    while (Date.now() < fin) {}",
                    "}",
                    "",
                ]
            )
        if "redon" in self.need:
            head = (
                "function _traza_redon(numero: number): number {"
                if typed
                else "function _traza_redon(numero) {"
            )
            rows.extend(
                [
                    head,
                    "    return numero >= 0 ? Math.floor(numero + 0.5) : Math.ceil(numero - 0.5);",
                    "}",
                    "",
                ]
            )
        if "subcadena" in self.need:
            head = (
                "function _traza_subcadena(texto: string, inicio: number, fin: number): string {"
                if typed
                else "function _traza_subcadena(texto, inicio, fin) {"
            )
            rows.extend(
                [
                    head,
                    f"    const base = {self.base};",
                    "    return texto.slice(inicio - base, fin - base + 1);",
                    "}",
                    "",
                ]
            )
        if "aleatorio" in self.need:
            head = (
                "function _traza_aleatorio(inicio?: number, fin?: number): number {"
                if typed
                else "function _traza_aleatorio(inicio, fin) {"
            )
            rows.extend(
                [
                    head,
                    "    if (inicio === undefined) return Math.random();",
                    "    return Math.floor(Math.random() * (Number(fin) - Number(inicio) + 1)) + Number(inicio);",
                    "}",
                    "",
                ]
            )
        if "numero" in self.need:
            head = (
                "function _traza_numero(texto: string): number {"
                if typed
                else "function _traza_numero(texto) {"
            )
            rows.extend(
                [
                    head,
                    "    const limpio = String(texto).trim();",
                    "    return limpio.includes('.') ? Number(limpio) : parseInt(limpio, 10);",
                    "}",
                    "",
                ]
            )
        return "\n".join(rows).strip("\n")

    def _support_java(self) -> str:
        rows: list[str] = []
        if "leer" in self.need:
            rows.append(
                "    static final java.util.Scanner _traza_entrada = new java.util.Scanner(System.in);"
            )
        for kind in ("entero", "real", "logico", "caracter", "cadena"):
            if kind not in self.box_types:
                continue
            scalar = self._scalar(kind)
            box = _BOX[kind]
            rows.extend(
                [
                    f"    static final class {box} {{",
                    f"        {scalar} valor;",
                    f"        {box}({scalar} valor) {{ this.valor = valor; }}",
                    "    }",
                ]
            )
        if "borrar" in self.need:
            rows.extend(
                [
                    "    static void _traza_borrar() {",
                    '        System.out.print("\\033[2J\\033[H");',
                    "    }",
                ]
            )
        if "esperar" in self.need:
            rows.extend(
                [
                    "    static void _traza_esperar(double segundos) {",
                    "        try { Thread.sleep((long) (segundos * 1000)); }",
                    "        catch (InterruptedException error) { Thread.currentThread().interrupt(); }",
                    "    }",
                ]
            )
        if "redon" in self.need:
            rows.extend(
                [
                    "    static int _traza_redon(double numero) {",
                    "        return (int) (numero >= 0 ? Math.floor(numero + 0.5) : Math.ceil(numero - 0.5));",
                    "    }",
                ]
            )
        if "subcadena" in self.need:
            rows.extend(
                [
                    "    static String _traza_subcadena(String texto, int inicio, int fin) {",
                    f"        int base = {self.base};",
                    "        return texto.substring(inicio - base, fin - base + 1);",
                    "    }",
                ]
            )
        if "aleatorio" in self.need:
            rows.extend(
                [
                    "    static final java.util.Random _traza_azar = new java.util.Random();",
                    "    static double _traza_aleatorio() { return _traza_azar.nextDouble(); }",
                    "    static int _traza_aleatorio(int inicio, int fin) { return inicio + _traza_azar.nextInt(fin - inicio + 1); }",
                ]
            )
        if "numero" in self.need:
            rows.extend(
                [
                    "    static double _traza_numero(String texto) {",
                    "        String limpio = texto.trim();",
                    "        return Double.parseDouble(limpio);",
                    "    }",
                ]
            )
        return "\n".join(rows).strip("\n")

    def _support_cpp(self) -> str:
        rows: list[str] = []
        if "mayusculas" in self.need or "minusculas" in self.need:
            rows.append("#include <cctype>")
        if "aleatorio" in self.need:
            rows.append("#include <random>")
        if "borrar" in self.need:
            rows.extend(["void _traza_borrar() {", '    std::cout << "\\033[2J\\033[H";', "}"])
        if "esperar" in self.need:
            rows.append("#include <thread>")
            rows.append("#include <chrono>")
            rows.extend(
                [
                    "void _traza_esperar(double segundos) {",
                    "    std::this_thread::sleep_for(std::chrono::milliseconds((int) (segundos * 1000)));",
                    "}",
                ]
            )
        if "redon" in self.need:
            rows.extend(
                [
                    "int _traza_redon(double numero) {",
                    "    return (int) (numero >= 0 ? std::floor(numero + 0.5) : std::ceil(numero - 0.5));",
                    "}",
                ]
            )
        if "subcadena" in self.need:
            rows.extend(
                [
                    "std::string _traza_subcadena(const std::string& texto, int inicio, int fin) {",
                    f"    int base = {self.base};",
                    "    return texto.substr((size_t) (inicio - base), (size_t) (fin - inicio + 1));",
                    "}",
                ]
            )
        if "mayusculas" in self.need:
            rows.extend(
                [
                    "std::string _traza_mayusculas(std::string texto) {",
                    "    for (char& simbolo : texto) simbolo = (char) std::toupper((unsigned char) simbolo);",
                    "    return texto;",
                    "}",
                ]
            )
        if "minusculas" in self.need:
            rows.extend(
                [
                    "std::string _traza_minusculas(std::string texto) {",
                    "    for (char& simbolo : texto) simbolo = (char) std::tolower((unsigned char) simbolo);",
                    "    return texto;",
                    "}",
                ]
            )
        if "aleatorio" in self.need:
            rows.extend(
                [
                    "double _traza_aleatorio() {",
                    "    static std::mt19937 generador{std::random_device{}()};",
                    "    return std::uniform_real_distribution<double>(0.0, 1.0)(generador);",
                    "}",
                    "int _traza_aleatorio(int inicio, int fin) {",
                    "    static std::mt19937 generador{std::random_device{}()};",
                    "    return std::uniform_int_distribution<int>(inicio, fin)(generador);",
                    "}",
                ]
            )
        if "numero" in self.need:
            rows.extend(
                [
                    "double _traza_numero(const std::string& texto) {",
                    "    return std::stod(texto);",
                    "}",
                ]
            )
        return "\n".join(rows).strip("\n")

    def _support_cs(self) -> str:
        rows: list[str] = []
        if "borrar" in self.need:
            rows.extend(["    static void _traza_borrar() {", "        Console.Clear();", "    }"])
        if "esperar" in self.need:
            rows.extend(
                [
                    "    static void _traza_esperar(double segundos) {",
                    "        System.Threading.Thread.Sleep((int) (segundos * 1000));",
                    "    }",
                ]
            )
        if "redon" in self.need:
            rows.extend(
                [
                    "    static int _traza_redon(double numero) {",
                    "        return (int) (numero >= 0 ? Math.Floor(numero + 0.5) : Math.Ceiling(numero - 0.5));",
                    "    }",
                ]
            )
        if "subcadena" in self.need:
            rows.extend(
                [
                    "    static string _traza_subcadena(string texto, int inicio, int fin) {",
                    f"        int base = {self.base};",
                    "        return texto.Substring(inicio - base, fin - inicio + 1);",
                    "    }",
                ]
            )
        if "aleatorio" in self.need:
            rows.extend(
                [
                    "    static readonly Random _traza_azar = new Random();",
                    "    static double _traza_aleatorio() { return _traza_azar.NextDouble(); }",
                    "    static int _traza_aleatorio(int inicio, int fin) { return _traza_azar.Next(inicio, fin + 1); }",
                ]
            )
        if "numero" in self.need:
            rows.extend(
                [
                    "    static double _traza_numero(string texto) {",
                    "        return double.Parse(texto.Trim(), System.Globalization.CultureInfo.InvariantCulture);",
                    "    }",
                ]
            )
        return "\n".join(rows).strip("\n")


_HEADER = (
    "Generado por Aulivana-FCDdesign. Traduce el algoritmo; el intérprete sigue siendo quien lo ejecuta.",
    "Real se escribe como número de coma flotante. DIV y MOD truncan hacia cero.",
    "Si el índice del arreglo empieza en 1, el dato se guarda desde 0 y el acceso resta 1.",
)


def _insert_before_last_brace(text: str, insert: str) -> str:
    mark = text.rfind("\n}")
    if mark < 0:
        return text
    return text[:mark] + "\n" + insert + text[mark:]
