from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import math

from scanner import Token


@dataclass
class AstNode:
    node_type: str
    attributes: Dict[str, str] = field(default_factory=dict)
    children: List["AstNode"] = field(default_factory=list)
    token: Optional[Token] = None

    def add_child(self, child: "AstNode"):
        self.children.append(child)


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


class SemanticAnalyzer:
    def __init__(self):
        self._errors: List[SemanticError] = []
        self.symbol_table = SymbolTable()

    def _add_error(self, token: Optional[Token], message: str):
        if token:
            self._errors.append(SemanticError(token.value, token.line, token.start_pos, message))
        else:
            self._errors.append(SemanticError("<неизвестно>", 1, 1, message))

    def _resolve_expression(self, expr_node: AstNode) -> Tuple[Optional[str], Optional[float]]:
        if expr_node.node_type == "FloatLiteralNode":
            value_text = expr_node.attributes.get("value", "0")
            try:
                v = float(value_text)
            except ValueError:
                self._add_error(expr_node.token, "Некорректное числовое значение")
                return "real", None
            if not math.isfinite(v):
                self._add_error(
                    expr_node.token,
                    "Значение вызывает переполнение (бесконечность) или не является допустимым вещественным числом",
                )
                return "real", None
            return "real", v

        if expr_node.node_type == "IdentifierNode":
            name = expr_node.attributes.get("name", "")
            symbol = self.symbol_table.lookup(name)
            if not symbol:
                self._add_error(expr_node.token, f"Идентификатор '{name}' не объявлен")
                return None, None
            return symbol.symbol_type, symbol.value

        if expr_node.node_type == "UnaryOpNode":
            operator = expr_node.attributes.get("operator", "+")
            operand_type, operand_value = (
                self._resolve_expression(expr_node.children[0]) if expr_node.children else (None, None)
            )
            if operand_type is None:
                return None, None
            if operand_value is None:
                return operand_type, None
            if operator == "-":
                v = -operand_value
                if not math.isfinite(v):
                    self._add_error(expr_node.token, "Результат выражения не является конечным вещественным числом")
                    return operand_type, None
                return operand_type, v
            return operand_type, operand_value

        return None, None

    def analyze(self, root: AstNode) -> List[SemanticError]:
        self._errors = []
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
                    self._add_error(ident_token, f"Повторное объявление идентификатора '{ident_name}'")
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
                self._add_error(
                    initializer_node.token,
                    f"Несовместимость типов: объявлен '{declared_type}', а получен '{init_type}'",
                )

            if init_value is not None and not (min_real <= init_value <= max_real):
                self._add_error(
                    initializer_node.token,
                    f"Значение {init_value} выходит за допустимый диапазон [{min_real}; {max_real}]",
                )

            if not duplicate_decl and ident_name:
                symbol = self.symbol_table.lookup(ident_name)
                if symbol and init_value is not None:
                    symbol.value = init_value

        return self._errors


class AstFormatter:
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

    def format(self, root: AstNode) -> str:
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
