from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import math
import re
from scanner import Token, TokenType

_REAL_LITERAL_LEX = re.compile(r"^(?:\d+\.\d+(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)$")


@dataclass
class AstNode:
    node_type: str
    attributes: Dict[str, str] = field(default_factory=dict)
    children: List["AstNode"] = field(default_factory=list)
    token: Optional[Token] = None

    def add_child(self, child: "AstNode"):
        self.children.append(child)


class SyntaxError:
    def __init__(self, fragment: str, line: int, pos: int, message: str):
        self.fragment = fragment
        self.line = line
        self.pos = pos
        self.message = message


class SemanticError:
    def __init__(self, fragment: str, line: int, pos: int, message: str):
        self.fragment = fragment
        self.line = line
        self.pos = pos
        self.message = message


@dataclass
class Symbol:
    name: str
    symbol_type: str
    value: Optional[float]
    token: Token


class SymbolTable:
    def __init__(self):
        self.symbols: Dict[str, Symbol] = {}

    def lookup(self, name: str) -> Optional[Symbol]:
        return self.symbols.get(name)

    def check_duplicate(self, name: str) -> bool:
        return name in self.symbols

    def declare(self, name: str, symbol_type: str, value: Optional[float], token: Token) -> bool:
        if self.check_duplicate(name):
            return False
        self.symbols[name] = Symbol(name=name, symbol_type=symbol_type, value=value, token=token)
        return True


