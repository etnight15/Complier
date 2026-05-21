"""Генерация трёхадресного кода (TAC) из AST объявлений констант (ЛР5)."""

from dataclasses import dataclass
from typing import List, Optional

from ast_semantic import AstNode


@dataclass
class TAC:
    op: str
    arg1: str
    arg2: str
    result: str

    def format_line(self, index: int) -> str:
        if self.op == "declare":
            return f"{index}. declare {self.result}, {self.arg1}"
        if self.op == "uminus":
            return f"{index}. {self.result} = -{self.arg1}"
        if self.op == "copy":
            return f"{index}. {self.result} = {self.arg1}"
        if self.op == "assign":
            return f"{index}. {self.result} = {self.arg1}"
        return f"{index}. ({self.op}, {self.arg1}, {self.arg2}, {self.result})"


def format_ir(instructions: List[TAC], title: str = "") -> str:
    lines: List[str] = []
    if title:
        lines.append(title)
    if not instructions:
        lines.append("(пусто)")
        return "\n".join(lines)
    for i, ins in enumerate(instructions, 1):
        lines.append(ins.format_line(i))
    return "\n".join(lines)


class IrGenerator:
    """Строит TAC для программы из узлов ConstDeclNode."""

    def __init__(self):
        self.instructions: List[TAC] = []
        self._temp_counter = 0

    def _new_temp(self) -> str:
        self._temp_counter += 1
        return f"t{self._temp_counter}"

    def reset(self) -> None:
        self.instructions = []
        self._temp_counter = 0

    @staticmethod
    def _declared_type(decl: AstNode) -> str:
        for child in decl.children:
            if child.node_type == "TypeNode":
                return child.attributes.get("name", "real")
        return "real"

    @staticmethod
    def _initializer(decl: AstNode) -> Optional[AstNode]:
        for child in decl.children:
            if child.node_type == "ValueNode" and child.children:
                return child.children[0]
        return None

    def _emit_initializer(self, node: AstNode) -> str:
        if node.node_type == "FloatLiteralNode":
            return node.attributes.get("value", "0")

        if node.node_type == "IdentifierNode":
            name = node.attributes.get("name", "")
            temp = self._new_temp()
            self.instructions.append(TAC("copy", name, "", temp))
            return temp

        if node.node_type == "UnaryOpNode" and node.children:
            operand = self._emit_initializer(node.children[0])
            if node.attributes.get("operator") == "-":
                temp = self._new_temp()
                self.instructions.append(TAC("uminus", operand, "", temp))
                return temp

        return "0"

    def generate(self, root: AstNode) -> List[TAC]:
        self.reset()
        for decl in root.children:
            if decl.node_type != "ConstDeclNode":
                continue
            name = decl.attributes.get("name", "")
            if not name:
                continue

            type_name = self._declared_type(decl)
            self.instructions.append(TAC("declare", type_name, "", name))

            init = self._initializer(decl)
            if not init:
                continue

            src = self._emit_initializer(init)
            if src != name:
                self.instructions.append(TAC("assign", src, "", name))

        return list(self.instructions)
