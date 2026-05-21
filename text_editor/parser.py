from typing import List, Optional, Tuple
import re

from scanner import Token, TokenType
from ast_semantic import AstNode, SemanticAnalyzer, SemanticError, AstFormatter, SymbolTable

_REAL_LITERAL_LEX = re.compile(r"^(?:\d+\.\d+(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)$")


class SyntaxError:
    def __init__(self, fragment: str, line: int, pos: int, message: str):
        self.fragment = fragment
        self.line = line
        self.pos = pos
        self.message = message


class Parser:
    def __init__(self):
        self.tokens = []
        self.index = 0
        self.errors = []

    def reset(self):
        self.index = 0
        self.errors = []

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

    def analyze_semantics(self, root: AstNode) -> List[SemanticError]:
        return SemanticAnalyzer().analyze(root)

    def analyze(self, tokens: List[Token]) -> Tuple[bool, List[SyntaxError]]:
        _, syntax_errors = self.parse(tokens)
        return len(syntax_errors) == 0, syntax_errors

    def analyze_full(
        self, tokens: List[Token]
    ) -> Tuple[AstNode, List[SyntaxError], List[SemanticError], SymbolTable]:
        root, syntax_errors = self.parse(tokens)
        if syntax_errors:
            return root, syntax_errors, [], SymbolTable()
        analyzer = SemanticAnalyzer()
        semantic_errors = analyzer.analyze(root)
        return root, syntax_errors, semantic_errors, analyzer.symbol_table

    def format_ast(self, root: AstNode) -> str:
        return AstFormatter().format(root)


ParserV2 = Parser