class Parser:
    def __init__(self):
        self.tokens = []
        self.index = 0
        self.errors = []
        self.semantic_errors: List[SemanticError] = []
        self.symbol_table = SymbolTable()
        
    def reset(self):
        self.index = 0
        self.errors = []
        self.semantic_errors = []
        self.symbol_table = SymbolTable()
    
    def current(self):
        if self.index < len(self.tokens):
            return self.tokens[self.index]
        return None
    
    def next(self):
        if self.index < len(self.tokens):
            self.index += 1
            return self.current()
        return None
    
    def add_error(self, token, message):
        if token:
            self.errors.append(SyntaxError(token.value, token.line, token.start_pos, message))
        else:
            if self.tokens:
                last = self.tokens[-1]
                self.errors.append(SyntaxError("<конец>", last.line, last.end_pos + 1, message))
            else:
                self.errors.append(SyntaxError("<конец>", 1, 1, message))
    
    def match(self, token_type, value=None):
        token = self.current()
        if token and token.type == token_type and (value is None or token.value == value):
            self.next()
            return True
        return False

    def _consume_repeats(self, token_type):
        count = 0
        first = None
        while self.current() and self.current().type == token_type:
            if count == 0:
                first = self.current()
            count += 1
            self.next()
        return count, first

    def _skip_until(self, stop_types):
        while self.current() and self.current().type not in stop_types:
            self.next()

    def _parse_initializer(self) -> Optional[AstNode]:
        sign_token = None
        if self.current() and self.current().type == TokenType.SIGN:
            sign_token = self.current()
            self.next()

        token = self.current()
        if not token:
            self.add_error(None, "Отсутствует значение инициализации")
            return None

        if token.type == TokenType.NUMBER:
            literal_node = AstNode(
                node_type="FloatLiteralNode",
                attributes={"value": token.value},
                token=token,
            )
            if not _REAL_LITERAL_LEX.fullmatch(token.value):
                self.add_error(
                    token,
                    "Ожидалось вещественное число с дробной частью (формат n.m, .m или n.m с экспонентой; целое без точки недопустимо)",
                )
            self.next()
            if sign_token:
                return AstNode(
                    node_type="UnaryOpNode",
                    attributes={"operator": sign_token.value},
                    children=[literal_node],
                    token=sign_token,
                )
            return literal_node

        if token.type == TokenType.IDENTIFIER:
            id_node = AstNode(
                node_type="IdentifierNode",
                attributes={"name": token.value},
                token=token,
            )
            self.next()
            if sign_token:
                return AstNode(
                    node_type="UnaryOpNode",
                    attributes={"operator": sign_token.value},
                    children=[id_node],
                    token=sign_token,
                )
            return id_node

        self.add_error(token, "Ожидалось число или идентификатор")
        self.next()
        return None

    def _parse_const_declaration(self) -> Optional[AstNode]:
        has_error = False
        const_node = AstNode(node_type="ConstDeclNode", attributes={"modifiers": "[const]"})

        if not self.match(TokenType.KEYWORD_CONST, "const"):
            self.add_error(self.current(), "Отсутствует 'const'")
            has_error = True
            self._skip_until({TokenType.KEYWORD_CONST, TokenType.IDENTIFIER, TokenType.SEPARATOR_SEMICOLON})
            self.match(TokenType.KEYWORD_CONST, "const")

        name_token = self.current()
        if name_token and name_token.type == TokenType.IDENTIFIER:
            const_node.attributes["name"] = name_token.value
            const_node.token = name_token
            const_node.add_child(AstNode("IdentifierNode", {"name": name_token.value}, token=name_token))
            self.next()
        else:
            self.add_error(self.current(), "Отсутствует идентификатор")
            has_error = True

        if self.current() and self.current().type == TokenType.OPERATOR_ASSIGN:
            self.add_error(self.current(), "Ожидалось ':' (найдено ':=')")
            has_error = True
            self.next()

        colon_count, colon_start = self._consume_repeats(TokenType.SEPARATOR_COLON)
        if colon_count == 0:
            self.add_error(self.current(), "Отсутствует ':'")
            has_error = True
        elif colon_count > 1:
            self.add_error(colon_start, f"Повторяющийся ':' ({colon_count} раза)")
            has_error = True

        type_token = self.current()
        if type_token and type_token.type == TokenType.KEYWORD_REAL and type_token.value == "real":
            type_node = AstNode("TypeNode", {"name": type_token.value}, token=type_token)
            const_node.add_child(type_node)
            self.next()
        else:
            self.add_error(self.current(), "Отсутствует 'real'")
            has_error = True

        equal_count, equal_start = self._consume_repeats(TokenType.OPERATOR_EQUAL)
        if equal_count == 0:
            self.add_error(self.current(), "Отсутствует '='")
            has_error = True
        elif equal_count > 1:
            self.add_error(equal_start, f"Повторяющийся '=' ({equal_count} раза)")
            has_error = True

        init_node = self._parse_initializer()
        if init_node:
            const_node.add_child(AstNode("ValueNode", children=[init_node], token=init_node.token))
        else:
            has_error = True

        semicolon_count, semicolon_start = self._consume_repeats(TokenType.SEPARATOR_SEMICOLON)
        if semicolon_count == 0:
            self.add_error(self.current(), "Отсутствует ';'")
            has_error = True
        elif semicolon_count > 1:
            self.add_error(semicolon_start, f"Повторяющийся ';' ({semicolon_count} раза)")
            has_error = True

        if has_error:
            self._skip_until({TokenType.SEPARATOR_SEMICOLON, TokenType.KEYWORD_CONST})
            if self.current() and self.current().type == TokenType.SEPARATOR_SEMICOLON:
                self.next()
        return const_node

    def parse(self, tokens: List[Token]) -> Tuple[AstNode, List[SyntaxError]]:
        self.tokens = [t for t in tokens if t.type not in [TokenType.WHITESPACE, TokenType.NEWLINE]]
        self.reset()
        root = AstNode(node_type="Program")

        if not self.tokens:
            self.add_error(None, "Пустая строка")
            return root, self.errors

        while self.index < len(self.tokens):
            decl = self._parse_const_declaration()
            if decl:
                root.add_child(decl)
            else:
                self.next()

        return root, self.errors

    def _add_semantic_error(self, token: Optional[Token], message: str):
        if token:
            self.semantic_errors.append(SemanticError(token.value, token.line, token.start_pos, message))
        else:
            self.semantic_errors.append(SemanticError("<неизвестно>", 1, 1, message))

    def _resolve_expression(self, expr_node: AstNode) -> Tuple[Optional[str], Optional[float]]:
        if expr_node.node_type == "FloatLiteralNode":
            value_text = expr_node.attributes.get("value", "0")
            try:
                v = float(value_text)
            except ValueError:
                self._add_semantic_error(expr_node.token, "Некорректное числовое значение")
                return "real", None
            if not math.isfinite(v):
                self._add_semantic_error(
                    expr_node.token,
                    "Значение вызывает переполнение (бесконечность) или не является допустимым вещественным числом",
                )
                return "real", None
            return "real", v

        if expr_node.node_type == "IdentifierNode":
            name = expr_node.attributes.get("name", "")
            symbol = self.symbol_table.lookup(name)
            if not symbol:
                self._add_semantic_error(expr_node.token, f"Идентификатор '{name}' не объявлен")
                return None, None
            return symbol.symbol_type, symbol.value

        if expr_node.node_type == "UnaryOpNode":
            operator = expr_node.attributes.get("operator", "+")
            operand_type, operand_value = self._resolve_expression(expr_node.children[0]) if expr_node.children else (None, None)
            if operand_type is None:
                return None, None
            if operand_value is None:
                return operand_type, None
            if operator == "-":
                v = -operand_value
                if not math.isfinite(v):
                    self._add_semantic_error(expr_node.token, "Результат выражения не является конечным вещественным числом")
                    return operand_type, None
                return operand_type, v
            return operand_type, operand_value

        return None, None

    def analyze_semantics(self, root: AstNode) -> List[SemanticError]:
        self.semantic_errors = []
        self.symbol_table = SymbolTable()
        min_real = -1.0e308
        max_real = 1.0e308

        for node in root.children:
            if node.node_type != "ConstDeclNode":
                continue

            ident_name = node.attributes.get("name", "")
            declared_type = "real"
            for child in node.children:
                if child.node_type == "TypeNode":
                    declared_type = child.attributes.get("name", "real")
                    break
            ident_token = node.token

            duplicate_decl = False
            if ident_name:
                if self.symbol_table.check_duplicate(ident_name):
                    duplicate_decl = True
                    self._add_semantic_error(ident_token, f"Повторное объявление идентификатора '{ident_name}'")
                else:
                    self.symbol_table.declare(ident_name, declared_type, None, ident_token)

            initializer_node = None
            for child in node.children:
                if child.node_type == "ValueNode" and child.children:
                    initializer_node = child.children[0]
                    break

            if not initializer_node:
                continue

            init_type, init_value = self._resolve_expression(initializer_node)

            if init_type and declared_type != init_type:
                self._add_semantic_error(
                    initializer_node.token,
                    f"Несовместимость типов: объявлен '{declared_type}', а получен '{init_type}'",
                )

            if init_value is not None and not (min_real <= init_value <= max_real):
                self._add_semantic_error(
                    initializer_node.token,
                    f"Значение {init_value} выходит за допустимый диапазон [{min_real}; {max_real}]",
                )

            if not duplicate_decl and ident_name:
                symbol = self.symbol_table.lookup(ident_name)
                if symbol and init_value is not None:
                    symbol.value = init_value

        return self.semantic_errors

    def analyze(self, tokens: List[Token]) -> Tuple[bool, List[SyntaxError]]:
        _, syntax_errors = self.parse(tokens)
        return len(syntax_errors) == 0, syntax_errors

    def analyze_full(self, tokens: List[Token]) -> Tuple[AstNode, List[SyntaxError], List[SemanticError]]:
        root, syntax_errors = self.parse(tokens)
        if syntax_errors:
            return root, syntax_errors, []
        semantic_errors = self.analyze_semantics(root)
        return root, syntax_errors, semantic_errors

    def _format_const_decl_subtree(self, decl: AstNode) -> List[str]:
        def add_line(lines: List[str], prefix: str, is_last: bool, text: str):
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{text}")

        lines: List[str] = ["ConstDeclNode"]
        name = decl.attributes.get("name", "")
        modifiers = decl.attributes.get("modifiers", "[]")
        add_line(lines, "", False, f"modifiers: {modifiers}")
        add_line(lines, "", False, f"name: '{name}'")
        add_line(lines, "", False, "type: TypeNode")

        type_name = "real"
        value_node: Optional[AstNode] = None
        for child in decl.children:
            if child.node_type == "TypeNode":
                type_name = child.attributes.get("name", "real")
            if child.node_type == "ValueNode" and child.children:
                value_node = child.children[0]

        add_line(lines, "│   ", True, f"name: {type_name}")

        value_label = value_node.node_type if value_node else "UnknownValueNode"
        add_line(lines, "", True, f"value: {value_label}")
        value_prefix = "    "

        if value_node:
            if value_node.node_type == "FloatLiteralNode":
                add_line(lines, value_prefix, True, f"value: {value_node.attributes.get('value', '')}")
            elif value_node.node_type == "IdentifierNode":
                add_line(lines, value_prefix, True, f"name: '{value_node.attributes.get('name', '')}'")
            elif value_node.node_type == "UnaryOpNode":
                add_line(lines, value_prefix, False, f"operator: {value_node.attributes.get('operator', '+')}")
                if value_node.children:
                    operand = value_node.children[0]
                    if operand.node_type == "FloatLiteralNode":
                        add_line(lines, value_prefix, True, f"value: {operand.attributes.get('value', '')}")
                    elif operand.node_type == "IdentifierNode":
                        add_line(lines, value_prefix, True, f"name: '{operand.attributes.get('name', '')}'")
                    else:
                        add_line(lines, value_prefix, True, f"node: {operand.node_type}")

        return lines

    def format_ast(self, root: AstNode) -> str:
        program_label = (
            "Program"
            if root.node_type in ("Program", "ProgramNode")
            else (root.node_type or "Program")
        )
        declarations = [child for child in root.children if child.node_type == "ConstDeclNode"]
        if not declarations:
            return program_label

        out: List[str] = [program_label]
        n = len(declarations)
        for i, decl in enumerate(declarations):
            is_last_decl = i == n - 1
            decl_lines = self._format_const_decl_subtree(decl)
            for j, dl in enumerate(decl_lines):
                if j == 0:
                    branch = "└── " if is_last_decl else "├── "
                    out.append(f"{branch}{dl}")
                else:
                    indent = "    " if is_last_decl else "│   "
                    out.append(f"{indent}{dl}")

        return "\n".join(out)


ParserV2 = Parser