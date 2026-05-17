from enum import Enum, auto
from typing import List, Tuple


class ExprTokenType(Enum):
    IDENTIFIER = auto()
    NUMBER = auto()
    PLUS = auto()
    MINUS = auto()
    MULT = auto()
    DIV = auto()
    LPAREN = auto()
    RPAREN = auto()
    WHITESPACE = auto()
    ERROR = auto()


class ExprToken:
    def __init__(self, token_type: ExprTokenType, value: str, line: int, start_pos: int, end_pos: int):
        self.type = token_type
        self.value = value
        self.line = line
        self.start_pos = start_pos
        self.end_pos = end_pos

    def get_type_code(self) -> int:
        codes = {
            ExprTokenType.IDENTIFIER: 1,
            ExprTokenType.NUMBER: 2,
            ExprTokenType.PLUS: 3,
            ExprTokenType.MINUS: 4,
            ExprTokenType.MULT: 5,
            ExprTokenType.DIV: 6,
            ExprTokenType.LPAREN: 7,
            ExprTokenType.RPAREN: 8,
            ExprTokenType.WHITESPACE: 9,
            ExprTokenType.ERROR: 99,
        }
        return codes.get(self.type, 0)

    def get_type_name(self) -> str:
        names = {
            ExprTokenType.IDENTIFIER: "Идентификатор",
            ExprTokenType.NUMBER: "Целое число",
            ExprTokenType.PLUS: "Оператор '+'",
            ExprTokenType.MINUS: "Оператор '-'",
            ExprTokenType.MULT: "Оператор '*'",
            ExprTokenType.DIV: "Оператор '/'",
            ExprTokenType.LPAREN: "Скобка '('",
            ExprTokenType.RPAREN: "Скобка ')'",
            ExprTokenType.WHITESPACE: "Пробельный символ",
            ExprTokenType.ERROR: "Ошибка",
        }
        return names.get(self.type, "Неизвестный тип")

    def __repr__(self) -> str:
        return (
            f"ExprToken({self.type.name}, '{self.value}', "
            f"line={self.line}, pos={self.start_pos}-{self.end_pos})"
        )


class ExprScanner:
    """Лексический анализатор арифметических выражений (id, num, + - * /, скобки)."""

    def __init__(self):
        self.tokens: List[ExprToken] = []
        self.errors: List[ExprToken] = []

    def reset(self) -> None:
        self.tokens = []
        self.errors = []

    def analyze(self, text: str) -> Tuple[List[ExprToken], List[ExprToken]]:
        self.reset()
        line = 1
        pos = 1
        i = 0
        length = len(text)

        while i < length:
            ch = text[i]

            if ch == "\n":
                self.tokens.append(ExprToken(ExprTokenType.WHITESPACE, ch, line, pos, pos))
                line += 1
                pos = 1
                i += 1
                continue

            if ch.isspace():
                start_pos = pos
                start_i = i
                while i < length and text[i].isspace() and text[i] != "\n":
                    i += 1
                    pos += 1
                self.tokens.append(
                    ExprToken(ExprTokenType.WHITESPACE, text[start_i:i], line, start_pos, pos - 1)
                )
                continue

            if ch.isalpha():
                start_pos = pos
                start_i = i
                i += 1
                pos += 1
                while i < length and (text[i].isalnum()):
                    i += 1
                    pos += 1
                value = text[start_i:i]
                self.tokens.append(ExprToken(ExprTokenType.IDENTIFIER, value, line, start_pos, pos - 1))
                continue

            if ch.isdigit():
                start_pos = pos
                start_i = i
                while i < length and text[i].isdigit():
                    i += 1
                    pos += 1
                value = text[start_i:i]
                self.tokens.append(ExprToken(ExprTokenType.NUMBER, value, line, start_pos, pos - 1))
                continue

            single_ops = {
                "+": ExprTokenType.PLUS,
                "-": ExprTokenType.MINUS,
                "*": ExprTokenType.MULT,
                "/": ExprTokenType.DIV,
                "(": ExprTokenType.LPAREN,
                ")": ExprTokenType.RPAREN,
            }
            if ch in single_ops:
                token = ExprToken(single_ops[ch], ch, line, pos, pos)
                self.tokens.append(token)
                i += 1
                pos += 1
                continue

            start_pos = pos
            err = ExprToken(ExprTokenType.ERROR, ch, line, start_pos, pos)
            self.tokens.append(err)
            self.errors.append(err)
            i += 1
            pos += 1

        return self.tokens, self.errors
